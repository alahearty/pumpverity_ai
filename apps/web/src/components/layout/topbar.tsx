import { useQuery } from '@tanstack/react-query'
import { LogOut, Menu, ShieldCheck } from 'lucide-react'
import { useLocation } from 'react-router-dom'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/providers/auth-provider'
import { fetchHealth } from '@/services/health-service'
import { routeMeta } from '@/routes/navigation'
import { cn, formatRole, initials } from '@/lib/utils'

interface TopbarProps {
  onMenuClick: () => void
  onLogout: () => void
  logoutPending: boolean
}

function ApiState() {
  const health = useQuery({
    queryKey: ['health'],
    queryFn: fetchHealth,
    refetchInterval: 60_000,
    retry: 1,
    staleTime: 30_000,
  })

  let label = 'Checking API'
  let dot = 'bg-slate-400'
  if (health.isError) {
    label = 'API unreachable'
    dot = 'bg-fault'
  } else if (health.data?.status === 'ok') {
    label = 'API online'
    dot = 'bg-success'
  } else if (health.data?.status === 'degraded') {
    label = 'API degraded'
    dot = 'bg-uncertain'
  }

  return (
    <div
      className="hidden items-center gap-2 rounded-full border border-slate-200/90 bg-white/80 px-3 py-1.5 text-[10px] font-semibold text-slate-600 shadow-[0_1px_2px_rgba(11,31,51,0.04)] sm:flex"
      title="Monitoring API availability — distinct from edge-device connectivity"
    >
      <span className={cn('size-1.5 rounded-full', dot)} />
      {label}
    </div>
  )
}

function Topbar({ onMenuClick, onLogout, logoutPending }: TopbarProps) {
  const { user } = useAuth()
  const location = useLocation()
  const meta = routeMeta(location.pathname)

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl">
      <div className="flex h-16 items-center gap-3 px-4 sm:px-6 lg:px-8">
        <Button
          variant="ghost"
          size="icon"
          onClick={onMenuClick}
          className="lg:hidden"
          aria-label="Open navigation"
        >
          <Menu className="size-5" />
        </Button>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-400">
            <span>PUMPVERITY AI</span>
            <span className="text-slate-300">/</span>
            <span>{meta.section}</span>
          </div>
          <p className="truncate text-[13px] font-semibold tracking-[-0.01em] text-navy-900">
            {meta.title}
          </p>
        </div>

        <ApiState />

        <Badge
          variant="outline"
          className="hidden gap-1.5 border-slate-200/80 bg-slate-50/80 text-[9px] xl:inline-flex"
        >
          <ShieldCheck className="size-3" aria-hidden="true" />
          Research build
        </Badge>

        <div className="flex items-center gap-2 border-l border-slate-200/80 pl-3">
          <div className="hidden text-right sm:block">
            <p className="max-w-[150px] truncate text-[11px] font-semibold text-navy-900">
              {user?.full_name}
            </p>
            <p className="text-[9px] uppercase tracking-[0.08em] text-slate-500">
              {user ? formatRole(user.role) : ''}
            </p>
          </div>
          <div className="flex size-9 items-center justify-center rounded-lg border border-accent-200/70 bg-gradient-to-br from-accent-50 to-industrial-50 text-[11px] font-semibold text-accent-700 shadow-sm">
            {user ? initials(user.full_name) : '--'}
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onLogout}
            disabled={logoutPending}
            aria-label="Sign out"
            title="Sign out"
            className="size-8 text-slate-500"
          >
            <LogOut className="size-3.5" />
          </Button>
        </div>
      </div>
    </header>
  )
}

export { Topbar }

