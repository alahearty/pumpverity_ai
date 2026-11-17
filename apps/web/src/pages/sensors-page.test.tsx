import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Pump, Sensor, SensorHealth } from '@petrosense/shared-contracts'

import { SensorsPage } from './sensors-page'

const fetchSensors = vi.hoisted(() => vi.fn())
const fetchPumps = vi.hoisted(() => vi.fn())
const createSensor = vi.hoisted(() => vi.fn())
const updateSensor = vi.hoisted(() => vi.fn())
const fetchSensorHealth = vi.hoisted(() => vi.fn())

vi.mock('@/services/equipment-service', () => ({
  fetchSensors,
  fetchPumps,
  createSensor,
  updateSensor,
}))

vi.mock('@/services/monitoring-service', () => ({
  fetchSensorHealth,
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
  manufacturer: 'Research Instruments',
  model_name: 'ACC-100',
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
  total_windows: 5,
  valid_windows: 4,
  invalid_windows: 1,
  missing_window_gaps: 1,
  last_reading_at: '2026-11-16T12:00:03Z',
  last_valid_reading_at: '2026-11-16T12:00:02Z',
  freshness_seconds: 30,
  latest_quality: 'SENSOR_INVALID',
  data_quality: 'SENSOR_INVALID',
  sampling_status: 'SENSOR_INVALID',
  connection_state: 'NO_LIVE_CHANNEL',
  latest_rms: 0.0231,
  latest_peak_abs: 0.04,
  latest_scenario: 'sensor_disconnect',
  provenance: 'SIMULATED',
  latest_validation_issues: [{ code: 'sensor_disconnected', message: 'Disconnected' }],
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SensorsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('SensorsPage', () => {
  beforeEach(() => {
    fetchSensors.mockReset()
    fetchPumps.mockReset()
    createSensor.mockReset()
    updateSensor.mockReset()
    fetchSensorHealth.mockReset()
    fetchPumps.mockResolvedValue({ items: [PUMP], total: 1, page: 1, page_size: 100 })
  })

  it('shows real diagnostics from persisted windows', async () => {
    fetchSensors.mockResolvedValue({ items: [SENSOR], total: 1, page: 1, page_size: 100 })
    fetchSensorHealth.mockResolvedValue([HEALTH])
    renderPage()

    expect(await screen.findByText('0.0231 g RMS')).toBeInTheDocument()
    expect(screen.getByText('VIB-01')).toBeInTheDocument()
    expect(screen.getAllByText('LAB-PUMP-01').length).toBeGreaterThan(0)
    expect(screen.getByText('0.0231 g RMS')).toBeInTheDocument()
    expect(screen.getAllByText('Sensor invalid').length).toBeGreaterThan(0)
    expect(screen.getByText('1 / 1')).toBeInTheDocument()
    expect(screen.getByText('No live channel')).toBeInTheDocument()
    expect(screen.getByText('sensor_disconnected')).toBeInTheDocument()
    expect(screen.getByText(/Diagnostics come from persisted windows/i)).toBeInTheDocument()
  })

  it('shows a no-data diagnostic state for a sensor without windows', async () => {
    fetchSensors.mockResolvedValue({ items: [SENSOR], total: 1, page: 1, page_size: 100 })
    fetchSensorHealth.mockResolvedValue([
      {
        ...HEALTH,
        total_windows: 0,
        valid_windows: 0,
        invalid_windows: 0,
        missing_window_gaps: 0,
        last_reading_at: null,
        last_valid_reading_at: null,
        freshness_seconds: null,
        latest_quality: null,
        data_quality: null,
        sampling_status: 'NO_DATA',
        latest_rms: null,
        latest_peak_abs: null,
        latest_validation_issues: [],
      },
    ])
    renderPage()

    expect(await screen.findByText('No valid reading')).toBeInTheDocument()
    expect(screen.getAllByText('No data').length).toBeGreaterThan(0)
  })

  it('shows the empty state when no sensors exist', async () => {
    fetchSensors.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    fetchSensorHealth.mockResolvedValue([])
    renderPage()

    expect(await screen.findByText('No sensors registered')).toBeInTheDocument()
  })
})
