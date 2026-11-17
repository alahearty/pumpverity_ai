import type * as React from 'react'

import { cn } from '@/lib/utils'

function Textarea({ className, ...props }: React.ComponentProps<'textarea'>) {
  return (
    <textarea
      className={cn(
        'flex min-h-20 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-navy-900 shadow-[0_1px_2px_rgba(11,31,51,0.04)] outline-none transition duration-150 placeholder:text-slate-400',
        'hover:border-slate-300 focus:border-accent-500 focus:ring-4 focus:ring-accent-500/12',
        'aria-invalid:border-fault aria-invalid:focus:border-fault aria-invalid:ring-fault/15',
        'disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500',
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }

