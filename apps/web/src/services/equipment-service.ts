import type {
  OperatingRegime,
  Page,
  Pump,
  PumpCreate,
  PumpStatus,
  PumpType,
  PumpUpdate,
  Sensor,
  SensorRegister,
  SensorUpdate,
} from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export interface PumpQuery {
  page?: number
  page_size?: number
  q?: string
  status?: PumpStatus
  pump_type?: PumpType
}

export interface SensorQuery {
  page?: number
  page_size?: number
  q?: string
  pump_id?: string
  is_active?: boolean
}

function pageParams(page = 1, pageSize = 25): URLSearchParams {
  return new URLSearchParams({ page: String(page), page_size: String(pageSize) })
}

export function fetchPumps(query: PumpQuery = {}): Promise<Page<Pump>> {
  const params = pageParams(query.page, query.page_size)
  if (query.q?.trim()) params.set('q', query.q.trim())
  if (query.status) params.set('status', query.status)
  if (query.pump_type) params.set('pump_type', query.pump_type)
  return apiFetch<Page<Pump>>(`/pumps?${params.toString()}`)
}

export function fetchPump(pumpId: string): Promise<Pump> {
  return apiFetch<Pump>(`/pumps/${pumpId}`)
}

export function createPump(payload: PumpCreate): Promise<Pump> {
  return apiFetch<Pump>('/pumps', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updatePump(pumpId: string, payload: PumpUpdate): Promise<Pump> {
  return apiFetch<Pump>(`/pumps/${pumpId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function fetchSensors(query: SensorQuery = {}): Promise<Page<Sensor>> {
  const params = pageParams(query.page, query.page_size)
  if (query.q?.trim()) params.set('q', query.q.trim())
  if (query.pump_id) params.set('pump_id', query.pump_id)
  if (query.is_active !== undefined) params.set('is_active', String(query.is_active))
  return apiFetch<Page<Sensor>>(`/sensors?${params.toString()}`)
}

export function createSensor(payload: SensorRegister): Promise<Sensor> {
  return apiFetch<Sensor>('/sensors', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function updateSensor(sensorId: string, payload: SensorUpdate): Promise<Sensor> {
  return apiFetch<Sensor>(`/sensors/${sensorId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function fetchOperatingRegimes(): Promise<OperatingRegime[]> {
  return apiFetch<OperatingRegime[]>('/operating-regimes')
}
