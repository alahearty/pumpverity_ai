import { FlaskConical, Microscope } from 'lucide-react'

import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

interface ProvenanceBadgeProps {
  provenance: 'SIMULATED' | 'EXPERIMENTAL' | string
  className?: string
}

function ProvenanceBadge({ provenance, className }: ProvenanceBadgeProps) {
  if (provenance === 'EXPERIMENTAL') {
    return (
      <Badge
        variant="accent"
        className={cn('gap-1.5', className)}
        title="Experimental measurement provenance"
      >
        <Microscope className="size-3" aria-hidden="true" />
        Experimental data
      </Badge>
    )
  }
  return (
    <Badge
      variant="uncertain"
      className={cn('gap-1.5', className)}
      title="Simulated data - not experimental evidence"
    >
      <FlaskConical className="size-3" aria-hidden="true" />
      Simulated data
    </Badge>
  )
}

export { ProvenanceBadge }
