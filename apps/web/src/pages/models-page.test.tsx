import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { ModelEvaluation, ModelVersion } from '@petrosense/shared-contracts'

import { ModelsPage } from './models-page'

const fetchModels = vi.hoisted(() => vi.fn())
const fetchActiveModel = vi.hoisted(() => vi.fn())
const validateModel = vi.hoisted(() => vi.fn())
const activateModel = vi.hoisted(() => vi.fn())
const rollbackModel = vi.hoisted(() => vi.fn())

vi.mock('@/services/models-service', () => ({
  fetchModels,
  fetchActiveModel,
  validateModel,
  activateModel,
  rollbackModel,
}))

const EVALUATION: ModelEvaluation = {
  id: 'evaluation-1',
  model_version_id: 'model-1',
  dataset_name: 'Synthetic grouped hold-out set',
  dataset_version: 'synthetic-eval-v1',
  data_provenance: 'SIMULATED',
  evaluation_protocol: 'grouped hold-out',
  split_description: 'Grouped by run',
  sample_count: 180,
  balanced_accuracy: 0.9,
  macro_f1: 0.89,
  metrics: { coverage: 0.92, risk: 0.04 },
  confusion_matrix: null,
  risk_coverage: null,
  calibration: null,
  is_verified: true,
  verified_by_name: 'Fatima Yusuf',
  verified_at: '2026-11-16T10:01:00Z',
  evaluated_by: 'pipeline',
  evaluated_at: '2026-11-16T10:00:00Z',
  notes: 'Synthetic metrics only.',
}

const MODEL: ModelVersion = {
  id: 'model-1',
  model_code: 'petrosense-linear',
  name: 'PUMPVERITY lightweight linear',
  version: '0.1.0',
  algorithm: 'logistic-regression',
  runtime: 'LINEAR_JSON',
  feature_contract: { version: 'petrosense-time-v1', features: ['rms'] },
  training_dataset_version: 'synthetic-train-v1',
  evaluation_dataset: 'synthetic-eval-v1',
  deployment_compatibility: { edge: 'petrosense-edge' },
  artifact_path: 'ml/artifacts/model.json',
  artifact_sha256: 'a'.repeat(64),
  status: 'VALIDATED',
  registered_by_name: 'Fatima Yusuf',
  registered_at: '2026-11-16T10:00:00Z',
  validated_at: '2026-11-16T10:01:00Z',
  activated_at: null,
  retired_at: null,
  notes: null,
  latest_evaluation: EVALUATION,
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <ModelsPage />
    </QueryClientProvider>,
  )
}

describe('ModelsPage', () => {
  beforeEach(() => {
    fetchModels.mockReset()
    fetchActiveModel.mockReset()
    validateModel.mockReset()
    activateModel.mockReset()
    rollbackModel.mockReset()
    fetchModels.mockResolvedValue({ items: [MODEL], total: 1, page: 1, page_size: 100 })
    fetchActiveModel.mockResolvedValue(null)
    activateModel.mockResolvedValue({ ...MODEL, status: 'ACTIVE' })
  })

  it('shows model metadata and synthetic evaluation evidence', async () => {
    renderPage()

    expect(await screen.findByText('PUMPVERITY lightweight linear')).toBeInTheDocument()
    expect(screen.getByText(/Metrics are from a synthetic grouped hold-out set/i)).toBeInTheDocument()
    expect(screen.getByText('0.900')).toBeInTheDocument()
    expect(screen.getByText('0.890')).toBeInTheDocument()
    expect(screen.getAllByText('Validated').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /activate/i })).toBeInTheDocument()
  })

  it('activates a validated model through the API', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /activate/i }))
    expect(activateModel.mock.calls[0]?.[0]).toBe('model-1')
    expect(await screen.findByText(/Activated petrosense-linear/i)).toBeInTheDocument()
  })
})
