import type { Role } from '@petrosense/shared-contracts'
import {
  CheckCircle2,
  Database,
  Info,
  ListChecks,
  Server,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'

import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/shared/page-header'
import { ResearchNotice } from '@/components/shared/research-notice'
import { StageBadge } from '@/components/shared/stage-badge'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { cn, formatRole } from '@/lib/utils'

interface PlannedCapability {
  title: string
  description: string
  icon: LucideIcon
}

interface PlannedScreenProps {
  eyebrow: string
  title: string
  description: string
  stage: number
  roles: Role[]
  capabilities: PlannedCapability[]
  endpoints: string[]
  entities: string[]
  controls: string[]
  previewTitle: string
  previewDescription: string
  previewIcon: LucideIcon
  extra?: ReactNode
  className?: string
}

function PlannedScreen({
  eyebrow,
  title,
  description,
  stage,
  roles,
  capabilities,
  endpoints,
  entities,
  controls,
  previewTitle,
  previewDescription,
  previewIcon,
  extra,
  className,
}: PlannedScreenProps) {
  return (
    <div className={cn('space-y-6', className)}>
      <PageHeader
        eyebrow={eyebrow}
        title={title}
        description={description}
        badge={<StageBadge stage={stage} />}
      />

      <div className="flex items-start gap-3 rounded-xl border border-industrial-200/80 bg-industrial-50/70 p-4 text-industrial-900">
        <Info className="mt-0.5 size-4 shrink-0 text-industrial-600" aria-hidden="true" />
        <div className="space-y-1 text-xs leading-relaxed">
          <p className="font-semibold">Planned scope — not active in this build</p>
          <p className="text-industrial-900/75">
            This route is present for navigation and design review. It does not display
            operational, simulated or experimental measurements. Implementation arrives in Stage{' '}
            {stage} with backend persistence and automated tests.
          </p>
        </div>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <section className="space-y-3">
            <h2 className="text-sm font-semibold text-navy-900">Planned capability</h2>
            <div className="grid gap-3 sm:grid-cols-2">
              {capabilities.map((capability) => {
                const Icon = capability.icon
                return (
                  <Card key={capability.title} className="p-5">
                    <div className="mb-3 flex size-9 items-center justify-center rounded-lg bg-navy-900/5 text-navy-800">
                      <Icon className="size-4" aria-hidden="true" />
                    </div>
                    <p className="text-sm font-semibold text-navy-900">{capability.title}</p>
                    <p className="mt-1 text-xs leading-relaxed text-slate-500">
                      {capability.description}
                    </p>
                  </Card>
                )
              })}
            </div>
          </section>

          {extra}

          <Card>
            <CardHeader>
              <CardTitle>{previewTitle}</CardTitle>
              <CardDescription>{previewDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="relative overflow-hidden rounded-lg border border-dashed border-slate-300 bg-grid">
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-white/30 via-white/70 to-white/90" />
                <EmptyState
                  icon={previewIcon}
                  title={`Available in Stage ${stage}`}
                  description="No placeholder measurements are displayed. Values will be rendered only from validated backend records with explicit data provenance."
                  className="relative border-0 bg-transparent"
                />
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-5">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <ShieldCheck className="size-4 text-accent-600" aria-hidden="true" />
                Access policy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-xs text-slate-500">
                Enforced by the API, not only by hidden navigation.
              </p>
              <div className="flex flex-wrap gap-1.5">
                {roles.map((role) => (
                  <Badge key={role} variant="info" className="font-medium tracking-normal">
                    {formatRole(role)}
                  </Badge>
                ))}
                <Badge variant="outline" className="font-medium tracking-normal">
                  Administrator
                </Badge>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Server className="size-4 text-industrial-600" aria-hidden="true" />
                Planned API contract
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-1.5">
                {endpoints.map((endpoint) => (
                  <li
                    key={endpoint}
                    className="rounded-md bg-slate-50 px-2.5 py-1.5 font-mono text-[11px] text-slate-600"
                  >
                    {endpoint}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <Database className="size-4 text-navy-700" aria-hidden="true" />
                Data entities
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-1.5">
              {entities.map((entity) => (
                <Badge key={entity} variant="neutral" className="font-mono text-[10px]">
                  {entity}
                </Badge>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2 text-sm">
                <ListChecks className="size-4 text-accent-600" aria-hidden="true" />
                Required controls
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2">
                {controls.map((control) => (
                  <li key={control} className="flex gap-2 text-xs leading-relaxed text-slate-600">
                    <CheckCircle2
                      className="mt-0.5 size-3.5 shrink-0 text-accent-600"
                      aria-hidden="true"
                    />
                    {control}
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>

      <ResearchNotice />
    </div>
  )
}

export { PlannedScreen }
export type { PlannedCapability }
