import type { PredictionDecision } from '@petrosense/shared-contracts'
import { AlertTriangle, CheckCircle2, CircleHelp, ShieldOff, Activity } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

// Frozen selective-alert policy used by the edge decision stage (DecisionThresholds defaults).
export const NORMAL_THRESHOLD = 0.35
export const FAULT_THRESHOLD = 0.65

export type ConditionKey = PredictionDecision | 'NONE'

export interface ConditionMeta {
  headline: string
  short: string
  icon: LucideIcon
  /** Hero surface + accent classes. */
  surface: string
  ring: string
  accentText: string
  iconTile: string
  dot: string
}

export const CONDITION_META: Record<ConditionKey, ConditionMeta> = {
  NORMAL: {
    headline: 'Operating normally',
    short: 'Normal',
    icon: CheckCircle2,
    surface: 'bg-gradient-to-br from-emerald-50 via-white to-white',
    ring: 'border-emerald-200',
    accentText: 'text-emerald-700',
    iconTile: 'bg-emerald-600 text-white',
    dot: 'bg-emerald-500',
  },
  FAULT: {
    headline: 'Fault suspected - inspect',
    short: 'Fault',
    icon: AlertTriangle,
    surface: 'bg-gradient-to-br from-red-50 via-white to-white',
    ring: 'border-red-300',
    accentText: 'text-red-700',
    iconTile: 'bg-red-600 text-white',
    dot: 'bg-red-500',
  },
  UNCERTAIN: {
    headline: 'Uncertain - engineering review',
    short: 'Uncertain',
    icon: CircleHelp,
    surface: 'bg-gradient-to-br from-amber-50 via-white to-white',
    ring: 'border-amber-300',
    accentText: 'text-amber-700',
    iconTile: 'bg-amber-500 text-white',
    dot: 'bg-amber-500',
  },
  SENSOR_INVALID: {
    headline: 'Sensor invalid - not inferred',
    short: 'Sensor invalid',
    icon: ShieldOff,
    surface: 'bg-gradient-to-br from-violet-50 via-white to-white',
    ring: 'border-violet-300',
    accentText: 'text-violet-700',
    iconTile: 'bg-violet-600 text-white',
    dot: 'bg-violet-500',
  },
  NONE: {
    headline: 'Waiting for data',
    short: 'No data',
    icon: Activity,
    surface: 'bg-white',
    ring: 'border-slate-200',
    accentText: 'text-slate-600',
    iconTile: 'bg-slate-200 text-slate-600',
    dot: 'bg-slate-400',
  },
}

const SCENARIO_LABELS: Record<string, string> = {
  normal: 'Healthy operation',
  imbalance: 'Rotor imbalance',
  cavitation: 'Cavitation',
  custom_abnormal: 'Weak anomaly',
  incipient_fault: 'Incipient fault',
  sensor_disconnect: 'Sensor disconnect',
  corrupted_samples: 'Corrupted samples',
}

export function scenarioLabel(scenario: string | null | undefined): string {
  if (!scenario) return 'Unknown'
  return SCENARIO_LABELS[scenario] ?? scenario.replace(/_/g, ' ')
}

export function relativeTime(from: Date, now: number): string {
  const seconds = Math.max(0, Math.round((now - from.getTime()) / 1000))
  if (seconds < 5) return 'just now'
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min ago`
  const hours = Math.round(minutes / 60)
  return `${hours} h ago`
}
