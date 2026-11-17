import { ChevronDown } from 'lucide-react'
import type * as React from 'react'

import { cn } from '@/lib/utils'

function Select({ className, children, ...props }: React.ComponentProps<'select'>) {
  return (
    <div className="relative">
      <select
        className={cn(
          'h-10 w-full appearance-none rounded-xl border border-slate-200 bg-white pl-3 pr-9 text-sm text-navy-900 shadow-[0_1px_2px_rgba(11,31,51,0.04)] outline-none transition duration-150',
          'hover:border-slate-300 focus:border-accent-500 focus:ring-4 focus:ring-accent-500/12',
          'disabled:cursor-not-allowed disabled:bg-slate-50',
          className,
        )}
        {...props}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-slate-400"
      />
    </div>
  )
}

export { Select }

