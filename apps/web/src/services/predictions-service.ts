import type {
  Page,
  Prediction,
  PredictionDecision,
} from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export interface PredictionQuery {
  page?: number
  page_size?: number
  pump_id?: string
  sensor_id?: string
  decision?: PredictionDecision
  model_version_id?: string
}

export function fetchPredictions(query: PredictionQuery = {}): Promise<Page<Prediction>> {
  const params = new URLSearchParams({
    page: String(query.page ?? 1),
    page_size: String(query.page_size ?? 25),
  })
  if (query.pump_id) params.set('pump_id', query.pump_id)
  if (query.sensor_id) params.set('sensor_id', query.sensor_id)
  if (query.decision) params.set('decision', query.decision)
  if (query.model_version_id) params.set('model_version_id', query.model_version_id)
  return apiFetch<Page<Prediction>>(`/predictions?${params.toString()}`)
}

export function fetchPrediction(predictionId: string): Promise<Prediction> {
  return apiFetch<Prediction>(`/predictions/${predictionId}`)
}
