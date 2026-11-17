import type {
  Alert,
  AlertCategory,
  AlertDetail,
  AlertReview,
  AlertReviewCreate,
  AlertSeverity,
  AlertStatus,
  Page,
} from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export interface AlertQuery {
  page?: number
  page_size?: number
  status?: AlertStatus
  category?: AlertCategory
  severity?: AlertSeverity
  pump_id?: string
  sensor_id?: string
  assigned_to?: string
}

export function fetchAlerts(query: AlertQuery = {}): Promise<Page<Alert>> {
  const params = new URLSearchParams({
    page: String(query.page ?? 1),
    page_size: String(query.page_size ?? 25),
  })
  if (query.status) params.set('status', query.status)
  if (query.category) params.set('category', query.category)
  if (query.severity) params.set('severity', query.severity)
  if (query.pump_id) params.set('pump_id', query.pump_id)
  if (query.sensor_id) params.set('sensor_id', query.sensor_id)
  if (query.assigned_to) params.set('assigned_to', query.assigned_to)
  return apiFetch<Page<Alert>>(`/alerts?${params.toString()}`)
}

export function fetchAlert(alertId: string): Promise<AlertDetail> {
  return apiFetch<AlertDetail>(`/alerts/${alertId}`)
}

export function acknowledgeAlert(alertId: string): Promise<AlertDetail> {
  return apiFetch<AlertDetail>(`/alerts/${alertId}/acknowledge`, {
    method: 'POST',
  })
}

export function createAlertReview(
  payload: AlertReviewCreate,
): Promise<AlertReview> {
  return apiFetch<AlertReview>('/alert-reviews', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
