import type { Prediction, PredictionDecision } from '@petrosense/shared-contracts'
import {
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { NORMAL_THRESHOLD, FAULT_THRESHOLD } from '@/components/dashboard/decision-meta'
import { parseApiDate } from '@/lib/utils'

const DOT_COLOR: Record<PredictionDecision, string> = {
  NORMAL: '#16a34a',
  FAULT: '#dc2626',
  UNCERTAIN: '#d97706',
  SENSOR_INVALID: '#7c3aed',
}

interface Point {
  t: string
  score: number | null
  invalid: number | null
  decision: PredictionDecision
}

function timeLabel(value: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  }).format(parseApiDate(value))
}

interface DotProps {
  cx?: number
  cy?: number
  payload?: Point
}

function ScoreDot({ cx, cy, payload }: DotProps) {
  if (cx === undefined || cy === undefined || !payload || payload.score === null) return null
  return (
    <circle
      cx={cx}
      cy={cy}
      r={3.2}
      fill={DOT_COLOR[payload.decision]}
      stroke="#ffffff"
      strokeWidth={1}
    />
  )
}

function InvalidDot({ cx, cy, payload }: DotProps) {
  if (cx === undefined || cy === undefined || !payload || payload.invalid === null) return null
  return <rect x={cx - 3.5} y={cy - 3.5} width={7} height={7} rx={1.5} fill="#7c3aed" />
}

function DecisionTimelineChart({
  predictions,
  height = 280,
}: {
  predictions: Prediction[]
  height?: number
}) {
  const data: Point[] = [...predictions]
    .sort((a, b) => parseApiDate(a.inferred_at).getTime() - parseApiDate(b.inferred_at).getTime())
    .map((prediction) => ({
      t: timeLabel(prediction.window_end ?? prediction.inferred_at),
      score: prediction.decision === 'SENSOR_INVALID' ? null : prediction.decision_score,
      invalid: prediction.decision === 'SENSOR_INVALID' ? 0.03 : null,
      decision: prediction.decision,
    }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 10, right: 16, bottom: 0, left: -8 }}>
        <ReferenceArea y1={0} y2={NORMAL_THRESHOLD} fill="#16a34a" fillOpacity={0.07} ifOverflow="hidden" />
        <ReferenceArea
          y1={NORMAL_THRESHOLD}
          y2={FAULT_THRESHOLD}
          fill="#d97706"
          fillOpacity={0.11}
          ifOverflow="hidden"
        />
        <ReferenceArea y1={FAULT_THRESHOLD} y2={1} fill="#dc2626" fillOpacity={0.07} ifOverflow="hidden" />
        <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
        <ReferenceLine
          y={FAULT_THRESHOLD}
          stroke="#dc2626"
          strokeDasharray="5 4"
          label={{ value: 'FAULT ZONE', position: 'insideTopLeft', fontSize: 10, fontWeight: 700, fill: '#b91c1c' }}
        />
        <ReferenceLine
          y={NORMAL_THRESHOLD}
          stroke="#16a34a"
          strokeDasharray="5 4"
          label={{ value: 'NORMAL ZONE', position: 'insideBottomLeft', fontSize: 10, fontWeight: 700, fill: '#15803d' }}
        />
        <ReferenceLine
          y={(NORMAL_THRESHOLD + FAULT_THRESHOLD) / 2}
          stroke="transparent"
          label={{ value: 'ABSTAIN · ENGINEERING REVIEW', position: 'insideLeft', fontSize: 10, fontWeight: 700, fill: '#b45309' }}
        />
        <XAxis
          dataKey="t"
          tick={{ fontSize: 10, fill: '#64748b' }}
          minTickGap={48}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 1]}
          ticks={[0, NORMAL_THRESHOLD, FAULT_THRESHOLD, 1]}
          tick={{ fontSize: 10, fill: '#64748b' }}
          width={40}
          axisLine={false}
          tickLine={false}
        />
        <Tooltip
          contentStyle={{ borderRadius: 8, border: '1px solid #e2e8f0', fontSize: 11 }}
          labelFormatter={(label) => `${label} UTC`}
          formatter={(value, name, item) => {
            const point = (item as { payload?: Point }).payload
            if (name === 'invalid') return ['inference suppressed', 'Sensor invalid']
            return [
              `${Number(value).toFixed(3)} · ${point?.decision ?? ''}`,
              'Fault score',
            ]
          }}
        />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#102a44"
          strokeWidth={1.75}
          dot={<ScoreDot />}
          activeDot={{ r: 5 }}
          connectNulls={false}
          isAnimationActive={false}
        />
        <Line
          dataKey="invalid"
          name="invalid"
          stroke="transparent"
          dot={<InvalidDot />}
          activeDot={false}
          isAnimationActive={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

export { DecisionTimelineChart }
