import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { ModelVersion } from '@petrosense/shared-contracts'
import {
  Activity,
  BadgeCheck,
  Boxes,
  GitBranch,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Terminal,
} from 'lucide-react'
import { useState } from 'react'

import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { ProvenanceBadge } from '@/components/shared/provenance-badge'
import { QueryError } from '@/components/shared/query-error'
import { ResearchNotice } from '@/components/shared/research-notice'
import { StatCard } from '@/components/shared/stat-card'
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
import { Skeleton } from '@/components/ui/skeleton'
import { ApiClientError } from '@/lib/api'
import {
  activateModel,
  fetchActiveModel,
  fetchModels,
  rollbackModel,
  validateModel,
} from '@/services/models-service'
import { useCopilotPageContext } from '@/providers/copilot-context-provider'
import { formatDateTime } from '@/lib/utils'

function metricValue(value: unknown): string {
  return typeof value === 'number' ? value.toFixed(3) : '—'
}

function ModelCard({
  model,
  busy,
  onValidate,
  onActivate,
}: {
  model: ModelVersion
  busy: boolean
  onValidate: () => void
  onActivate: () => void
}) {
  const evaluation = model.latest_evaluation
  const metrics = (evaluation?.metrics ?? {}) as Record<string, unknown>
  const featureCount = Array.isArray(model.feature_contract.features)
    ? model.feature_contract.features.length
    : 0

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between gap-4 pb-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>{model.name}</CardTitle>
            <StatusBadge status={model.status} />
          </div>
          <CardDescription>
            {model.model_code} v{model.version} · {model.algorithm} · {model.runtime}
          </CardDescription>
        </div>
        {evaluation ? <ProvenanceBadge provenance={evaluation.data_provenance} /> : null}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
              Balanced accuracy
            </p>
            <p className="mt-1 text-lg font-semibold text-navy-900">
              {metricValue(evaluation?.balanced_accuracy)}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
              Macro-F1
            </p>
            <p className="mt-1 text-lg font-semibold text-navy-900">
              {metricValue(evaluation?.macro_f1)}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
              Coverage / risk
            </p>
            <p className="mt-1 text-sm font-semibold text-navy-900">
              {metricValue(metrics.coverage)} / {metricValue(metrics.risk)}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
            <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
              Feature count
            </p>
            <p className="mt-1 text-lg font-semibold text-navy-900">{featureCount}</p>
          </div>
        </div>

        <div className="space-y-2 rounded-lg border border-slate-200 p-3 text-xs">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-slate-500">Evaluation dataset</span>
            <span className="text-right font-medium text-navy-900">
              {evaluation?.dataset_name ?? 'Not evaluated'}
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-slate-500">Dataset version</span>
            <span className="font-mono text-[10px] text-slate-600">
              {evaluation?.dataset_version ?? model.evaluation_dataset}
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-slate-500">Verified evaluation</span>
            <span className="font-medium text-navy-900">
              {evaluation?.is_verified ? 'Yes (research pipeline)' : 'No'}
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-slate-500">Artifact hash</span>
            <span className="font-mono text-[10px] text-slate-600">
              {model.artifact_sha256.slice(0, 16)}…
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-slate-500">Artifact path</span>
            <span className="truncate font-mono text-[10px] text-slate-600">
              {model.artifact_path}
            </span>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span className="text-slate-500">Registered</span>
            <span className="text-slate-600">{formatDateTime(model.registered_at)}</span>
          </div>
        </div>

        {evaluation?.data_provenance === 'SIMULATED' ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-2 text-[11px] leading-relaxed text-amber-900">
            Metrics are from a synthetic grouped hold-out set. They are not real-pump accuracy and
            must not be presented as industrial performance.
          </p>
        ) : null}

        <div className="flex flex-wrap gap-2">
          {model.status === 'REGISTERED' ? (
            <Button variant="secondary" size="sm" onClick={onValidate} disabled={busy}>
              <BadgeCheck className="size-3.5" aria-hidden="true" />
              Validate
            </Button>
          ) : null}
          {model.status === 'VALIDATED' ? (
            <Button size="sm" onClick={onActivate} disabled={busy}>
              <ShieldCheck className="size-3.5" aria-hidden="true" />
              Activate
            </Button>
          ) : model.status === 'ACTIVE' ? (
            <Badge variant="success">Active model</Badge>
          ) : null}
          {model.activated_at ? (
            <span className="self-center text-[10px] text-slate-400">
              activated {formatDateTime(model.activated_at)}
            </span>
          ) : null}
        </div>
      </CardContent>
    </Card>
  )
}

function ModelsPage() {
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const modelsQuery = useQuery({
    queryKey: ['models', { page: 1, page_size: 100 }],
    queryFn: () => fetchModels({ page_size: 100 }),
  })
  const activeModelQuery = useQuery({
    queryKey: ['models', 'active'],
    queryFn: fetchActiveModel,
    staleTime: 30_000,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['models'] })
    queryClient.invalidateQueries({ queryKey: ['monitoring-overview'] })
    queryClient.invalidateQueries({ queryKey: ['monitoring-live'] })
  }

  const validateMutation = useMutation({
    mutationFn: validateModel,
    onSuccess: (model) => {
      invalidate()
      setSuccessMessage(`Validated ${model.model_code} v${model.version}.`)
    },
  })
  const activateMutation = useMutation({
    mutationFn: activateModel,
    onSuccess: (model) => {
      invalidate()
      setSuccessMessage(
        `Activated ${model.model_code} v${model.version}; the previous active model was retired.`,
      )
    },
  })
  const rollbackMutation = useMutation({
    mutationFn: rollbackModel,
    onSuccess: (model) => {
      invalidate()
      setSuccessMessage(
        `Rolled back to ${model.model_code} v${model.version}.`,
      )
    },
  })

  const models = modelsQuery.data?.items ?? []
  const activeModel = activeModelQuery.data ?? null

  useCopilotPageContext({
    selectedPumpId: null,
    selectedSensorId: null,
    activeModelVersion: activeModel?.version ?? null,
    monitoringMode: 'SIMULATED',
    connectivityStatus: 'NO_LIVE_CHANNEL',
  })

  const validatedCount = models.filter(
    (model) => model.status === 'VALIDATED' || model.status === 'ACTIVE',
  ).length
  const canRollback = models.some(
    (model) => model.status === 'RETIRED' && model.activated_at !== null,
  )
  const mutationError =
    validateMutation.error ?? activateMutation.error ?? rollbackMutation.error
  const busy =
    validateMutation.isPending ||
    activateMutation.isPending ||
    rollbackMutation.isPending

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Governance"
        title="Model management"
        description="Review model metadata and synthetic evaluation evidence, validate compatible artifacts, activate one edge model and roll back safely."
        badge={<Badge variant="info">Registry active</Badge>}
        actions={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                modelsQuery.refetch()
                activeModelQuery.refetch()
              }}
              disabled={modelsQuery.isFetching}
            >
              <RefreshCw className="size-3.5" aria-hidden="true" />
              Refresh
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => rollbackMutation.mutate()}
              disabled={!canRollback || busy}
              title={canRollback ? 'Restore the most recently retired active model' : 'No rollback model'}
            >
              <RotateCcw className="size-3.5" aria-hidden="true" />
              Roll back
            </Button>
          </>
        }
      />

      <div className="flex flex-col gap-2 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4 text-xs leading-relaxed text-industrial-900 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2">
          <ShieldCheck className="mt-0.5 size-4 shrink-0 text-industrial-600" aria-hidden="true" />
          <p>
            <span className="font-semibold">Activation requires evidence.</span> A model must have
            a verified research evaluation, a compatible edge runtime and a registered artefact
            hash. Uploaded files are never executed by the API. The edge verifies the hash before
            loading the JSON artefact.
          </p>
        </div>
        {activeModel ? (
          <StatusBadge status={activeModel.status} label={`Active: ${activeModel.model_code}`} />
        ) : (
          <StatusBadge status="NO_DATA" label="No active model" />
        )}
      </div>

      {successMessage ? (
        <div className="rounded-xl border border-green-200 bg-success-soft px-4 py-3 text-sm text-green-800">
          {successMessage}
        </div>
      ) : null}

      {mutationError ? (
        <div role="alert" className="rounded-xl border border-red-200 bg-fault-soft px-4 py-3 text-sm text-red-800">
          {mutationError instanceof ApiClientError
            ? mutationError.message
            : 'The model action could not be completed.'}
        </div>
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Registered models"
          value={modelsQuery.isPending ? '—' : (modelsQuery.data?.total ?? 0)}
          hint="Model versions in the registry"
          icon={Boxes}
          tone="info"
        />
        <StatCard
          label="Validated models"
          value={modelsQuery.isPending ? '—' : validatedCount}
          hint="Evidence-reviewed and activation-eligible"
          icon={BadgeCheck}
          tone="accent"
        />
        <StatCard
          label="Active model"
          value={activeModel ? `${activeModel.model_code} v${activeModel.version}` : 'None'}
          hint={
            activeModel?.latest_evaluation
              ? `Balanced accuracy ${metricValue(activeModel.latest_evaluation.balanced_accuracy)} (synthetic)`
              : 'No verified evaluation on the active model'
          }
          icon={Activity}
          tone={activeModel ? 'success' : 'default'}
        />
        <StatCard
          label="Rollback available"
          value={canRollback ? 'Yes' : 'No'}
          hint="Restores the most recently retired active version"
          icon={GitBranch}
          tone={canRollback ? 'uncertain' : 'default'}
        />
      </div>

      {modelsQuery.isError ? (
        <QueryError
          error={modelsQuery.error}
          onRetry={() => modelsQuery.refetch()}
        />
      ) : modelsQuery.isPending ? (
        <div className="space-y-3">
          <Skeleton className="h-48 w-full" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : models.length === 0 ? (
        <Card>
          <CardContent className="p-5">
            <EmptyState
              icon={Boxes}
              title="No model versions registered"
              description="Run the research pipeline to train, evaluate and register a synthetic model. Models cannot be activated without verified evaluation evidence."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {models.map((model) => (
            <ModelCard
              key={model.id}
              model={model}
              busy={busy}
              onValidate={() => validateMutation.mutate(model.id)}
              onActivate={() => activateMutation.mutate(model.id)}
            />
          ))}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Terminal className="size-4 text-accent-600" aria-hidden="true" />
            Register from the research pipeline
          </CardTitle>
          <CardDescription>
            Model files are created outside the web application. This API records metadata,
            evaluation evidence and hashes; it never executes an uploaded model.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2">
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-navy-950 p-3 font-mono text-[10px] leading-relaxed text-accent-100">
{`apps/api/.venv/Scripts/python -m pip install -e ml
$env:PETROSENSE_ML_PASSWORD = "<researcher password>"
apps/api/.venv/Scripts/python -m petrosense_ml.pipeline --register`}
          </pre>
          <p className="text-[10px] leading-relaxed text-slate-400">
            The generated evaluation report is synthetic and is not evidence of real-pump
            fault-detection performance.
          </p>
        </CardContent>
      </Card>

      <ResearchNotice compact />
    </div>
  )
}

export { ModelsPage }


