import type { LiveWindow, Prediction } from '@petrosense/shared-contracts'
import { Activity, BellRing, BrainCircuit, ChevronRight, ShieldCheck } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

import { CONDITION_META } from '@/components/dashboard/decision-meta'
import { cn } from '@/lib/utils'

type StageTone = 'ok' | 'skipped' | 'warn' | 'fault' | 'sensor' | 'idle'

const TONE: Record<StageTone, string> = {
  ok: 'border-slate-200 bg-white',
  skipped: 'border-dashed border-slate-300 bg-slate-50 opacity-70',
  warn: 'border-amber-300 bg-amber-50/70',
  fault: 'border-red-300 bg-red-50/70',
  sensor: 'border-violet-300 bg-violet-50/70',
  idle: 'border-slate-200 bg-slate-50/60',
}

interface StageProps {
  step: string
  title: string
  caption: string
  icon: LucideIcon
  tone: StageTone
  children: ReactNode
}

function Stage({ step, title, caption, icon: Icon, tone, children }: StageProps) {
  return (
    <div className={cn('flex min-w-0 flex-1 flex-col gap-2 rounded-xl border p-3.5 transition-colors duration-500', TONE[tone])}>
      <div className="flex items-center gap-2.5">
        <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-navy-900 text-white">
          <Icon className="size-4" aria-hidden="true" />
        </span>
        <div className="min-w-0 leading-tight">
          <p className="text-xs font-bold tracking-wide text-navy-900">
            <span className="mr-1 text-slate-400">{step}</span>
            {title}
          </p>
          <p className="truncate text-[10px] text-slate-500">{caption}</p>
        </div>
      </div>
      <div className="text-xs leading-relaxed text-slate-700">{children}</div>
    </div>
  )
}

function Arrow() {
  return (
    <div className="hidden shrink-0 items-center text-slate-300 lg:flex" aria-hidden="true">
      <ChevronRight className="size-5" />
    </div>
  )
}

interface DecisionPipelineCardProps {
  latestWindow: LiveWindow | null | undefined
  latestPrediction: Prediction | null | undefined
}

function DecisionPipelineCard({ latestWindow, latestPrediction }: DecisionPipelineCardProps) {
  const invalid = latestWindow?.quality_status === 'SENSOR_INVALID'
  const prediction = latestPrediction ?? null
  const decision = invalid ? 'SENSOR_INVALID' : (prediction?.decision ?? null)
  const actTone: StageTone =
    decision === 'FAULT'
      ? 'fault'
      : decision === 'UNCERTAIN'
        ? 'warn'
        : decision === 'SENSOR_INVALID'
          ? 'sensor'
          : decision === 'NORMAL'
            ? 'ok'
            : 'idle'

  return (
    <div className="flex flex-col gap-2 lg:flex-row lg:items-stretch">
      <Stage
        step="01"
        title="SENSE"
        caption="ADXL355-class accelerometer · 2,048 Hz"
        icon={Activity}
        tone={latestWindow ? 'ok' : 'idle'}
      >
        {latestWindow ? (
          <>
            1-second window ·{' '}
            <span className="font-semibold">
              RMS {latestWindow.rms !== null ? `${latestWindow.rms.toFixed(4)} g` : 'n/a'}
            </span>
          </>
        ) : (
          'Waiting for the first window'
        )}
      </Stage>
      <Arrow />
      <Stage
        step="02"
        title="QUALIFY SIGNAL"
        caption="Flat-line, gaps, clipping checks"
        icon={ShieldCheck}
        tone={invalid ? 'sensor' : latestWindow ? 'ok' : 'idle'}
      >
        {invalid ? (
          <span className="font-semibold text-violet-700">Rejected - model will not run</span>
        ) : latestWindow ? (
          <span className="font-semibold text-emerald-700">Signal valid</span>
        ) : (
          '-'
        )}
      </Stage>
      <Arrow />
      <Stage
        step="03"
        title="INTERPRET"
        caption={prediction?.model ? `${prediction.model.name} v${prediction.model.version}` : 'On-device model'}
        icon={BrainCircuit}
        tone={invalid ? 'skipped' : prediction ? 'ok' : 'idle'}
      >
        {invalid ? (
          'Skipped'
        ) : prediction ? (
          <>
            Fault score <span className="font-semibold">{prediction.decision_score?.toFixed(3) ?? '-'}</span> in{' '}
            <span className="font-semibold">{prediction.latency_ms?.toFixed(2) ?? '-'} ms</span>
          </>
        ) : (
          '-'
        )}
      </Stage>
      <Arrow />
      <Stage
        step="04"
        title="DECIDE & ACT"
        caption="Frozen selective-alert policy"
        icon={BellRing}
        tone={actTone}
      >
        {decision ? (
          <span className={cn('font-semibold', CONDITION_META[decision].accentText)}>
            {decision === 'NORMAL'
              ? 'Normal - no alert'
              : decision === 'FAULT'
                ? 'Fault - alert to engineer'
                : decision === 'UNCERTAIN'
                  ? 'Abstain - review queue'
                  : 'Sensor alert - not inferred'}
          </span>
        ) : (
          'Waiting for a decision'
        )}
      </Stage>
    </div>
  )
}

export { DecisionPipelineCard }
