import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Pump } from '@petrosense/shared-contracts'

import { PumpsPage } from './pumps-page'

const fetchPumps = vi.hoisted(() => vi.fn())
const fetchOperatingRegimes = vi.hoisted(() => vi.fn())
const createPump = vi.hoisted(() => vi.fn())
const updatePump = vi.hoisted(() => vi.fn())
const fetchAcquisitionSessions = vi.hoisted(() => vi.fn())

vi.mock('@/services/equipment-service', () => ({
  fetchPumps,
  fetchOperatingRegimes,
  createPump,
  updatePump,
}))

vi.mock('@/services/acquisition-service', () => ({
  fetchAcquisitionSessions,
}))

const PUMP: Pump = {
  id: 'pump-1',
  pump_code: 'LAB-PUMP-01',
  name: 'Laboratory Centrifugal Pump',
  pump_type: 'CENTRIFUGAL',
  location: 'Thermofluids Laboratory',
  rated_speed_rpm: 2900,
  default_regime: {
    id: 'regime-1',
    code: 'STEADY_STATE',
    name: 'Steady state',
    description: 'Nominal operation',
    is_active: true,
  },
  status: 'ACTIVE',
  notes: null,
  sensors: [
    {
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
    },
  ],
  registered_at: '2026-11-16T10:00:00Z',
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <PumpsPage />
    </QueryClientProvider>,
  )
}

describe('PumpsPage', () => {
  beforeEach(() => {
    fetchPumps.mockReset()
    fetchOperatingRegimes.mockReset()
    createPump.mockReset()
    updatePump.mockReset()
    fetchAcquisitionSessions.mockReset()
    fetchOperatingRegimes.mockResolvedValue(PUMP.default_regime ? [PUMP.default_regime] : [])
    fetchAcquisitionSessions.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 8 })
  })

  it('renders the registered pump and sensor association', async () => {
    fetchPumps.mockResolvedValue({ items: [PUMP], total: 1, page: 1, page_size: 100 })
    renderPage()

    expect(await screen.findByText('LAB-PUMP-01')).toBeInTheDocument()
    expect(screen.getByText('Laboratory Centrifugal Pump')).toBeInTheDocument()
    expect(screen.getByText('VIB-01')).toBeInTheDocument()
    expect(screen.getByText('2,900 RPM')).toBeInTheDocument()
    expect(screen.getByText('Steady state')).toBeInTheDocument()
    expect(screen.getByText('Recent simulated acquisition')).toBeInTheDocument()
    expect(screen.getByText('No simulated sessions yet')).toBeInTheDocument()
  })

  it('shows an honest empty equipment state', async () => {
    fetchPumps.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    renderPage()

    expect(await screen.findByText('No pumps registered')).toBeInTheDocument()
    expect(screen.getByText(/No demonstration equipment record is pre-seeded/i)).toBeInTheDocument()
  })

  it('opens the registration form from the empty state', async () => {
    fetchPumps.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 100 })
    const { default: userEvent } = await import('@testing-library/user-event')
    const user = userEvent.setup()
    renderPage()

    const buttons = await screen.findAllByRole('button', { name: /register (first )?pump/i })
    await user.click(buttons[0])
    expect(await screen.findByLabelText('Pump ID')).toBeInTheDocument()
    expect(screen.getByLabelText('Sensor ID')).toBeInTheDocument()
  })
})
