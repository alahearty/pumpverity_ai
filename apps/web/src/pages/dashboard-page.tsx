import { useQuery } from '@tanstack/react-query'
import {
  Activity,
  BellRing,
  BrainCircuit,
  CheckCircle2,
  Circle,
  Database,
  Gauge,
  KeyRound,
  Radio,
  RefreshCw,
  Server,
  ShieldAlert,
  ShieldCheck,
  Stethoscope,
  Waves,
  WifiOff,
} from 'lucide-react'

import { RmsTrendChart } from '@/components/charts/rms-trend-chart'
import { WaveformChart } from '@/components/charts/waveform-chart'
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
import { useAuth } from '@/providers/auth-provider'
import { useCopilotPageContext } from '@/providers/copilot-context-provider'
import { fetchHealth } from '@/services/health-service'
import { fetchSystemInfo } from '@/services/system-service'
import { fetchMonitoringOverview } from '@/services/monitoring-service'
import { formatDateTime, formatRole, formatScenario } from '@/lib/utils'

const VERIFICATION_CHECKS = [
  { label: 'Monitoring, SSE, sensor diagnostics and history views', done: true },
  { label: 'Versioned feature contract and edge inference pipeline', done: true },
  { label: 'Uncertainty abstention and sensor-invalid suppression', done: true },
  { label: 'Model registry with synthetic validation, activation and rollback', done: true },
  { label: 'Immutable predictions and AI analysis interface', done: true },
  { label: 'Backend automated tests (74 passing)', done: true },
  { label: 'Edge simulation, feature, inference and decision tests (38 passing)', done: true },
  { label: 'ML pipeline tests (3 passing) and synthetic comparison report', done: true },
  { label: 'Frontend automated tests (41 passing) and production build', done: true },
  { label: 'Playwright auth, equipment, live/SSE, alerts and Copilot tests (7 passing)', done: true },
]

function DashboardPage() {
  const { user } = useAuth()
  const health = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 60_000,
    retry: 1,
    staleTime: 30_000,
  })
  const systemInfo = useQuery({
    queryKey: ['system-info'],
    queryFn: fetchSystemInfo,
    staleTime: 5 * 60_000,
  })
  const overviewQuery = useQuery({
    queryKey: ['monitoring-overview'],
    queryFn: fetchMonitoringOverview,
    refetchInterval: 15_000,
    staleTime: 5_000,
  })

  const overview = overviewQuery.data
  const latest = overview?.latest_window
  const latestPrediction = overview?.latest_prediction
  const trend = overview?.trend ?? []
  const activeModel = overview?.active_model
  const latestEvaluation = overview?.latest_evaluation
  const quality = overview?.data_quality ?? null

  useCopilotPageContext({
    selectedPumpId: null,
    selectedSensorId: null,
    activeModelVersion: activeModel?.version ?? null,
    operatingRegime: null,
    monitoringMode: overview?.latest_window?.data_provenance ?? 'SIMULATED',
    connectivityStatus: overview?.edge_connectivity ?? 'NO_LIVE_CHANNEL',
  })

  const apiTone = health.isError
    ? 'fault'
    : health.data?.status === 'ok'
      ? 'success'
      : 'uncertain'
  const apiValue = health.isError
    ? 'Unreachable'
    : health.isPending
      ? 'Checking…'
      : health.data?.status === 'ok'
        ? 'Operational'
        : 'Degraded'

  function refreshStatus() {
    health.refetch()
    systemInfo.refetch()
    overviewQuery.refetch()
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations overview"
        title="Dashboard"
        description="Operational monitoring state from persisted simulated windows: model decisions, uncertainty, sensor health, acquisition activity and reviewable alerts."
        badge={<Badge variant="info">Monitoring & review</Badge>}
        actions={
          <Button variant="secondary" size="sm" onClick={refreshStatus}>
            <RefreshCw className="size-3.5" aria-hidden="true" />
            Refresh status
          </Button>
        }
      />

      <div className="flex items-start gap-3 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4">
        <Activity className="mt-0.5 size-4 shrink-0 text-industrial-600" aria-hidden="true" />
        <div className="space-y-1 text-xs leading-relaxed text-industrial-900">
          <p className="font-semibold">Live replay, not a certified live channel</p>
          <p className="text-industrial-900/75">
            The dashboard reflects persisted provenance-tagged windows and an authenticated SSE
            update stream. Equipment condition is shown only when a current model prediction exists;
            otherwise it is explicitly not inferred. No physical edge channel is connected.
          </p>
        </div>
      </div>

      {overviewQuery.isError ? (
        <QueryError
          error={overviewQuery.error}
          onRetry={() => overviewQuery.refetch()}
        />
      ) : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Monitoring API"
          value={apiValue}
          hint={
            health.data
              ? `${health.data.service} · v${health.data.version} · DB ${health.data.database}`
              : 'Live readiness check of the local FastAPI service'
          }
          icon={Server}
          tone={apiTone}
        />
        <StatCard
          label="Equipment condition"
          value={
            overview?.condition_available && overview.equipment_condition ? (
              <StatusBadge status={overview.equipment_condition} />
            ) : (
              <Badge variant="outline">Not inferred</Badge>
            )
          }
          hint={
            latestPrediction && latestPrediction.decision !== 'SENSOR_INVALID'
              ? `${latestPrediction.model?.name ?? 'Model'} v${latestPrediction.model?.version ?? '—'} · score ${latestPrediction.decision_score?.toFixed(4) ?? '—'} · uncertainty ${latestPrediction.uncertainty_score?.toFixed(4) ?? '—'}`
              : quality === 'SENSOR_INVALID'
                ? 'Inference suppressed by sensor validation.'
                : overview
                  ? `${overview.pumps_total} pump(s), ${overview.sensors_active} active sensor(s). No current inference for the latest window.`
                  : 'No current inference available.'
          }
          icon={BrainCircuit}
          tone={
            overview?.equipment_condition === 'FAULT'
              ? 'fault'
              : overview?.equipment_condition === 'UNCERTAIN'
                ? 'uncertain'
                : overview?.condition_available
                  ? 'success'
                  : 'default'
          }
        />
        <StatCard
          label="Data quality"
          value={<StatusBadge status={quality ?? 'NO_DATA'} />}
          hint={
            latest
              ? `Latest window ${formatDateTime(latest.window_end)} · ${overview?.invalid_windows ?? 0} invalid total`
              : 'No persisted window yet'
          }
          icon={ShieldAlert}
          tone={quality === 'SENSOR_INVALID' ? 'sensor' : 'info'}
        />
        <StatCard
          label="Active alerts"
          value={overview?.active_alerts ?? 0}
          hint="Open Alerts & Review to acknowledge and record an outcome."
          icon={BellRing}
          tone={(overview?.active_alerts ?? 0) > 0 ? 'fault' : 'default'}
        />
        <StatCard
          label="Sensor health"
          value={overview ? `${overview.sensors_with_data}/${overview.sensors_total}` : '—'}
          hint={
            overview
              ? `${overview.sensors_invalid} invalid latest, ${overview.sensors_stale} stale, ${overview.sensors_no_data} no data`
              : 'Sensor diagnostics unavailable'
          }
          icon={Stethoscope}
          tone={overview?.sensors_invalid ? 'sensor' : 'success'}
        />
        <StatCard
          label="Edge connectivity"
          value={
            <Badge variant="neutral">
              <WifiOff className="size-3" aria-hidden="true" />
              No live channel
            </Badge>
          }
          hint={overview?.edge_note ?? 'Persisted simulated windows; offline synchronisation is not configured.'}
          icon={Radio}
          tone="default"
        />
        <StatCard
          label="Latest model"
          value={
            activeModel
              ? `${activeModel.name} v${activeModel.version}`
              : latestEvaluation
                ? 'No active model'
                : 'Not evaluated'
          }
          hint={
            activeModel
              ? `Macro-F1 ${activeModel.macro_f1 ?? '—'} · ${activeModel.evaluation_dataset ?? 'no dataset'}`
              : latestEvaluation
                ? `Last evaluation: ${latestEvaluation.dataset_name}`
                : 'No active model or verified evaluation is available.'
          }
          icon={Database}
          tone={activeModel ? 'success' : 'uncertain'}
        />
        <StatCard
          label="Simulated acquisition"
          value={overview?.sessions_total ?? '—'}
          hint={
            overview
              ? `${overview.windows_total} window(s), ${overview.valid_windows} valid.`
              : 'Acquisition counts unavailable'
          }
          icon={Activity}
          tone="accent"
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-5">
          <Card>
            <CardHeader className="flex-row items-start justify-between gap-4 pb-3">
              <div>
                <CardTitle>Latest vibration preview</CardTitle>
                <CardDescription>
                  Latest persisted window, or the RMS trend when the newest window is
                  sensor-invalid.
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-1.5">
                <Badge variant="outline">model output</Badge>
                <StatusBadge status="SIMULATED" />
              </div>
            </CardHeader>
            <CardContent>
              {overviewQuery.isPending ? (
                <Skeleton className="h-56 w-full" />
              ) : latest?.waveform ? (
                <WaveformChart window={latest} height={220} />
              ) : trend.some((window) => window.rms !== null) ? (
                <RmsTrendChart windows={trend} height={220} />
              ) : (
                <EmptyState
                  icon={Activity}
                  title={
                    latest?.quality_status === 'SENSOR_INVALID'
                      ? 'Latest window is sensor-invalid'
                      : 'No vibration data yet'
                  }
                  description={
                    latest?.quality_status === 'SENSOR_INVALID'
                      ? 'No waveform is presented as current. Earlier valid windows may be visible in Live Monitoring.'
                      : 'Run the edge simulator to persist a simulated window. The dashboard never fabricates a preview.'
                  }
                />
              )}
              <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
                {latest ? (
                  <>
                    <span>{latest.pump_code}</span>
                    <span>·</span>
                    <span>{latest.sensor_code}</span>
                    <span>·</span>
                    <span>{latest.units ?? 'units unavailable'}</span>
                    <span>·</span>
                    <span>{formatDateTime(latest.window_end)}</span>
                    <span>·</span>
                    <span>RMS {latest.rms !== null ? `${latest.rms.toFixed(4)} g` : '—'}</span>
                  </>
                ) : (
                  <span>No persisted window</span>
                )}
                <ProvenanceBadge
                  provenance={latest?.data_provenance ?? 'SIMULATED'}
                  className="ml-auto"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Recent acquisition activity</CardTitle>
              <CardDescription>
                Latest simulated sessions. Engineering reviews are appended without rewriting the original predictions.
              </CardDescription>
            </CardHeader>
            <CardContent>
              {overviewQuery.isPending ? (
                <div className="space-y-2">
                  <Skeleton className="h-12 w-full" />
                  <Skeleton className="h-12 w-full" />
                </div>
              ) : overview && overview.recent_sessions.length > 0 ? (
                <div className="divide-y divide-slate-100">
                  {overview.recent_sessions.map((session) => (
                    <div
                      key={session.id}
                      className="flex flex-col gap-2 py-3 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-navy-900">
                          {formatScenario(session.scenario)}
                        </p>
                        <p className="text-[11px] text-slate-500">
                          {session.pump_code} / {session.sensor_code} · started{' '}
                          {formatDateTime(session.started_at)}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge status={session.status} />
                        <StatusBadge status={session.data_provenance} />
                        <span className="text-[11px] text-slate-500">
                          {session.window_count} windows
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  compact
                  icon={Waves}
                  title="No acquisition activity"
                  description="Run the edge simulator against a registered pump to populate the monitoring view."
                />
              )}
            </CardContent>
          </Card>

          <div className="grid gap-5 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Prototype verification gate</CardTitle>
                <CardDescription>What Stages 1–3 have actually demonstrated.</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2.5">
                  {VERIFICATION_CHECKS.map((check) => (
                    <li key={check.label} className="flex gap-2.5 text-xs leading-relaxed">
                      {check.done ? (
                        <CheckCircle2
                          className="mt-0.5 size-3.5 shrink-0 text-accent-600"
                          aria-hidden="true"
                        />
                      ) : (
                        <Circle
                          className="mt-0.5 size-3.5 shrink-0 text-slate-300"
                          aria-hidden="true"
                        />
                      )}
                      <span className={check.done ? 'text-slate-600' : 'text-slate-400'}>
                        {check.label}
                      </span>
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Data quality and provenance</CardTitle>
                <CardDescription>
                  Simulation and experiment are never conflated.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex flex-wrap gap-1.5">
                  <StatusBadge status={quality ?? 'NO_DATA'} />
                  <StatusBadge status="SIMULATED" />
                  <StatusBadge status="NO_LIVE_CHANNEL" />
                </div>
                <p className="text-xs leading-relaxed text-slate-500">
                  Persisted simulated windows are labelled at storage, API and UI level.
                  Sensor-invalid windows keep their validation summary and never display a current
                  NORMAL/FAULT inference.
                </p>
                <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] leading-relaxed text-slate-600">
                  <span className="font-semibold text-navy-900">Ground truth:</span> engineer review
                  labels will not be promoted automatically to verified experimental ground truth.
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Account & session</CardTitle>
              <CardDescription>Current authenticated session.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <div className="flex size-10 items-center justify-center rounded-full bg-accent-50 text-sm font-semibold text-accent-700">
                  {user?.full_name
                    .split(' ')
                    .map((part) => part[0])
                    .slice(0, 2)
                    .join('')}
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-navy-900">{user?.full_name}</p>
                  <p className="truncate text-xs text-slate-500">{user?.email}</p>
                </div>
              </div>
              <dl className="space-y-2.5 border-t border-slate-100 pt-3 text-xs">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-slate-500">Role</dt>
                  <dd>
                    {user ? <StatusBadge status={user.role} label={formatRole(user.role)} /> : '—'}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-slate-500">Last sign-in</dt>
                  <dd className="text-right font-medium text-navy-900">
                    {formatDateTime(user?.last_login_at)}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-slate-500">Access token</dt>
                  <dd className="font-medium text-navy-900">
                    {systemInfo.data
                      ? `${systemInfo.data.access_token_minutes} min`
                      : systemInfo.isError
                        ? 'Unavailable'
                        : <Skeleton className="h-3.5 w-12" />}
                  </dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-slate-500">Refresh session</dt>
                  <dd className="font-medium text-navy-900">
                    {systemInfo.data
                      ? `${systemInfo.data.refresh_token_days} days`
                      : systemInfo.isError
                        ? 'Unavailable'
                        : <Skeleton className="h-3.5 w-12" />}
                  </dd>
                </div>
              </dl>
              <div className="flex items-center gap-2 rounded-lg bg-slate-50 px-3 py-2 text-[11px] text-slate-500">
                <KeyRound className="size-3.5 text-slate-400" aria-hidden="true" />
                Access token is held in memory; refresh uses an HttpOnly cookie.
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Gauge className="size-4 text-accent-600" aria-hidden="true" />
                Interpretation limits
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-xs leading-relaxed text-slate-500">
              <p>
                The workspace presents model decisions and abstention as research outputs. A decision
                score is not a failure probability, and no real-pump accuracy or automatic shutdown
                claim is made.
              </p>
              <p>
                The SSE stream indicates API update delivery, not physical sensor connectivity.
                Edge connectivity remains not configured in this build.
              </p>
              <div className="flex flex-wrap gap-1.5 pt-1">
                <StatusBadge status="NO_LIVE_CHANNEL" />
                {overview?.condition_available && overview.equipment_condition ? (
                  <StatusBadge status={overview.equipment_condition} />
                ) : (
                  <Badge variant="outline">Condition: not inferred</Badge>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <ShieldCheck className="size-4 text-accent-600" aria-hidden="true" />
                Provenance policy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <ProvenanceBadge provenance="SIMULATED" />
              <p className="text-xs leading-relaxed text-slate-500">
                Simulated signals are suitable for integration testing, not for establishing
                real-world fault-detection accuracy.
              </p>
            </CardContent>
          </Card>

          <ResearchNotice compact />
        </div>
      </div>
    </div>
  )
}

export { DashboardPage }






