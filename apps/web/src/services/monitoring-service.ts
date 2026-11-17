import type {
  LiveSnapshot,
  MonitoringOverview,
  SensorHealth,
} from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export function fetchMonitoringOverview(): Promise<MonitoringOverview> {
  return apiFetch<MonitoringOverview>('/monitoring/overview')
}

export function fetchLiveSnapshot(
  pumpId: string,
  sensorId?: string,
  limit = 25,
): Promise<LiveSnapshot> {
  const params = new URLSearchParams({
    pump_id: pumpId,
    limit: String(limit),
  })
  if (sensorId) params.set('sensor_id', sensorId)
  return apiFetch<LiveSnapshot>(`/monitoring/live?${params.toString()}`)
}

export function fetchSensorHealth(pumpId?: string): Promise<SensorHealth[]> {
  const params = new URLSearchParams()
  if (pumpId) params.set('pump_id', pumpId)
  const suffix = params.toString()
  return apiFetch<SensorHealth[]>(`/sensors/health${suffix ? `?${suffix}` : ''}`)
}
