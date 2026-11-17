import { cva, type VariantProps } from 'class-variance-authority'
import type * as React from 'react'

import { cn } from '@/lib/utils'

const buttonVariants = cva(
  [
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-xl text-sm font-semibold',
    'transition-[background-color,border-color,color,box-shadow,transform] duration-150',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-500/70 focus-visible:ring-offset-2 focus-visible:ring-offset-white',
    'disabled:pointer-events-none disabled:opacity-55 [&_svg]:pointer-events-none [&_svg]:shrink-0',
  ].join(' '),
  {
    variants: {
      variant: {
        default:
          'bg-industrial-600 text-white shadow-[0_1px_2px_rgba(11,31,51,0.12)] hover:bg-industrial-700 active:translate-y-px',
        secondary:
          'border border-slate-200 bg-white text-navy-900 shadow-[0_1px_2px_rgba(11,31,51,0.05)] hover:border-slate-300 hover:bg-slate-50 active:translate-y-px',
        ghost: 'text-slate-600 hover:bg-slate-100/80 hover:text-navy-900',
        accent:
          'bg-accent-500 text-white shadow-[0_1px_2px_rgba(0,80,80,0.14)] hover:bg-accent-600 active:translate-y-px',
        destructive:
          'bg-fault text-white shadow-[0_1px_2px_rgba(120,20,20,0.16)] hover:bg-red-700 active:translate-y-px',
        outline:
          'border border-industrial-200 bg-industrial-50/80 text-industrial-700 hover:border-industrial-300 hover:bg-industrial-100',
        link: 'h-auto rounded-none px-0 text-industrial-600 underline-offset-4 hover:underline',
      },
      size: {
        sm: 'h-9 px-3 text-xs [&_svg]:size-3.5',
        md: 'h-10 px-4 [&_svg]:size-4',
        lg: 'h-11 px-5 text-base [&_svg]:size-4',
        icon: 'size-9 [&_svg]:size-4',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'md',
    },
  },
)

type ButtonProps = React.ComponentProps<'button'> & VariantProps<typeof buttonVariants>

function Button({ className, variant, size, type = 'button', ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(buttonVariants({ variant, size }), className)}
      {...props}
    />
  )
}

export { Button, buttonVariants }

