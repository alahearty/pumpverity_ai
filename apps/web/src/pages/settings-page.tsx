import { useQuery } from '@tanstack/react-query'
import {
  Database,
  Fingerprint,
  HardDrive,
  Server,
  Settings2,
  SlidersHorizontal,
} from 'lucide-react'

import { PlannedScreen } from '@/components/shared/planned-screen'
import { QueryError } from '@/components/shared/query-error'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { fetchSystemInfo } from '@/services/system-service'
import { formatRole } from '@/lib/utils'

function RuntimeInformation() {
  const systemInfo = useQuery({
    queryKey: ['system-info'],
    queryFn: fetchSystemInfo,
    staleTime: 5 * 60_000,
  })

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Server className="size-4 text-accent-600" aria-hidden="true" />
          Runtime information
        </CardTitle>
        <CardDescription>
          Live, read-only values from the authenticated API. Editable settings are not available in this build.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {systemInfo.isError ? (
          <QueryError error={systemInfo.error} onRetry={() => systemInfo.refetch()} />
        ) : systemInfo.isPending ? (
          <div className="grid gap-3 sm:grid-cols-2">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-16 w-full" />
            ))}
          </div>
        ) : (
          <dl className="grid gap-3 sm:grid-cols-2">
            {[
              ['Project', systemInfo.data.project],
              ['API version', `v${systemInfo.data.version}`],
              ['Environment', systemInfo.data.environment],
              ['Database dialect', systemInfo.data.database_dialect],
              ['Authentication', systemInfo.data.auth_scheme],
              ['Your role', formatRole(systemInfo.data.role)],
              ['Access token lifetime', `${systemInfo.data.access_token_minutes} minutes`],
              ['Refresh session', `${systemInfo.data.refresh_token_days} days`],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-slate-50/60 p-3">
                <dt className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-500">
                  {label}
                </dt>
                <dd className="mt-1 text-xs font-medium capitalize text-navy-900">{value}</dd>
              </div>
            ))}
          </dl>
        )}
      </CardContent>
    </Card>
  )
}

function SettingsPage() {
  return (
    <PlannedScreen
      eyebrow="Governance"
      title="System settings"
      description="Validated, audited configuration for acquisition, inference thresholds, retention, synchronisation and device identity."
      stage={7}
      roles={['ENGINEER', 'RESEARCHER', 'REVIEWER']}
      capabilities={[
        {
          title: 'Acquisition and signal',
          description:
            'Default sampling rate, window size and overlap, with compatibility checks against the active model feature contract.',
          icon: SlidersHorizontal,
        },
        {
          title: 'Decision policy',
          description:
            'Fault and uncertainty thresholds with validation, authorised-role restrictions and audit records.',
          icon: Settings2,
        },
        {
          title: 'Storage and synchronisation',
          description:
            'Local retention, storage limits, sync batch size, retry limits and device identity.',
          icon: HardDrive,
        },
        {
          title: 'Data and export preferences',
          description:
            'Export formats and provenance labelling defaults that keep simulated and experimental data distinct.',
          icon: Database,
        },
      ]}
      endpoints={[
        'GET /api/v1/system-settings',
        'PATCH /api/v1/system-settings',
        'GET /api/v1/system-settings/{key}/history',
        'POST /api/v1/edge-sync/events',
      ]}
      entities={['configuration_settings', 'audit_logs', 'sync_outbox', 'model_versions']}
      controls={[
        'Sensitive changes require an administrator role, checked by the API.',
        'Every configuration change records before/after values, actor and timestamp.',
        'Values are validated before they are applied; invalid thresholds cannot be saved.',
        'Secret values are never returned to the browser or embedded in the frontend.',
      ]}
      previewTitle="Configuration workspace"
      previewDescription="A settings surface that treats configuration as auditable research metadata."
      previewIcon={Fingerprint}
      extra={<RuntimeInformation />}
    />
  )
}

export { SettingsPage }

