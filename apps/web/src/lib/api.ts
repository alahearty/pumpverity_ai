import type {
  ApiErrorBody,
  ApiErrorDetail,
  AuthSession,
  LoginRequest,
} from '@petrosense/shared-contracts'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

export class ApiClientError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null
  readonly details: ApiErrorDetail[]

  constructor(
    message: string,
    status: number,
    code: string,
    requestId: string | null = null,
    details: ApiErrorDetail[] = [],
  ) {
    super(message)
    this.name = 'ApiClientError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.details = details
  }
}

let accessToken: string | null = null
let refreshPromise: Promise<AuthSession> | null = null
let sessionListener: ((session: AuthSession | null) => void) | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function setSessionListener(listener: ((session: AuthSession | null) => void) | null): void {
  sessionListener = listener
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204) return undefined as T
  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = null
    }
  }
  if (!response.ok) {
    const body = payload as ApiErrorBody | null
    const error = body?.error
    throw new ApiClientError(
      error?.message ?? `Request failed with status ${response.status}.`,
      response.status,
      error?.code ?? 'HTTP_ERROR',
      error?.request_id ?? response.headers.get('X-Request-ID'),
      error?.details ?? [],
    )
  }
  return payload as T
}

function buildHeaders(init: RequestInit): Headers {
  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  return headers
}

async function rawRequest(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${API_BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
    headers: buildHeaders(init),
  })
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  options: { retryAfterRefresh?: boolean } = {},
): Promise<T> {
  const retryAfterRefresh = options.retryAfterRefresh ?? true
  let response = await rawRequest(path, init)

  if (response.status === 401 && retryAfterRefresh && !path.startsWith('/auth/')) {
    await refreshSession()
    response = await rawRequest(path, init)
  }

  return parseResponse<T>(response)
}

export async function loginWithPassword(payload: LoginRequest): Promise<AuthSession> {
  const response = await rawRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  const session = await parseResponse<AuthSession>(response)
  setAccessToken(session.access_token)
  sessionListener?.(session)
  return session
}

export async function refreshSession(): Promise<AuthSession> {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          credentials: 'include',
          headers: { Accept: 'application/json' },
        })
        const session = await parseResponse<AuthSession>(response)
        setAccessToken(session.access_token)
        sessionListener?.(session)
        return session
      } catch (error) {
        setAccessToken(null)
        sessionListener?.(null)
        throw error
      } finally {
        refreshPromise = null
      }
    })()
  }
  return refreshPromise
}

export interface SseEvent {
  id?: string
  event: string
  data: unknown
}

function parseSseChunk(chunk: string, onEvent: (event: SseEvent) => void): void {
  let id: string | undefined
  let eventName = 'message'
  const dataLines: string[] = []
  for (const rawLine of chunk.split('\n')) {
    const line = rawLine.endsWith('\r') ? rawLine.slice(0, -1) : rawLine
    if (!line || line.startsWith(':')) continue
    const separator = line.indexOf(':')
    const field = separator >= 0 ? line.slice(0, separator) : line
    const value = separator >= 0 ? line.slice(separator + 1).replace(/^ /, '') : ''
    if (field === 'id') id = value
    else if (field === 'event') eventName = value
    else if (field === 'data') dataLines.push(value)
  }
  if (dataLines.length === 0) return
  const rawData = dataLines.join('\n')
  let data: unknown = rawData
  try {
    data = JSON.parse(rawData)
  } catch {
    data = rawData
  }
  onEvent({ id, event: eventName, data })
}

export async function streamSse(
  path: string,
  onEvent: (event: SseEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const connect = () =>
    fetch(`${API_BASE_URL}${path}`, {
      headers: {
        Accept: 'text/event-stream',
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      credentials: 'include',
      signal,
    })

  let response = await connect()
  if (response.status === 401) {
    await refreshSession()
    response = await connect()
  }
  if (!response.ok) {
    await parseResponse<never>(response)
    throw new ApiClientError('The live stream could not be opened.', response.status, 'STREAM_ERROR')
  }
  if (!response.body) {
    throw new ApiClientError('Streaming is not supported by this browser.', 0, 'STREAM_UNAVAILABLE')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    buffer = buffer.replace(/\r\n/g, '\n')
    let boundary = buffer.indexOf('\n\n')
    while (boundary >= 0) {
      const chunk = buffer.slice(0, boundary)
      buffer = buffer.slice(boundary + 2)
      parseSseChunk(chunk, onEvent)
      boundary = buffer.indexOf('\n\n')
    }
  }
}


export async function downloadAuthenticatedFile(
  path: string,
  filename: string,
): Promise<void> {
  let response = await rawRequest(path, { headers: { Accept: "application/json" } })
  if (response.status === 401) {
    await refreshSession()
    response = await rawRequest(path, { headers: { Accept: "application/json" } })
  }
  if (!response.ok) {
    await parseResponse<never>(response)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  document.body.append(anchor)
  anchor.click()
  anchor.remove()
  URL.revokeObjectURL(url)
}

export async function logoutSession(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
  } finally {
    setAccessToken(null)
    sessionListener?.(null)
  }
}

