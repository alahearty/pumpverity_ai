import { useQuery } from '@tanstack/react-query'
import type { Prediction, PredictionDecision } from '@petrosense/shared-contracts'
import { BrainCircuit, ExternalLink, FileText, RefreshCw, ShieldAlert } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { ProvenanceBadge } from '@/components/shared/provenance-badge'
import { QueryError } from '@/components/shared/query-error'
import { ResearchNotice } from '@/components/shared/research-notice'
import { StatusBadge } from '@/components/shared/status-badge'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Select } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { fetchPredictions } from '@/services/predictions-service'
import { fetchActiveModel } from '@/services/models-service'
import { useAuth } from '@/providers/auth-provider'
import { useCopilotPageContext } from '@/providers/copilot-context-provider'
import { formatDateTime, formatScenario } from '@/lib/utils'

const DECISION_OPTIONS: Array<{ value: 'ALL' | PredictionDecision; label: string }> = [
  { value: 'ALL', label: 'All decisions' },
  { value: 'NORMAL', label: 'Normal' },
  { value: 'FAULT', label: 'Fault' },
  { value: 'UNCERTAIN', label: 'Uncertain' },
  { value: 'SENSOR_INVALID', label: 'Sensor invalid' },
]

function formatScore(value: number | null): string {
  return typeof value === 'number' ? value.toFixed(4) : '—'
}

function featureEntries(prediction: Prediction): Array<[string, unknown]> {
  return Object.entries(prediction.features ?? {})
}

function AnalysisPage() {
  const { predictionId } = useParams()
  const { user } = useAuth()
  const canManageModels = user?.role === 'RESEARCHER' || user?.role === 'ADMINISTRATOR'
  const [decision, setDecision] = useState<'ALL' | PredictionDecision>('ALL')
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const predictionsQuery = useQuery({
    queryKey: ['predictions', { decision }],
    queryFn: () =>
      fetchPredictions({
        page_size: 50,
        decision: decision === 'ALL' ? undefined : decision,
      }),
    refetchInterval: 30_000,
    staleTime: 5_000,
  })
  const activeModelQuery = useQuery({
    queryKey: ['models', 'active'],
    queryFn: fetchActiveModel,
    staleTime: 30_000,
  })

  const predictions = predictionsQuery.data?.items ?? []
  const selected =
    predictions.find((prediction) => prediction.id === (selectedId ?? predictionId)) ??
    (!predictionId ? predictions[0] ?? null : null)
  const activeModel = activeModelQuery.data

  useCopilotPageContext({
    selectedPumpId: selected?.pump_id ?? null,
    selectedSensorId: selected?.sensor_id ?? null,
    activeModelVersion: selected?.model?.version ?? activeModel?.version ?? null,
    operatingRegime: selected?.operating_regime?.code ?? null,
    monitoringMode: selected?.data_provenance ?? 'SIMULATED',
    connectivityStatus: 'NO_LIVE_CHANNEL',
  })

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="AI analysis and prediction"
        description="Inspect model decisions, uncertainty/abstention, data validity and the model version that produced each prediction."
        badge={
          <Badge variant={activeModel ? 'info' : 'outline'}>
            {activeModel ? 'Inference active' : 'No active model'}
          </Badge>
        }
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              predictionsQuery.refetch()
              activeModelQuery.refetch()
            }}
            disabled={predictionsQuery.isFetching}
          >
            <RefreshCw className="size-3.5" aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      <div className="flex flex-col gap-2 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4 text-xs leading-relaxed text-industrial-900 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2">
          <BrainCircuit className="mt-0.5 size-4 shrink-0 text-industrial-600" aria-hidden="true" />
          <p>
            <span className="font-semibold">Uncertainty-aware decisions, not failure probabilities.</span>{' '}
            A decision score is a model output, not the probability that a pump will fail. An
            abstained (UNCERTAIN) result is reviewable; sensor-invalid windows never receive a
            condition inference.
          </p>
        </div>
        <StatusBadge status={activeModel ? 'ACTIVE' : 'NO_DATA'} label={activeModel ? 'Model active' : 'No model'} />
      </div>

      <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card>
          <CardHeader className="gap-3 border-b border-slate-100 pb-4">
            <div className="flex items-center justify-between gap-2">
              <CardTitle>Recent predictions</CardTitle>
              <Badge variant="neutral">{predictionsQuery.data?.total ?? 0}</Badge>
            </div>
            <Select
              value={decision}
              onChange={(event) => {
                setDecision(event.target.value as 'ALL' | PredictionDecision)
                setSelectedId(null)
              }}
              aria-label="Filter predictions by decision"
            >
              {DECISION_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          </CardHeader>
          <CardContent className="max-h-[620px] overflow-y-auto p-2">
            {predictionsQuery.isError ? (
              <QueryError
                error={predictionsQuery.error}
                onRetry={() => predictionsQuery.refetch()}
              />
            ) : predictionsQuery.isPending ? (
              <div className="space-y-2 p-2">
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
                <Skeleton className="h-16 w-full" />
              </div>
            ) : predictions.length === 0 ? (
              <div className="p-3">
                <EmptyState
                  compact
                  icon={BrainCircuit}
                  title="No predictions yet"
                  description={
                    activeModel
                      ? 'Run the edge simulator against a registered pump to generate inference results.'
                      : 'No active model is available. Register and activate a validated model first.'
                  }
                  action={
                    activeModel || canManageModels ? (
                      <Link
                        to={activeModel ? '/monitoring' : '/models'}
                        className="text-xs font-semibold text-industrial-600 hover:underline"
                      >
                        {activeModel ? 'Open Live Monitoring' : 'Open Model Registry'}
                      </Link>
                    ) : undefined
                  }
                />
              </div>
            ) : (
              <ul className="space-y-1">
                {predictions.map((prediction) => (
                  <li key={prediction.id}>
                    <button
                      type="button"
                      onClick={() => setSelectedId(prediction.id)}
                      className={`w-full rounded-lg border px-3 py-2.5 text-left transition ${
                        selected?.id === prediction.id
                          ? 'border-industrial-300 bg-industrial-50'
                          : 'border-transparent hover:border-slate-200 hover:bg-slate-50'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <StatusBadge status={prediction.decision} />
                        <span className="text-[10px] text-slate-400">
                          {formatDateTime(prediction.inferred_at)}
                        </span>
                      </div>
                      <p className="mt-1.5 truncate text-xs font-medium text-navy-900">
                        {prediction.pump_code} / {prediction.sensor_code}
                      </p>
                      <p className="mt-0.5 truncate text-[10px] text-slate-500">
                        score {formatScore(prediction.decision_score)} · uncertainty{' '}
                        {formatScore(prediction.uncertainty_score)}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {predictionsQuery.isPending ? (
          <Card>
            <CardContent className="space-y-4 p-6">
              <Skeleton className="h-8 w-56" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-40 w-full" />
            </CardContent>
          </Card>
        ) : selected ? (
          <PredictionDetail prediction={selected} />
        ) : (
          <Card>
            <CardContent className="p-5">
              <EmptyState
                icon={FileText}
                title="Select a prediction"
                description="Choose a prediction from the list to inspect its model, uncertainty, validity and explanation."
              />
            </CardContent>
          </Card>
        )}
      </div>

      <ResearchNotice compact />
    </div>
  )
}

function PredictionDetail({ prediction }: { prediction: Prediction }) {
  const features = featureEntries(prediction)
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader className="flex-row items-start justify-between gap-4 pb-3">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={prediction.decision} data-testid="prediction-decision" />
              <StatusBadge status={prediction.data_quality} />
              <Badge variant="outline">Model decision</Badge>
            </div>
            <CardTitle className="mt-3">
              {prediction.pump_code} / {prediction.sensor_code}
            </CardTitle>
            <CardDescription>
              Inference at {formatDateTime(prediction.inferred_at)} · {formatScenario(prediction.scenario)}
            </CardDescription>
          </div>
          <ProvenanceBadge provenance={prediction.data_provenance} />
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Decision score
              </p>
              <p className="mt-1 text-xl font-semibold text-navy-900">
                {formatScore(prediction.decision_score)}
              </p>
              <p className="text-[10px] text-slate-400">Not a failure probability</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Uncertainty
              </p>
              <p className="mt-1 text-xl font-semibold text-navy-900">
                {formatScore(prediction.uncertainty_score)}
              </p>
              <p className="text-[10px] text-slate-400">Higher = closer to abstention</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Inference latency
              </p>
              <p className="mt-1 text-xl font-semibold text-navy-900">
                {prediction.latency_ms !== null ? `${prediction.latency_ms.toFixed(2)} ms` : '—'}
              </p>
              <p className="text-[10px] text-slate-400">Model inference only</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
              <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Equipment condition
              </p>
              <div className="mt-1.5">
                {prediction.equipment_condition ? (
                  <StatusBadge status={prediction.equipment_condition} />
                ) : (
                  <Badge variant="outline">Not inferred</Badge>
                )}
              </div>
              <p className="mt-1 text-[10px] text-slate-400">Separate from signal validity</p>
            </div>
          </div>

          <div
            className={`rounded-lg border p-4 text-xs leading-relaxed ${
              prediction.decision === 'FAULT'
                ? 'border-red-200 bg-fault-soft/60 text-red-900'
                : prediction.decision === 'UNCERTAIN'
                  ? 'border-amber-200 bg-uncertain-soft/60 text-amber-900'
                  : prediction.decision === 'SENSOR_INVALID'
                    ? 'border-violet-200 bg-sensor-soft/50 text-violet-900'
                    : 'border-green-200 bg-success-soft/60 text-green-900'
            }`}
          >
            <p className="mb-1 font-semibold">Why this result?</p>
            <p>{prediction.explanation}</p>
          </div>

          <div className="grid gap-3 text-xs sm:grid-cols-2">
            <div className="rounded-lg border border-slate-200 p-3">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Model
              </p>
              {prediction.model ? (
                <>
                  <p className="font-semibold text-navy-900">
                    {prediction.model.name} v{prediction.model.version}
                  </p>
                  <p className="mt-1 text-slate-500">
                    {prediction.model.model_code} · {prediction.model.runtime}
                  </p>
                </>
              ) : (
                <p className="text-slate-500">No model — sensor validation failed.</p>
              )}
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Window
              </p>
              <p className="text-slate-600">
                {formatDateTime(prediction.window_start)} → {formatDateTime(prediction.window_end)}
              </p>
              <p className="mt-1 text-slate-500">
                {prediction.sample_count.toLocaleString()} samples ·{' '}
                {prediction.window_quality}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Operating context
              </p>
              <p className="text-slate-600">
                Regime: {prediction.operating_regime?.name ?? 'Not recorded'}
              </p>
              <p className="mt-1 text-slate-500">
                Session: {prediction.session_id.slice(0, 8)} · Window:{' '}
                {prediction.signal_window_id.slice(0, 8)}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 p-3">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                Review routing
              </p>
              <p className="text-slate-500">
                FAULT, UNCERTAIN and SENSOR_INVALID decisions create reviewable alerts
                automatically. This prediction remains immutable evidence; engineering labels are
                appended separately.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Feature values</CardTitle>
          <CardDescription>
            Features extracted by the versioned edge feature contract and validated against the
            model contract.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {features.length === 0 ? (
            <p className="text-xs text-slate-500">
              No feature vector is available for this sensor-invalid window.
            </p>
          ) : (
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {features.map(([name, value]) => (
                <div
                  key={name}
                  className="flex items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2"
                >
                  <span className="font-mono text-[10px] text-slate-500">{name}</span>
                  <span className="font-mono text-xs font-semibold text-navy-900">
                    {typeof value === 'number' ? value.toFixed(5) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-3 p-4">
          <Link
            to="/history"
            className="inline-flex items-center gap-1 text-xs font-semibold text-industrial-600 hover:underline"
          >
            Historical trends <ExternalLink className="size-3" aria-hidden="true" />
          </Link>
          <Separator orientation="vertical" className="h-4" />
          <Link
            to="/sensors"
            className="inline-flex items-center gap-1 text-xs font-semibold text-industrial-600 hover:underline"
          >
            Sensor health <ExternalLink className="size-3" aria-hidden="true" />
          </Link>
          <Separator orientation="vertical" className="h-4" />
          <span className="flex items-center gap-1 text-[11px] text-slate-400">
            <ShieldAlert className="size-3" aria-hidden="true" />
            No automatic shutdown; research decision support only.
          </span>
        </CardContent>
      </Card>
    </div>
  )
}

export { AnalysisPage }

