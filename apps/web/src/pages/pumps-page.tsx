import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { Pump, PumpCreate, PumpUpdate } from '@petrosense/shared-contracts'
import {
  Activity,
  Gauge,
  Pencil,
  Plus,
  Radio,
  RefreshCw,
  Terminal,
  Waves,
} from 'lucide-react'
import { useState } from 'react'

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
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { PumpEditForm } from '@/features/equipment/pump-edit-form'
import { PumpRegistrationForm } from '@/features/equipment/pump-registration-form'
import {
  createPump,
  fetchOperatingRegimes,
  fetchPumps,
  updatePump,
} from '@/services/equipment-service'
import { fetchAcquisitionSessions } from '@/services/acquisition-service'
import { formatDateTime, formatScenario } from '@/lib/utils'

function PumpsPage() {
  const [showRegistration, setShowRegistration] = useState(false)
  const [editingPump, setEditingPump] = useState<Pump | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const pumpsQuery = useQuery({
    queryKey: ['pumps', { page: 1, page_size: 100 }],
    queryFn: () => fetchPumps({ page: 1, page_size: 100 }),
  })
  const regimesQuery = useQuery({
    queryKey: ['operating-regimes'],
    queryFn: fetchOperatingRegimes,
    staleTime: 5 * 60_000,
  })
  const sessionsQuery = useQuery({
    queryKey: ['acquisition-sessions', { page: 1, page_size: 8 }],
    queryFn: () => fetchAcquisitionSessions({ page: 1, page_size: 8, provenance: 'SIMULATED' }),
  })

  const invalidateEquipment = () => {
    queryClient.invalidateQueries({ queryKey: ['pumps'] })
    queryClient.invalidateQueries({ queryKey: ['sensors'] })
    queryClient.invalidateQueries({ queryKey: ['acquisition-sessions'] })
  }

  const createMutation = useMutation({
    mutationFn: (payload: PumpCreate) => createPump(payload),
    onSuccess: (pump) => {
      invalidateEquipment()
      setShowRegistration(false)
      setSuccessMessage(`Registered ${pump.pump_code} with ${pump.sensors.length} sensor(s).`)
    },
  })
  const updateMutation = useMutation({
    mutationFn: ({ pumpId, payload }: { pumpId: string; payload: PumpUpdate }) =>
      updatePump(pumpId, payload),
    onSuccess: (pump) => {
      invalidateEquipment()
      setEditingPump(null)
      setSuccessMessage(`Updated ${pump.pump_code}.`)
    },
  })

  const pumps = pumpsQuery.data?.items ?? []
  const regimes = regimesQuery.data ?? []
  const sessions = sessionsQuery.data?.items ?? []
  const totalPumps = pumpsQuery.data?.total ?? 0
  const totalSensors = pumps.reduce((total, pump) => total + pump.sensors.length, 0)
  const activePumps = pumps.filter((pump) => pump.status === 'ACTIVE').length

  const examplePump = pumps[0]
  const exampleSensor =
    examplePump?.sensors.find((sensor) => sensor.sensor_type === 'VIBRATION') ??
    examplePump?.sensors[0]
  const simulationCommand = [
    '$env:PETROSENSE_EDGE_PASSWORD = "<demo password>"',
    `python -m petrosense_edge.cli --pump-code ${examplePump?.pump_code ?? 'LAB-PUMP-01'} --sensor-code ${exampleSensor?.sensor_code ?? 'VIB-01'} --scenario normal --windows 5 --seed 42`,
  ].join('\n')

  function openRegistration() {
    setEditingPump(null)
    setShowRegistration(true)
    setSuccessMessage(null)
  }

  function openEdit(pump: Pump) {
    setShowRegistration(false)
    setEditingPump(pump)
    setSuccessMessage(null)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Assets"
        title="Pump registration"
        description="Register the laboratory centrifugal pump and its vibration sensor. Equipment identity is stored independently from condition, sensor quality and connectivity."
        badge={<Badge variant="info">Equipment registry</Badge>}
        actions={
          <>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => {
                pumpsQuery.refetch()
                regimesQuery.refetch()
                sessionsQuery.refetch()
              }}
              disabled={pumpsQuery.isFetching}
            >
              <RefreshCw className="size-3.5" aria-hidden="true" />
              Refresh
            </Button>
            <Button size="sm" onClick={openRegistration}>
              <Plus className="size-3.5" aria-hidden="true" />
              Register pump
            </Button>
          </>
        }
      />

      {successMessage ? (
        <div className="rounded-xl border border-green-200 bg-success-soft px-4 py-3 text-sm text-green-800">
          {successMessage}
        </div>
      ) : null}

      <div className="flex items-start gap-3 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4">
        <Gauge className="mt-0.5 size-4 shrink-0 text-industrial-600" aria-hidden="true" />
        <div className="space-y-1 text-xs leading-relaxed text-industrial-900">
          <p className="font-semibold">Equipment registration is active</p>
          <p className="text-industrial-900/75">
            This screen stores pump ratings, the initial sensor assignment and lifecycle status.
            Simulation writes only provenance-tagged <span className="font-mono">SIMULATED</span>{' '}
            sessions; experimental acquisition remains disabled until physical hardware is
            validated.
          </p>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Registered pumps"
          value={pumpsQuery.isPending ? '—' : totalPumps}
          hint="Laboratory rigs in the equipment registry"
          icon={Gauge}
          tone="info"
        />
        <StatCard
          label="Assigned sensors"
          value={pumpsQuery.isPending ? '—' : totalSensors}
          hint="Vibration, RPM or temperature channels"
          icon={Radio}
          tone="accent"
        />
        <StatCard
          label="Active equipment"
          value={pumpsQuery.isPending ? '—' : activePumps}
          hint="Pumps currently marked ACTIVE"
          icon={Waves}
          tone="success"
        />
        <StatCard
          label="Simulated sessions"
          value={sessionsQuery.isPending ? '—' : (sessionsQuery.data?.total ?? 0)}
          hint="Deterministic simulated acquisition runs"
          icon={Activity}
          tone="uncertain"
        />
      </div>

      {showRegistration ? (
        <Card>
          <CardHeader>
            <CardTitle>Register laboratory pump</CardTitle>
            <CardDescription>
              Pump and initial sensor are created in one transaction. A duplicate sensor code
              rejects the whole registration.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PumpRegistrationForm
              regimes={regimes}
              onSubmit={async (payload) => {
                await createMutation.mutateAsync(payload)
              }}
              onCancel={() => setShowRegistration(false)}
            />
          </CardContent>
        </Card>
      ) : null}

      {editingPump ? (
        <Card>
          <CardHeader>
            <CardTitle>Edit pump · {editingPump.pump_code}</CardTitle>
            <CardDescription>
              Identity, ratings, operating-regime default and equipment status.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <PumpEditForm
              pump={editingPump}
              regimes={regimes}
              onSubmit={async (payload) => {
                await updateMutation.mutateAsync({ pumpId: editingPump.id, payload })
              }}
              onCancel={() => setEditingPump(null)}
            />
          </CardContent>
        </Card>
      ) : null}

      <Card>
        <CardHeader className="border-b border-slate-100 pb-4">
          <CardTitle>Equipment registry</CardTitle>
          <CardDescription>
            {pumpsQuery.data
              ? `${pumpsQuery.data.total} registered pump(s). The initial scope is one laboratory rig.`
              : 'Loading equipment registry…'}
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {pumpsQuery.isError ? (
            <div className="p-5">
              <QueryError error={pumpsQuery.error} onRetry={() => pumpsQuery.refetch()} />
            </div>
          ) : pumpsQuery.isPending ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 3 }).map((_, index) => (
                <div key={index} className="flex items-center gap-4">
                  <Skeleton className="size-9 rounded-lg" />
                  <div className="flex-1 space-y-2">
                    <Skeleton className="h-3.5 w-48" />
                    <Skeleton className="h-3 w-72" />
                  </div>
                  <Skeleton className="h-6 w-20" />
                </div>
              ))}
            </div>
          ) : pumps.length === 0 ? (
            <div className="p-5">
              <EmptyState
                icon={Gauge}
                title="No pumps registered"
                description="Register the laboratory centrifugal pump and assign its first vibration sensor. No demonstration equipment record is pre-seeded."
                action={
                  <Button onClick={openRegistration}>
                    <Plus className="size-4" aria-hidden="true" />
                    Register first pump
                  </Button>
                }
              />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="bg-slate-50/70">
                  <TableHead>Pump</TableHead>
                  <TableHead className="hidden md:table-cell">Location / type</TableHead>
                  <TableHead>Rated speed</TableHead>
                  <TableHead className="hidden lg:table-cell">Default regime</TableHead>
                  <TableHead>Sensors</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pumps.map((pump) => (
                  <TableRow key={pump.id}>
                    <TableCell>
                      <p className="font-mono text-xs font-semibold text-navy-900">
                        {pump.pump_code}
                      </p>
                      <p className="mt-0.5 text-sm text-slate-600">{pump.name}</p>
                    </TableCell>
                    <TableCell className="hidden text-xs text-slate-500 md:table-cell">
                      <p>{pump.location}</p>
                      <p className="mt-0.5 capitalize">{pump.pump_type.replaceAll('_', ' ').toLowerCase()}</p>
                    </TableCell>
                    <TableCell className="text-sm text-slate-600">
                      {pump.rated_speed_rpm.toLocaleString()} RPM
                    </TableCell>
                    <TableCell className="hidden text-xs text-slate-500 lg:table-cell">
                      {pump.default_regime?.name ?? 'Not set'}
                    </TableCell>
                    <TableCell>
                      <div className="flex flex-col gap-1">
                        {pump.sensors.length === 0 ? (
                          <span className="text-xs text-slate-400">No sensors</span>
                        ) : (
                          pump.sensors.map((sensor) => (
                            <div key={sensor.id} className="flex items-center gap-1.5">
                              <Radio className="size-3 text-accent-600" aria-hidden="true" />
                              <span className="font-mono text-[11px] font-medium text-navy-800">
                                {sensor.sensor_code}
                              </span>
                              <span className="text-[10px] text-slate-400">
                                {sensor.mounting_axis.replaceAll('_', ' ')}
                              </span>
                            </div>
                          ))
                        )}
                      </div>
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={pump.status} />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => openEdit(pump)}
                        aria-label={`Edit ${pump.pump_code}`}
                      >
                        <Pencil className="size-3.5" aria-hidden="true" />
                        Edit
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="border-b border-slate-100 pb-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle>Recent simulated acquisition</CardTitle>
              <CardDescription>
                Deterministic sessions persisted by the edge simulator. All rows are simulated and
                are not experimental evidence.
              </CardDescription>
            </div>
            <Badge variant="uncertain">SIMULATED ONLY</Badge>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {sessionsQuery.isError ? (
            <div className="p-5">
              <QueryError error={sessionsQuery.error} onRetry={() => sessionsQuery.refetch()} />
            </div>
          ) : sessionsQuery.isPending ? (
            <div className="space-y-2 p-5">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : sessions.length === 0 ? (
            <div className="grid gap-4 p-5 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
              <EmptyState
                compact
                icon={Terminal}
                title="No simulated sessions yet"
                description="Register a pump and sensor, then run the edge simulator CLI. The session and validated windows will appear here."
              />
              <div className="rounded-lg border border-slate-200 bg-navy-950 p-4">
                <p className="mb-2 flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  <Terminal className="size-3.5" aria-hidden="true" />
                  From the repository root
                </p>
                <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[11px] leading-relaxed text-accent-100">
                  {simulationCommand}
                </pre>
                <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
                  The invocation writes provenance-tagged simulated sessions to the local API.
                </p>
              </div>
            </div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="bg-slate-50/70">
                    <TableHead>Scenario</TableHead>
                    <TableHead>Equipment</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Windows</TableHead>
                    <TableHead>Provenance</TableHead>
                    <TableHead className="hidden lg:table-cell">Started</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sessions.map((session) => (
                    <TableRow key={session.id}>
                      <TableCell>
                        <p className="text-sm font-medium text-navy-900">
                          {formatScenario(session.scenario)}
                        </p>
                        <p className="font-mono text-[10px] text-slate-400">
                          {session.id.slice(0, 8)} · seed {session.random_seed ?? '—'}
                        </p>
                      </TableCell>
                      <TableCell className="text-xs text-slate-500">
                        <p className="font-mono">{session.pump_code}</p>
                        <p className="font-mono text-slate-400">{session.sensor_code}</p>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={session.status} />
                      </TableCell>
                      <TableCell className="text-sm text-slate-600">
                        {session.window_count}
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={session.data_provenance} />
                      </TableCell>
                      <TableCell className="hidden text-xs text-slate-500 lg:table-cell">
                        {formatDateTime(session.started_at)}
                        {session.started_by_name ? (
                          <p className="text-[10px] text-slate-400">
                            by {session.started_by_name} ·{' '}
                            {session.regime?.name ?? 'Regime not set'}
                          </p>
                        ) : null}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              <div className="border-t border-slate-100 p-4">
                <p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                  Run another deterministic simulation
                </p>
                <pre className="overflow-x-auto whitespace-pre-wrap rounded-lg bg-navy-950 p-3 font-mono text-[10px] leading-relaxed text-accent-100">
                  {simulationCommand}
                </pre>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      <ResearchNotice compact />
    </div>
  )
}

export { PumpsPage }

