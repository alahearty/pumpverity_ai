import { apiFetch } from '@/lib/api'

export type DemoExpectedOutcome = 'NORMAL' | 'FAULT' | 'UNCERTAIN' | 'SENSOR_INVALID'

export interface DemoPreset {
  code: string
  label: string
  description: string
  expected_outcome: DemoExpectedOutcome
  scenario: string
  custom_amplitude_g: number | null
}

export interface DemoDriverHeartbeat {
  preset: string | null
  pump_code: string | null
  session_id: string | null
  windows_streamed: number
  last_decision: string | null
  message: string | null
}

export interface DemoControlState {
  enabled: boolean
  preset: string
  pump_code: string | null
  paused: boolean
  updated_at: string
  updated_by: string | null
  driver_online: boolean
  driver: DemoDriverHeartbeat | null
  driver_heartbeat_at: string | null
  presets: DemoPreset[]
}

export function fetchDemoControl(): Promise<DemoControlState> {
  return apiFetch<DemoControlState>('/demo/control')
}

export function updateDemoControl(payload: {
  preset?: string
  paused?: boolean
}): Promise<DemoControlState> {
  return apiFetch<DemoControlState>('/demo/control', {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}
