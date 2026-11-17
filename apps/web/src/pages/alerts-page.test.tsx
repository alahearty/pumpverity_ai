import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type {
  Alert,
  AlertDetail,
  AlertReview,
  Page,
  Prediction,
  Pump,
} from '@petrosense/shared-contracts'

import { AlertsPage } from './alerts-page'

const fetchAlerts = vi.hoisted(() => vi.fn())
const fetchAlert = vi.hoisted(() => vi.fn())
const acknowledgeAlert = vi.hoisted(() => vi.fn())
const createAlertReview = vi.hoisted(() => vi.fn())
const fetchPumps = vi.hoisted(() => vi.fn())
const authState = vi.hoisted(() => ({
  role: 'ENGINEER' as 'ENGINEER' | 'REVIEWER' | 'RESEARCHER' | 'ADMINISTRATOR',
}))

vi.mock('@/services/alerts-service', () => ({
  fetchAlerts,
  fetchAlert,
  acknowledgeAlert,
  createAlertReview,
}))
vi.mock('@/services/equipment-service', () => ({ fetchPumps }))
vi.mock('@/providers/auth-provider', () => ({
  useAuth: () => ({
    status: 'authenticated',
    user: {
      id: 'user-1',
      email: 'engineer@petrosense.local',
      username: 'engineer',
      full_name: 'Chinedu Okafor',
      role: authState.role,
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

const PREDICTION: Prediction = {
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

const ALERT: Alert = {
  id: 'alert-1',
  event_id: 'alert-event-1',
  pump_id: 'pump-1',
  pump_code: 'LAB-PUMP-01',
  sensor_id: 'sensor-1',
  sensor_code: 'VIB-01',
  prediction_id: 'prediction-1',
  signal_window_id: 'window-1',
  window_start: '2026-11-16T11:59:59Z',
  window_end: '2026-11-16T12:00:00Z',
  category: 'FAULT',
  severity: 'HIGH',
  status: 'OPEN',
  title: 'Fault decision on LAB-PUMP-01 / VIB-01',
  description:
    'Synthetic model accepted an abnormal decision.\n\nModel: PUMPVERITY lightweight linear v0.1.0 (LINEAR_JSON). Data provenance: SIMULATED.',
  decision: 'FAULT',
  data_quality: 'VALID',
  decision_score: 0.92,
  uncertainty_score: 0.08,
  model_name: 'PUMPVERITY lightweight linear',
  model_version: '0.1.0',
  data_provenance: 'SIMULATED',
  assigned_reviewer_id: null,
  assigned_reviewer_name: null,
  acknowledged_at: null,
  closed_at: null,
  created_at: '2026-11-16T12:00:01Z',
  updated_at: '2026-11-16T12:00:01Z',
  review_count: 0,
}

const ACK_REVIEW: AlertReview = {
  id: 'review-ack',
  alert_id: 'alert-1',
  reviewer_id: 'user-1',
  reviewer_name: 'Chinedu Okafor',
  action: 'ACKNOWLEDGE',
  reviewed_label: null,
  notes: 'Alert acknowledged.',
  label_source: 'ENGINEER_REVIEW',
  is_verified_ground_truth: false,
  created_at: '2026-11-16T12:05:00Z',
}

const DETAIL: AlertDetail = {
  ...ALERT,
  prediction: PREDICTION,
  reviews: [],
}

const ACKNOWLEDGED_DETAIL: AlertDetail = {
  ...ALERT,
  status: 'ACKNOWLEDGED',
  assigned_reviewer_id: 'user-1',
  assigned_reviewer_name: 'Chinedu Okafor',
  acknowledged_at: '2026-11-16T12:05:00Z',
  review_count: 1,
  prediction: PREDICTION,
  reviews: [ACK_REVIEW],
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
  sensors: [],
  registered_at: '2026-11-16T10:00:00Z',
  created_at: '2026-11-16T10:00:00Z',
  updated_at: '2026-11-16T10:00:00Z',
}

function page<T>(items: T[]): Page<T> {
  return { items, total: items.length, page: 1, page_size: 20 }
}

function renderPage(initialPath = '/alerts/alert-1') {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/alerts" element={<AlertsPage />} />
          <Route path="/alerts/:alertId" element={<AlertsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AlertsPage', () => {
  beforeEach(() => {
    authState.role = 'ENGINEER'
    fetchAlerts.mockResolvedValue(page([ALERT]))
    fetchAlert.mockResolvedValue(DETAIL)
    acknowledgeAlert.mockResolvedValue(ACKNOWLEDGED_DETAIL)
    createAlertReview.mockResolvedValue({
      ...ACK_REVIEW,
      id: 'review-2',
      action: 'CORRECT_LABEL',
      reviewed_label: 'UNCERTAIN',
      notes: 'Evidence is inconclusive.',
    })
    fetchPumps.mockResolvedValue(page([PUMP]))
  })

  it('shows the immutable prediction evidence and acknowledges the alert', async () => {
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByRole('heading', { name: 'Fault decision on LAB-PUMP-01 / VIB-01' })).toBeInTheDocument()
    expect(screen.getByText('Original AI prediction')).toBeInTheDocument()
    expect(screen.getByText('Synthetic model accepted a FAULT decision.')).toBeInTheDocument()
    expect(screen.getByText(/never overwrite this/)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Acknowledge alert' }))

    expect(acknowledgeAlert).toHaveBeenCalledWith('alert-1')
    expect(
      await screen.findByText('Alert acknowledged and assigned to you.'),
    ).toBeInTheDocument()
    expect(await screen.findByText('Alert acknowledged.')).toBeInTheDocument()
  })

  it('submits an appended correction with a label and notes', async () => {
    const user = userEvent.setup()
    renderPage()

    await screen.findByRole('heading', { name: 'Fault decision on LAB-PUMP-01 / VIB-01' })
    await user.selectOptions(screen.getByLabelText('Action'), 'CORRECT_LABEL')
    await user.selectOptions(screen.getByLabelText('Reviewed label'), 'UNCERTAIN')
    await user.type(
      screen.getByLabelText(/Engineering notes/),
      'Evidence is inconclusive after inspection.',
    )
    await user.click(screen.getByRole('button', { name: 'Record review' }))

    await waitFor(() => {
      expect(createAlertReview).toHaveBeenCalledWith({
        alert_id: 'alert-1',
        action: 'CORRECT_LABEL',
        reviewed_label: 'UNCERTAIN',
        notes: 'Evidence is inconclusive after inspection.',
      })
    })
    expect(
      await screen.findByText(
        'Engineering review recorded without changing the original prediction.',
      ),
    ).toBeInTheDocument()
  })

  it('requires notes for a review and permits read-only inspection', async () => {
    const user = userEvent.setup()
    const engineerView = renderPage()

    await screen.findByRole('heading', { name: 'Fault decision on LAB-PUMP-01 / VIB-01' })
    await user.click(screen.getByRole('button', { name: 'Record review' }))
    expect(
      screen.getByText('Add at least three characters of engineering notes for this action.'),
    ).toBeInTheDocument()
    expect(createAlertReview).not.toHaveBeenCalled()
    engineerView.unmount()

    authState.role = 'RESEARCHER'
    renderPage()
    expect(
      await screen.findByText(
        'Your role can inspect alerts but cannot acknowledge or record engineering judgements.',
      ),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'Acknowledge alert' }),
    ).not.toBeInTheDocument()
  })
})

