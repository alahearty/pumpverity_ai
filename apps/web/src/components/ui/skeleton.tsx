import { cn } from '@/lib/utils'

function Skeleton({ className, ...props }: React.ComponentProps<'div'>) {
  return (
    <div
      className={cn('relative overflow-hidden rounded-lg bg-slate-200/60 before:absolute before:inset-0 before:-translate-x-full before:animate-[shimmer_1.8s_infinite] before:bg-gradient-to-r before:from-transparent before:via-white/55 before:to-transparent', className)}
      {...props}
    />
  )
}

export { Skeleton }

