import { useEffect, useRef, useState } from 'react'

import { streamSse, type SseEvent } from '@/lib/api'

export type StreamStatus = 'disabled' | 'connecting' | 'connected' | 'reconnecting'

interface UseMonitoringStreamOptions {
  pumpId?: string
  sensorId?: string
  onEvent: (event: SseEvent) => void
}

export function useMonitoringStream({
  pumpId,
  sensorId,
  onEvent,
}: UseMonitoringStreamOptions) {
  const [status, setStatus] = useState<StreamStatus>(pumpId ? 'connecting' : 'disabled')
  const [lastEventAt, setLastEventAt] = useState<Date | null>(null)
  const handlerRef = useRef(onEvent)

  useEffect(() => {
    handlerRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    if (!pumpId) return

    let active = true
    let controller: AbortController | null = null
    let reconnectTimer: number | undefined

    const connect = async () => {
      if (!active) return
      setStatus((current) => (current === 'connected' ? 'reconnecting' : 'connecting'))
      controller = new AbortController()
      const params = new URLSearchParams({ pump_id: pumpId })
      if (sensorId) params.set('sensor_id', sensorId)

      try {
        await streamSse(
          `/monitoring/stream?${params.toString()}`,
          (event) => {
            if (!active) return
            setStatus('connected')
            setLastEventAt(new Date())
            handlerRef.current(event)
          },
          controller.signal,
        )
      } catch {
        if (!active || controller.signal.aborted) return
        setStatus('reconnecting')
      } finally {
        if (active) {
          reconnectTimer = window.setTimeout(connect, 3000)
        }
      }
    }

    void connect()

    return () => {
      active = false
      controller?.abort()
      if (reconnectTimer) window.clearTimeout(reconnectTimer)
    }
  }, [pumpId, sensorId])

  return { status: pumpId ? status : 'disabled', lastEventAt }
}
