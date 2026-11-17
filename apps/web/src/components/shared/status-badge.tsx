import type { BadgeProps } from '@/components/ui/badge'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type StatusTone =
  | 'neutral'
  | 'info'
  | 'success'
  | 'fault'
  | 'uncertain'
  | 'sensor'
  | 'accent'
  | 'outline'

const STATUS_MAP: Record<
  string,
  { label: string; tone: StatusTone; dot: string }
> = {
  NORMAL: { label: 'Normal', tone: 'success', dot: 'bg-success' },
  INACTIVE: { label: 'Inactive', tone: 'neutral', dot: 'bg-slate-400' },
  ADMINISTRATOR: { label: 'Administrator', tone: 'info', dot: 'bg-industrial-600' },
  ENGINEER: { label: 'Engineer', tone: 'accent', dot: 'bg-accent-500' },
  RESEARCHER: { label: 'Researcher', tone: 'neutral', dot: 'bg-slate-400' },
  REVIEWER: { label: 'Reviewer', tone: 'uncertain', dot: 'bg-uncertain' },
  FAULT: { label: 'Fault', tone: 'fault', dot: 'bg-fault' },
  UNCERTAIN: { label: 'Uncertain', tone: 'uncertain', dot: 'bg-uncertain' },
  SENSOR_INVALID: { label: 'Sensor invalid', tone: 'sensor', dot: 'bg-sensor' },
  VALID: { label: 'Valid signal', tone: 'info', dot: 'bg-industrial-600' },
  NO_DATA: { label: 'No data', tone: 'neutral', dot: 'bg-slate-400' },
  RECENT: { label: 'Recent data', tone: 'success', dot: 'bg-success' },
  STALE: { label: 'Stale data', tone: 'uncertain', dot: 'bg-uncertain' },
  NO_LIVE_CHANNEL: { label: 'No live channel', tone: 'neutral', dot: 'bg-slate-400' },
  ONLINE: { label: 'Online', tone: 'success', dot: 'bg-success' },
  OFFLINE_BUFFERING: { label: 'Offline — buffering', tone: 'uncertain', dot: 'bg-uncertain' },
  SYNCING: { label: 'Syncing', tone: 'info', dot: 'bg-industrial-600' },
  SYNCED: { label: 'Synced', tone: 'success', dot: 'bg-success' },
  SYNC_ERROR: { label: 'Sync error', tone: 'fault', dot: 'bg-fault' },
  MAINTENANCE: { label: 'Maintenance', tone: 'uncertain', dot: 'bg-uncertain' },
  COMPLETED: { label: 'Completed', tone: 'success', dot: 'bg-success' },
  QUEUED: { label: 'Queued', tone: 'neutral', dot: 'bg-slate-400' },
  RUNNING: { label: 'Running', tone: 'info', dot: 'bg-industrial-600' },
  FAILED: { label: 'Failed', tone: 'fault', dot: 'bg-fault' },
  ABORTED: { label: 'Aborted', tone: 'fault', dot: 'bg-fault' },
  OPEN: { label: 'Open', tone: 'fault', dot: 'bg-fault' },
  ACKNOWLEDGED: { label: 'Acknowledged', tone: 'info', dot: 'bg-industrial-600' },
  REVIEWED: { label: 'Reviewed', tone: 'success', dot: 'bg-success' },
  CLOSED: { label: 'Closed', tone: 'neutral', dot: 'bg-slate-400' },
  DISMISSED: { label: 'Dismissed', tone: 'neutral', dot: 'bg-slate-400' },
  LOW: { label: 'Low', tone: 'neutral', dot: 'bg-slate-400' },
  MEDIUM: { label: 'Medium', tone: 'uncertain', dot: 'bg-uncertain' },
  HIGH: { label: 'High', tone: 'fault', dot: 'bg-fault' },
  CRITICAL: { label: 'Critical', tone: 'fault', dot: 'bg-red-700' },
  REGISTERED: { label: 'Registered', tone: 'neutral', dot: 'bg-slate-400' },
  VALIDATED: { label: 'Validated', tone: 'info', dot: 'bg-industrial-600' },
  ACTIVE: { label: 'Active', tone: 'success', dot: 'bg-success' },
  RETIRED: { label: 'Retired', tone: 'neutral', dot: 'bg-slate-400' },
  REJECTED: { label: 'Rejected', tone: 'fault', dot: 'bg-fault' },
  SIMULATED: { label: 'Simulated', tone: 'uncertain', dot: 'bg-uncertain' },
  EXPERIMENTAL: { label: 'Experimental', tone: 'success', dot: 'bg-success' },
}

interface StatusBadgeProps extends Omit<BadgeProps, 'variant' | 'children'> {
  status: string
  label?: string
  showDot?: boolean
}

function StatusBadge({ status, label, showDot = true, className, ...props }: StatusBadgeProps) {
  const entry = STATUS_MAP[status] ?? {
    label: status
      .toLowerCase()
      .split('_')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' '),
    tone: 'neutral' as StatusTone,
    dot: 'bg-slate-400',
  }
  return (
    <Badge variant={entry.tone} className={cn('whitespace-nowrap', className)} {...props}>
      {showDot ? <span className={cn('size-1.5 rounded-full', entry.dot)} /> : null}
      {label ?? entry.label}
    </Badge>
  )
}

export { StatusBadge }

