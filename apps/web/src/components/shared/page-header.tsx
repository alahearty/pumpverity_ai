import type { ReactNode } from 'react'

import { cn } from '@/lib/utils'

interface PageHeaderProps {
  eyebrow?: string
  title: string
  description?: string
  actions?: ReactNode
  badge?: ReactNode
  className?: string
}

function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  badge,
  className,
}: PageHeaderProps) {
  return (
    <header
      className={cn(
        'flex flex-col gap-5 border-b border-slate-200/70 pb-6 sm:flex-row sm:items-end sm:justify-between sm:gap-8',
        className,
      )}
    >
      <div className="min-w-0 max-w-4xl space-y-2.5">
        {eyebrow ? (
          <div className="flex items-center gap-2">
            <span className="h-px w-5 bg-accent-500/70" aria-hidden="true" />
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-accent-700">
              {eyebrow}
            </p>
          </div>
        ) : null}
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-balance text-[26px] font-semibold leading-tight tracking-[-0.025em] text-navy-950 sm:text-[30px]">
            {title}
          </h1>
          {badge}
        </div>
        {description ? (
          <p className="max-w-3xl text-[13px] leading-relaxed text-slate-500 sm:text-sm">
            {description}
          </p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 flex-wrap items-center gap-2 sm:justify-end">
          {actions}
        </div>
      ) : null}
    </header>
  )
}

export { PageHeader }
