import { FlaskConical } from 'lucide-react'

import { cn } from '@/lib/utils'

interface ResearchNoticeProps {
  className?: string
  compact?: boolean
  variant?: 'light' | 'dark'
}

function ResearchNotice({
  className,
  compact = false,
  variant = 'light',
}: ResearchNoticeProps) {
  const isDark = variant === 'dark'
  return (
    <div
      className={cn(
        'flex gap-3 rounded-xl border',
        isDark
          ? 'border-amber-300/20 bg-white/5'
          : 'border-amber-200/80 bg-amber-50/70 text-amber-950',
        compact ? 'p-3.5' : 'p-4',
        className,
      )}
      role="note"
    >
      <FlaskConical
        className={cn(
          'mt-0.5 size-4 shrink-0',
          isDark ? 'text-amber-300' : 'text-amber-700',
        )}
        aria-hidden="true"
      />
      <div className="space-y-1 text-xs leading-relaxed">
        <p className={cn('font-semibold', isDark ? 'text-amber-100' : 'text-amber-950')}>
          Academic research prototype
        </p>
        <p className={isDark ? 'text-amber-100/70' : 'text-amber-900/80'}>
          Not certified for industrial safety or autonomous shutdown. Simulated signals are for
          software integration only and never establish real-world fault-detection accuracy.
        </p>
      </div>
    </div>
  )
}

export { ResearchNotice }
