import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface StageBadgeProps {
  stage: number
  label?: string
  className?: string
}

function StageBadge({ stage, label, className }: StageBadgeProps) {
  return (
    <Badge variant="outline" className={cn('font-medium tracking-normal', className)}>
      {label ?? `Stage ${stage} · Planned`}
    </Badge>
  )
}

export { StageBadge }
