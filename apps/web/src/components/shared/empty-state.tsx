import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
  className?: string
  compact?: boolean
}

function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
  compact = false,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300/90 bg-gradient-to-b from-slate-50/80 to-white px-6 text-center',
        compact ? 'py-8' : 'py-14',
        className,
      )}
    >
      <div className="mb-4 rounded-full border border-slate-200 bg-white p-3 shadow-sm">
        <Icon className="size-5 text-slate-400" aria-hidden="true" />
      </div>
      <p className="text-sm font-semibold text-navy-900">{title}</p>
      <p className="mt-1.5 max-w-md text-sm leading-relaxed text-slate-500">{description}</p>
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  )
}

export { EmptyState }

