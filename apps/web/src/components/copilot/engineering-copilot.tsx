import { useQuery, useQueryClient } from '@tanstack/react-query'
import type {
  CopilotAction,
  CopilotApproval,
  CopilotPageContext,
  CopilotStatus,
  CopilotToolRun,
} from '@petrosense/shared-contracts'
import {
  AlertTriangle,
  Bot,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Maximize2,
  Minus,
  Send,
  Square,
  Trash2,
  Wrench,
  X,
} from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'

import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { useCopilot } from '@/providers/copilot-context-provider'
import {
  approveCopilotAction,
  fetchCopilotStatus,
  rejectCopilotAction,
  runCopilotTool,
  sendCopilotMessage,
} from '@/services/copilot-service'
import { cn, formatDateTime } from '@/lib/utils'

interface ChatEntry {
  id: string
  role: 'USER' | 'ASSISTANT' | 'SYSTEM'
  content: string
  createdAt: string
  actions: CopilotAction[]
  suggestions: string[]
  toolRuns: CopilotToolRun[]
  approval: CopilotApproval | null
}

const TOOL_LABELS: Record<string, string> = {
  pumpverity_get_monitoring_overview: 'Monitoring overview',
  pumpverity_get_pump_status: 'Pump status',
  pumpverity_get_sensor_health: 'Sensor diagnostics',
  pumpverity_get_latest_prediction: 'Latest prediction',
  pumpverity_get_fault_history: 'Fault history',
  pumpverity_get_vibration_summary: 'Vibration summary',
  pumpverity_get_model_evaluation: 'Model evaluation',
  pumpverity_get_alert_details: 'Alert evidence',
  pumpverity_get_edge_connectivity: 'Edge connectivity',
  pumpverity_acknowledge_alert: 'Acknowledge alert',
  pumpverity_mark_alert_reviewed: 'Mark alert reviewed',
  pumpverity_add_engineering_note: 'Add engineering note',
  pumpverity_generate_monitoring_report: 'Generate monitoring report',
}

const ACTION_LABELS: Partial<Record<CopilotAction['type'], string>> = {
  NAVIGATE_TO_SCREEN: 'Open screen',
  SELECT_PUMP: 'Select pump',
  OPEN_ALERT_DETAILS: 'Open alert details',
  HIGHLIGHT_SENSOR: 'Highlight sensor',
  OPEN_HISTORICAL_TRENDS: 'Open historical trends',
  SET_MONITORING_TIME_RANGE: 'Set time range',
  OPEN_REPORT: 'Open report',
}

function shortId(value: string | null | undefined): string {
  return value ? value.slice(0, 8) : 'None'
}

function statusLabel(status: CopilotStatus | undefined, isError: boolean): string {
  if (isError) return 'Copilot offline'
  if (!status) return 'Checking Copilot'
  if (!status.enabled) return 'Copilot disabled'
  if (!status.mcpAvailable) return 'MCP unavailable'
  return status.provider === 'deterministic' ? 'Ready · local grounded mode' : 'Ready · LLM planner'
}

function statusTone(
  status: CopilotStatus | undefined,
  isError: boolean,
): 'success' | 'fault' | 'uncertain' | 'neutral' {
  if (isError || (status && (!status.enabled || !status.mcpAvailable))) {
    return 'fault'
  }
  if (!status) return 'uncertain'
  return 'success'
}

function metric(value: unknown, suffix = ''): string {
  return typeof value === 'number' ? `${value.toFixed(4)}${suffix}` : 'Not available'
}

function ToolResultCard({ run }: { run: CopilotToolRun }) {
  const result = run.result
  if (run.status === 'FAILED') {
    return (
      <p className="rounded-lg border border-red-200 bg-red-50 p-2.5 text-[11px] leading-relaxed text-red-700">
        {run.error ?? 'The tool did not return a result.'}
      </p>
    )
  }
  if (!result) return null
  if (run.toolName === 'pumpverity_get_sensor_health') {
    const sensors = Array.isArray(result.sensors)
      ? (result.sensors as Array<Record<string, unknown>>)
      : []
    return (
      <div className="space-y-1.5">
        {sensors.map((sensor) => (
          <div
            key={String(sensor.sensor_id)}
            className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 text-[11px]"
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold text-navy-900">
                {String(sensor.sensor_code)}
              </span>
              <Badge variant="neutral">{String(sensor.sampling_status)}</Badge>
            </div>
            <p className="mt-1 text-slate-500">
              Latest RMS {metric(sensor.latest_rms_g, ' g')} · invalid{' '}
              {String(sensor.invalid_windows)} · gaps{' '}
              {String(sensor.missing_window_gaps)} ·{' '}
              {String(sensor.provenance ?? 'provenance unknown')}
            </p>
          </div>
        ))}
      </div>
    )
  }
  if (
    run.toolName === 'pumpverity_get_latest_prediction' ||
    run.toolName === 'pumpverity_get_alert_details'
  ) {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 text-[11px] text-slate-600">
        <div className="flex flex-wrap gap-1.5">
          <Badge variant="outline">
            {String(result.decision ?? result.category ?? 'Unknown')}
          </Badge>
          <Badge variant="neutral">
            Quality {String(result.data_quality ?? 'unknown')}
          </Badge>
        </div>
        <p className="mt-1.5">
          Uncertainty{' '}
          {metric(
            result.uncertainty_score ??
              (result.prediction as Record<string, unknown> | undefined)
                ?.uncertainty_score,
          )}{' '}
          · provenance {String(result.provenance ?? 'unknown')}
        </p>
      </div>
    )
  }
  if (run.toolName === 'pumpverity_get_pump_status') {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 text-[11px] text-slate-600">
        <p className="font-semibold text-navy-900">
          {String(result.pump_code)} · {String(result.pump_status)}
        </p>
        <p className="mt-1">
          Condition {String(result.equipment_condition ?? 'not inferred')} · quality{' '}
          {String(result.data_quality ?? 'unknown')} · mode{' '}
          {String(result.data_mode)}
        </p>
      </div>
    )
  }
  if (run.toolName === 'pumpverity_get_vibration_summary') {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 text-[11px] text-slate-600">
        <p>
          Latest RMS {metric(result.latest_rms_g, ' g')} · mean{' '}
          {metric(result.mean_rms_g, ' g')} · mark range{' '}
          {metric(result.min_rms_g)}–{metric(result.max_rms_g, ' g')}
        </p>
        <p className="mt-1">
          {String(result.valid_window_count)} valid /{' '}
          {String(result.invalid_window_count)} invalid ·{' '}
          {String(result.provenance ?? 'provenance unknown')}
        </p>
      </div>
    )
  }
  if (run.toolName === 'pumpverity_get_fault_history') {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 text-[11px] text-slate-600">
        <p className="font-semibold text-navy-900">
          {String(result.total_events)} alert-backed event(s)
        </p>
        <p className="mt-1">{String(result.message)}</p>
      </div>
    )
  }
  if (run.toolName === 'pumpverity_get_model_evaluation') {
    return (
      <div className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 text-[11px] text-slate-600">
        <p className="font-semibold text-navy-900">
          {String(result.name ?? 'No active model')}{' '}
          {result.version ? `v${String(result.version)}` : ''}
        </p>
        <p className="mt-1">
          {result.evaluation
            ? `${String((result.evaluation as Record<string, unknown>).provenance)} evaluation · macro-F1 ${metric((result.evaluation as Record<string, unknown>).macro_f1)}`
            : String(result.message)}
        </p>
      </div>
    )
  }
  if (
    run.toolName === 'pumpverity_acknowledge_alert' ||
    run.toolName === 'pumpverity_mark_alert_reviewed' ||
    run.toolName === 'pumpverity_add_engineering_note' ||
    run.toolName === 'pumpverity_generate_monitoring_report'
  ) {
    return (
      <div className="rounded-lg border border-green-200 bg-green-50 p-2.5 text-[11px] text-green-800">
        <p className="font-semibold">{String(result.message ?? 'Action completed')}</p>
        <p className="mt-1">Status {String(result.status ?? 'unknown')}</p>
      </div>
    )
  }
  return (
    <details className="rounded-lg border border-slate-200 bg-slate-50/70 p-2.5 text-[10px] text-slate-500">
      <summary className="cursor-pointer font-medium text-slate-600">
        Structured result
      </summary>
      <pre className="mt-1 max-h-40 overflow-auto whitespace-pre-wrap break-words">
        {JSON.stringify(result, null, 2)}
      </pre>
    </details>
  )
}

function ToolRunList({ runs }: { runs: CopilotToolRun[] }) {
  if (runs.length === 0) return null
  return (
    <div className="space-y-2">
      {runs.map((run) => (
        <div key={run.id} className="rounded-lg border border-slate-200 bg-white p-2.5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-1.5">
              {run.status === 'EXECUTED' ? (
                <CheckCircle2 className="size-3.5 text-success" aria-hidden="true" />
              ) : run.status === 'PENDING_APPROVAL' ? (
                <Wrench className="size-3.5 text-uncertain" aria-hidden="true" />
              ) : run.status === 'FAILED' ? (
                <AlertTriangle className="size-3.5 text-fault" aria-hidden="true" />
              ) : (
                <Loader2 className="size-3.5 animate-spin text-slate-400" aria-hidden="true" />
              )}
              <span className="text-[11px] font-semibold text-navy-900">
                {TOOL_LABELS[run.toolName] ?? run.toolName}
              </span>
            </div>
            <Badge variant={run.status === 'FAILED' ? 'fault' : 'outline'}>
              {run.status.replaceAll('_', ' ').toLowerCase()}
            </Badge>
          </div>
          {run.arguments && Object.keys(run.arguments).length > 0 ? (
            <p className="mt-1 truncate text-[10px] text-slate-400">
              Args: {JSON.stringify(run.arguments)}
            </p>
          ) : null}
          <div className="mt-2">
            <ToolResultCard run={run} />
          </div>
        </div>
      ))}
    </div>
  )
}

function ContextChips({ context }: { context: CopilotPageContext }) {
  return (
    <div className="flex flex-wrap gap-1.5 text-[10px]">
      <Badge variant="navy">{context.screenName}</Badge>
      <Badge variant="outline">
        Pump {context.selectedPumpId ? shortId(context.selectedPumpId) : 'not selected'}
      </Badge>
      {context.selectedAlertId ? (
        <Badge variant="uncertain">Alert {shortId(context.selectedAlertId)}</Badge>
      ) : null}
      <Badge variant="outline">{context.monitoringMode}</Badge>
      <Badge variant="outline">{context.connectivityStatus}</Badge>
    </div>
  )
}

function ApprovalCard({
  approval,
  busy,
  onApprove,
  onReject,
}: {
  approval: CopilotApproval
  busy: boolean
  onApprove: () => void
  onReject: () => void
}) {
  return (
    <div className="rounded-xl border border-amber-300 bg-amber-50/90 p-3">
      <div className="flex items-center gap-2">
        <AlertTriangle className="size-4 text-amber-700" aria-hidden="true" />
        <p className="text-xs font-semibold text-amber-950">Confirmation required</p>
      </div>
      <p className="mt-1 text-[11px] leading-relaxed text-amber-900">
        {approval.summary}. Review the exact arguments before changing an operational record.
      </p>
      <pre className="mt-2 max-h-36 overflow-auto rounded-lg border border-amber-200 bg-white/70 p-2 text-[10px] text-amber-950">
        {JSON.stringify(approval.arguments, null, 2)}
      </pre>
      <div className="mt-2 flex gap-2">
        <Button size="sm" onClick={onApprove} disabled={busy}>
          {busy ? <Loader2 className="size-3.5 animate-spin" /> : null}
          Confirm and execute
        </Button>
        <Button size="sm" variant="secondary" onClick={onReject} disabled={busy}>
          Reject
        </Button>
      </div>
    </div>
  )
}

function EngineeringCopilot() {
  const { context, dispatchAction, externalRequest, clearExternalRequest } = useCopilot()
  const queryClient = useQueryClient()
  const statusQuery = useQuery({
    queryKey: ['copilot-status'],
    queryFn: ({ signal }) => fetchCopilotStatus(signal),
    refetchInterval: 30_000,
    staleTime: 15_000,
    retry: 1,
  })
  const [open, setOpen] = useState(false)
  const [minimized, setMinimized] = useState(false)
  const [entries, setEntries] = useState<ChatEntry[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [retryText, setRetryText] = useState<string | null>(null)
  const [pendingApproval, setPendingApproval] = useState<CopilotApproval | null>(null)
  const [approvalBusy, setApprovalBusy] = useState(false)
  const abortRef = useRef<AbortController | null>(null)
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const inputRef = useRef<HTMLTextAreaElement | null>(null)

  const status = statusQuery.data
  const tone = statusTone(status, statusQuery.isError)
  const disabled = status?.enabled === false

  const appendAssistant = useCallback(
    (
      content: string,
      options: {
        actions?: CopilotAction[]
        suggestions?: string[]
        toolRuns?: CopilotToolRun[]
        approval?: CopilotApproval | null
      } = {},
    ) => {
      const entry: ChatEntry = {
        id: `assistant-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        role: 'ASSISTANT',
        content,
        createdAt: new Date().toISOString(),
        actions: options.actions ?? [],
        suggestions: options.suggestions ?? [],
        toolRuns: options.toolRuns ?? [],
        approval: options.approval ?? null,
      }
      setEntries((current) => [...current, entry])
    },
    [],
  )

  const sendMessage = useCallback(
    async (text: string) => {
      const message = text.trim()
      if (!message || sending || disabled) return
      setOpen(true)
      setMinimized(false)
      setError(null)
      setRetryText(null)
      setInput('')
      setSending(true)
      const userEntry: ChatEntry = {
        id: `user-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        role: 'USER',
        content: message,
        createdAt: new Date().toISOString(),
        actions: [],
        suggestions: [],
        toolRuns: [],
        approval: null,
      }
      setEntries((current) => [...current, userEntry])
      const controller = new AbortController()
      abortRef.current = controller
      try {
        const response = await sendCopilotMessage(
          { message, conversationId, context },
          controller.signal,
        )
        setConversationId(response.conversationId)
        appendAssistant(response.assistantMessage.content, {
          actions: response.assistantMessage.actions,
          suggestions: response.assistantMessage.suggestedQuestions,
          toolRuns: response.toolRuns,
          approval: response.approval,
        })
        setPendingApproval(response.approval)
      } catch (caught) {
        if ((caught as Error).name === 'AbortError') {
          appendAssistant('The Copilot request was cancelled. No tool success is claimed.')
        } else {
          const messageText =
            caught instanceof Error ? caught.message : 'Copilot request failed.'
          setError(messageText)
          setRetryText(message)
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null
        setSending(false)
      }
    },
    [appendAssistant, context, conversationId, disabled, sending],
  )

  const executeDirectTool = useCallback(
    async (toolName: string, args: Record<string, unknown>) => {
      if (sending || disabled) return
      setOpen(true)
      setMinimized(false)
      setError(null)
      const requestId = `tool-${Date.now()}`
      setEntries((current) => [
        ...current,
        {
          id: `${requestId}-request`,
          role: 'SYSTEM',
          content: `Explicit tool request: ${TOOL_LABELS[toolName] ?? toolName}`,
          createdAt: new Date().toISOString(),
          actions: [],
          suggestions: [],
          toolRuns: [],
          approval: null,
        },
      ])
      setSending(true)
      const controller = new AbortController()
      abortRef.current = controller
      try {
        const response = await runCopilotTool(
          toolName,
          { arguments: args, context, conversationId },
          controller.signal,
        )
        if (response.conversationId) setConversationId(response.conversationId)
        appendAssistant('Authorised read-only MCP tool result.', {
          toolRuns: [response.toolRun],
          actions: response.actions,
        })
        for (const action of response.actions) dispatchAction(action)
        queryClient.invalidateQueries({ queryKey: ['sensor-health'] })
        queryClient.invalidateQueries({ queryKey: ['monitoring-live'] })
      } catch (caught) {
        if ((caught as Error).name !== 'AbortError') {
          setError(caught instanceof Error ? caught.message : 'Tool invocation failed.')
        }
      } finally {
        if (abortRef.current === controller) abortRef.current = null
        setSending(false)
      }
    },
    [appendAssistant, context, conversationId, disabled, dispatchAction, queryClient, sending],
  )

  useEffect(() => {
    if (!externalRequest) return
    if (externalRequest.kind === 'prompt' && externalRequest.prompt) {
      setOpen(true)
      setInput(externalRequest.prompt)
    }
    if (
      externalRequest.kind === 'tool' &&
      externalRequest.toolName
    ) {
      void executeDirectTool(
        externalRequest.toolName,
        externalRequest.arguments ?? {},
      )
    }
    clearExternalRequest()
  }, [clearExternalRequest, executeDirectTool, externalRequest])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [entries, pendingApproval])

  useEffect(() => {
    if (open && !minimized) inputRef.current?.focus()
  }, [open, minimized])

  const approve = useCallback(async () => {
    if (!pendingApproval || approvalBusy) return
    setApprovalBusy(true)
    setError(null)
    try {
      const resolvedId = pendingApproval.id
      const response = await approveCopilotAction(resolvedId)
      setPendingApproval(null)
      setEntries((current) =>
        current.map((entry) =>
          entry.approval?.id === resolvedId ? { ...entry, approval: null } : entry,
        ),
      )
      appendAssistant(response.message, {
        actions: response.actions,
        toolRuns: [response.toolRun],
      })
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
      queryClient.invalidateQueries({ queryKey: ['alert'] })
      queryClient.invalidateQueries({ queryKey: ['monitoring-live'] })
      queryClient.invalidateQueries({ queryKey: ['monitoring-overview'] })
      queryClient.invalidateQueries({ queryKey: ['predictions'] })
      queryClient.invalidateQueries({ queryKey: ['copilot-status'] })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Approval failed.')
      queryClient.invalidateQueries({ queryKey: ['alert'] })
    } finally {
      setApprovalBusy(false)
    }
  }, [appendAssistant, approvalBusy, pendingApproval, queryClient])

  const reject = useCallback(async () => {
    if (!pendingApproval || approvalBusy) return
    setApprovalBusy(true)
    try {
      const resolvedId = pendingApproval.id
      const response = await rejectCopilotAction(resolvedId)
      setPendingApproval(null)
      setEntries((current) =>
        current.map((entry) =>
          entry.approval?.id === resolvedId ? { ...entry, approval: null } : entry,
        ),
      )
      appendAssistant(response.message, { toolRuns: [response.toolRun] })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Rejection failed.')
    } finally {
      setApprovalBusy(false)
    }
  }, [appendAssistant, approvalBusy, pendingApproval])

  function clearConversation() {
    abortRef.current?.abort()
    setEntries([])
    setConversationId(null)
    setPendingApproval(null)
    setError(null)
    setRetryText(null)
    setInput('')
  }

  function cancelRequest() {
    abortRef.current?.abort()
  }

  function openPrompt(prompt: string) {
    setOpen(true)
    setMinimized(false)
    setInput(prompt)
  }

  const quickActions = [
    context.selectedPumpId
      ? { label: 'Pump status', tool: 'pumpverity_get_pump_status' }
      : null,
    context.selectedPumpId
      ? { label: 'Sensor diagnostic', tool: 'pumpverity_get_sensor_health' }
      : null,
    context.selectedPumpId
      ? { label: 'Latest prediction', tool: 'pumpverity_get_latest_prediction' }
      : null,
    context.selectedPumpId
      ? { label: 'Fault history', tool: 'pumpverity_get_fault_history' }
      : null,
  ].filter((item): item is { label: string; tool: string } => Boolean(item))

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-40 flex items-center gap-2 rounded-full bg-navy-900 px-3.5 py-3 text-xs font-semibold text-white shadow-xl transition hover:bg-navy-800 sm:px-4"
        aria-label="Open Engineering Copilot"
      >
        <Bot className="size-4" aria-hidden="true" />
        Engineering Copilot
      </button>
    )
  }

  return (
    <section
      role="dialog"
      aria-label="PUMPVERITY AI Engineering Copilot"
      className={cn(
        'fixed bottom-3 right-3 z-40 flex w-[min(430px,calc(100vw-1.5rem))] flex-col overflow-hidden rounded-2xl border border-slate-300 bg-white shadow-2xl',
        minimized
          ? 'h-auto'
          : 'h-[min(680px,calc(100vh-1.5rem))] sm:bottom-5 sm:right-5',
      )}
    >
      <header className="bg-gradient-to-r from-navy-950 to-navy-800 px-4 py-3 text-white">
        <div className="flex items-start justify-between gap-2">
          <div className="flex min-w-0 items-start gap-2.5">
            <div className="rounded-lg bg-white/10 p-1.5">
              <Bot className="size-4" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">
                PUMPVERITY AI Engineering Copilot
              </p>
              <p className="mt-0.5 flex items-center gap-1.5 truncate text-[10px] text-slate-300">
                <span
                  className={cn(
                    'size-1.5 rounded-full',
                    tone === 'success'
                      ? 'bg-success'
                      : tone === 'fault'
                        ? 'bg-fault'
                        : 'bg-uncertain',
                  )}
                />
                {statusLabel(status, statusQuery.isError)}
                <span className="text-slate-500">·</span>
                {context.screenName}
                <span className="text-slate-500">·</span>
                {context.selectedPumpId
                  ? `Pump ${shortId(context.selectedPumpId)}`
                  : 'No pump selected'}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <button
              type="button"
              onClick={() => setMinimized((value) => !value)}
              className="rounded-md p-1.5 text-slate-300 hover:bg-white/10 hover:text-white"
              aria-label={minimized ? 'Maximise Copilot' : 'Minimise Copilot'}
            >
              {minimized ? (
                <Maximize2 className="size-3.5" />
              ) : (
                <Minus className="size-3.5" />
              )}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="rounded-md p-1.5 text-slate-300 hover:bg-white/10 hover:text-white"
              aria-label="Close Copilot"
            >
              <X className="size-3.5" />
            </button>
          </div>
        </div>
        {!minimized ? (
          <div className="mt-2.5 flex flex-wrap gap-1.5">
            <SpanChip label={context.monitoringMode} />
            <SpanChip label={context.connectivityStatus} />
            {context.selectedAlertId ? (
              <SpanChip label={`Alert ${shortId(context.selectedAlertId)}`} />
            ) : null}
          </div>
        ) : null}
      </header>

      {minimized ? (
        <div className="flex items-center justify-between gap-2 bg-slate-50 px-4 py-2 text-[11px] text-slate-500">
          <span>Minimised. Monitoring remains visible.</span>
          <Button size="sm" variant="secondary" onClick={() => setMinimized(false)}>
            Expand
          </Button>
        </div>
      ) : (
        <>
          <div className="border-b border-slate-200 bg-slate-50 px-3 py-2">
            {status && (!status.mcpAvailable || !status.enabled) ? (
              <p className="mb-2 flex items-start gap-1.5 rounded-lg border border-amber-200 bg-amber-50 p-2 text-[10px] leading-relaxed text-amber-900">
                <AlertTriangle className="mt-0.5 size-3.5 shrink-0" aria-hidden="true" />
                {status.message}
              </p>
            ) : null}
            <ContextChips context={context} />
            <div className="mt-2 flex flex-wrap gap-1.5">
              {quickActions.map((action) => (
                <button
                  key={action.tool}
                  type="button"
                  onClick={() => void executeDirectTool(action.tool, {})}
                  className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-medium text-slate-600 hover:border-industrial-300 hover:text-industrial-700"
                >
                  {action.label}
                </button>
              ))}
              {context.selectedAlertId ? (
                <button
                  type="button"
                  onClick={() => openPrompt('Why was this event marked uncertain?')}
                  className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[10px] font-medium text-slate-600 hover:border-industrial-300 hover:text-industrial-700"
                >
                  Why uncertain?
                </button>
              ) : null}
            </div>
          </div>

          <div
            ref={scrollRef}
            aria-live="polite"
            aria-relevant="additions text"
            className="flex-1 space-y-3 overflow-y-auto bg-canvas/50 p-3"
          >
            {entries.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-white/70 p-4">
                <p className="text-sm font-semibold text-navy-900">
                  Ask about the selected monitoring context
                </p>
                <p className="mt-1 text-xs leading-relaxed text-slate-500">
                  I can explain pump status, predictions, uncertainty, sensor validity, alerts,
                  model evidence and connectivity. Monitoring data is retrieved through
                  authorised MCP tools; missing data is reported as unavailable.
                </p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {[
                    'What is happening with this pump?',
                    'Show sensor health',
                    'Explain the latest prediction',
                    'What data is simulated?',
                  ].map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => openPrompt(prompt)}
                      className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-left text-[10px] text-slate-600 hover:border-industrial-300"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : null}
            {entries.map((entry) => (
              <div
                key={entry.id}
                className={cn(
                  'flex',
                  entry.role === 'USER' ? 'justify-end' : 'justify-start',
                )}
              >
                <div
                  className={cn(
                    'max-w-[92%] space-y-2 rounded-xl px-3 py-2.5 text-xs leading-relaxed shadow-sm',
                    entry.role === 'USER'
                      ? 'bg-industrial-600 text-white'
                      : entry.role === 'SYSTEM'
                        ? 'border border-slate-200 bg-slate-100 text-slate-600'
                        : 'border border-slate-200 bg-white text-slate-700',
                  )}
                >
                  {entry.role !== 'USER' ? (
                    <p className="text-[10px] font-semibold uppercase tracking-[0.12em] text-slate-400">
                      {entry.role === 'SYSTEM' ? 'Tool request' : 'Copilot'}
                    </p>
                  ) : null}
                  <p className="whitespace-pre-line">{entry.content}</p>
                  <ToolRunList runs={entry.toolRuns} />
                  {entry.approval ? (
                    <ApprovalCard
                      approval={entry.approval}
                      busy={approvalBusy}
                      onApprove={() => void approve()}
                      onReject={() => void reject()}
                    />
                  ) : null}
                  {entry.actions.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {entry.actions
                        .filter((action) => action.type !== 'SHOW_CONFIRMATION_DIALOG')
                        .map((action, index) => (
                          <button
                            key={`${action.type}-${index}`}
                            type="button"
                            onClick={() => {
                              if (!dispatchAction(action)) {
                                setError('That navigation action is not permitted here.')
                              }
                            }}
                            className="inline-flex items-center gap-1 rounded-full border border-industrial-200 bg-industrial-50 px-2.5 py-1 text-[10px] font-semibold text-industrial-700 hover:bg-industrial-100"
                          >
                            {ACTION_LABELS[action.type] ?? action.type}
                            <ExternalLink className="size-3" aria-hidden="true" />
                          </button>
                        ))}
                    </div>
                  ) : null}
                  {entry.suggestions.length > 0 ? (
                    <div className="flex flex-wrap gap-1.5 border-t border-slate-100 pt-2">
                      {entry.suggestions.map((suggestion) => (
                        <button
                          key={suggestion}
                          type="button"
                          onClick={() => openPrompt(suggestion)}
                          className="rounded-full border border-slate-200 bg-slate-50 px-2 py-1 text-[10px] text-slate-500 hover:border-industrial-300 hover:text-industrial-700"
                        >
                          {suggestion}
                        </button>
                      ))}
                    </div>
                  ) : null}
                  <p className="text-[9px] text-slate-400">
                    {formatDateTime(entry.createdAt)}
                  </p>
                </div>
              </div>
            ))}
            {sending ? (
              <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs text-slate-500">
                <Loader2 className="size-3.5 animate-spin" aria-hidden="true" />
                Checking authorised MCP tools…
              </div>
            ) : null}
            {error ? (
              <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
                <p>{error}</p>
                {retryText ? (
                  <Button
                    size="sm"
                    variant="secondary"
                    className="mt-2"
                    onClick={() => {
                      setRetryText(null)
                      setError(null)
                      void sendMessage(retryText)
                    }}
                  >
                    Retry
                  </Button>
                ) : null}
              </div>
            ) : null}
          </div>

          <form
            className="border-t border-slate-200 bg-white p-3"
            onSubmit={(event) => {
              event.preventDefault()
              void sendMessage(input)
            }}
          >
            <label htmlFor="copilot-message" className="sr-only">
              Message the Engineering Copilot
            </label>
            <Textarea
              ref={inputRef}
              id="copilot-message"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter' && !event.shiftKey) {
                  event.preventDefault()
                  void sendMessage(input)
                }
                if (event.key === 'Escape') setOpen(false)
              }}
              placeholder="Ask about the selected pump, alert, model or sensor…"
              className="min-h-16 max-h-28 resize-none text-xs"
              disabled={sending || disabled}
              aria-describedby="copilot-shortcuts"
            />
            <div className="mt-2 flex items-center justify-between gap-2">
              <p id="copilot-shortcuts" className="text-[9px] text-slate-400">
                Enter send · Shift+Enter newline · Esc close
              </p>
              <div className="flex items-center gap-1.5">
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={clearConversation}
                  aria-label="Clear Copilot conversation"
                >
                  <Trash2 className="size-3.5" />
                </Button>
                {sending ? (
                  <Button
                    type="button"
                    variant="secondary"
                    size="sm"
                    onClick={cancelRequest}
                  >
                    <Square className="size-3" />
                    Cancel
                  </Button>
                ) : null}
                <Button
                  type="submit"
                  size="sm"
                  disabled={!input.trim() || sending || disabled}
                >
                  <Send className="size-3.5" />
                  Send
                </Button>
              </div>
            </div>
            {status?.enabled === false ? (
              <p className="mt-1 text-[10px] text-fault">
                Copilot is disabled. Monitoring remains available.
              </p>
            ) : null}
          </form>
        </>
      )}
    </section>
  )
}

function SpanChip({ label }: { label: string }) {
  return (
    <span className="rounded-full bg-white/10 px-2 py-0.5 text-[9px] font-medium uppercase tracking-[0.1em] text-slate-200">
      {label}
    </span>
  )
}

export { EngineeringCopilot }





