from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.copilot.contracts import CopilotAction, CopilotPageContext


class CopilotBaseModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class CopilotAvailability(CopilotBaseModel):
    enabled: bool
    provider: str
    model: str | None = None
    mode: Literal["deterministic", "remote_llm", "deterministic_fallback", "unavailable"]
    mcp_available: bool
    mcp_transport: str
    message: str


class CopilotToolRun(CopilotBaseModel):
    id: str
    tool_name: str
    status: str
    requires_approval: bool
    arguments: dict[str, Any]
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class CopilotApproval(CopilotBaseModel):
    id: str
    tool_name: str
    status: str
    arguments: dict[str, Any]
    summary: str
    created_at: datetime


class CopilotAssistantMessage(CopilotBaseModel):
    id: str
    role: Literal["ASSISTANT"] = "ASSISTANT"
    content: str
    actions: list[CopilotAction] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)
    tool_run_ids: list[str] = Field(default_factory=list)
    approval_id: str | None = None
    created_at: datetime


class CopilotChatRequest(CopilotBaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, max_length=36)
    context: CopilotPageContext = Field(default_factory=CopilotPageContext)


class CopilotChatResponse(CopilotBaseModel):
    conversation_id: str
    assistant_message: CopilotAssistantMessage
    tool_runs: list[CopilotToolRun]
    approval: CopilotApproval | None = None
    availability: CopilotAvailability


class CopilotToolRequest(CopilotBaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)
    context: CopilotPageContext = Field(default_factory=CopilotPageContext)
    conversation_id: str | None = Field(default=None, max_length=36)


class CopilotToolResponse(CopilotBaseModel):
    conversation_id: str | None
    tool_run: CopilotToolRun
    actions: list[CopilotAction] = Field(default_factory=list)


class CopilotApprovalDecisionResponse(CopilotBaseModel):
    approval: CopilotApproval
    tool_run: CopilotToolRun
    actions: list[CopilotAction] = Field(default_factory=list)
    message: str
    availability: CopilotAvailability


class CopilotConversationMessage(CopilotBaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    actions: list[CopilotAction] = Field(default_factory=list)
    approval_id: str | None = None


class CopilotConversation(CopilotBaseModel):
    id: str
    title: str
    context: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    messages: list[CopilotConversationMessage]
    tool_runs: list[CopilotToolRun]
    pending_approvals: list[CopilotApproval]


class CopilotStatus(CopilotBaseModel):
    enabled: bool
    provider: str
    model: str | None = None
    provider_configured: bool
    mcp_available: bool
    mcp_transport: str
    tool_count: int
    message: str
