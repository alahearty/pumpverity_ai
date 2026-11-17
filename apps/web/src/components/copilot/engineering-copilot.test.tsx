import type { CopilotChatResponse, CopilotStatus } from '@petrosense/shared-contracts'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useNavigate } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { CopilotContextProvider, useCopilot, useCopilotPageContext } from '@/providers/copilot-context-provider'

import { EngineeringCopilot } from './engineering-copilot'

const fetchCopilotStatus = vi.hoisted(() => vi.fn())
const sendCopilotMessage = vi.hoisted(() => vi.fn())
const approveCopilotAction = vi.hoisted(() => vi.fn())
const rejectCopilotAction = vi.hoisted(() => vi.fn())
const runCopilotTool = vi.hoisted(() => vi.fn())

vi.mock('@/services/copilot-service', () => ({
  fetchCopilotStatus,
  sendCopilotMessage,
  approveCopilotAction,
  rejectCopilotAction,
  runCopilotTool,
}))
vi.mock('@/providers/auth-provider', () => ({
  useAuth: () => ({
    status: 'authenticated',
    user: {
      id: 'user-1',
      email: 'engineer@petrosense.local',
      username: 'engineer',
      full_name: 'Chinedu Okafor',
      role: 'ENGINEER',
      is_active: true,
      must_change_password: false,
      created_at: '2026-01-01T00:00:00Z',
      last_login_at: null,
    },
    isAuthenticated: true,
    login: async () => {},
    logout: async () => {},
  }),
}))

const STATUS: CopilotStatus = {
  enabled: true,
  provider: 'deterministic',
  model: 'grounded-local-planner',
  providerConfigured: true,
  mcpAvailable: true,
  mcpTransport: 'memory',
  toolCount: 13,
  message: 'Copilot is ready with authorised MCP tools.',
}

function chatResponse(overrides: Partial<CopilotChatResponse> = {}): CopilotChatResponse {
  return {
    conversationId: 'conversation-1',
    assistantMessage: {
      id: 'assistant-1',
      role: 'ASSISTANT',
      content: 'Latest decision: FAULT. Data provenance: simulated.',
      actions: [
        {
          type: 'OPEN_HISTORICAL_TRENDS',
          payload: { pumpId: '11111111-1111-1111-1111-111111111111' },
        },
      ],
      suggestedQuestions: ['Show sensor health'],
      toolRunIds: ['run-1'],
      approvalId: null,
      createdAt: '2026-11-17T10:00:00Z',
    },
    toolRuns: [
      {
        id: 'run-1',
        toolName: 'pumpverity_get_latest_prediction',
        status: 'EXECUTED',
        requiresApproval: false,
        arguments: { pump_id: '11111111-1111-1111-1111-111111111111' },
        result: {
          decision: 'FAULT',
          data_quality: 'VALID',
          uncertainty_score: 0.08,
          provenance: 'SIMULATED',
        },
        error: null,
        createdAt: '2026-11-17T10:00:00Z',
        completedAt: '2026-11-17T10:00:01Z',
      },
    ],
    approval: null,
    availability: {
      enabled: true,
      provider: 'deterministic',
      model: 'grounded-local-planner',
      mode: 'deterministic',
      mcpAvailable: true,
      mcpTransport: 'memory',
      message: 'Local grounded planner selected authorised MCP tools.',
    },
    ...overrides,
  }
}

function Harness({ path = '/monitoring' }: { path?: string }) {
  useCopilotPageContext({
    selectedPumpId: '11111111-1111-1111-1111-111111111111',
    selectedSensorId: '22222222-2222-2222-2222-222222222222',
    selectedAlertId: null,
    activeModelVersion: '0.1.0',
    operatingRegime: 'STEADY_STATE',
    monitoringMode: 'SIMULATED',
    connectivityStatus: 'NO_LIVE_CHANNEL',
  })
  return <p data-testid="route-probe">{path}</p>
}

function ContextProbe() {
  const { context } = useCopilot()
  const navigate = useNavigate()
  return (
    <div>
      <p data-testid="screen-context">{context.screenName}</p>
      <button type="button" onClick={() => navigate('/history')}>
        Go to history
      </button>
    </div>
  )
}

function renderPanel() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/monitoring']}>
        <Routes>
          <Route
            path="/monitoring"
            element={
              <CopilotContextProvider>
                <Harness path="/monitoring" />
                <EngineeringCopilot />
              </CopilotContextProvider>
            }
          />
          <Route
            path="/history"
            element={
              <CopilotContextProvider>
                <ContextProbe />
              </CopilotContextProvider>
            }
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('EngineeringCopilot', () => {
  beforeEach(() => {
    fetchCopilotStatus.mockResolvedValue(STATUS)
    sendCopilotMessage.mockResolvedValue(chatResponse())
    runCopilotTool.mockResolvedValue({
      conversationId: 'conversation-1',
      toolRun: chatResponse().toolRuns[0],
      actions: [],
    })
    approveCopilotAction.mockResolvedValue({
      approval: {
        id: 'approval-1',
        toolName: 'pumpverity_mark_alert_reviewed',
        status: 'EXECUTED',
        arguments: { alert_id: 'alert-1', notes: 'reviewed' },
        summary: 'Mark alert reviewed',
        createdAt: '2026-11-17T10:00:00Z',
      },
      toolRun: {
        ...chatResponse().toolRuns[0],
        id: 'run-2',
        toolName: 'pumpverity_mark_alert_reviewed',
        status: 'EXECUTED',
        result: { status: 'REVIEWED', message: 'Engineering review appended.' },
      },
      actions: [],
      message: 'The engineering review was appended.',
      availability: chatResponse().availability,
    })
    rejectCopilotAction.mockResolvedValue({
      approval: {
        id: 'approval-1',
        toolName: 'pumpverity_mark_alert_reviewed',
        status: 'REJECTED',
        arguments: { alert_id: 'alert-1', notes: 'reviewed' },
        summary: 'Mark alert reviewed',
        createdAt: '2026-11-17T10:00:00Z',
      },
      toolRun: chatResponse().toolRuns[0],
      actions: [],
      message: 'Rejected. No write was executed.',
      availability: chatResponse().availability,
    })
    fetchCopilotStatus.mockClear()
    sendCopilotMessage.mockClear()
    approveCopilotAction.mockClear()
    rejectCopilotAction.mockClear()
    runCopilotTool.mockClear()
  })

  it('opens, sends a grounded question and shows the tool timeline', async () => {
    const user = userEvent.setup()
    renderPanel()
    await user.click(
      screen.getByRole('button', { name: 'Open Engineering Copilot' }),
    )
    expect(
      screen.getByRole('dialog', { name: 'PUMPVERITY AI Engineering Copilot' }),
    ).toBeInTheDocument()
    expect(await screen.findByText(/Ready/)).toBeInTheDocument()
    expect(screen.getAllByText(/Pump 11111111/).length).toBeGreaterThan(0)

    await user.type(
      screen.getByLabelText('Message the Engineering Copilot'),
      'Explain the latest prediction',
    )
    await user.click(screen.getByRole('button', { name: 'Send' }))

    await waitFor(() => {
      expect(sendCopilotMessage).toHaveBeenCalledWith(
        expect.objectContaining({
          message: 'Explain the latest prediction',
          context: expect.objectContaining({
            selectedPumpId: '11111111-1111-1111-1111-111111111111',
            screenName: 'Live Monitoring',
            monitoringMode: 'SIMULATED',
          }),
        }),
        expect.any(AbortSignal),
      )
    })
    expect(await screen.findByText(/Latest decision: FAULT/)).toBeInTheDocument()
    expect(screen.getAllByText('Latest prediction').length).toBeGreaterThan(0)
    expect(screen.getByRole('button', { name: /Open historical trends/ })).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Close Copilot' }))
    expect(
      screen.getByRole('button', { name: 'Open Engineering Copilot' }),
    ).toBeInTheDocument()
  })

  it('requires explicit confirmation for a write proposal', async () => {
    sendCopilotMessage.mockResolvedValue(
      chatResponse({
        assistantMessage: {
          ...chatResponse().assistantMessage,
          content: 'I prepared mark alert reviewed. Nothing has been changed yet.',
          approvalId: 'approval-1',
          actions: [
            { type: 'SHOW_CONFIRMATION_DIALOG', payload: { approvalId: 'approval-1' } },
          ],
        },
        approval: {
          id: 'approval-1',
          toolName: 'pumpverity_mark_alert_reviewed',
          status: 'PENDING_APPROVAL',
          arguments: { alert_id: 'alert-1', notes: 'reviewed' },
          summary: 'Mark alert reviewed',
          createdAt: '2026-11-17T10:00:00Z',
        },
      }),
    )
    const user = userEvent.setup()
    renderPanel()
    await user.click(
      screen.getByRole('button', { name: 'Open Engineering Copilot' }),
    )
    await user.type(
      screen.getByLabelText('Message the Engineering Copilot'),
      'Mark this alert reviewed',
    )
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(await screen.findByText('Confirmation required')).toBeInTheDocument()
    expect(screen.getAllByText(/alert-1/).length).toBeGreaterThan(0)
    await user.click(
      screen.getByRole('button', { name: 'Confirm and execute' }),
    )
    await waitFor(() => {
      expect(approveCopilotAction).toHaveBeenCalledWith('approval-1')
    })
    expect(await screen.findByText('The engineering review was appended.')).toBeInTheDocument()
    expect(screen.queryByText('Confirmation required')).not.toBeInTheDocument()
  })

  it('updates the screen context after navigation', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    const user = userEvent.setup()
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={['/monitoring']}>
          <Routes>
            <Route
              path="/monitoring"
              element={
                <CopilotContextProvider>
                  <ContextProbe />
                </CopilotContextProvider>
              }
            />
            <Route
              path="/history"
              element={
                <CopilotContextProvider>
                  <ContextProbe />
                </CopilotContextProvider>
              }
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    )
    expect(screen.getByTestId('screen-context')).toHaveTextContent('Live Monitoring')
    await user.click(screen.getByRole('button', { name: 'Go to history' }))
    expect(screen.getByTestId('screen-context')).toHaveTextContent('Historical Trends')
  })
})



