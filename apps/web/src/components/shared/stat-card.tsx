import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: ReactNode
  hint?: string
  icon: LucideIcon
  tone?: 'default' | 'accent' | 'success' | 'fault' | 'uncertain' | 'sensor' | 'info'
  className?: string
}

const TONE_STYLES = {
  default: {
    tile: 'bg-slate-100/80 text-slate-600 ring-slate-200/70',
    value: 'text-navy-950',
    bar: 'bg-slate-300',
  },
  accent: {
    tile: 'bg-accent-50 text-accent-700 ring-accent-100',
    value: 'text-navy-950',
    bar: 'bg-accent-500',
  },
  success: {
    tile: 'bg-success-soft text-green-700 ring-green-200/70',
    value: 'text-green-800',
    bar: 'bg-success',
  },
  fault: {
    tile: 'bg-fault-soft text-red-700 ring-red-200/70',
    value: 'text-red-800',
    bar: 'bg-fault',
  },
  uncertain: {
    tile: 'bg-uncertain-soft text-amber-800 ring-amber-200/70',
    value: 'text-amber-900',
    bar: 'bg-uncertain',
  },
  sensor: {
    tile: 'bg-sensor-soft text-violet-700 ring-violet-200/70',
    value: 'text-violet-900',
    bar: 'bg-sensor',
  },
  info: {
    tile: 'bg-industrial-50 text-industrial-700 ring-industrial-100',
    value: 'text-navy-950',
    bar: 'bg-industrial-500',
  },
}

function StatCard({ label, value, hint, icon: Icon, tone = 'default', className }: StatCardProps) {
  const styles = TONE_STYLES[tone]
  const isLongText = typeof value === 'string' && value.length > 22
  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-2xl border border-slate-200/75 bg-white/95 p-5 shadow-[0_1px_2px_rgba(11,31,51,0.035),0_18px_44px_-36px_rgba(11,31,51,0.32)] transition-colors hover:border-slate-300/80',
        className,
      )}
    >
      <span
        className={cn(
          'absolute inset-x-0 top-0 h-0.5 opacity-70',
          styles.bar,
        )}
        aria-hidden="true"
      />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 space-y-1.5">
          <p className="text-[10px] font-semibold uppercase tracking-[0.15em] text-slate-500">
            {label}
          </p>
          <div
            className={cn(
              'font-semibold tracking-[-0.03em]',
              isLongText
                ? 'text-[15px] leading-snug'
                : 'text-[26px] leading-none',
              styles.value,
            )}
          >
            {value}
          </div>
          {hint ? <p className="text-xs leading-relaxed text-slate-500">{hint}</p> : null}
        </div>
        <div className={cn('rounded-xl p-2.5 ring-1 ring-inset', styles.tile)}>
          <Icon className="size-[18px]" aria-hidden="true" />
        </div>
      </div>
    </div>
  )
}

export { StatCard }

