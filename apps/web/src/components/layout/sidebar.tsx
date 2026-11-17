import { LogOut, ShieldCheck, X } from 'lucide-react'
import { NavLink } from 'react-router-dom'

import { BrandMark } from '@/components/shared/brand-mark'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/providers/auth-provider'
import { NAV_SECTIONS, canAccess } from '@/routes/navigation'
import { cn, formatRole, initials } from '@/lib/utils'

interface SidebarProps {
  open: boolean
  onClose: () => void
  onLogout: () => void
}

function Sidebar({ open, onClose, onLogout }: SidebarProps) {
  const { user } = useAuth()

  const sections = NAV_SECTIONS.map((section) => ({
    ...section,
    items: section.items.filter((item) => canAccess(user?.role, item.roles)),
  })).filter((section) => section.items.length > 0)

  return (
    <>
      <div
        aria-hidden="true"
        onClick={onClose}
        className={cn(
          'fixed inset-0 z-40 bg-navy-950/60 backdrop-blur-sm transition-opacity duration-200 lg:hidden',
          open ? 'opacity-100' : 'pointer-events-none opacity-0',
        )}
      />
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-72 flex-col overflow-hidden border-r border-white/5 bg-gradient-to-b from-navy-950 via-[#0a1b2d] to-navy-900 text-slate-300 transition-transform duration-200 lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="pointer-events-none absolute inset-x-0 top-0 h-64 bg-[radial-gradient(28rem_16rem_at_15%_0%,rgba(0,166,166,0.12),transparent_70%)]" />
        <div className="relative flex items-center gap-3 border-b border-white/10 px-5 py-5">
          <BrandMark className="size-10 shadow-lg shadow-black/20" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold tracking-tight text-white">PUMPVERITY AI</p>
            <p className="truncate text-[10px] font-medium uppercase tracking-[0.15em] text-slate-500">
              Condition intelligence
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClose}
            className="size-8 text-slate-400 hover:bg-white/10 hover:text-white lg:hidden"
            aria-label="Close navigation"
          >
            <X className="size-4" />
          </Button>
        </div>

        <div className="relative px-4 pt-4">
          <div className="flex items-center justify-between gap-2 rounded-xl border border-amber-400/15 bg-amber-400/[0.07] px-3 py-2">
            <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-amber-200/90">
              Research prototype
            </span>
            <ShieldCheck className="size-3.5 text-amber-200/80" aria-hidden="true" />
          </div>
        </div>

        <nav
          aria-label="Primary"
          className="scrollbar-thin relative mt-4 min-h-0 flex-1 space-y-5 overflow-y-auto px-3 pb-5"
        >
          {sections.map((section) => (
            <div key={section.label}>
              <p className="flex items-center gap-2 px-3 pb-2 text-[9px] font-semibold uppercase tracking-[0.19em] text-slate-600">
                {section.label}
                <span className="h-px flex-1 bg-white/[0.06]" aria-hidden="true" />
              </p>
              <ul className="space-y-0.5">
                {section.items.map((item) => {
                  const Icon = item.icon
                  return (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        end={item.end}
                        onClick={onClose}
                        className={({ isActive }) =>
                          cn(
                            'group relative flex items-center gap-2.5 rounded-xl px-3 py-2 text-[13px] font-medium transition-all duration-150',
                            isActive
                              ? 'bg-white/[0.09] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]'
                              : 'text-slate-400 hover:bg-white/[0.05] hover:text-slate-100',
                          )
                        }
                      >
                        {({ isActive }) => (
                          <>
                            <span
                              className={cn(
                                'absolute left-0 h-5 w-0.5 rounded-full bg-accent-400 transition-opacity',
                                isActive ? 'opacity-100' : 'opacity-0',
                              )}
                              aria-hidden="true"
                            />
                            <Icon
                              className={cn(
                                'size-4 transition-colors',
                                isActive
                                  ? 'text-accent-200'
                                  : 'text-slate-500 group-hover:text-slate-300',
                              )}
                              aria-hidden="true"
                            />
                            <span className="flex-1 truncate">{item.label}</span>
                            {item.stage ? (
                              <span
                                className={cn(
                                  'rounded-md border px-1 py-px font-mono text-[9px]',
                                  isActive
                                    ? 'border-accent-200/25 text-accent-100'
                                    : 'border-white/10 text-slate-500',
                                )}
                                title={`Planned for Stage ${item.stage}`}
                              >
                                S{item.stage}
                              </span>
                            ) : null}
                          </>
                        )}
                      </NavLink>
                    </li>
                  )
                })}
              </ul>
            </div>
          ))}
        </nav>

        <div className="relative border-t border-white/10 p-4">
          <div className="flex items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.04] px-3 py-2.5">
            <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-accent-500/25 to-industrial-500/20 text-[11px] font-semibold text-accent-100 ring-1 ring-white/10">
              {user ? initials(user.full_name) : '--'}
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-semibold text-white">{user?.full_name}</p>
              <p className="truncate text-[10px] text-slate-400">
                {user ? formatRole(user.role) : 'Signed in'}
              </p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onLogout}
              className="size-8 text-slate-400 hover:bg-white/10 hover:text-white"
              aria-label="Sign out"
            >
              <LogOut className="size-3.5" />
            </Button>
          </div>
          <div className="mt-3 flex items-center justify-between px-1">
            <Badge variant="navy" className="border-white/10 text-[9px] text-slate-400">
              v0.6.0 · Copilot
            </Badge>
            <span className="text-[9px] uppercase tracking-[0.14em] text-slate-600">
              Offline-first
            </span>
          </div>
        </div>
      </aside>
    </>
  )
}

export { Sidebar }

