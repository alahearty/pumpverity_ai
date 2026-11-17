import type { Alert, AlertCategory, WindowPoint } from '@petrosense/shared-contracts'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { parseApiDate } from '@/lib/utils'

interface RmsTrendChartProps {
  windows: WindowPoint[]
  alerts?: Alert[]
  height?: number
}

const EVENT_META: Record<
  AlertCategory,
  { label: string; short: string; color: string }
> = {
  FAULT: { label: 'Fault alert', short: 'Fault', color: '#dc2626' },
  UNCERTAIN: { label: 'Uncertain alert', short: 'Uncertain', color: '#d97706' },
  SENSOR_INVALID: {
    label: 'Sensor-invalid alert',
    short: 'Sensor',
    color: '#7c3aed',
  },
}

function formatWindowTime(value: string): string {
  const date = parseApiDate(value)
  if (Number.isNaN(date.getTime())) return 'Unknown'
  return new Intl.DateTimeFormat('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
    timeZone: 'UTC',
  }).format(date)
}

function RmsTrendChart({ windows, alerts = [], height = 240 }: RmsTrendChartProps) {
  const windowsById = new Map(windows.map((window) => [window.window_id, window]))
  const data = windows.map((window) => ({
    label: formatWindowTime(window.window_start),
    rms: window.quality_status === 'VALID' ? window.rms : null,
    quality: window.quality_status,
    index: window.window_index,
  }))
  const eventLines = alerts.flatMap((alert) => {
    if (!alert.signal_window_id) return []
    const window = windowsById.get(alert.signal_window_id)
    if (!window) return []
    return [
      {
        id: alert.id,
        label: formatWindowTime(window.window_start),
        category: alert.category,
      },
    ]
  })
  const eventCounts = eventLines.reduce<Partial<Record<AlertCategory, number>>>(
    (counts, event) => {
      counts[event.category] = (counts[event.category] ?? 0) + 1
      return counts
    },
    {},
  )

  if (data.length === 0) return null

  return (
    <div className="space-y-2">
      {eventLines.length > 0 ? (
        <div className="flex flex-wrap items-center gap-3 text-[10px] text-slate-500">
          {Object.entries(eventCounts).map(([category, count]) => {
            const meta = EVENT_META[category as AlertCategory]
            return (
              <span key={category} className="inline-flex items-center gap-1.5">
                <span
                  className="size-2 rounded-full"
                  style={{ backgroundColor: meta.color }}
                />
                {meta.label} ({count})
              </span>
            )
          })}
          <span className="text-slate-400">Dashed markers align to the source window.</span>
        </div>
      ) : null}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
          <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 10, fill: '#64748b' }}
            minTickGap={40}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tick={{ fontSize: 10, fill: '#64748b' }}
            width={58}
            axisLine={false}
            tickLine={false}
            tickFormatter={(value: number) => value.toFixed(3)}
          />
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #e2e8f0',
              fontSize: 11,
            }}
            formatter={(value) => {
              if (value === null || value === undefined) {
                return ['Sensor invalid', 'RMS']
              }
              return [`${Number(value).toFixed(4)} g`, 'RMS']
            }}
          />
          {eventLines.map((event) => {
            const meta = EVENT_META[event.category]
            return (
              <ReferenceLine
                key={event.id}
                x={event.label}
                stroke={meta.color}
                strokeDasharray="4 3"
                ifOverflow="extendDomain"
                label={
                  eventLines.length <= 8
                    ? {
                        value: meta.short,
                        position: 'insideTopLeft',
                        fontSize: 9,
                        fill: meta.color,
                      }
                    : undefined
                }
              />
            )
          })}
          <Line
            type="monotone"
            dataKey="rms"
            stroke="#00A6A6"
            strokeWidth={2}
            dot={{ r: 2.5, fill: '#00A6A6' }}
            connectNulls={false}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export { RmsTrendChart }
