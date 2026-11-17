from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.copilot import orchestrator
from app.db.models import User
from app.db.session import get_db
from app.schemas.copilot import (
    CopilotApprovalDecisionResponse,
    CopilotChatRequest,
    CopilotChatResponse,
    CopilotConversation,
    CopilotStatus,
    CopilotToolRequest,
    CopilotToolResponse,
)

router = APIRouter(prefix="/copilot", tags=["Engineering Copilot"])


@router.get("/status", response_model=CopilotStatus, summary="Engineering Copilot status")
async def status(actor: User = Depends(get_current_user)) -> CopilotStatus:
    return await orchestrator.get_status(actor)


@router.post("/chat", response_model=CopilotChatResponse, summary="Ask the Engineering Copilot")
async def chat(
    payload: CopilotChatRequest,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CopilotChatResponse:
    return await orchestrator.chat(
        db,
        actor=actor,
        message=payload.message,
        context=payload.context,
        conversation_id=payload.conversation_id,
    )


@router.get(
    "/conversations/{conversation_id}",
    response_model=CopilotConversation,
    summary="Read a traceable Copilot conversation",
)
def conversation(
    conversation_id: str,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CopilotConversation:
    return orchestrator.get_conversation(
        db, actor=actor, conversation_id=conversation_id
    )


@router.post(
    "/tools/{tool_name}",
    response_model=CopilotToolResponse,
    summary="Explicitly invoke an approved read-only MCP tool",
)
async def run_tool(
    tool_name: str,
    payload: CopilotToolRequest,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CopilotToolResponse:
    return await orchestrator.run_direct_tool(
        db,
        actor=actor,
        tool_name=tool_name,
        arguments=payload.arguments,
        context=payload.context,
        conversation_id=payload.conversation_id,
    )


@router.post(
    "/approvals/{approval_id}/approve",
    response_model=CopilotApprovalDecisionResponse,
    summary="Approve the exact stored Copilot write arguments",
)
async def approve(
    approval_id: str,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CopilotApprovalDecisionResponse:
    return await orchestrator.approve(db, actor=actor, approval_id=approval_id)


@router.post(
    "/approvals/{approval_id}/reject",
    response_model=CopilotApprovalDecisionResponse,
    summary="Reject a pending Copilot write",
)
async def reject(
    approval_id: str,
    actor: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CopilotApprovalDecisionResponse:
    return await orchestrator.reject(db, actor=actor, approval_id=approval_id)
