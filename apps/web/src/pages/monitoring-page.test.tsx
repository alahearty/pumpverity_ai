import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  LiveSnapshot,
  Prediction,
  Pump,
  Sensor,
  SensorHealth,
  WindowPoint,
} from '@petrosense/shared-contracts'

import { LiveMonitoringPage } from './monitoring-page'

const fetchPumps = vi.hoisted(() => vi.fn())
const fetchLiveSnapshot = vi.hoisted(() => vi.fn())

vi.mock('@/services/equipment-service', () => ({ fetchPumps }))
vi.mock('@/services/monitoring-service', () => ({ fetchLiveSnapshot }))
vi.mock('@/hooks/use-monitoring-stream', () => ({
  useMonitoringStream: () => ({ status: 'connected', lastEventAt: null }),
}))
vi.mock('@/providers/auth-provider', () => ({
  useAuth: () => ({
    status: 'authenticated',
    user: {
      id: 'user-1',
      email: 'engineer@petrosense.local',
      username: 'engineer',
      full_name: 'Chinedu Okafor',
      role: 'ENGINEER',
      is_active: true,
      must_change_password: false,
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    },
    isAuthenticated: true,
    login: async () => {},
    logout: async () => {},
  }),
}))

const SENSOR: Sensor = {
  id: 'sensor-1',
  sensor_code: 'VIB-01',
  pump_id: 'pump-1',
  pump_code: 'LAB-PUMP-01',
  sensor_type: 'VIBRATION',
  manufacturer: null,
  model_name: null,
  mounting_axis: 'RADIAL_X',
  mounting_position: 'Drive-end bearing housing',
  sampling_rate_hz: 2048,
  is_active: true,
  installed_at: '2026-11-16T10:00:00Z',
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
}

const PUMP: Pump = {
  id: 'pump-1',
  pump_code: 'LAB-PUMP-01',
  name: 'Laboratory Centrifugal Pump',
  pump_type: 'CENTRIFUGAL',
  location: 'Thermofluids Laboratory',
  rated_speed_rpm: 2900,
  default_regime: null,
  status: 'ACTIVE',
  notes: null,
  sensors: [SENSOR],
  registered_at: '2026-11-16T10:00:00Z',
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
}

const HEALTH: SensorHealth = {
  sensor_id: 'sensor-1',
  sensor_code: 'VIB-01',
  pump_id: 'pump-1',
  pump_code: 'LAB-PUMP-01',
  sensor_type: 'VIBRATION',
  is_active: true,
  sampling_rate_hz: 2048,
  total_windows: 2,
  valid_windows: 2,
  invalid_windows: 0,
  missing_window_gaps: 0,
  last_reading_at: '2026-11-16T12:00:02Z',
  last_valid_reading_at: '2026-11-16T12:00:02Z',
  freshness_seconds: 15,
  latest_quality: 'VALID',
  data_quality: 'VALID',
  sampling_status: 'RECENT',
  connection_state: 'NO_LIVE_CHANNEL',
  latest_rms: 0.035,
  latest_peak_abs: 0.05,
  latest_scenario: 'normal',
  provenance: 'SIMULATED',
  latest_validation_issues: [],
}

const FAULT_PREDICTION: Prediction = {
  id: 'prediction-1',
  event_id: 'pred-event-1',
  pump_id: 'pump-1',
  pump_code: 'LAB-PUMP-01',
  sensor_id: 'sensor-1',
  sensor_code: 'VIB-01',
  session_id: 'session-1',
  signal_window_id: 'window-1',
  model: {
    id: 'model-1',
    model_code: 'petrosense-linear',
    name: 'PUMPVERITY lightweight linear',
    version: '0.1.0',
    runtime: 'LINEAR_JSON',
  },
  operating_regime: null,
  decision: 'FAULT',
  data_quality: 'VALID',
  equipment_condition: 'FAULT',
  decision_score: 0.92,
  uncertainty_score: 0.08,
  explanation: 'Synthetic model accepted a FAULT decision.',
  latency_ms: 0.3,
  inferred_at: '2026-11-16T12:00:00Z',
  data_provenance: 'SIMULATED',
  created_at: '2026-11-16T12:00:01Z',
  window_start: '2026-11-16T11:59:59Z',
  window_end: '2026-11-16T12:00:00Z',
  window_quality: 'VALID',
  sample_count: 2048,
  features: { rms: 0.09 },
  scenario: 'imbalance',
}

const WINDOW: WindowPoint = {
  window_id: 'window-1',
  session_id: 'session-1',
  pump_id: 'pump-1',
  pump_code: 'LAB-PUMP-01',
  sensor_id: 'sensor-1',
  sensor_code: 'VIB-01',
  window_index: 0,
  window_start: '2026-11-16T12:00:01Z',
  window_end: '2026-11-16T12:00:02Z',
  quality_status: 'VALID',
  data_provenance: 'SIMULATED',
  scenario: 'normal',
  sample_count: 2048,
  rms: 0.035,
  peak_abs: 0.05,
  validation_issue_codes: [],
}

function snapshot(overrides: Partial<LiveSnapshot> = {}): LiveSnapshot {
  return {
    pump_id: 'pump-1',
    pump_code: 'LAB-PUMP-01',
    pump_name: 'Laboratory Centrifugal Pump',
    sensor_id: 'sensor-1',
    sensor_code: 'VIB-01',
    sensor_type: 'VIBRATION',
    latest_window: {
      ...WINDOW,
      sampling_rate_hz: 2048,
      units: 'g',
      waveform: null,
      validation_summary: { metrics: { rms: 0.035, units: 'g' } },
    },
    recent_windows: [WINDOW],
    latest_prediction: null,
    session: {
      id: 'session-1',
      pump_id: 'pump-1',
      pump_code: 'LAB-PUMP-01',
      sensor_id: 'sensor-1',
      sensor_code: 'VIB-01',
      scenario: 'normal',
      status: 'COMPLETED',
      data_provenance: 'SIMULATED',
      sampling_rate_hz: 2048,
      started_at: '2026-11-16T12:00:00Z',
      ended_at: '2026-11-16T12:00:03Z',
      window_count: 2,
      started_by_name: 'Chinedu Okafor',
    },
    sensor_health: HEALTH,
    equipment_condition: null,
    condition_available: false,
    data_quality: 'VALID',
    edge_connectivity: null,
    edge_note: 'No live edge channel.',
    data_mode: 'SIMULATED_REPLAY',
    buffering_state: null,
    generated_at: '2026-11-16T12:00:03Z',
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LiveMonitoringPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('LiveMonitoringPage', () => {
  beforeEach(() => {
    fetchPumps.mockReset()
    fetchLiveSnapshot.mockReset()
    fetchPumps.mockResolvedValue({ items: [PUMP], total: 1, page: 1, page_size: 100 })
    fetchLiveSnapshot.mockResolvedValue(snapshot())
  })

  it('shows persisted monitoring state without inventing a condition', async () => {
    renderPage()

    expect(await screen.findByText('0.0350 g')).toBeInTheDocument()
    expect(screen.getByText('Live stream connected')).toBeInTheDocument()
    expect(screen.getAllByText('Not inferred').length).toBeGreaterThan(0)
    expect(screen.getAllByText('No live channel').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Valid signal').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Normal').length).toBeGreaterThan(0)
    expect(screen.getByText(/Latest signal waveform/i)).toBeInTheDocument()
  })

  it('pauses chart rendering with an explicit state', async () => {
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('0.0350 g')
    await user.click(screen.getByRole('button', { name: /pause chart/i }))
    expect(screen.getByText('Chart paused')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /resume chart/i }))
    expect(screen.queryByText('Chart paused')).not.toBeInTheDocument()
  })

  it('shows a current model decision when one exists', async () => {
    fetchLiveSnapshot.mockResolvedValue(
      snapshot({
        latest_prediction: FAULT_PREDICTION,
        condition_available: true,
        equipment_condition: 'FAULT',
      }),
    )
    renderPage()

    expect(await screen.findByText('Latest AI decision')).toBeInTheDocument()
    expect(await screen.findByText('0.9200')).toBeInTheDocument()
    expect(screen.getAllByText('Fault').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/PUMPVERITY lightweight linear v0.1.0/).length).toBeGreaterThan(0)
    expect(screen.getByText('Open full AI analysis')).toBeInTheDocument()
  })

  it('suppresses the waveform when the latest window is sensor-invalid', async () => {
    const invalidWindow = {
      ...snapshot().latest_window!,
      quality_status: 'SENSOR_INVALID' as const,
      waveform: null,
      rms: null,
      peak_abs: null,
      validation_issue_codes: ['sensor_disconnected'],
      validation_summary: {
        issues: [{ code: 'sensor_disconnected', message: 'Disconnected' }],
      },
    }
    fetchLiveSnapshot.mockResolvedValue(
      snapshot({
        latest_window: invalidWindow,
        data_quality: 'SENSOR_INVALID',
        sensor_health: {
          ...HEALTH,
          latest_quality: 'SENSOR_INVALID',
          data_quality: 'SENSOR_INVALID',
          sampling_status: 'SENSOR_INVALID',
          invalid_windows: 1,
          latest_validation_issues: [
            { code: 'sensor_disconnected', message: 'Disconnected' },
          ],
        },
      }),
    )
    renderPage()

    expect(
      (await screen.findAllByText(/Latest window is sensor-invalid/i)).length,
    ).toBeGreaterThan(0)
    expect(screen.getByText('No current valid waveform')).toBeInTheDocument()
    expect(screen.getByText('sensor_disconnected')).toBeInTheDocument()
  })
})
