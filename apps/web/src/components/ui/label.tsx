import type * as React from 'react'

import { cn } from '@/lib/utils'

function Label({ className, ...props }: React.ComponentProps<'label'>) {
  return (
    <label
      className={cn('text-[12px] font-semibold leading-none text-slate-700', className)}
      {...props}
    />
  )
}

export { Label }

