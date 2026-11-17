import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleHelp,
  Pause,
  Play,
  PlugZap,
  ShieldOff,
  Zap,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { cn } from '@/lib/utils'
import { useAuth } from '@/providers/auth-provider'
import {
  fetchDemoControl,
  updateDemoControl,
  type DemoControlState,
  type DemoExpectedOutcome,
} from '@/services/demo-service'

const OUTCOME: Record<DemoExpectedOutcome, { icon: LucideIcon; active: string; text: string }> = {
  NORMAL: { icon: CheckCircle2, active: 'bg-emerald-500 text-white', text: 'text-emerald-300' },
  FAULT: { icon: AlertTriangle, active: 'bg-red-500 text-white', text: 'text-red-300' },
  UNCERTAIN: { icon: CircleHelp, active: 'bg-amber-500 text-white', text: 'text-amber-300' },
  SENSOR_INVALID: { icon: ShieldOff, active: 'bg-violet-500 text-white', text: 'text-violet-300' },
}

const SHORT_LABEL: Record<string, string> = {
  normal: 'Healthy',
  imbalance: 'Imbalance',
  cavitation: 'Cavitation',
  weak_anomaly: 'Weak anomaly',
  sensor_disconnect: 'Sensor fault',
}

const STORAGE_KEY = 'pumpverity.presenterDock.collapsed'

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem(STORAGE_KEY) === '1'
  } catch {
    return false
  }
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  const tag = target.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || target.isContentEditable
}

function PresenterDock() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const canControl = user?.role === 'ENGINEER' || user?.role === 'ADMINISTRATOR'
  const [collapsed, setCollapsed] = useState(readCollapsed)

  const control = useQuery({
    queryKey: ['demo-control'],
    queryFn: fetchDemoControl,
    refetchInterval: 2_000,
    retry: false,
    enabled: Boolean(user),
  })

  const mutation = useMutation({
    mutationFn: updateDemoControl,
    onSuccess: (state: DemoControlState) => {
      queryClient.setQueryData(['demo-control'], state)
      queryClient.invalidateQueries({ queryKey: ['monitoring-overview'] })
    },
  })

  const state = control.data
  const presets = useMemo(() => state?.presets ?? [], [state?.presets])
  const { mutate } = mutation

  const toggleCollapsed = useCallback(() => {
    setCollapsed((value) => {
      const next = !value
      try {
        window.localStorage.setItem(STORAGE_KEY, next ? '1' : '0')
      } catch {
        // Per-viewer convenience only.
      }
      return next
    })
  }, [])

  useEffect(() => {
    if (!state?.enabled || !canControl) return
    function onKey(event: KeyboardEvent) {
      if (event.ctrlKey || event.metaKey || event.altKey || isTypingTarget(event.target)) return
      const number = Number.parseInt(event.key, 10)
      if (number >= 1 && number <= presets.length) {
        event.preventDefault()
        mutate({ preset: presets[number - 1].code, paused: false })
      } else if (event.key === 'p' || event.key === 'P') {
        event.preventDefault()
        mutate({ paused: !state?.paused })
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [state?.enabled, state?.paused, canControl, presets, mutate])

  if (!state?.enabled || !canControl) return null

  const driverOnline = state.driver_online
  const streaming = driverOnline && !state.paused
  const switching = streaming && state.driver?.preset !== state.preset

  return (
    <>
      <div className="h-24" aria-hidden="true" />
      <div
        role="toolbar"
        aria-label="Presenter controls"
        className="fixed bottom-4 left-4 z-30 max-w-[calc(100vw-2rem)] lg:left-[calc(18rem+1.5rem)] lg:max-w-[calc(100vw-18rem-15rem)]"
      >
        <div className="flex items-center gap-2 overflow-x-auto rounded-2xl border border-white/10 bg-navy-950/95 p-1.5 text-white shadow-2xl shadow-navy-950/30 backdrop-blur">
          <button
            type="button"
            onClick={toggleCollapsed}
            className="flex shrink-0 items-center gap-2 rounded-xl px-2.5 py-2 text-left hover:bg-white/5"
            aria-expanded={!collapsed}
            title={collapsed ? 'Show presenter controls' : 'Hide presenter controls'}
          >
            <span className="relative flex size-2.5">
              {streaming ? (
                <span className="absolute inline-flex size-full animate-ping rounded-full bg-emerald-400 opacity-75" />
              ) : null}
              <span
                className={cn(
                  'relative inline-flex size-2.5 rounded-full',
                  streaming ? 'bg-emerald-400' : driverOnline ? 'bg-amber-400' : 'bg-red-500',
                )}
              />
            </span>
            <span className="leading-tight">
              <span className="block text-[10px] font-semibold uppercase tracking-[0.14em] text-slate-400">
                Simulated rig
              </span>
              <span className="block text-xs font-semibold">
                {!driverOnline
                  ? 'Edge stream offline'
                  : state.paused
                    ? 'Paused'
                    : switching
                      ? 'Switching…'
                      : `${state.driver?.windows_streamed ?? 0} windows`}
              </span>
            </span>
            {collapsed ? (
              <ChevronUp className="size-4 text-slate-400" aria-hidden="true" />
            ) : (
              <ChevronDown className="size-4 text-slate-400" aria-hidden="true" />
            )}
          </button>

          {!collapsed ? (
            <>
              <span className="h-8 w-px shrink-0 bg-white/10" aria-hidden="true" />
              <div className="flex shrink-0 items-center gap-1">
                <Zap className="mx-1 hidden size-3.5 text-slate-500 2xl:block" aria-hidden="true" />
                {presets.map((preset, index) => {
                  const meta = OUTCOME[preset.expected_outcome]
                  const Icon = meta.icon
                  const selected = preset.code === state.preset && !state.paused
                  return (
                    <button
                      key={preset.code}
                      type="button"
                      disabled={mutation.isPending}
                      aria-pressed={selected}
                      title={`${preset.label}: ${preset.description} (key ${index + 1})`}
                      onClick={() => mutate({ preset: preset.code, paused: false })}
                      className={cn(
                        'flex items-center gap-1.5 rounded-xl px-2.5 py-2 text-xs font-semibold transition 2xl:px-3',
                        selected ? meta.active : 'text-slate-200 hover:bg-white/10',
                      )}
                    >
                      <Icon className={cn('size-4', selected ? 'text-white' : meta.text)} aria-hidden="true" />
                      {SHORT_LABEL[preset.code] ?? preset.label}
                      <kbd
                        className={cn(
                          'ml-0.5 hidden rounded px-1 font-mono text-[10px] 2xl:inline',
                          selected ? 'bg-white/20 text-white' : 'bg-white/10 text-slate-400',
                        )}
                      >
                        {index + 1}
                      </kbd>
                    </button>
                  )
                })}
              </div>
              <span className="h-8 w-px shrink-0 bg-white/10" aria-hidden="true" />
              <button
                type="button"
                disabled={mutation.isPending || !driverOnline}
                onClick={() => mutate({ paused: !state.paused })}
                title="Pause or resume the stream (key P)"
                className="flex shrink-0 items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-semibold text-slate-200 hover:bg-white/10 disabled:opacity-40"
              >
                {state.paused ? <Play className="size-4" aria-hidden="true" /> : <Pause className="size-4" aria-hidden="true" />}
                {state.paused ? 'Resume' : 'Pause'}
              </button>
              {!driverOnline ? (
                <span className="flex shrink-0 items-center gap-1.5 pr-2 text-[11px] text-red-300">
                  <PlugZap className="size-3.5" aria-hidden="true" />
                  Run scripts/demo.ps1
                </span>
              ) : null}
            </>
          ) : null}
        </div>
      </div>
    </>
  )
}

export { PresenterDock }
