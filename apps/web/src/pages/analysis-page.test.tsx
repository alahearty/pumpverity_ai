import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ModelVersion, Prediction } from '@petrosense/shared-contracts'

import { AnalysisPage } from './analysis-page'

const fetchPredictions = vi.hoisted(() => vi.fn())
const fetchActiveModel = vi.hoisted(() => vi.fn())

vi.mock('@/services/predictions-service', () => ({ fetchPredictions }))
vi.mock('@/services/models-service', () => ({ fetchActiveModel }))
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
  explanation: 'Synthetic model accepted a FAULT decision for this window.',
  latency_ms: 0.42,
  inferred_at: '2026-11-16T12:00:00Z',
  data_provenance: 'SIMULATED',
  created_at: '2026-11-16T12:00:01Z',
  window_start: '2026-11-16T11:59:59Z',
  window_end: '2026-11-16T12:00:00Z',
  window_quality: 'VALID',
  sample_count: 2048,
  features: { rms: 0.094, peak_abs: 0.16, crest_factor: 1.7 },
  scenario: 'imbalance',
}

const ACTIVE_MODEL: ModelVersion = {
  id: 'model-1',
  model_code: 'petrosense-linear',
  name: 'PUMPVERITY lightweight linear',
  version: '0.1.0',
  algorithm: 'logistic-regression',
  runtime: 'LINEAR_JSON',
  feature_contract: { version: 'petrosense-time-v1', features: ['rms'] },
  training_dataset_version: 'synthetic-v2',
  evaluation_dataset: 'synthetic-eval',
  deployment_compatibility: {},
  artifact_path: 'ml/artifacts/model.json',
  artifact_sha256: 'a'.repeat(64),
  status: 'ACTIVE',
  registered_by_name: 'Fatima Yusuf',
  registered_at: '2026-11-16T10:00:00Z',
  validated_at: '2026-11-16T10:01:00Z',
  activated_at: '2026-11-16T10:02:00Z',
  retired_at: null,
  notes: null,
  latest_evaluation: null,
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/analysis']}>
        <AnalysisPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AnalysisPage', () => {
  beforeEach(() => {
    fetchPredictions.mockReset()
    fetchActiveModel.mockReset()
    fetchActiveModel.mockResolvedValue(ACTIVE_MODEL)
    fetchPredictions.mockResolvedValue({
      items: [PREDICTION],
      total: 1,
      page: 1,
      page_size: 50,
    })
  })

  it('shows the model decision, uncertainty and explanation', async () => {
    renderPage()

    expect(await screen.findByText(/Synthetic model accepted a FAULT decision/i)).toBeInTheDocument()
    expect(screen.getAllByText('PUMPVERITY lightweight linear v0.1.0').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Fault').length).toBeGreaterThan(0)
    expect(screen.getByText('0.9200')).toBeInTheDocument()
    expect(screen.getByText('0.0800')).toBeInTheDocument()
    expect(screen.getByText('Not a failure probability')).toBeInTheDocument()
    expect(screen.getByText('rms')).toBeInTheDocument()
    expect(screen.getByText('0.09400')).toBeInTheDocument()
    expect(screen.getByText(/Inference active/i)).toBeInTheDocument()
  })

  it('shows an empty state when no predictions exist', async () => {
    fetchPredictions.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 50 })
    renderPage()

    expect(await screen.findByText('No predictions yet')).toBeInTheDocument()
    expect(screen.getByText('Open Live Monitoring')).toBeInTheDocument()
  })
})
