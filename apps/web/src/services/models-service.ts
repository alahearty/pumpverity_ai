import type {
  ModelDetail,
  ModelRuntime,
  ModelStatus,
  ModelVersion,
  Page,
} from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export interface ModelQuery {
  page?: number
  page_size?: number
  status?: ModelStatus
  runtime?: ModelRuntime
  q?: string
}

export function fetchModels(query: ModelQuery = {}): Promise<Page<ModelVersion>> {
  const params = new URLSearchParams({
    page: String(query.page ?? 1),
    page_size: String(query.page_size ?? 25),
  })
  if (query.status) params.set('status', query.status)
  if (query.runtime) params.set('runtime', query.runtime)
  if (query.q?.trim()) params.set('q', query.q.trim())
  return apiFetch<Page<ModelVersion>>(`/models?${params.toString()}`)
}

export function fetchModel(modelId: string): Promise<ModelDetail> {
  return apiFetch<ModelDetail>(`/models/${modelId}`)
}

export function fetchActiveModel(): Promise<ModelVersion | null> {
  return apiFetch<ModelVersion | null>('/models/active')
}

export function validateModel(modelId: string): Promise<ModelVersion> {
  return apiFetch<ModelVersion>(`/models/${modelId}/validate`, { method: 'POST' })
}

export function activateModel(modelId: string): Promise<ModelVersion> {
  return apiFetch<ModelVersion>(`/models/${modelId}/activate`, { method: 'POST' })
}

export function rollbackModel(): Promise<ModelVersion> {
  return apiFetch<ModelVersion>('/models/rollback', { method: 'POST' })
}
