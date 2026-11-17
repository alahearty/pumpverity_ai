import { useQuery, useQueryClient } from '@tanstack/react-query'
import type { LiveSnapshot } from '@petrosense/shared-contracts'
import {
  Activity,
  BrainCircuit,
  Clock3,
  Gauge,
  Pause,
  Play,
  Radio,
  RefreshCw,
  ShieldAlert,
  Stethoscope,
  Waves,
  WifiOff,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import { RmsTrendChart } from '@/components/charts/rms-trend-chart'
import { WaveformChart } from '@/components/charts/waveform-chart'
import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
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
import { Label } from '@/components/ui/label'
import { Select } from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import {
  useMonitoringStream,
  type StreamStatus,
} from '@/hooks/use-monitoring-stream'
import type { SseEvent } from '@/lib/api'
import { useAuth } from '@/providers/auth-provider'
import { useCopilotPageContext } from '@/providers/copilot-context-provider'
import { fetchDemoControl } from '@/services/demo-service'
import { fetchPumps } from '@/services/equipment-service'
import { fetchLiveSnapshot } from '@/services/monitoring-service'
import { formatDateTime, formatScenario } from '@/lib/utils'

const STREAM_STATUS: Record<StreamStatus, { label: string; dot: string }> = {
  connected: { label: 'Live stream connected', dot: 'bg-success' },
  connecting: { label: 'Connecting stream', dot: 'bg-uncertain' },
  reconnecting: { label: 'Stream reconnecting', dot: 'bg-uncertain' },
  disabled: { label: 'Stream idle', dot: 'bg-slate-400' },
}

function formatMetric(value: number | null | undefined, digits = 4): string {
  return typeof value === 'number' && Number.isFinite(value)
    ? `${value.toFixed(digits)} g`
    : '—'
}

function PausedChartPlaceholder() {
  return (
    <EmptyState
      compact
      icon={Pause}
      title="Chart paused"
      description="Live statistics continue to update. Resume rendering to display the latest validated chart data."
    />
  )
}

function LiveMonitoringPage() {
  const { user } = useAuth()
  const [searchParams] = useSearchParams()
  const queryClient = useQueryClient()
  const [pumpId, setPumpId] = useState('')
  const [sensorId, setSensorId] = useState('')
  const [limit, setLimit] = useState(25)
  const [chartMode, setChartMode] = useState<'waveform' | 'trend'>('waveform')
  const [chartPaused, setChartPaused] = useState(false)
  const [frozenSnapshot, setFrozenSnapshot] = useState<LiveSnapshot | null>(null)

  useEffect(() => {
    const requestedPump = searchParams.get('pump_id')
    const requestedSensor = searchParams.get('sensor_id')
    if (requestedPump) setPumpId(requestedPump)
    if (requestedSensor) setSensorId(requestedSensor)
  }, [searchParams])

  const pumpsQuery = useQuery({
    queryKey: ['pumps', { page: 1, page_size: 100 }],
    queryFn: () => fetchPumps({ page: 1, page_size: 100 }),
  })

  const pumps = pumpsQuery.data?.items ?? []
  const selectedPump = pumps.find((pump) => pump.id === pumpId) ?? pumps[0]
  const sensors = selectedPump?.sensors ?? []
  const effectivePumpId = selectedPump?.id ?? ''
  const selectedSensor =
    sensors.find((sensor) => sensor.id === sensorId) ??
    sensors.find((sensor) => sensor.sensor_type === 'VIBRATION' && sensor.is_active) ??
    sensors.find((sensor) => sensor.is_active) ??
    sensors[0]
  const effectiveSensorId = selectedSensor?.id ?? ''

  const snapshotQuery = useQuery({
    queryKey: ['monitoring-live', effectivePumpId, effectiveSensorId, limit],
    queryFn: () => fetchLiveSnapshot(effectivePumpId, effectiveSensorId, limit),
    enabled: Boolean(effectivePumpId && effectiveSensorId),
    refetchInterval: 15_000,
    staleTime: 3_000,
  })

  const handleStreamEvent = useCallback(
    (event: SseEvent) => {
      if (
        event.event === 'reading' ||
        event.event === 'sensor_health' ||
        event.event === 'prediction'
      ) {
        queryClient.invalidateQueries({ queryKey: ['monitoring-live'] }, { cancelRefetch: false })
        queryClient.invalidateQueries({ queryKey: ['monitoring-overview'] }, { cancelRefetch: false })
        queryClient.invalidateQueries({ queryKey: ['sensor-health'] }, { cancelRefetch: false })
        queryClient.invalidateQueries({ queryKey: ['predictions'] }, { cancelRefetch: false })
      }
    },
    [queryClient],
  )

  const stream = useMonitoringStream({
    pumpId: effectivePumpId || undefined,
    sensorId: effectiveSensorId || undefined,
    onEvent: handleStreamEvent,
  })

  const demoControl = useQuery({
    queryKey: ['demo-control'],
    queryFn: fetchDemoControl,
    refetchInterval: 2_000,
    retry: false,
  })
  const demoMode = Boolean(demoControl.data?.enabled)

  const snapshot = snapshotQuery.data
  const chartSnapshot = chartPaused ? frozenSnapshot : snapshot
  const latest = snapshot?.latest_window
  const latestValid = latest?.quality_status === 'VALID' ? latest : null
  const latestPrediction = snapshot?.latest_prediction
  const health = snapshot?.sensor_health
  const streamState = STREAM_STATUS[stream.status]

  useCopilotPageContext({
    selectedPumpId: effectivePumpId || null,
    selectedSensorId: effectiveSensorId || null,
    activeModelVersion: latestPrediction?.model?.version ?? null,
    operatingRegime: latestPrediction?.operating_regime?.code ?? null,
    monitoringMode: snapshot?.latest_window?.data_provenance ?? 'SIMULATED',
    connectivityStatus: snapshot?.edge_connectivity ?? 'NO_LIVE_CHANNEL',
  })

  const simulationCommand = selectedPump
    ? [
        '$env:PETROSENSE_EDGE_PASSWORD = "<demo password>"',
        `python -m petrosense_edge.cli --pump-code ${selectedPump.pump_code} --sensor-code ${selectedSensor?.sensor_code ?? 'VIB-01'} --scenario normal --windows 5 --seed 42`,
      ].join('\n')
    : ''

  function resetChartPause() {
    setChartPaused(false)
    setFrozenSnapshot(null)
  }

  function togglePause() {
    if (chartPaused) {
      resetChartPause()
    } else {
      setFrozenSnapshot(snapshot ?? null)
      setChartPaused(true)
    }
  }

  if (pumpsQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Operations"
          title="Live monitoring"
          description="Validated signal windows, sensor health and live-update status."
        />
        <QueryError error={pumpsQuery.error} onRetry={() => pumpsQuery.refetch()} />
      </div>
    )
  }

  if (pumpsQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Operations"
          title="Live monitoring"
          description="Validated signal windows, sensor health and live-update status."
        />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    )
  }

  if (pumps.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Operations"
          title="Live monitoring"
          description="Live monitoring is unavailable until a pump and sensor are registered."
          badge={<Badge variant="outline">Live inference</Badge>}
        />
        <Card>
          <CardContent className="p-5">
            <EmptyState
              icon={Gauge}
              title="No pump registered"
              description="An engineer must register the laboratory pump and its vibration sensor before monitoring can begin."
              action={
                user?.role === 'ENGINEER' || user?.role === 'ADMINISTRATOR' ? (
                  <Link
                    to="/pumps"
                    className="text-sm font-semibold text-industrial-600 hover:underline"
                  >
                    Open Pump Registry
                  </Link>
                ) : undefined
              }
            />
          </CardContent>
        </Card>
        <ResearchNotice />
      </div>
    )
  }

  if (sensors.length === 0) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Operations"
          title="Live monitoring"
          description="A pump is registered but has no sensor assigned."
          badge={<Badge variant="outline">Live inference</Badge>}
        />
        <Card>
          <CardContent className="p-5">
            <EmptyState
              icon={Radio}
              title="No sensor assigned"
              description="Register a vibration sensor for this pump before starting an acquisition."
              action={
                user?.role === 'ENGINEER' || user?.role === 'ADMINISTRATOR' ? (
                  <Link
                    to="/sensors"
                    className="text-sm font-semibold text-industrial-600 hover:underline"
                  >
                    Open Sensor Health
                  </Link>
                ) : undefined
              }
            />
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Live monitoring"
        description="Latest persisted signal windows, waveform preview, sensor diagnostics and SSE update status for the selected pump."
        badge={<Badge variant="info">Live inference</Badge>}
        actions={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                pumpsQuery.refetch()
                snapshotQuery.refetch()
              }}
              disabled={snapshotQuery.isFetching}
            >
              <RefreshCw className="size-3.5" aria-hidden="true" />
              Refresh
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={togglePause}
              disabled={!snapshot}
            >
              {chartPaused ? (
                <>
                  <Play className="size-3.5" aria-hidden="true" />
                  Resume chart
                </>
              ) : (
                <>
                  <Pause className="size-3.5" aria-hidden="true" />
                  Pause chart
                </>
              )}
            </Button>
          </>
        }
      />

      <div className="flex flex-col gap-2 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4 text-xs leading-relaxed text-industrial-900 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-2">
          <Activity className="mt-0.5 size-4 shrink-0 text-industrial-600" aria-hidden="true" />
          <p>
            <span className="font-semibold">Simulated replay with SSE updates.</span> Values come
            from persisted provenance-tagged windows. No physical edge channel is active; model
            decisions appear only when they exist for the latest valid window.
          </p>
        </div>
        <span className="flex items-center gap-2 whitespace-nowrap rounded-full border border-slate-200 bg-white px-3 py-1.5 text-[11px] font-medium text-slate-600">
          <span className={`size-1.5 rounded-full ${streamState.dot}`} />
          {streamState.label}
        </span>
      </div>

      {snapshotQuery.isError ? (
        <QueryError
          error={snapshotQuery.error}
          onRetry={() => snapshotQuery.refetch()}
        />
      ) : null}

      {latest?.quality_status === 'SENSOR_INVALID' ? (
        <div
          role="status"
          className="flex items-start gap-3 rounded-xl border border-sensor/25 bg-sensor-soft/50 p-4 text-xs leading-relaxed text-violet-950"
        >
          <ShieldAlert className="mt-0.5 size-4 shrink-0 text-sensor" aria-hidden="true" />
          <p>
            <span className="font-semibold">Latest window is sensor-invalid.</span> Condition
            inference is suppressed. The validation summary is shown below; earlier valid windows
            remain visible in the trend but are not presented as the current state.
          </p>
        </div>
      ) : null}

      <Card>
        <CardContent className="grid gap-4 p-4 md:grid-cols-3">
          <div className="space-y-1.5">
            <Label htmlFor="monitor-pump">Pump</Label>
            <Select
              id="monitor-pump"
              value={effectivePumpId}
              onChange={(event) => {
                setPumpId(event.target.value)
                setSensorId('')
                resetChartPause()
              }}
            >
              {pumps.map((pump) => (
                <option key={pump.id} value={pump.id}>
                  {pump.pump_code} — {pump.name}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="monitor-sensor">Sensor</Label>
            <Select
              id="monitor-sensor"
              value={effectiveSensorId}
              onChange={(event) => {
                setSensorId(event.target.value)
                resetChartPause()
              }}
            >
              {sensors.map((sensor) => (
                <option key={sensor.id} value={sensor.id}>
                  {sensor.sensor_code} — {sensor.mounting_axis.replaceAll('_', ' ')}
                </option>
              ))}
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="monitor-window">Trend window</Label>
            <Select
              id="monitor-window"
              value={String(limit)}
              onChange={(event) => {
                setLimit(Number(event.target.value))
                resetChartPause()
              }}
            >
              <option value="10">Last 10 windows</option>
              <option value="25">Last 25 windows</option>
              <option value="50">Last 50 windows</option>
            </Select>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        <StatCard
          label="Latest RMS"
          value={formatMetric(latestValid?.rms ?? health?.latest_rms)}
          hint={
            latestValid
              ? formatDateTime(latestValid.window_end)
              : health?.last_valid_reading_at
                ? `Last valid: ${formatDateTime(health.last_valid_reading_at)}`
                : 'No valid reading'
          }
          icon={Activity}
          tone={latestValid ? 'success' : 'default'}
        />
        <StatCard
          label="Latest peak"
          value={formatMetric(latestValid?.peak_abs ?? health?.latest_peak_abs)}
          hint="Absolute peak of the last valid window"
          icon={Waves}
          tone="accent"
        />
        <StatCard
          label="Sampling"
          value={
            latest
              ? `${latest.sampling_rate_hz.toLocaleString()} Hz`
              : health
                ? `${health.sampling_rate_hz.toLocaleString()} Hz`
                : '—'
          }
          hint={
            latest
              ? latest.sample_count > 0
                ? `${latest.sample_count.toLocaleString()} samples/window`
                : 'Latest window has no samples'
              : 'No window data'
          }
          icon={Radio}
          tone="info"
        />
        <StatCard
          label="Equipment condition"
          value={
            snapshot?.condition_available && snapshot.equipment_condition ? (
              <StatusBadge status={snapshot.equipment_condition} />
            ) : (
              <Badge variant="outline">Not inferred</Badge>
            )
          }
          hint={
            latestPrediction && latestPrediction.decision !== 'SENSOR_INVALID'
              ? `${latestPrediction.model?.name ?? 'Model'} v${latestPrediction.model?.version ?? '—'} · score ${latestPrediction.decision_score?.toFixed(4) ?? '—'}`
              : latest?.quality_status === 'SENSOR_INVALID'
                ? 'Inference suppressed by sensor validation'
                : 'No current inference for the latest window'
          }
          icon={BrainCircuit}
          tone={snapshot?.condition_available ? 'success' : 'default'}
        />
        <StatCard
          label="Data quality"
          value={<StatusBadge status={latest?.quality_status ?? 'NO_DATA'} />}
          hint={
            latest
              ? `Window received ${formatDateTime(latest.window_end)}`
              : 'No validated window received'
          }
          icon={ShieldAlert}
          tone={latest?.quality_status === 'SENSOR_INVALID' ? 'sensor' : 'info'}
        />
        <StatCard
          label="Sensor diagnostics"
          value={<StatusBadge status={health?.sampling_status ?? 'NO_DATA'} />}
          hint={
            health
              ? `${health.invalid_windows} invalid window(s), ${health.missing_window_gaps} gap(s)`
              : 'No sensor diagnostics'
          }
          icon={Stethoscope}
          tone={
            health?.sampling_status === 'SENSOR_INVALID'
              ? 'sensor'
              : health?.sampling_status === 'STALE'
                ? 'uncertain'
                : 'success'
          }
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="space-y-5">
          <Card>
            <CardHeader className="flex-row items-start justify-between gap-4 pb-3">
              <div>
                <CardTitle>
                  {chartMode === 'waveform' ? 'Latest signal waveform' : 'RMS trend'}
                </CardTitle>
                <CardDescription>
                  {chartMode === 'waveform'
                    ? 'Downsampled from the latest persisted window; it is not a live hardware trace.'
                    : 'One RMS value per validated window. Sensor-invalid windows are excluded from the line.'}
                </CardDescription>
              </div>
              <div className="flex flex-wrap items-center justify-end gap-1.5">
                <Button
                  variant={chartMode === 'waveform' ? 'default' : 'secondary'}
                  size="sm"
                  onClick={() => setChartMode('waveform')}
                >
                  Waveform
                </Button>
                <Button
                  variant={chartMode === 'trend' ? 'default' : 'secondary'}
                  size="sm"
                  onClick={() => setChartMode('trend')}
                >
                  RMS trend
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {chartPaused ? (
                <PausedChartPlaceholder />
              ) : snapshotQuery.isPending ? (
                <Skeleton className="h-64 w-full" />
              ) : chartMode === 'waveform' ? (
                chartSnapshot?.latest_window?.waveform ? (
                  <WaveformChart window={chartSnapshot.latest_window} />
                ) : (
                  <EmptyState
                    compact
                    icon={Radio}
                    title="No current valid waveform"
                    description={
                      latest?.quality_status === 'SENSOR_INVALID'
                        ? 'The latest window is sensor-invalid, so no waveform is presented as current. Switch to RMS trend to inspect earlier valid windows.'
                        : 'Run a simulated acquisition to generate the first validated window.'
                    }
                  />
                )
              ) : chartSnapshot && chartSnapshot.recent_windows.length > 0 ? (
                <RmsTrendChart windows={chartSnapshot.recent_windows} />
              ) : (
                <EmptyState
                  compact
                  icon={Activity}
                  title="No trend data"
                  description="No persisted windows exist for this sensor yet."
                />
              )}

              <div className="mt-4 flex flex-wrap items-center gap-2 border-t border-slate-100 pt-3 text-[11px] text-slate-500">
                {latest ? (
                  <>
                    <span>Window {latest.window_index}</span>
                    <span>·</span>
                    <span>{formatDateTime(latest.window_end)}</span>
                    <span>·</span>
                    <span>{latest.units ?? 'units unavailable'}</span>
                    <span>·</span>
                    <span>{formatScenario(latest.scenario)}</span>
                  </>
                ) : (
                  <span>No window received</span>
                )}
                <StatusBadge status="SIMULATED" className="ml-auto" />
                {chartPaused ? <Badge variant="uncertain">Paused</Badge> : null}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>State separation</CardTitle>
              <CardDescription>
                Condition, signal quality, connectivity and provenance remain independent.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Equipment condition
                </p>
                <div className="mt-2">
                  {snapshot?.condition_available && snapshot.equipment_condition ? (
                    <StatusBadge status={snapshot.equipment_condition} />
                  ) : (
                    <Badge variant="outline">Not inferred</Badge>
                  )}
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Data quality
                </p>
                <div className="mt-2">
                  <StatusBadge status={latest?.quality_status ?? 'NO_DATA'} />
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Edge connectivity
                </p>
                <div className="mt-2">
                  <Badge variant="neutral">
                    <WifiOff className="size-3" aria-hidden="true" />
                    No live channel
                  </Badge>
                </div>
              </div>
              <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-3">
                <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  Data provenance
                </p>
                <div className="mt-2">
                  <StatusBadge status={latest?.data_provenance ?? 'SIMULATED'} />
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Latest AI decision</CardTitle>
              <CardDescription>
                Current model output for the selected sensor, when available.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5 text-xs">
              {latestPrediction ? (
                <>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Decision</span>
                    <StatusBadge status={latestPrediction.decision} />
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Model</span>
                    <span className="text-right font-medium text-navy-900">
                      {latestPrediction.model
                        ? `${latestPrediction.model.name} v${latestPrediction.model.version}`
                        : 'No model'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Decision score</span>
                    <span className="font-mono font-medium text-navy-900">
                      {latestPrediction.decision_score?.toFixed(4) ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Uncertainty</span>
                    <span className="font-mono font-medium text-navy-900">
                      {latestPrediction.uncertainty_score?.toFixed(4) ?? '—'}
                    </span>
                  </div>
                  <p className="rounded-lg bg-slate-50 p-2.5 text-[10px] leading-relaxed text-slate-500">
                    {latestPrediction.explanation}
                  </p>
                  <Link
                    to={`/analysis/${latestPrediction.id}`}
                    className="inline-flex text-xs font-semibold text-industrial-600 hover:underline"
                  >
                    Open full AI analysis
                  </Link>
                </>
              ) : (
                <div className="space-y-2">
                  <p className="text-slate-500">
                    {latest?.quality_status === 'SENSOR_INVALID'
                      ? 'The latest window failed validation, so no model decision was attempted.'
                      : 'No current model inference exists for the latest window.'}
                  </p>
                  <Link
                    to="/analysis"
                    className="inline-flex text-xs font-semibold text-industrial-600 hover:underline"
                  >
                    Open AI analysis
                  </Link>
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Sensor health</CardTitle>
              <CardDescription>
                Diagnostics from persisted windows; no physical sensor channel is connected.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-500">Sampling status</span>
                <StatusBadge status={health?.sampling_status ?? 'NO_DATA'} />
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-500">Connection</span>
                <StatusBadge status="NO_LIVE_CHANNEL" />
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-500">Last valid reading</span>
                <span className="text-right font-medium text-navy-900">
                  {formatDateTime(health?.last_valid_reading_at)}
                </span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-500">Invalid windows</span>
                <span className="font-medium text-navy-900">{health?.invalid_windows ?? 0}</span>
              </div>
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-500">Missing index gaps</span>
                <span className="font-medium text-navy-900">
                  {health?.missing_window_gaps ?? 0}
                </span>
              </div>
              {health && health.latest_validation_issues.length > 0 ? (
                <div className="rounded-lg border border-sensor/20 bg-sensor-soft/40 p-2.5">
                  <p className="mb-1.5 text-[10px] font-semibold uppercase tracking-[0.12em] text-violet-700">
                    Latest validation issues
                  </p>
                  <div className="flex flex-wrap gap-1">
                    {health.latest_validation_issues.map((issue, index) => (
                      <Badge key={index} variant="sensor" className="font-mono text-[9px]">
                        {String(issue.code ?? 'unknown')}
                      </Badge>
                    ))}
                  </div>
                </div>
              ) : null}
              <Link
                to="/sensors"
                className="inline-flex text-xs font-semibold text-industrial-600 hover:underline"
              >
                Open full sensor health
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle>Latest session</CardTitle>
              <CardDescription>Acquisition context for the selected sensor.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5 text-xs">
              {snapshot?.session ? (
                <>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Scenario</span>
                    <span className="font-medium text-navy-900">
                      {formatScenario(snapshot.session.scenario)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Status</span>
                    <StatusBadge status={snapshot.session.status} />
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Windows</span>
                    <span className="font-medium text-navy-900">
                      {snapshot.session.window_count}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Started</span>
                    <span className="text-right font-medium text-navy-900">
                      {formatDateTime(snapshot.session.started_at)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-slate-500">Provenance</span>
                    <StatusBadge status={snapshot.session.data_provenance} />
                  </div>
                </>
              ) : (
                <div className="rounded-lg bg-slate-50 p-3 text-slate-500">
                  No acquisition session has been recorded for this sensor.
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <Clock3 className="size-4 text-accent-600" aria-hidden="true" />
                Simulated data source
              </CardTitle>
              <CardDescription>
                New windows arrive through SSE when the edge simulator writes to the API.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="flex items-center justify-between gap-2 text-xs">
                <span className="text-slate-500">Mode</span>
                <StatusBadge
                  status={snapshot?.data_mode === 'SIMULATED_REPLAY' ? 'SIMULATED' : 'NO_DATA'}
                  label={snapshot?.data_mode === 'SIMULATED_REPLAY' ? 'Simulated replay' : 'No data'}
                />
              </div>
              {demoMode ? (
                <p className="text-[11px] leading-relaxed text-slate-500">
                  Presentation mode: the edge demo driver generates one simulated window per second
                  and runs the same validation, feature and inference pipeline as the edge device.
                  Choose the scenario in the panel above.
                </p>
              ) : (
                <>
                  <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-navy-950 p-3 font-mono text-[10px] leading-relaxed text-accent-100">
                    {simulationCommand}
                  </pre>
                  <p className="text-[10px] leading-relaxed text-slate-400">
                    Network outage and buffering controls are not available in this build. Sensor-disconnect and
                    corrupted-sample scenarios can be run with the edge CLI.
                  </p>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      <ResearchNotice compact />
    </div>
  )
}

export { LiveMonitoringPage }


