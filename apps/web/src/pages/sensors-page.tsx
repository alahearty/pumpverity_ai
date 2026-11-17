import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { SensorRegister } from '@petrosense/shared-contracts'
import {
  Activity,
  Plus,
  Radar,
  Radio,
  RefreshCw,
  ShieldAlert,
  Stethoscope,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

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
import { SensorRegistrationForm } from '@/features/equipment/sensor-registration-form'
import { useAuth } from '@/providers/auth-provider'
import { useCopilotOptional, useCopilotPageContext } from '@/providers/copilot-context-provider'
import {
  createSensor,
  fetchPumps,
  fetchSensors,
  updateSensor,
} from '@/services/equipment-service'
import { fetchSensorHealth } from '@/services/monitoring-service'
import { formatDateTime } from '@/lib/utils'

function SensorsPage() {
  const { user } = useAuth()
  const canWrite = user?.role === 'ENGINEER' || user?.role === 'ADMINISTRATOR'
  const [showForm, setShowForm] = useState(false)
  const [pumpFilter, setPumpFilter] = useState('ALL')
  const [highlightedSensorId, setHighlightedSensorId] = useState('')
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [searchParams] = useSearchParams()
  const copilot = useCopilotOptional()
  const requestTool = copilot?.requestTool
  const queryClient = useQueryClient()

  useEffect(() => {
    const requestedPump = searchParams.get('pump_id')
    const requestedSensor = searchParams.get('sensor_id')
    setPumpFilter(requestedPump ?? 'ALL')
    setHighlightedSensorId(requestedSensor ?? '')
  }, [searchParams])

  const pumpsQuery = useQuery({
    queryKey: ['pumps', { page: 1, page_size: 100 }],
    queryFn: () => fetchPumps({ page: 1, page_size: 100 }),
  })
  const sensorsQuery = useQuery({
    queryKey: ['sensors', { page: 1, page_size: 100, pumpFilter }],
    queryFn: () =>
      fetchSensors({
        page: 1,
        page_size: 100,
        pump_id: pumpFilter === 'ALL' ? undefined : pumpFilter,
      }),
  })
  const healthQuery = useQuery({
    queryKey: ['sensor-health', pumpFilter],
    queryFn: () => fetchSensorHealth(pumpFilter === 'ALL' ? undefined : pumpFilter),
    refetchInterval: 30_000,
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['sensors'] })
    queryClient.invalidateQueries({ queryKey: ['pumps'] })
    queryClient.invalidateQueries({ queryKey: ['sensor-health'] })
    queryClient.invalidateQueries({ queryKey: ['monitoring-overview'] })
  }

  const createMutation = useMutation({
    mutationFn: (payload: SensorRegister) => createSensor(payload),
    onSuccess: (sensor) => {
      invalidate()
      setShowForm(false)
      setSuccessMessage(`Registered ${sensor.sensor_code}.`)
    },
  })
  const toggleMutation = useMutation({
    mutationFn: ({ sensorId, isActive }: { sensorId: string; isActive: boolean }) =>
      updateSensor(sensorId, { is_active: isActive }),
    onSuccess: (sensor) => {
      invalidate()
      setSuccessMessage(
        `${sensor.sensor_code} is now ${sensor.is_active ? 'active' : 'inactive'}.`,
      )
    },
  })

  const sensors = sensorsQuery.data?.items ?? []
  const pumps = pumpsQuery.data?.items ?? []
  const healthList = healthQuery.data ?? []
  const healthBySensor = new Map(
    healthList.map((health) => [health.sensor_id, health]),
  )
  const total = sensorsQuery.data?.total ?? 0
  const active = sensors.filter((sensor) => sensor.is_active).length
  const reporting = healthList.filter((health) => health.total_windows > 0).length
  const invalidLatest = healthList.filter(
    (health) => health.sampling_status === 'SENSOR_INVALID',
  ).length
  const loading = sensorsQuery.isPending || healthQuery.isPending
  const error = sensorsQuery.error ?? healthQuery.error

  useCopilotPageContext({
    selectedPumpId: pumpFilter === 'ALL' ? null : pumpFilter,
    selectedSensorId: highlightedSensorId || null,
    monitoringMode: healthList[0]?.provenance ?? 'SIMULATED',
    connectivityStatus: 'NO_LIVE_CHANNEL',
  })

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Assets"
        title="Sensor health"
        description="Signal validity, freshness, missing-window gaps and validation warnings derived from persisted acquisition windows."
        badge={<Badge variant="info">Diagnostics active</Badge>}
        actions={
          <>
            <Button
              variant="outline"
              size="sm"
              onClick={() =>
                requestTool?.(
                  'pumpverity_get_sensor_health',
                  highlightedSensorId
                    ? { sensor_id: highlightedSensorId }
                    : {},
                )
              }
              disabled={pumpFilter === 'ALL' || !requestTool}
            >
              <Stethoscope className="size-3.5" aria-hidden="true" />
              Run Copilot diagnostic
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                sensorsQuery.refetch()
                healthQuery.refetch()
                pumpsQuery.refetch()
              }}
              disabled={sensorsQuery.isFetching || healthQuery.isFetching}
            >
              <RefreshCw className="size-3.5" aria-hidden="true" />
              Refresh
            </Button>
            {canWrite ? (
              <Button
                size="sm"
                onClick={() => {
                  setShowForm(true)
                  setSuccessMessage(null)
                }}
                disabled={pumps.length === 0}
                title={pumps.length === 0 ? 'Register a pump first' : undefined}
              >
                <Plus className="size-3.5" aria-hidden="true" />
                Register sensor
              </Button>
            ) : null}
          </>
        }
      />

      {successMessage ? (
        <div className="rounded-xl border border-green-200 bg-success-soft px-4 py-3 text-sm text-green-800">
          {successMessage}
        </div>
      ) : null}

      {toggleMutation.isError ? (
        <div
          role="alert"
          className="rounded-xl border border-red-200 bg-fault-soft px-4 py-3 text-sm text-red-800"
        >
          Sensor state could not be updated. Check the local API and retry.
        </div>
      ) : null}

      <div className="flex items-start gap-3 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4">
        <Stethoscope className="mt-0.5 size-4 shrink-0 text-industrial-600" aria-hidden="true" />
        <div className="space-y-1 text-xs leading-relaxed text-industrial-900">
          <p className="font-semibold">Diagnostics come from persisted windows, not a live channel</p>
          <p className="text-industrial-900/75">
            Sampling status is based on the latest window and its ingestion freshness. No physical
            edge channel is connected, and no condition inference is displayed. Sensor-invalid
            windows carry their validation warnings and contribute to the invalid/gap counts.
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Registered sensors"
          value={loading ? '—' : total}
          hint="All channels in the current filter"
          icon={Radio}
          tone="info"
        />
        <StatCard
          label="Active sensors"
          value={loading ? '—' : active}
          hint="Available for acquisition configuration"
          icon={Activity}
          tone="success"
        />
        <StatCard
          label="Sensors with data"
          value={loading ? '—' : reporting}
          hint="At least one persisted window"
          icon={Radar}
          tone="accent"
        />
        <StatCard
          label="Latest sensor-invalid"
          value={loading ? '—' : invalidLatest}
          hint="Sensors whose latest window failed validation"
          icon={ShieldAlert}
          tone={invalidLatest > 0 ? 'sensor' : 'default'}
        />
      </div>

      {showForm ? (
        <Card>
          <CardHeader>
            <CardTitle>Register sensor</CardTitle>
            <CardDescription>
              Assign a sensor to a registered pump. Sensor codes are unique across the deployment.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SensorRegistrationForm
              pumps={pumps}
              defaultPumpId={pumps[0]?.id}
              onSubmit={async (payload) => {
                await createMutation.mutateAsync(payload)
              }}
              onCancel={() => setShowForm(false)}
            />
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader className="gap-4 border-b border-slate-100 pb-4">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Sensor diagnostics</CardTitle>
              <CardDescription>
                {healthQuery.data
                  ? `${total} registered sensor(s); ${reporting} with persisted data.`
                  : 'Loading sensor diagnostics…'}
              </CardDescription>
            </div>
            <div className="w-full sm:w-64">
              <Select
                value={pumpFilter}
                onChange={(event) => setPumpFilter(event.target.value)}
                aria-label="Filter sensors by pump"
              >
                <option value="ALL">All pumps</option>
                {pumps.map((pump) => (
                  <option key={pump.id} value={pump.id}>
                    {pump.pump_code}
                  </option>
                ))}
              </Select>
            </div>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {error ? (
            <div className="p-5">
              <QueryError
                error={error}
                onRetry={() => {
                  sensorsQuery.refetch()
                  healthQuery.refetch()
                }}
              />
            </div>
          ) : loading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index} className="flex items-center gap-4">
                  <Skeleton className="size-9 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-3.5 w-40" />
                    <Skeleton className="h-3 w-64" />
                  </div>
                  <Skeleton className="h-6 w-24" />
                </div>
              ))}
            </div>
          ) : sensors.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={Radar}
                title="No sensors registered"
                description={
                  pumps.length === 0
                    ? 'Register a pump first; sensor assignment requires a registered pump.'
                    : 'No sensors match the selected pump filter.'
                }
                action={
                  canWrite && pumps.length > 0 ? (
                    <Button onClick={() => setShowForm(true)}>
                      <Plus className="size-4" aria-hidden="true" />
                      Register sensor
                    </Button>
                  ) : undefined
                }
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50/70">
                  <TableHead>Sensor</TableHead>
                  <TableHead>Pump</TableHead>
                  <TableHead>Last valid reading</TableHead>
                  <TableHead>Latest quality</TableHead>
                  <TableHead>Sampling</TableHead>
                  <TableHead>Invalid / gaps</TableHead>
                  <TableHead>Connection</TableHead>
                  <TableHead className="hidden xl:table-cell">Warnings</TableHead>
                  {canWrite ? <TableHead className="text-right">Action</TableHead> : null}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sensors.map((sensor) => {
                  const health = healthBySensor.get(sensor.id)
                  const warnings = health?.latest_validation_issues ?? []
                  return (
                    <TableRow
                      key={sensor.id}
                      className={
                        sensor.id === highlightedSensorId
                          ? 'bg-industrial-50/80'
                          : undefined
                      }
                    >
                      <TableCell>
                        <p className="font-mono text-xs font-semibold text-navy-900">
                          {sensor.sensor_code}
                        </p>
                        <p className="mt-0.5 text-[10px] text-slate-500">
                          {sensor.sensor_type.toLowerCase()} ·{' '}
                          {sensor.mounting_axis.replaceAll('_', ' ')} ·{' '}
                          {sensor.sampling_rate_hz.toLocaleString()} Hz
                        </p>
                      </TableCell>
                      <TableCell className="text-xs text-slate-500">
                        {sensor.pump_code ?? 'Unassigned'}
                      </TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {health?.last_valid_reading_at ? (
                          <>
                            <p>{formatDateTime(health.last_valid_reading_at)}</p>
                            <p className="text-[10px] text-slate-400">
                              {health.latest_rms !== null
                                ? `${health.latest_rms.toFixed(4)} g RMS`
                                : 'RMS unavailable'}
                            </p>
                          </>
                        ) : (
                          <span className="text-slate-400">No valid reading</span>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="space-y-1">
                          <StatusBadge status={health?.latest_quality ?? 'NO_DATA'} />
                          {health?.last_reading_at ? (
                            <p className="text-[10px] text-slate-400">
                              {formatDateTime(health.last_reading_at)}
                            </p>
                          ) : null}
                        </div>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={health?.sampling_status ?? 'NO_DATA'} />
                      </TableCell>
                      <TableCell className="text-xs text-slate-600">
                        {health
                          ? `${health.invalid_windows} / ${health.missing_window_gaps}`
                          : '—'}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status="NO_LIVE_CHANNEL" />
                      </TableCell>
                      <TableCell className="hidden xl:table-cell">
                        {warnings.length === 0 ? (
                          <span className="text-xs text-slate-400">No current warnings</span>
                        ) : (
                          <div className="flex flex-wrap gap-1">
                            {warnings.map((issue, index) => (
                              <Badge
                                key={index}
                                variant="sensor"
                                className="font-mono text-[9px]"
                              >
                                {String(issue.code ?? 'unknown')}
                              </Badge>
                            ))}
                          </div>
                        )}
                      </TableCell>
                      {canWrite ? (
                        <TableCell className="text-right">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              toggleMutation.mutate({
                                sensorId: sensor.id,
                                isActive: !sensor.is_active,
                              })
                            }
                            disabled={toggleMutation.isPending}
                          >
                            {sensor.is_active ? 'Deactivate' : 'Activate'}
                          </Button>
                        </TableCell>
                      ) : null}
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <ResearchNotice compact />
    </div>
  )
}

export { SensorsPage }

