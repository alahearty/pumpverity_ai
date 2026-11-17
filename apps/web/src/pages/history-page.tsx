import { useQuery } from '@tanstack/react-query'
import type { Alert, WindowPoint } from '@petrosense/shared-contracts'
import {
  Activity,
  BellRing,
  CalendarRange,
  Gauge,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { RmsTrendChart } from '@/components/charts/rms-trend-chart'
import { useCopilotPageContext } from '@/providers/copilot-context-provider'
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { fetchAlerts } from '@/services/alerts-service'
import { fetchPumps } from '@/services/equipment-service'
import { fetchLiveSnapshot } from '@/services/monitoring-service'
import { formatDateTime, formatScenario } from '@/lib/utils'

function issueCodes(window: WindowPoint): string {
  return window.validation_issue_codes.length > 0
    ? window.validation_issue_codes.join(', ')
    : 'None'
}

function HistoryPage() {
  const [pumpId, setPumpId] = useState('')
  const [sensorId, setSensorId] = useState('')
  const [limit, setLimit] = useState(50)
  const [searchParams] = useSearchParams()

  useEffect(() => {
    const requestedPump = searchParams.get('pump_id')
    const requestedSensor = searchParams.get('sensor_id')
    const requestedLimit = Number(searchParams.get('limit'))
    if (requestedPump) setPumpId(requestedPump)
    if (requestedSensor) setSensorId(requestedSensor)
    if ([25, 50, 100].includes(requestedLimit)) setLimit(requestedLimit)
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
    sensors.find((sensor) => sensor.sensor_type === 'VIBRATION') ??
    sensors[0]
  const effectiveSensorId = selectedSensor?.id ?? ''

  const snapshotQuery = useQuery({
    queryKey: ['monitoring-live', effectivePumpId, effectiveSensorId, limit],
    queryFn: () => fetchLiveSnapshot(effectivePumpId, effectiveSensorId, limit),
    enabled: Boolean(effectivePumpId && effectiveSensorId),
    staleTime: 30_000,
  })
  const alertsQuery = useQuery({
    queryKey: ['alerts', { pump_id: effectivePumpId, sensor_id: effectiveSensorId }],
    queryFn: () =>
      fetchAlerts({
        pump_id: effectivePumpId,
        sensor_id: effectiveSensorId,
        page_size: 100,
      }),
    enabled: Boolean(effectivePumpId && effectiveSensorId),
    staleTime: 30_000,
  })

  const snapshot = snapshotQuery.data
  const windows = snapshot?.recent_windows ?? []
  const alerts = alertsQuery.data?.items ?? []
  const health = snapshot?.sensor_health
  const validWindows = windows.filter((window) => window.quality_status === 'VALID')
  const invalidWindows = windows.filter(
    (window) => window.quality_status === 'SENSOR_INVALID',
  )
  const windowEvents = new Map<string, Alert[]>()
  for (const alert of alerts) {
    if (!alert.signal_window_id) continue
    const current = windowEvents.get(alert.signal_window_id) ?? []
    current.push(alert)
    windowEvents.set(alert.signal_window_id, current)
  }
  const openAlerts = alerts.filter((alert) => alert.status === 'OPEN').length

  useCopilotPageContext({
    selectedPumpId: effectivePumpId || null,
    selectedSensorId: effectiveSensorId || null,
    activeModelVersion: snapshot?.latest_prediction?.model?.version ?? null,
    operatingRegime: snapshot?.latest_prediction?.operating_regime?.code ?? null,
    monitoringMode: snapshot?.latest_window?.data_provenance ?? 'SIMULATED',
    connectivityStatus: snapshot?.edge_connectivity ?? 'NO_LIVE_CHANNEL',
  })

  if (pumpsQuery.isError) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Analysis"
          title="Historical data and trends"
          description="Persisted window history for the selected sensor."
        />
        <QueryError error={pumpsQuery.error} onRetry={() => pumpsQuery.refetch()} />
      </div>
    )
  }

  if (pumpsQuery.isPending) {
    return (
      <div className="space-y-6">
        <PageHeader
          eyebrow="Analysis"
          title="Historical data and trends"
          description="Persisted window history for the selected sensor."
        />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-80 w-full" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Analysis"
        title="Historical data and trends"
        description="Inspect persisted simulation windows, sensor-invalid intervals, RMS trends and alert-backed event overlays for the selected sensor."
        badge={<Badge variant="info">Event overlays</Badge>}
        actions={
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              snapshotQuery.refetch()
              alertsQuery.refetch()
            }}
            disabled={snapshotQuery.isFetching}
          >
            <RefreshCw className="size-3.5" aria-hidden="true" />
            Refresh
          </Button>
        }
      />

      <div className="flex items-start gap-3 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4">
        <CalendarRange
          className="mt-0.5 size-4 shrink-0 text-industrial-600"
          aria-hidden="true"
        />
        <div className="space-y-1 text-xs leading-relaxed text-industrial-900">
          <p className="font-semibold">Persisted window history with traceable event overlays</p>
          <p className="text-industrial-900/75">
            Overlay markers are drawn only where a persisted alert references the same signal
            window. Engineer review labels are engineering judgements, not automatically verified
            experimental ground truth.
          </p>
        </div>
      </div>

      {pumps.length === 0 ? (
        <Card>
          <CardContent className="p-5">
            <EmptyState
              icon={Gauge}
              title="No equipment registered"
              description="Register a pump and sensor before inspecting historical windows."
            />
          </CardContent>
        </Card>
      ) : sensors.length === 0 ? (
        <Card>
          <CardContent className="p-5">
            <EmptyState
              icon={Activity}
              title="No sensor assigned"
              description="Register a vibration sensor for this pump before inspecting historical windows."
            />
          </CardContent>
        </Card>
      ) : (
        <>
          <Card>
            <CardContent className="grid gap-4 p-4 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label htmlFor="history-pump">Pump</Label>
                <Select
                  id="history-pump"
                  value={effectivePumpId}
                  onChange={(event) => {
                    setPumpId(event.target.value)
                    setSensorId('')
                  }}
                >
                  {pumps.map((pump) => (
                    <option key={pump.id} value={pump.id}>
                      {pump.pump_code} - {pump.name}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="history-sensor">Sensor</Label>
                <Select
                  id="history-sensor"
                  value={effectiveSensorId}
                  onChange={(event) => setSensorId(event.target.value)}
                >
                  {sensors.map((sensor) => (
                    <option key={sensor.id} value={sensor.id}>
                      {sensor.sensor_code}
                    </option>
                  ))}
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="history-limit">Window range</Label>
                <Select
                  id="history-limit"
                  value={String(limit)}
                  onChange={(event) => setLimit(Number(event.target.value))}
                >
                  <option value="25">Last 25 windows</option>
                  <option value="50">Last 50 windows</option>
                  <option value="100">Last 100 windows</option>
                </Select>
              </div>
            </CardContent>
          </Card>

          {snapshotQuery.isError ? (
            <QueryError
              error={snapshotQuery.error}
              onRetry={() => snapshotQuery.refetch()}
            />
          ) : null}

          {alertsQuery.isError ? (
            <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs leading-relaxed text-amber-900">
              Alert overlays are temporarily unavailable. Window history remains visible without
              fabricated event markers.
            </div>
          ) : null}

          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
            <StatCard
              label="Windows in range"
              value={snapshotQuery.isPending ? '...' : windows.length}
              hint={selectedSensor?.sensor_code ?? 'No sensor selected'}
              icon={Activity}
              tone="info"
            />
            <StatCard
              label="Valid windows"
              value={snapshotQuery.isPending ? '...' : validWindows.length}
              hint="Eligible input for inference"
              icon={ShieldCheck}
              tone="success"
            />
            <StatCard
              label="Sensor-invalid"
              value={snapshotQuery.isPending ? '...' : invalidWindows.length}
              hint="Validation failed; no condition decision"
              icon={ShieldAlert}
              tone={invalidWindows.length > 0 ? 'sensor' : 'default'}
            />
            <StatCard
              label="Persisted alerts"
              value={alertsQuery.isPending ? '...' : alerts.length}
              hint={`${openAlerts} currently open`}
              icon={BellRing}
              tone={openAlerts > 0 ? 'fault' : 'default'}
            />
            <StatCard
              label="Sampling status"
              value={<StatusBadge status={health?.sampling_status ?? 'NO_DATA'} />}
              hint={
                health?.last_valid_reading_at
                  ? `Last valid ${formatDateTime(health.last_valid_reading_at)}`
                  : 'No valid persisted reading'
              }
              icon={Gauge}
              tone="default"
            />
          </div>

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
            <Card>
              <CardHeader>
                <CardTitle>RMS trend</CardTitle>
                <CardDescription>
                  Invalid windows are excluded from the line. Alert markers align to the persisted
                  source signal window.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {snapshotQuery.isPending ? (
                  <Skeleton className="h-64 w-full" />
                ) : windows.length > 0 ? (
                  <RmsTrendChart windows={windows} alerts={alerts} height={280} />
                ) : (
                  <EmptyState
                    icon={Activity}
                    title="No windows in range"
                    description="Run a simulated acquisition for this pump and sensor."
                  />
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Data scope</CardTitle>
                <CardDescription>Traceability of the displayed window set.</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2.5 text-xs">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Provenance</span>
                  <StatusBadge
                    status={snapshot?.latest_window?.data_provenance ?? 'SIMULATED'}
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Latest scenario</span>
                  <span className="font-medium text-navy-900">
                    {formatScenario(snapshot?.session?.scenario)}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Latest session</span>
                  <StatusBadge
                    status={snapshot?.session?.status ?? 'NO_DATA'}
                    label={snapshot?.session?.status ? undefined : 'None'}
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Invalid / gaps</span>
                  <span className="font-medium text-navy-900">
                    {health?.invalid_windows ?? 0} / {health?.missing_window_gaps ?? 0}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-slate-500">Event overlays</span>
                  <span className="font-medium text-navy-900">
                    {alertsQuery.isPending ? '...' : alerts.length}
                  </span>
                </div>
                <div className="space-y-1.5 rounded-lg border border-slate-200 bg-slate-50 p-3 text-[11px] leading-relaxed text-slate-500">
                  <p className="font-semibold text-slate-600">Overlay categories</p>
                  <div className="flex flex-wrap gap-1.5">
                    <StatusBadge status="FAULT" />
                    <StatusBadge status="UNCERTAIN" />
                    <StatusBadge status="SENSOR_INVALID" />
                  </div>
                  <p>
                    Markers use persisted alert records only. No event is inferred from waveform
                    appearance.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Window records</CardTitle>
              <CardDescription>
                Persisted metadata only; waveform bytes are not exposed in the history table.
              </CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              {snapshotQuery.isPending ? (
                <div className="space-y-2 p-5">
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                  <Skeleton className="h-10 w-full" />
                </div>
              ) : windows.length === 0 ? (
                <div className="p-5">
                  <EmptyState
                    compact
                    icon={CalendarRange}
                    title="No historical windows"
                    description="Simulated acquisition has not written any windows for this sensor."
                  />
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow className="bg-slate-50/70">
                      <TableHead>Window</TableHead>
                      <TableHead>Received window</TableHead>
                      <TableHead>Quality</TableHead>
                      <TableHead>RMS</TableHead>
                      <TableHead>Peak</TableHead>
                      <TableHead>Samples</TableHead>
                      <TableHead className="hidden lg:table-cell">Scenario</TableHead>
                      <TableHead>Event</TableHead>
                      <TableHead className="hidden xl:table-cell">Issues</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {windows.map((window) => {
                      const events = windowEvents.get(window.window_id) ?? []
                      return (
                        <TableRow
                          key={window.window_id}
                          className={
                            window.quality_status === 'SENSOR_INVALID'
                              ? 'bg-sensor-soft/20'
                              : undefined
                          }
                        >
                          <TableCell className="font-mono text-xs text-navy-900">
                            {window.window_index}
                          </TableCell>
                          <TableCell className="text-xs text-slate-600">
                            {formatDateTime(window.window_end)}
                          </TableCell>
                          <TableCell>
                            <StatusBadge status={window.quality_status} />
                          </TableCell>
                          <TableCell className="text-xs text-slate-600">
                            {window.rms !== null ? `${window.rms.toFixed(4)} g` : 'None'}
                          </TableCell>
                          <TableCell className="text-xs text-slate-600">
                            {window.peak_abs !== null
                              ? `${window.peak_abs.toFixed(4)} g`
                              : 'None'}
                          </TableCell>
                          <TableCell className="text-xs text-slate-600">
                            {window.sample_count}
                          </TableCell>
                          <TableCell className="hidden text-xs text-slate-500 lg:table-cell">
                            {formatScenario(window.scenario)}
                          </TableCell>
                          <TableCell>
                            {events.length === 0 ? (
                              <span className="text-[10px] text-slate-400">None</span>
                            ) : (
                              <div className="flex flex-wrap gap-1">
                                {events.map((alert) => (
                                  <StatusBadge key={alert.id} status={alert.category} />
                                ))}
                              </div>
                            )}
                          </TableCell>
                          <TableCell className="hidden text-[10px] text-slate-500 xl:table-cell">
                            {issueCodes(window)}
                          </TableCell>
                        </TableRow>
                      )
                    })}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <ResearchNotice compact />
    </div>
  )
}

export { HistoryPage }


