import type { Alert, Prediction, PredictionDecision, SessionSummary } from '@petrosense/shared-contracts'
import { BellRing, ChevronRight, FlaskConical } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { Link } from 'react-router-dom'

import { CONDITION_META, relativeTime, scenarioLabel } from '@/components/dashboard/decision-meta'
import { cn, parseApiDate } from '@/lib/utils'

type FeedEvent = {
  id: string
  at: Date
  icon: LucideIcon
  tile: string
  title: string
  detail: string
  href?: string
}

const ALERT_TILE: Record<Alert['category'], string> = {
  FAULT: 'bg-red-100 text-red-700',
  UNCERTAIN: 'bg-amber-100 text-amber-800',
  SENSOR_INVALID: 'bg-violet-100 text-violet-700',
}

const DECISION_TILE: Record<PredictionDecision, string> = {
  NORMAL: 'bg-emerald-100 text-emerald-700',
  FAULT: 'bg-red-100 text-red-700',
  UNCERTAIN: 'bg-amber-100 text-amber-800',
  SENSOR_INVALID: 'bg-violet-100 text-violet-700',
}

function buildEvents(
  predictions: Prediction[],
  sessions: SessionSummary[],
  alerts: Alert[],
): FeedEvent[] {
  const events: FeedEvent[] = []

  for (const session of sessions) {
    events.push({
      id: `session-${session.id}`,
      at: parseApiDate(session.started_at),
      icon: FlaskConical,
      tile: 'bg-slate-100 text-slate-600',
      title: `Scenario: ${scenarioLabel(session.scenario)}`,
      detail: `New simulated session on ${session.pump_code} / ${session.sensor_code}`,
    })
  }

  const ordered = [...predictions].sort(
    (a, b) => parseApiDate(a.inferred_at).getTime() - parseApiDate(b.inferred_at).getTime(),
  )
  for (let index = 1; index < ordered.length; index += 1) {
    const previous = ordered[index - 1]
    const current = ordered[index]
    if (current.decision === previous.decision) continue
    const meta = CONDITION_META[current.decision]
    events.push({
      id: `decision-${current.id}`,
      at: parseApiDate(current.inferred_at),
      icon: meta.icon,
      tile: DECISION_TILE[current.decision],
      title: `Decision ${CONDITION_META[previous.decision].short} → ${meta.short}`,
      detail:
        current.decision === 'SENSOR_INVALID'
          ? 'Signal failed validation; inference suppressed'
          : `Fault score ${current.decision_score?.toFixed(3) ?? '-'}`,
    })
  }

  for (const alert of alerts) {
    events.push({
      id: `alert-${alert.id}`,
      at: parseApiDate(alert.created_at),
      icon: BellRing,
      tile: ALERT_TILE[alert.category],
      title: `${CONDITION_META[alert.category].short} alert raised`,
      detail: `${alert.severity} severity · ${alert.status.toLowerCase()} · awaiting engineer`,
      href: `/alerts/${alert.id}`,
    })
  }

  return events.sort((a, b) => b.at.getTime() - a.at.getTime()).slice(0, 9)
}

const TIME_FORMAT = new Intl.DateTimeFormat('en-GB', {
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
  hour12: false,
  timeZone: 'UTC',
})

function LiveEventFeed({
  predictions,
  sessions,
  alerts,
  now,
}: {
  predictions: Prediction[]
  sessions: SessionSummary[]
  alerts: Alert[]
  now: number
}) {
  const events = buildEvents(predictions, sessions, alerts)

  if (events.length === 0) {
    return (
      <p className="py-8 text-center text-xs text-slate-400">
        Events appear here as scenarios change, decisions flip and alerts are raised.
      </p>
    )
  }

  return (
    <ol className="relative space-y-1">
      {events.map((event, index) => {
        const Icon = event.icon
        const body = (
          <>
            <span
              className={cn(
                'relative z-10 flex size-7 shrink-0 items-center justify-center rounded-full ring-4 ring-white',
                event.tile,
              )}
            >
              <Icon className="size-3.5" aria-hidden="true" />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate text-[13px] font-semibold text-navy-900">{event.title}</p>
                <span className="shrink-0 text-[10px] tabular-nums text-slate-400">
                  {relativeTime(event.at, now)}
                </span>
              </div>
              <p className="truncate text-[11px] text-slate-500">
                {TIME_FORMAT.format(event.at)} UTC · {event.detail}
              </p>
            </div>
            {event.href ? (
              <ChevronRight className="size-4 shrink-0 text-slate-300 group-hover:text-slate-500" aria-hidden="true" />
            ) : null}
          </>
        )
        return (
          <li key={event.id} className="relative">
            {index < events.length - 1 ? (
              <span className="absolute left-[13px] top-8 h-[calc(100%-12px)] w-px bg-slate-200" aria-hidden="true" />
            ) : null}
            {event.href ? (
              <Link
                to={event.href}
                className="group flex items-start gap-3 rounded-lg px-1 py-1.5 transition hover:bg-slate-50"
              >
                {body}
              </Link>
            ) : (
              <div className="flex items-start gap-3 px-1 py-1.5">{body}</div>
            )}
          </li>
        )
      })}
    </ol>
  )
}

export { LiveEventFeed }
