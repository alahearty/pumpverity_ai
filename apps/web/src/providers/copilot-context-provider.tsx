import type {
  CopilotAction,
  CopilotActionType,
  CopilotPageContext,
  Role,
} from '@petrosense/shared-contracts'
import {
  createContext,
  use,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { useAuth } from '@/providers/auth-provider'
import { routeMeta } from '@/routes/navigation'

type PagePatch = Partial<
  Omit<CopilotPageContext, 'route' | 'screenName'>
>

interface PageFields extends PagePatch {
  pathname: string
}

export interface CopilotExternalRequest {
  id: number
  kind: 'prompt' | 'tool'
  prompt?: string
  toolName?: string
  arguments?: Record<string, unknown>
}

interface CopilotContextValue {
  context: CopilotPageContext
  setPageContext: (patch: PagePatch) => void
  dispatchAction: (action: CopilotAction) => boolean
  externalRequest: CopilotExternalRequest | null
  clearExternalRequest: () => void
  requestPrompt: (prompt: string) => void
  requestTool: (toolName: string, args?: Record<string, unknown>) => void
}

const CopilotContext = createContext<CopilotContextValue | null>(null)

const ROUTE_ROLES: Record<string, Role[]> = {
  '/dashboard': ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER', 'REVIEWER'],
  '/monitoring': ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER'],
  '/analysis': ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER'],
  '/alerts': ['ADMINISTRATOR', 'ENGINEER', 'REVIEWER'],
  '/pumps': ['ADMINISTRATOR', 'ENGINEER'],
  '/sensors': ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER'],
  '/history': ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER', 'REVIEWER'],
  '/reports': ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER', 'REVIEWER'],
  '/models': ['ADMINISTRATOR', 'RESEARCHER'],
  '/settings': ['ADMINISTRATOR', 'ENGINEER', 'RESEARCHER', 'REVIEWER'],
  '/users': ['ADMINISTRATOR'],
}

const SAFE_UUID = /^[0-9a-fA-F-]{8,36}$/

function canOpen(role: Role | undefined, path: string): boolean {
  if (!role) return false
  if (role === 'ADMINISTRATOR') return true
  return ROUTE_ROLES[path]?.includes(role) ?? false
}

function idPayload(payload: Record<string, unknown>, key: string): string | null {
  const value = payload[key]
  return typeof value === 'string' && SAFE_UUID.test(value) ? value : null
}

function queryString(values: Record<string, string | null | undefined>): string {
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(values)) {
    if (value) params.set(key, value)
  }
  const suffix = params.toString()
  return suffix ? `?${suffix}` : ''
}

function isActionType(value: unknown): value is CopilotActionType {
  return (
    value === 'NAVIGATE_TO_SCREEN' ||
    value === 'SELECT_PUMP' ||
    value === 'OPEN_ALERT_DETAILS' ||
    value === 'HIGHLIGHT_SENSOR' ||
    value === 'OPEN_HISTORICAL_TRENDS' ||
    value === 'SET_MONITORING_TIME_RANGE' ||
    value === 'OPEN_REPORT' ||
    value === 'SHOW_CONFIRMATION_DIALOG'
  )
}

function CopilotContextProvider({ children }: { children: ReactNode }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()
  const userRole = user?.role
  const [pageFields, setPageFields] = useState<PageFields | null>(null)
  const [externalRequest, setExternalRequest] =
    useState<CopilotExternalRequest | null>(null)
  const meta = routeMeta(location.pathname)

  const setPageContext = useCallback(
    (patch: PagePatch) => {
      setPageFields((current) => ({
        ...(current?.pathname === location.pathname ? current : {}),
        ...patch,
        pathname: location.pathname,
      }))
    },
    [location.pathname],
  )

  const context = useMemo<CopilotPageContext>(() => {
    const activePage: PagePatch =
      pageFields && pageFields.pathname === location.pathname ? pageFields : {}
    return {
      route: `${location.pathname}${location.search}`,
      screenName: meta.title,
      selectedPumpId: activePage.selectedPumpId ?? null,
      selectedSensorId: activePage.selectedSensorId ?? null,
      selectedAlertId: activePage.selectedAlertId ?? null,
      activeModelVersion: activePage.activeModelVersion ?? null,
      operatingRegime: activePage.operatingRegime ?? null,
      monitoringMode: activePage.monitoringMode ?? 'SIMULATED',
      connectivityStatus:
        activePage.connectivityStatus ?? 'NO_LIVE_CHANNEL',
    }
  }, [location.pathname, location.search, meta.title, pageFields])

  const requestPrompt = useCallback((prompt: string) => {
    setExternalRequest({ id: Date.now(), kind: 'prompt', prompt })
  }, [])

  const requestTool = useCallback(
    (toolName: string, args: Record<string, unknown> = {}) => {
      setExternalRequest({
        id: Date.now(),
        kind: 'tool',
        toolName,
        arguments: args,
      })
    },
    [],
  )

  const clearExternalRequest = useCallback(() => {
    setExternalRequest(null)
  }, [])

  const dispatchAction = useCallback(
    (action: CopilotAction): boolean => {
      if (!action || !isActionType(action.type)) return false
      const payload =
        action.payload && typeof action.payload === 'object' ? action.payload : {}
      switch (action.type) {
        case 'NAVIGATE_TO_SCREEN': {
          const path = payload.path
          if (typeof path !== 'string' || path.startsWith('//')) return false
          if (!path.startsWith('/') || !ROUTE_ROLES[path] || !canOpen(userRole, path)) {
            return false
          }
          const pumpId = idPayload(payload, 'pumpId')
          if (path === '/monitoring' && pumpId) {
            navigate(
              `${path}${queryString({
                pump_id: pumpId,
                sensor_id: idPayload(payload, 'sensorId'),
              })}`,
            )
          } else {
            navigate(path)
          }
          return true
        }
        case 'SELECT_PUMP': {
          const pumpId = idPayload(payload, 'pumpId')
          if (!pumpId || !canOpen(userRole, '/monitoring')) return false
          navigate(
            `/monitoring${queryString({
              pump_id: pumpId,
              sensor_id: idPayload(payload, 'sensorId'),
            })}`,
          )
          return true
        }
        case 'OPEN_ALERT_DETAILS': {
          const alertId = idPayload(payload, 'alertId')
          if (!alertId || !canOpen(userRole, '/alerts')) return false
          navigate(`/alerts/${alertId}`)
          return true
        }
        case 'HIGHLIGHT_SENSOR': {
          if (!canOpen(userRole, '/sensors')) return false
          const pumpId = idPayload(payload, 'pumpId')
          const sensorId = idPayload(payload, 'sensorId')
          if (!pumpId && !sensorId) return false
          navigate(
            `/sensors${queryString({
              pump_id: pumpId,
              sensor_id: sensorId,
            })}`,
          )
          return true
        }
        case 'OPEN_HISTORICAL_TRENDS': {
          if (!canOpen(userRole, '/history')) return false
          const pumpId = idPayload(payload, 'pumpId')
          navigate(
            `/history${queryString({
              pump_id: pumpId,
              sensor_id: idPayload(payload, 'sensorId'),
            })}`,
          )
          return true
        }
        case 'SET_MONITORING_TIME_RANGE': {
          if (!canOpen(userRole, '/history')) return false
          const raw = payload.limit
          const limit = typeof raw === 'number' ? Math.min(100, Math.max(5, raw)) : 50
          navigate(`/history?limit=${limit}`)
          return true
        }
        case 'OPEN_REPORT': {
          if (!canOpen(userRole, '/reports')) return false
          const reportId = idPayload(payload, 'reportId')
          if (!reportId) return false
          navigate(`/reports?reportId=${reportId}`)
          return true
        }
        case 'SHOW_CONFIRMATION_DIALOG':
          return true
        default:
          return false
      }
    },
    [navigate, userRole],
  )

  const value = useMemo<CopilotContextValue>(
    () => ({
      context,
      setPageContext,
      dispatchAction,
      externalRequest,
      clearExternalRequest,
      requestPrompt,
      requestTool,
    }),
    [
      context,
      setPageContext,
      dispatchAction,
      externalRequest,
      clearExternalRequest,
      requestPrompt,
      requestTool,
    ],
  )

  return <CopilotContext value={value}>{children}</CopilotContext>
}

export function useCopilot(): CopilotContextValue {
  const context = use(CopilotContext)
  if (!context) throw new Error('useCopilot must be used within CopilotContextProvider')
  return context
}

export function useCopilotOptional(): CopilotContextValue | null {
  return use(CopilotContext)
}

export function useCopilotPageContext(patch: PagePatch): void {
  const setPageContext = use(CopilotContext)?.setPageContext
  const serialized = JSON.stringify(patch)
  useEffect(() => {
    if (setPageContext) {
      setPageContext(JSON.parse(serialized) as PagePatch)
    }
  }, [serialized, setPageContext])
}

export { CopilotContextProvider }




