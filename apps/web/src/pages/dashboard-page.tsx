import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Activity,
  ArrowUpRight,
  BellRing,
  Database,
  ShieldAlert,
  Stethoscope,
  Workflow,
} from 'lucide-react'
import { useCallback } from 'react'
import { Link } from 'react-router-dom'

import { RmsTrendChart } from '@/components/charts/rms-trend-chart'
import { WaveformChart } from '@/components/charts/waveform-chart'
import { ConditionHero } from '@/components/dashboard/condition-hero'
import { DecisionTimelineChart } from '@/components/dashboard/decision-timeline-chart'
import { LiveEventFeed } from '@/components/dashboard/live-event-feed'
import { DecisionPipelineCard } from '@/components/shared/decision-pipeline-card'
import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { QueryError } from '@/components/shared/query-error'
import { StatCard } from '@/components/shared/stat-card'
import { StatusBadge } from '@/components/shared/status-badge'
import { Badge } from '@/components/ui/badge'
import { buttonVariants } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { useMonitoringStream } from '@/hooks/use-monitoring-stream'
import { useNow } from '@/hooks/use-now'
import type { SseEvent } from '@/lib/api'
import { useCopilotPageContext } from '@/providers/copilot-context-provider'
import { fetchAlerts } from '@/services/alerts-service'
import { fetchDemoControl } from '@/services/demo-service'
import { fetchPumps } from '@/services/equipment-service'
import { fetchMonitoringOverview } from '@/services/monitoring-service'
import { fetchPredictions } from '@/services/predictions-service'

const TIMELINE_WINDOWS = 90

function LegendDot({ className, label }: { className: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`size-2 rounded-full ${className}`} />
      {label}
    </span>
  )
}

function DashboardPage() {
  const queryClient = useQueryClient()
  const now = useNow()

  const overviewQuery = useQuery({
    queryKey: ['monitoring-overview'],
    queryFn: fetchMonitoringOverview,
    refetchInterval: 2_000,
    staleTime: 1_000,
  })
  const overview = overviewQuery.data
  const latest = overview?.latest_window ?? null
  const latestPrediction = overview?.latest_prediction ?? null

  const pumpsQuery = useQuery({
    queryKey: ['pumps', { page: 1, page_size: 100 }],
    queryFn: () => fetchPumps({ page: 1, page_size: 100 }),
  })
  const pump =
    pumpsQuery.data?.items.find((item) => item.id === latest?.pump_id) ??
    pumpsQuery.data?.items[0]
  const sensor =
    pump?.sensors.find((item) => item.id === latest?.sensor_id) ?? pump?.sensors[0]
  const pumpId = pump?.id

  const predictionsQuery = useQuery({
    queryKey: ['predictions', 'dashboard-timeline', pumpId],
    queryFn: () => fetchPredictions({ pump_id: pumpId, page_size: TIMELINE_WINDOWS }),
    enabled: Boolean(pumpId),
    refetchInterval: 2_000,
    staleTime: 1_000,
  })
  const alertsQuery = useQuery({
    queryKey: ['alerts', 'dashboard-feed', pumpId],
    queryFn: () => fetchAlerts({ pump_id: pumpId, page_size: 8 }),
    enabled: Boolean(pumpId),
    refetchInterval: 2_000,
    staleTime: 1_000,
  })
  const demoControl = useQuery({
    queryKey: ['demo-control'],
    queryFn: fetchDemoControl,
    refetchInterval: 2_000,
    retry: false,
  })

  const handleStreamEvent = useCallback(
    (event: SseEvent) => {
      if (event.event === 'reading' || event.event === 'prediction') {
        queryClient.invalidateQueries({ queryKey: ['monitoring-overview'] }, { cancelRefetch: false })
        queryClient.invalidateQueries({ queryKey: ['predictions', 'dashboard-timeline'] }, { cancelRefetch: false })
        queryClient.invalidateQueries({ queryKey: ['alerts', 'dashboard-feed'] }, { cancelRefetch: false })
      }
    },
    [queryClient],
  )
  useMonitoringStream({ pumpId, sensorId: sensor?.id, onEvent: handleStreamEvent })

  useCopilotPageContext({
    selectedPumpId: pumpId ?? null,
    selectedSensorId: sensor?.id ?? null,
    activeModelVersion: overview?.active_model?.version ?? null,
    operatingRegime: latestPrediction?.operating_regime?.code ?? null,
    monitoringMode: latest?.data_provenance ?? 'SIMULATED',
    connectivityStatus: overview?.edge_connectivity ?? 'NO_LIVE_CHANNEL',
  })

  const predictions = predictionsQuery.data?.items ?? []
  const alerts = alertsQuery.data?.items ?? []
  const streamOnline = Boolean(demoControl.data?.enabled && demoControl.data.driver_online)
  const validShare =
    overview && overview.windows_total > 0
      ? Math.round((overview.valid_windows / overview.windows_total) * 100)
      : null
  const activeModel = overview?.active_model

  return (
    <div className="space-y-5">
      <PageHeader
        eyebrow="Operations console"
        title="Dashboard"
        description="Live condition of the centrifugal-pump test rig, decided at the edge and qualified before any claim is made."
        badge={<StatusBadge status="SIMULATED" label="Simulated stream" />}
        actions={
          <>
            <Link to="/monitoring" className={buttonVariants({ variant: 'secondary', size: 'sm' })}>
              <Activity aria-hidden="true" />
              Live signal
            </Link>
            <Link to="/alerts" className={buttonVariants({ variant: 'secondary', size: 'sm' })}>
              <BellRing aria-hidden="true" />
              Alerts
              {overview?.active_alerts ? (
                <span className="rounded-full bg-fault px-1.5 text-[10px] font-bold text-white">
                  {overview.active_alerts}
                </span>
              ) : null}
            </Link>
          </>
        }
      />

      {overviewQuery.isError ? (
        <QueryError error={overviewQuery.error} onRetry={() => overviewQuery.refetch()} />
      ) : null}

      {overviewQuery.isPending ? (
        <Skeleton className="h-64 w-full rounded-2xl" />
      ) : (
        <ConditionHero
          pumpLabel={pump ? `${pump.pump_code} · ${pump.name}` : 'No pump registered'}
          sensorLabel={
            sensor ? `${sensor.sensor_code} · ${sensor.mounting_position}` : 'No sensor'
          }
          latestWindow={latest}
          latestPrediction={latestPrediction}
          streamOnline={streamOnline}
        />
      )}

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_400px]">
        <Card>
          <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 pb-2">
            <div>
              <CardTitle>Fault score over time</CardTitle>
              <CardDescription>
                Last {TIMELINE_WINDOWS} one-second windows. The amber band is where the system
                abstains instead of guessing.
              </CardDescription>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
              <LegendDot className="bg-emerald-500" label="Normal" />
              <LegendDot className="bg-amber-500" label="Uncertain" />
              <LegendDot className="bg-red-500" label="Fault" />
              <span className="inline-flex items-center gap-1.5">
                <span className="size-2 rounded-[2px] bg-violet-500" />
                Sensor invalid
              </span>
            </div>
          </CardHeader>
          <CardContent>
            {predictionsQuery.isPending && pumpId ? (
              <Skeleton className="h-[280px] w-full" />
            ) : predictions.length > 0 ? (
              <DecisionTimelineChart predictions={predictions} />
            ) : (
              <EmptyState
                icon={Activity}
                title="No decisions yet"
                description="Start the edge stream; each one-second window appears here as it is decided."
              />
            )}
          </CardContent>
        </Card>

        <Card className="flex flex-col">
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center justify-between">
              What just happened
              <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-slate-400">
                Live
              </span>
            </CardTitle>
            <CardDescription>Scenario changes, decision changes and alerts.</CardDescription>
          </CardHeader>
          <CardContent className="max-h-[330px] flex-1 overflow-y-auto">
            <LiveEventFeed
              predictions={predictions}
              sessions={overview?.recent_sessions ?? []}
              alerts={alerts}
              now={now}
            />
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <Workflow className="size-4 text-accent-600" aria-hidden="true" />
            How the latest window was decided
          </CardTitle>
          <CardDescription>
            Every window passes the same edge pipeline. A bad signal is stopped before the model runs.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <DecisionPipelineCard latestWindow={latest} latestPrediction={latestPrediction} />
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Open alerts"
          value={overview?.active_alerts ?? 0}
          hint="Engineers acknowledge and review; the original prediction is never edited."
          icon={BellRing}
          tone={(overview?.active_alerts ?? 0) > 0 ? 'fault' : 'default'}
        />
        <StatCard
          label="Valid signal"
          value={validShare !== null ? `${validShare}%` : '-'}
          hint={
            overview
              ? `${overview.windows_total.toLocaleString()} windows · ${overview.invalid_windows} rejected by validation`
              : 'No windows yet'
          }
          icon={ShieldAlert}
          tone="info"
        />
        <StatCard
          label="Sensor health"
          value={
            latest ? <StatusBadge status={latest.quality_status} /> : <Badge variant="outline">No data</Badge>
          }
          hint={
            overview
              ? `${overview.sensors_with_data}/${overview.sensors_total} sensor(s) reporting · ${overview.sensors_stale} stale`
              : 'Sensor diagnostics unavailable'
          }
          icon={Stethoscope}
          tone={latest?.quality_status === 'SENSOR_INVALID' ? 'sensor' : 'success'}
        />
        <StatCard
          label="Edge model"
          value={activeModel ? `v${activeModel.version}` : 'None active'}
          hint={
            activeModel
              ? `${activeModel.name} · hash-verified · synthetic evaluation only`
              : 'Register and activate a model to enable inference.'
          }
          icon={Database}
          tone={activeModel ? 'accent' : 'uncertain'}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-3 pb-2">
            <div>
              <CardTitle>Vibration waveform</CardTitle>
              <CardDescription>Newest valid one-second window (downsampled).</CardDescription>
            </div>
            <Link
              to="/monitoring"
              className="inline-flex items-center gap-1 text-xs font-semibold text-industrial-600 hover:underline"
            >
              Open <ArrowUpRight className="size-3.5" aria-hidden="true" />
            </Link>
          </CardHeader>
          <CardContent>
            {latest?.waveform ? (
              <WaveformChart window={latest} height={200} />
            ) : (
              <EmptyState
                compact
                icon={Activity}
                title={latest?.quality_status === 'SENSOR_INVALID' ? 'No valid waveform' : 'No waveform yet'}
                description={
                  latest?.quality_status === 'SENSOR_INVALID'
                    ? 'The latest signal was rejected; nothing is shown as current.'
                    : 'Waveforms appear once the edge stream starts.'
                }
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle>Vibration energy (RMS)</CardTitle>
            <CardDescription>Recent windows; gaps are sensor-invalid windows.</CardDescription>
          </CardHeader>
          <CardContent>
            {overview?.trend.some((point) => point.rms !== null) ? (
              <RmsTrendChart windows={overview.trend} height={200} />
            ) : (
              <EmptyState compact icon={Activity} title="No trend yet" description="RMS appears after the first valid window." />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export { DashboardPage }
