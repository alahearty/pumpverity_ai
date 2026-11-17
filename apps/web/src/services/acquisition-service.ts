import type {
  AcquisitionSession,
  Page,
  Provenance,
  SessionStatus,
} from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export interface SessionQuery {
  page?: number
  page_size?: number
  pump_id?: string
  status?: SessionStatus
  provenance?: Provenance
  scenario?: string
}

export function fetchAcquisitionSessions(
  query: SessionQuery = {},
): Promise<Page<AcquisitionSession>> {
  const params = new URLSearchParams({
    page: String(query.page ?? 1),
    page_size: String(query.page_size ?? 25),
  })
  if (query.pump_id) params.set('pump_id', query.pump_id)
  if (query.status) params.set('status', query.status)
  if (query.provenance) params.set('provenance', query.provenance)
  if (query.scenario?.trim()) params.set('scenario', query.scenario.trim())
  return apiFetch<Page<AcquisitionSession>>(`/acquisition-sessions?${params.toString()}`)
}
