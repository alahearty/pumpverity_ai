import { cva, type VariantProps } from 'class-variance-authority'
import type * as React from 'react'

import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold tracking-wide',
  {
    variants: {
      variant: {
        neutral: 'border-slate-200 bg-slate-50 text-slate-600',
        info: 'border-industrial-200 bg-industrial-50 text-industrial-700',
        success: 'border-green-200 bg-success-soft text-green-700',
        fault: 'border-red-200 bg-fault-soft text-red-700',
        uncertain: 'border-amber-200 bg-uncertain-soft text-amber-800',
        sensor: 'border-violet-200 bg-sensor-soft text-violet-700',
        navy: 'border-navy-700 bg-navy-800 text-slate-100',
        accent: 'border-accent-200 bg-accent-50 text-accent-700',
        outline: 'border-slate-300 bg-transparent text-slate-600',
      },
    },
    defaultVariants: {
      variant: 'neutral',
    },
  },
)

type BadgeProps = React.ComponentProps<'span'> & VariantProps<typeof badgeVariants>

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
export type { BadgeProps }

