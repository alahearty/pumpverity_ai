import type {
  CopilotApprovalDecisionResponse,
  CopilotChatRequest,
  CopilotChatResponse,
  CopilotConversation,
  CopilotStatus,
  CopilotToolRequest,
  CopilotToolResponse,
} from '@petrosense/shared-contracts'

import { apiFetch } from '@/lib/api'

export function fetchCopilotStatus(signal?: AbortSignal): Promise<CopilotStatus> {
  return apiFetch<CopilotStatus>('/copilot/status', { signal })
}

export function sendCopilotMessage(
  payload: CopilotChatRequest,
  signal?: AbortSignal,
): Promise<CopilotChatResponse> {
  return apiFetch<CopilotChatResponse>('/copilot/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
  })
}

export function runCopilotTool(
  toolName: string,
  payload: CopilotToolRequest,
  signal?: AbortSignal,
): Promise<CopilotToolResponse> {
  return apiFetch<CopilotToolResponse>(
    `/copilot/tools/${encodeURIComponent(toolName)}`,
    {
      method: 'POST',
      body: JSON.stringify(payload),
      signal,
    },
  )
}

export function approveCopilotAction(
  approvalId: string,
  signal?: AbortSignal,
): Promise<CopilotApprovalDecisionResponse> {
  return apiFetch<CopilotApprovalDecisionResponse>(
    `/copilot/approvals/${approvalId}/approve`,
    { method: 'POST', signal },
  )
}

export function rejectCopilotAction(
  approvalId: string,
  signal?: AbortSignal,
): Promise<CopilotApprovalDecisionResponse> {
  return apiFetch<CopilotApprovalDecisionResponse>(
    `/copilot/approvals/${approvalId}/reject`,
    { method: 'POST', signal },
  )
}

export function fetchCopilotConversation(
  conversationId: string,
  signal?: AbortSignal,
): Promise<CopilotConversation> {
  return apiFetch<CopilotConversation>(
    `/copilot/conversations/${conversationId}`,
    { signal },
  )
}
