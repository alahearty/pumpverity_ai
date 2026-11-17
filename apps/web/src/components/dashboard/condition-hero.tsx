import type { LiveWindow, Prediction } from '@petrosense/shared-contracts'
import { ArrowRight, FlaskConical } from 'lucide-react'

import {
  CONDITION_META,
  FAULT_THRESHOLD,
  NORMAL_THRESHOLD,
  relativeTime,
  scenarioLabel,
  type ConditionKey,
} from '@/components/dashboard/decision-meta'
import { useNow } from '@/hooks/use-now'
import { cn, parseApiDate } from '@/lib/utils'

function explanation(condition: ConditionKey, prediction: Prediction | null, window: LiveWindow | null) {
  const score = prediction?.decision_score
  const scoreText = typeof score === 'number' ? score.toFixed(3) : '-'
  switch (condition) {
    case 'NORMAL':
      return `Fault score ${scoreText} is below the ${NORMAL_THRESHOLD} normal threshold. No alert is raised.`
    case 'FAULT':
      return `Fault score ${scoreText} is above the ${FAULT_THRESHOLD} fault threshold. A reviewable alert has been raised for an engineer.`
    case 'UNCERTAIN':
      return `Fault score ${scoreText} sits inside the ${NORMAL_THRESHOLD}-${FAULT_THRESHOLD} abstention band. The system declines to guess and routes it to engineering review.`
    case 'SENSOR_INVALID': {
      const codes = window?.validation_issue_codes?.length
        ? window.validation_issue_codes.join(', ').replace(/_/g, ' ')
        : 'validation failure'
      return `Signal failed validation (${codes}). The model was not run, and the pump is never reported as healthy on bad data.`
    }
    default:
      return 'Start the edge stream to see live decisions.'
  }
}

interface MetricProps {
  label: string
  value: string
  unit?: string
  muted?: boolean
}

function Metric({ label, value, unit, muted }: MetricProps) {
  return (
    <div className="min-w-0 rounded-xl border border-slate-200/80 bg-white/80 px-4 py-3 backdrop-blur">
      <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">{label}</p>
      <p className={cn('mt-1 font-mono text-2xl font-semibold tabular-nums', muted ? 'text-slate-300' : 'text-navy-900')}>
        {value}
        {unit ? <span className="ml-1 text-xs font-medium text-slate-400">{unit}</span> : null}
      </p>
    </div>
  )
}

interface ConditionHeroProps {
  pumpLabel: string
  sensorLabel: string
  latestWindow: LiveWindow | null
  latestPrediction: Prediction | null
  streamOnline: boolean
}

function ConditionHero({
  pumpLabel,
  sensorLabel,
  latestWindow,
  latestPrediction,
  streamOnline,
}: ConditionHeroProps) {
  const now = useNow()
  const invalid = latestWindow?.quality_status === 'SENSOR_INVALID'
  const condition: ConditionKey = invalid
    ? 'SENSOR_INVALID'
    : (latestPrediction?.decision ?? 'NONE')
  const meta = CONDITION_META[condition]
  const Icon = meta.icon
  const updatedAt = latestWindow ? parseApiDate(latestWindow.window_end) : null
  const fresh = updatedAt ? now - updatedAt.getTime() < 10_000 : false
  const showScores = !invalid && latestPrediction && latestPrediction.decision !== 'SENSOR_INVALID'

  return (
    <section
      aria-live="polite"
      className={cn(
        'relative overflow-hidden rounded-2xl border-2 shadow-sm transition-colors duration-500',
        meta.surface,
        meta.ring,
      )}
    >
      <div className="grid gap-6 p-5 sm:p-6 xl:grid-cols-[minmax(0,1fr)_minmax(0,520px)] xl:items-center">
        <div className="min-w-0 space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 font-semibold',
                fresh && streamOnline ? 'bg-navy-900 text-white' : 'bg-slate-200 text-slate-600',
              )}
            >
              <span className="relative flex size-2">
                {fresh && streamOnline ? (
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
                ) : null}
                <span
                  className={cn(
                    'relative inline-flex size-2 rounded-full',
                    fresh && streamOnline ? 'bg-emerald-400' : 'bg-slate-400',
                  )}
                />
              </span>
              {fresh && streamOnline ? 'LIVE' : 'IDLE'}
            </span>
            <span className="font-semibold text-navy-900">{pumpLabel}</span>
            <span className="text-slate-400">·</span>
            <span className="text-slate-500">{sensorLabel}</span>
            <span className="text-slate-400">·</span>
            <span className="text-slate-500">
              {updatedAt ? `updated ${relativeTime(updatedAt, now)}` : 'no data yet'}
            </span>
          </div>

          <div className="flex items-start gap-4">
            <span
              className={cn(
                'flex size-14 shrink-0 items-center justify-center rounded-2xl shadow-sm transition-colors duration-500',
                meta.iconTile,
              )}
            >
              <Icon className="size-7" aria-hidden="true" />
            </span>
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                Equipment condition
              </p>
              <h2
                className={cn(
                  'text-3xl font-bold leading-tight tracking-tight transition-colors duration-500 sm:text-4xl',
                  meta.accentText,
                )}
              >
                {meta.headline}
              </h2>
            </div>
          </div>

          <p className="max-w-2xl text-sm leading-relaxed text-slate-600">
            {explanation(condition, latestPrediction, latestWindow)}
          </p>

          {latestWindow?.scenario ? (
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-slate-600">
                <FlaskConical className="size-3.5 text-slate-400" aria-hidden="true" />
                Simulated input: <span className="font-semibold text-navy-900">{scenarioLabel(latestWindow.scenario)}</span>
              </span>
              <ArrowRight className="size-3.5 text-slate-400" aria-hidden="true" />
              <span
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-lg border bg-white px-2.5 py-1.5 font-semibold',
                  meta.ring,
                  meta.accentText,
                )}
              >
                <span className={cn('size-1.5 rounded-full', meta.dot)} />
                Edge decision: {meta.short}
              </span>
            </div>
          ) : null}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Metric
            label="Fault score"
            value={showScores ? (latestPrediction?.decision_score?.toFixed(3) ?? '-') : '-'}
            muted={!showScores}
          />
          <Metric
            label="Uncertainty"
            value={showScores ? (latestPrediction?.uncertainty_score?.toFixed(3) ?? '-') : '-'}
            muted={!showScores}
          />
          <Metric
            label="Vibration RMS"
            value={latestWindow?.rms != null ? latestWindow.rms.toFixed(4) : '-'}
            unit={latestWindow?.rms != null ? 'g' : undefined}
            muted={latestWindow?.rms == null}
          />
          <Metric
            label="On-device inference"
            value={showScores ? (latestPrediction?.latency_ms?.toFixed(2) ?? '-') : '-'}
            unit={showScores ? 'ms' : undefined}
            muted={!showScores}
          />
        </div>
      </div>
    </section>
  )
}

export { ConditionHero }
