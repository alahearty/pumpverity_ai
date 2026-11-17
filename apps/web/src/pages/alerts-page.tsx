import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type {
  Alert,
  AlertCategory,
  AlertDetail,
  AlertSeverity,
  AlertStatus,
  PredictionDecision,
  ReviewAction,
} from '@petrosense/shared-contracts'
import {
  BellRing,
  CheckCheck,
  ChevronLeft,
  ChevronRight,
  ClipboardList,
  FileText,
  LockKeyhole,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  Tags,
  UserCheck,
} from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { ProvenanceBadge } from '@/components/shared/provenance-badge'
import { QueryError } from '@/components/shared/query-error'
import { ResearchNotice } from '@/components/shared/research-notice'
import { StatCard } from '@/components/shared/stat-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { Badge, type BadgeProps } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { useAuth } from '@/providers/auth-provider'
import { useCopilotPageContext } from '@/providers/copilot-context-provider'
import { formatDateTime, formatScenario, pluralise } from '@/lib/utils'
import {
  acknowledgeAlert,
  createAlertReview,
  fetchAlert,
  fetchAlerts,
} from '@/services/alerts-service'
import { fetchPumps } from '@/services/equipment-service'

interface AlertFilters {
  status: AlertStatus | 'ALL'
  category: AlertCategory | 'ALL'
  severity: AlertSeverity | 'ALL'
  pumpId: string
}

const DEFAULT_FILTERS: AlertFilters = {
  status: 'ALL',
  category: 'ALL',
  severity: 'ALL',
  pumpId: '',
}

const STATUS_OPTIONS: Array<AlertStatus | 'ALL'> = [
  'ALL',
  'OPEN',
  'ACKNOWLEDGED',
  'REVIEWED',
  'CLOSED',
  'DISMISSED',
]

const CATEGORY_OPTIONS: Array<AlertCategory | 'ALL'> = [
  'ALL',
  'FAULT',
  'UNCERTAIN',
  'SENSOR_INVALID',
]

const SEVERITY_OPTIONS: Array<AlertSeverity | 'ALL'> = [
  'ALL',
  'LOW',
  'MEDIUM',
  'HIGH',
  'CRITICAL',
]

const REVIEW_OPTIONS: Array<{
  value: Exclude<ReviewAction, 'ACKNOWLEDGE'>
  label: string
}> = [
  { value: 'REVIEW', label: 'Record engineering review' },
  { value: 'CONFIRM_LABEL', label: 'Confirm prediction label' },
  { value: 'CORRECT_LABEL', label: 'Correct prediction label' },
  { value: 'ADD_NOTE', label: 'Add note' },
  { value: 'CLOSE', label: 'Close alert' },
]

const LABEL_OPTIONS: PredictionDecision[] = [
  'NORMAL',
  'FAULT',
  'UNCERTAIN',
  'SENSOR_INVALID',
]

const ACTION_META: Record<
  ReviewAction,
  { label: string; variant: BadgeProps['variant'] }
> = {
  ACKNOWLEDGE: { label: 'Acknowledged', variant: 'info' },
  REVIEW: { label: 'Reviewed', variant: 'success' },
  CONFIRM_LABEL: { label: 'Label confirmed', variant: 'success' },
  CORRECT_LABEL: { label: 'Label corrected', variant: 'uncertain' },
  ADD_NOTE: { label: 'Note added', variant: 'neutral' },
  CLOSE: { label: 'Closed', variant: 'outline' },
}

function statusLabel(status: string): string {
  return status
    .toLowerCase()
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

function scoreValue(value: number | null): string {
  return typeof value === 'number' ? value.toFixed(4) : 'Not available'
}

function isClosed(alert: Alert): boolean {
  return alert.status === 'CLOSED' || alert.status === 'DISMISSED'
}

function AlertQueueItem({
  alert,
  selected,
  onSelect,
}: {
  alert: Alert
  selected: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-current={selected ? 'true' : undefined}
      className={`w-full rounded-lg border px-3 py-3 text-left transition ${
        selected
          ? 'border-industrial-300 bg-industrial-50'
          : 'border-transparent hover:border-slate-200 hover:bg-slate-50'
      }`}
    >
      <div className="flex flex-wrap items-center gap-1.5">
        <StatusBadge status={alert.category} />
        <StatusBadge status={alert.severity} />
        <StatusBadge status={alert.status} />
        {alert.review_count > 0 ? (
          <Badge variant="outline">{alert.review_count} reviews</Badge>
        ) : null}
      </div>
      <p className="mt-2 text-xs font-semibold leading-snug text-navy-900">
        {alert.title}
      </p>
      <div className="mt-1.5 flex flex-wrap items-center justify-between gap-2 text-[10px] text-slate-500">
        <span>
          {alert.pump_code} / {alert.sensor_code}
        </span>
        <span>{formatDateTime(alert.created_at)}</span>
      </div>
      <p className="mt-1 text-[10px] text-slate-400">
        {alert.assigned_reviewer_name
          ? `Assigned to ${alert.assigned_reviewer_name}`
          : 'Unassigned'}
      </p>
    </button>
  )
}

function ReviewTimeline({ alert }: { alert: AlertDetail }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <CardTitle className="text-sm">Engineering review trail</CardTitle>
        <Badge variant="neutral">{alert.reviews.length}</Badge>
      </div>
      {alert.reviews.length === 0 ? (
        <p className="rounded-lg border border-dashed border-slate-300 bg-slate-50/60 p-4 text-xs leading-relaxed text-slate-500">
          No reviews recorded. Acknowledgement, notes and label decisions will be appended here
          with reviewer identity and timestamps.
        </p>
      ) : (
        <ol className="space-y-2.5">
          {alert.reviews.map((review) => {
            const meta = ACTION_META[review.action]
            return (
              <li
                key={review.id}
                className="rounded-lg border border-slate-200 bg-white p-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <Badge variant={meta.variant}>{meta.label}</Badge>
                  <span className="text-[10px] text-slate-400">
                    {formatDateTime(review.created_at)}
                  </span>
                </div>
                <p className="mt-1.5 text-xs font-medium text-navy-900">
                  {review.reviewer_name}
                </p>
                {review.reviewed_label ? (
                  <div className="mt-1.5 flex items-center gap-1.5 text-[10px] text-slate-500">
                    <span>Reviewed label</span>
                    <StatusBadge status={review.reviewed_label} />
                  </div>
                ) : null}
                {review.notes ? (
                  <p className="mt-1.5 whitespace-pre-line text-xs leading-relaxed text-slate-600">
                    {review.notes}
                  </p>
                ) : null}
                <p className="mt-2 text-[10px] text-slate-400">
                  Engineer review - not verified ground truth
                </p>
              </li>
            )
          })}
        </ol>
      )}
    </div>
  )
}

function AlertReviewActions({ alert }: { alert: AlertDetail }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const canWrite =
    user?.role === 'ENGINEER' ||
    user?.role === 'REVIEWER' ||
    user?.role === 'ADMINISTRATOR'
  const closed = isClosed(alert)
  const [action, setAction] =
    useState<Exclude<ReviewAction, 'ACKNOWLEDGE'>>('REVIEW')
  const [label, setLabel] = useState<PredictionDecision>(
    alert.decision ?? 'FAULT',
  )
  const [notes, setNotes] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['alert', alert.id] })
    queryClient.invalidateQueries({ queryKey: ['alerts'] })
    queryClient.invalidateQueries({ queryKey: ['monitoring-overview'] })
  }

  const acknowledgeMutation = useMutation({
    mutationFn: () => acknowledgeAlert(alert.id),
    onSuccess: (updated) => {
      queryClient.setQueryData(['alert', alert.id], updated)
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['monitoring-overview'] })
      setSuccessMessage('Alert acknowledged and assigned to you.')
      setFormError(null)
    },
  })

  const reviewMutation = useMutation({
    mutationFn: () =>
      createAlertReview({
        alert_id: alert.id,
        action,
        reviewed_label:
          action === 'CONFIRM_LABEL' || action === 'CORRECT_LABEL'
            ? label
            : null,
        notes: notes.trim(),
      }),
    onSuccess: () => {
      setNotes('')
      setSuccessMessage('Engineering review recorded without changing the original prediction.')
      setFormError(null)
      invalidate()
    },
  })

  const mutationError = acknowledgeMutation.error ?? reviewMutation.error
  const busy = acknowledgeMutation.isPending || reviewMutation.isPending
  const needsLabel = action === 'CONFIRM_LABEL' || action === 'CORRECT_LABEL'
  const needsNotes = action === 'REVIEW' || action === 'ADD_NOTE'

  function submitReview(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setFormError(null)
    setSuccessMessage(null)
    if (needsNotes && notes.trim().length < 3) {
      setFormError('Add at least three characters of engineering notes for this action.')
      return
    }
    if (needsLabel && action === 'CONFIRM_LABEL' && label !== alert.decision) {
      setFormError('A confirmed label must match the original prediction. Use correction instead.')
      return
    }
    if (needsLabel && action === 'CORRECT_LABEL' && label === alert.decision) {
      setFormError('A corrected label must differ from the original prediction.')
      return
    }
    reviewMutation.mutate()
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_340px]">
      <div className="space-y-5">
        <ReviewTimeline alert={alert} />
      </div>

      <div className="space-y-3 rounded-xl border border-slate-200 bg-slate-50/50 p-4">
        <div className="flex items-center gap-2">
          <CheckCheck className="size-4 text-industrial-600" aria-hidden="true" />
          <p className="text-sm font-semibold text-navy-900">Review actions</p>
        </div>

        {!canWrite ? (
          <p className="rounded-lg border border-slate-200 bg-white p-3 text-xs leading-relaxed text-slate-500">
            <LockKeyhole className="mr-1.5 inline size-3.5" aria-hidden="true" />
            Your role can inspect alerts but cannot acknowledge or record engineering judgements.
          </p>
        ) : closed ? (
          <p className="rounded-lg border border-slate-200 bg-white p-3 text-xs leading-relaxed text-slate-500">
            This alert is closed. Its review trail remains available for audit and is never
            rewritten.
          </p>
        ) : (
          <>
            {alert.status === 'OPEN' ? (
              <Button
                className="w-full"
                size="sm"
                onClick={() => {
                  setSuccessMessage(null)
                  setFormError(null)
                  acknowledgeMutation.mutate()
                }}
                disabled={busy}
              >
                <UserCheck className="size-3.5" aria-hidden="true" />
                Acknowledge alert
              </Button>
            ) : (
              <p className="rounded-lg border border-industrial-200 bg-industrial-50 px-3 py-2 text-[11px] text-industrial-900">
                Acknowledged by {alert.assigned_reviewer_name ?? 'a reviewer'}.
              </p>
            )}

            <form className="space-y-3" onSubmit={submitReview}>
              <div className="space-y-1.5">
                <Label htmlFor="alert-review-action">Action</Label>
                <Select
                  id="alert-review-action"
                  value={action}
                  onChange={(event) =>
                    setAction(
                      event.target.value as Exclude<ReviewAction, 'ACKNOWLEDGE'>,
                    )
                  }
                  disabled={busy}
                >
                  {REVIEW_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </Select>
              </div>

              {needsLabel ? (
                <div className="space-y-1.5">
                  <Label htmlFor="alert-review-label">Reviewed label</Label>
                  <Select
                    id="alert-review-label"
                    value={label}
                    onChange={(event) =>
                      setLabel(event.target.value as PredictionDecision)
                    }
                    disabled={busy}
                  >
                    {LABEL_OPTIONS.map((option) => (
                      <option key={option} value={option}>
                        {statusLabel(option)}
                      </option>
                    ))}
                  </Select>
                  <p className="text-[10px] leading-relaxed text-slate-500">
                    Confirmation must match the original decision. Corrections must differ from
                    it. The original prediction row is never updated.
                  </p>
                </div>
              ) : null}

              <div className="space-y-1.5">
                <Label htmlFor="alert-review-notes">
                  Engineering notes{' '}
                  {needsNotes ? <span className="text-fault">(required)</span> : null}
                </Label>
                <Textarea
                  id="alert-review-notes"
                  value={notes}
                  onChange={(event) => setNotes(event.target.value)}
                  placeholder="Record observed evidence, operating context and the reason for this judgement."
                  maxLength={5000}
                  disabled={busy}
                />
              </div>

              <Button type="submit" variant="secondary" className="w-full" disabled={busy}>
                <ClipboardList className="size-3.5" aria-hidden="true" />
                {reviewMutation.isPending ? 'Recording...' : 'Record review'}
              </Button>
            </form>
          </>
        )}

        {formError ? (
          <p className="rounded-lg border border-amber-200 bg-amber-50 p-2.5 text-[11px] leading-relaxed text-amber-900">
            {formError}
          </p>
        ) : null}
        {mutationError ? (
          <p className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-[11px] leading-relaxed text-red-700">
            {mutationError instanceof Error
              ? mutationError.message
              : 'The alert action could not be recorded.'}
          </p>
        ) : null}
        {successMessage ? (
          <p className="rounded-lg border border-green-200 bg-green-50 p-2.5 text-[11px] leading-relaxed text-green-700">
            {successMessage}
          </p>
        ) : null}
      </div>
    </div>
  )
}

function AlertDetailPanel({ alert }: { alert: AlertDetail }) {
  return (
    <div className="space-y-5">
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-1.5">
          <StatusBadge status={alert.category} />
          <StatusBadge status={alert.severity} />
          <StatusBadge status={alert.status} />
          <ProvenanceBadge provenance={alert.data_provenance} />
        </div>
        <div>
          <h2 className="text-lg font-semibold tracking-tight text-navy-900">
            {alert.title}
          </h2>
          <p className="mt-1 text-xs text-slate-500">
            {alert.pump_code} / {alert.sensor_code} - opened {formatDateTime(alert.created_at)}
          </p>
        </div>
        <p className="whitespace-pre-line rounded-lg border border-slate-200 bg-slate-50/70 p-3 text-xs leading-relaxed text-slate-600">
          {alert.description}
        </p>
      </div>

      <div className="grid gap-3 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Original AI prediction</CardTitle>
            <CardDescription>
              Immutable evidence retained with the alert.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-xs">
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-500">Decision</span>
              {alert.decision ? <StatusBadge status={alert.decision} /> : 'Not available'}
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-500">Data quality</span>
              {alert.data_quality ? (
                <StatusBadge status={alert.data_quality} />
              ) : (
                'Not available'
              )}
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-500">Decision score</span>
              <span className="font-mono text-[11px] text-navy-900">
                {scoreValue(alert.decision_score)}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-500">Uncertainty</span>
              <span className="font-mono text-[11px] text-navy-900">
                {scoreValue(alert.uncertainty_score)}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-500">Model</span>
              <span className="text-right font-medium text-navy-900">
                {alert.model_name
                  ? `${alert.model_name} v${alert.model_version}`
                  : 'No model inference'}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-500">Scenario</span>
              <span className="font-medium text-navy-900">
                {formatScenario(alert.prediction?.scenario ?? null)}
              </span>
            </div>
            {alert.prediction?.explanation ? (
              <p className="rounded-lg border border-slate-200 bg-slate-50 p-2.5 text-[11px] leading-relaxed text-slate-500">
                {alert.prediction.explanation}
              </p>
            ) : null}
            <p className="flex items-start gap-1.5 border-t border-slate-100 pt-2 text-[10px] leading-relaxed text-slate-400">
              <FileText className="mt-0.5 size-3 shrink-0" aria-hidden="true" />
              Review labels are appended as engineering judgements and never overwrite this
              prediction.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Traceability</CardTitle>
            <CardDescription>
              Source records for audit and reproducibility.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-[11px]">
            <div className="flex items-start justify-between gap-3">
              <span className="text-slate-500">Alert ID</span>
              <span className="break-all text-right font-mono text-slate-600">
                {alert.id}
              </span>
            </div>
            <div className="flex items-start justify-between gap-3">
              <span className="text-slate-500">Prediction ID</span>
              <span className="break-all text-right font-mono text-slate-600">
                {alert.prediction_id ?? 'Not linked'}
              </span>
            </div>
            <div className="flex items-start justify-between gap-3">
              <span className="text-slate-500">Signal window</span>
              <span className="text-right font-mono text-slate-600">
                {alert.signal_window_id ?? 'Not linked'}
              </span>
            </div>
            <div className="flex items-start justify-between gap-3">
              <span className="text-slate-500">Window interval</span>
              <span className="text-right text-slate-600">
                {alert.window_start
                  ? `${formatDateTime(alert.window_start)} to ${formatDateTime(alert.window_end)}`
                  : 'Not available'}
              </span>
            </div>
            <div className="flex items-start justify-between gap-3">
              <span className="text-slate-500">Assigned reviewer</span>
              <span className="text-right text-slate-600">
                {alert.assigned_reviewer_name ?? 'Unassigned'}
              </span>
            </div>
            <div className="flex items-start justify-between gap-3">
              <span className="text-slate-500">Acknowledged</span>
              <span className="text-right text-slate-600">
                {formatDateTime(alert.acknowledged_at)}
              </span>
            </div>
            <div className="flex items-start justify-between gap-3">
              <span className="text-slate-500">Closed</span>
              <span className="text-right text-slate-600">
                {formatDateTime(alert.closed_at)}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <AlertReviewActions alert={alert} />
    </div>
  )
}

function AlertsPage() {
  const { alertId } = useParams()
  const navigate = useNavigate()
  const [filters, setFilters] = useState<AlertFilters>(DEFAULT_FILTERS)
  const [page, setPage] = useState(1)

  const alertsQuery = useQuery({
    queryKey: ['alerts', filters, page],
    queryFn: () =>
      fetchAlerts({
        page,
        page_size: 20,
        status: filters.status === 'ALL' ? undefined : filters.status,
        category: filters.category === 'ALL' ? undefined : filters.category,
        severity: filters.severity === 'ALL' ? undefined : filters.severity,
        pump_id: filters.pumpId || undefined,
      }),
    refetchInterval: 30_000,
    staleTime: 5_000,
  })
  const pumpsQuery = useQuery({
    queryKey: ['pumps', { page: 1, page_size: 100 }],
    queryFn: () => fetchPumps({ page: 1, page_size: 100 }),
    staleTime: 60_000,
  })

  const alerts = alertsQuery.data?.items ?? []
  const total = alertsQuery.data?.total ?? 0
  const pageSize = alertsQuery.data?.page_size ?? 20
  const detailId = alertId ?? alerts[0]?.id
  const detailQuery = useQuery({
    queryKey: ['alert', detailId],
    queryFn: () => fetchAlert(detailId as string),
    enabled: Boolean(detailId),
    refetchInterval: 20_000,
  })
  const openOnPage = alerts.filter((alert) => alert.status === 'OPEN').length
  const reviewCount = alerts.reduce((sum, alert) => sum + alert.review_count, 0)

  useCopilotPageContext({
    selectedPumpId: detailQuery.data?.pump_id ?? null,
    selectedSensorId: detailQuery.data?.sensor_id ?? null,
    selectedAlertId: detailQuery.data?.id ?? alertId ?? null,
    activeModelVersion: detailQuery.data?.model_version ?? null,
    monitoringMode: detailQuery.data?.data_provenance ?? 'SIMULATED',
    connectivityStatus: 'NO_LIVE_CHANNEL',
  })

  function updateFilter(patch: Partial<AlertFilters>) {
    setFilters((current) => ({ ...current, ...patch }))
    setPage(1)
    if (alertId) navigate('/alerts')
  }

  function resetFilters() {
    setFilters(DEFAULT_FILTERS)
    setPage(1)
    if (alertId) navigate('/alerts')
  }

  function selectAlert(alert: Alert) {
    navigate(`/alerts/${alert.id}`)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Fault alerts and engineering review"
        description="Triage fault, uncertain and sensor-invalid events, acknowledge them and append engineering judgements without mutating the original AI prediction."
        badge={<Badge variant="info">Review workflow active</Badge>}
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              alertsQuery.refetch()
              if (detailId) detailQuery.refetch()
              pumpsQuery.refetch()
            }}
            disabled={alertsQuery.isFetching}
          >
            <RefreshCw className="size-3.5" aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      <div className="flex items-start gap-3 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4 text-xs leading-relaxed text-industrial-900">
        <ShieldAlert className="mt-0.5 size-4 shrink-0 text-industrial-600" aria-hidden="true" />
        <p>
          <span className="font-semibold">Human review, not silent automation.</span> Every alert
          keeps its source prediction, signal window and model version. Engineer-reviewed labels
          are recorded as engineering judgement and are not automatically verified experimental
          ground truth.
        </p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Alerts matching filters"
          value={alertsQuery.isPending ? '...' : total}
          hint={`Page ${page} of ${Math.max(1, Math.ceil(total / pageSize))}`}
          icon={BellRing}
          tone="fault"
        />
        <StatCard
          label="Open on this page"
          value={alertsQuery.isPending ? '...' : openOnPage}
          hint="Awaiting acknowledgement"
          icon={ShieldAlert}
          tone={openOnPage > 0 ? 'uncertain' : 'success'}
        />
        <StatCard
          label="Reviews on this page"
          value={alertsQuery.isPending ? '...' : reviewCount}
          hint="Append-only engineering entries"
          icon={ClipboardList}
          tone="info"
        />
      </div>

      <Card>
        <CardContent className="grid gap-3 p-4 md:grid-cols-2 xl:grid-cols-5">
          <div className="space-y-1.5">
            <Label htmlFor="alert-filter-status">Status</Label>
            <Select
              id="alert-filter-status"
              value={filters.status}
              onChange={(event) =>
                updateFilter({
                  status: event.target.value as AlertStatus | 'ALL',
                })
              }
            >
              {STATUS_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === 'ALL' ? 'All statuses' : statusLabel(option)}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="alert-filter-category">Category</Label>
            <Select
              id="alert-filter-category"
              value={filters.category}
              onChange={(event) =>
                updateFilter({
                  category: event.target.value as AlertCategory | 'ALL',
                })
              }
            >
              {CATEGORY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === 'ALL' ? 'All categories' : statusLabel(option)}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="alert-filter-severity">Severity</Label>
            <Select
              id="alert-filter-severity"
              value={filters.severity}
              onChange={(event) =>
                updateFilter({
                  severity: event.target.value as AlertSeverity | 'ALL',
                })
              }
            >
              {SEVERITY_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option === 'ALL' ? 'All severities' : statusLabel(option)}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="alert-filter-pump">Pump</Label>
            <Select
              id="alert-filter-pump"
              value={filters.pumpId}
              onChange={(event) => updateFilter({ pumpId: event.target.value })}
            >
              <option value="">All pumps</option>
              {(pumpsQuery.data?.items ?? []).map((pump) => (
                <option key={pump.id} value={pump.id}>
                  {pump.pump_code}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex items-end">
            <Button
              variant="ghost"
              size="sm"
              className="w-full"
              onClick={resetFilters}
            >
              <RotateCcw className="size-3.5" aria-hidden="true" />
              Reset filters
            </Button>
          </div>
        </CardContent>
      </Card>

      {alertsQuery.isError ? (
        <QueryError error={alertsQuery.error} onRetry={() => alertsQuery.refetch()} />
      ) : null}

      <div className="grid gap-5 xl:grid-cols-[380px_minmax(0,1fr)]">
        <Card className="self-start">
          <CardHeader className="gap-2 pb-4">
            <div className="flex items-center justify-between gap-2">
              <CardTitle>Alert queue</CardTitle>
              <Badge variant="neutral">{total}</Badge>
            </div>
            <CardDescription>
              Newest first. Select an alert to inspect its immutable evidence and review trail.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 p-3 pt-0">
            {alertsQuery.isPending ? (
              <div className="space-y-2">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            ) : alerts.length === 0 ? (
              <EmptyState
                compact
                icon={BellRing}
                title="No alerts match"
                description="Fault, uncertain and sensor-invalid predictions create reviewable alerts. Run a simulated acquisition to generate one."
              />
            ) : (
              <div className="space-y-1">
                {alerts.map((alert) => (
                  <AlertQueueItem
                    key={alert.id}
                    alert={alert}
                    selected={detailId === alert.id}
                    onSelect={() => selectAlert(alert)}
                  />
                ))}
              </div>
            )}

            {total > pageSize ? (
              <div className="flex items-center justify-between gap-2 border-t border-slate-100 px-2 pt-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setPage((current) => Math.max(1, current - 1))}
                  disabled={page <= 1 || alertsQuery.isFetching}
                >
                  <ChevronLeft className="size-3.5" aria-hidden="true" />
                  Previous
                </Button>
                <span className="text-[10px] text-slate-500">
                  {pluralise(total, 'alert')}
                </span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setPage((current) => current + 1)}
                  disabled={page >= Math.ceil(total / pageSize) || alertsQuery.isFetching}
                >
                  Next
                  <ChevronRight className="size-3.5" aria-hidden="true" />
                </Button>
              </div>
            ) : null}
          </CardContent>
        </Card>

        <Card className="min-w-0">
          <CardContent className="p-4 sm:p-5">
            {detailQuery.isError ? (
              <QueryError
                error={detailQuery.error}
                onRetry={() => detailQuery.refetch()}
              />
            ) : detailQuery.isPending ? (
              <div className="space-y-4">
                <Skeleton className="h-6 w-56" />
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-40 w-full" />
              </div>
            ) : detailQuery.data ? (
              <AlertDetailPanel
                key={detailQuery.data.id}
                alert={detailQuery.data}
              />
            ) : (
              <EmptyState
                icon={Tags}
                title="Select an alert"
                description="Choose an alert from the queue to inspect the original prediction, acknowledge it and record an engineering review."
              />
            )}
          </CardContent>
        </Card>
      </div>

      <ResearchNotice compact />
    </div>
  )
}

export { AlertsPage }


