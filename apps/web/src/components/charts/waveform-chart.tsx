import type { LiveWindow } from '@petrosense/shared-contracts'
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

interface WaveformChartProps {
  window: LiveWindow
  height?: number
}

function WaveformChart({ window, height = 240 }: WaveformChartProps) {
  const samples = window.waveform ?? []
  const data = samples.map((value, index) => ({
    time: index / window.sampling_rate_hz,
    value,
  }))

  if (data.length === 0) return null

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }}>
        <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="time"
          type="number"
          domain={['dataMin', 'dataMax']}
          tick={{ fontSize: 10, fill: '#64748b' }}
          tickFormatter={(value: number) => `${value.toFixed(3)}s`}
          minTickGap={40}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 10, fill: '#64748b' }}
          width={54}
          axisLine={false}
          tickLine={false}
          tickFormatter={(value: number) => value.toFixed(2)}
        />
        <Tooltip
          contentStyle={{
            borderRadius: 8,
            border: '1px solid #e2e8f0',
            fontSize: 11,
          }}
          formatter={(value) => [
            `${Number(value).toFixed(4)} ${window.units ?? ''}`.trim(),
            'Amplitude',
          ]}
          labelFormatter={(value) => `${Number(value).toFixed(3)} s`}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#2563EB"
          strokeWidth={1.4}
          dot={false}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

export { WaveformChart }
