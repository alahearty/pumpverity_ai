import hashlib
import json
import logging
from copy import deepcopy
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import jsonschema
from mcp.types import Tool
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.copilot.client import McpToolError, McpUnavailableError, get_mcp_client
from app.copilot.contracts import (
    READ_TOOL_NAMES,
    REPORT_ROLES,
    WRITE_ROLES,
    WRITE_TOOL_NAMES,
    CopilotAction,
    CopilotActionType,
    CopilotPageContext,
    CopilotPlan,
)
from app.copilot.providers import (
    CopilotProvider,
    DeterministicProvider,
    ProviderUnavailableError,
    build_provider,
    provider_status,
)
from app.copilot.summarizer import summarize
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import (
    CopilotConversation,
    CopilotMessage,
    CopilotToolInvocation,
    User,
)
from app.domain.enums import RoleName
from app.schemas.copilot import (
    CopilotApproval,
    CopilotApprovalDecisionResponse,
    CopilotAssistantMessage,
    CopilotAvailability,
    CopilotChatResponse,
    CopilotConversationMessage,
    CopilotStatus,
    CopilotToolResponse,
    CopilotToolRun,
)
from app.schemas.copilot import (
    CopilotConversation as CopilotConversationSchema,
)

logger = logging.getLogger("pumpverity.copilot.orchestrator")

WRITE_PATH_ROLES: dict[str, set[RoleName]] = {
    "/dashboard": {
        RoleName.ADMINISTRATOR,
        RoleName.ENGINEER,
        RoleName.RESEARCHER,
        RoleName.REVIEWER,
    },
    "/monitoring": {RoleName.ADMINISTRATOR, RoleName.ENGINEER, RoleName.RESEARCHER},
    "/analysis": {RoleName.ADMINISTRATOR, RoleName.ENGINEER, RoleName.RESEARCHER},
    "/alerts": {RoleName.ADMINISTRATOR, RoleName.ENGINEER, RoleName.REVIEWER},
    "/pumps": {RoleName.ADMINISTRATOR, RoleName.ENGINEER},
    "/sensors": {RoleName.ADMINISTRATOR, RoleName.ENGINEER, RoleName.RESEARCHER},
    "/history": {
        RoleName.ADMINISTRATOR,
        RoleName.ENGINEER,
        RoleName.RESEARCHER,
        RoleName.REVIEWER,
    },
    "/reports": {
        RoleName.ADMINISTRATOR,
        RoleName.ENGINEER,
        RoleName.RESEARCHER,
        RoleName.REVIEWER,
    },
    "/models": {RoleName.ADMINISTRATOR, RoleName.RESEARCHER},
    "/settings": {
        RoleName.ADMINISTRATOR,
        RoleName.ENGINEER,
        RoleName.RESEARCHER,
        RoleName.REVIEWER,
    },
    "/users": {RoleName.ADMINISTRATOR},
}

WRITE_TOOL_LABELS = {
    "pumpverity_acknowledge_alert": "Acknowledge alert",
    "pumpverity_mark_alert_reviewed": "Mark alert reviewed",
    "pumpverity_add_engineering_note": "Add engineering note",
    "pumpverity_generate_monitoring_report": "Generate monitoring report",
}


def _now() -> datetime:
    return datetime.now(UTC)


def _role(actor: User) -> RoleName:
    return RoleName(actor.role.name)


def _can_path(role: RoleName, path: str) -> bool:
    return role in WRITE_PATH_ROLES.get(path, set())


def _availability(
    *,
    provider: CopilotProvider,
    mode: str,
    mcp_available: bool,
    message: str,
) -> CopilotAvailability:
    return CopilotAvailability(
        enabled=True,
        provider=provider.name,
        model=provider.model,
        mode=mode,
        mcp_available=mcp_available,
        mcp_transport=get_settings().mcp_transport,
        message=message,
    )


def _tool_run_public(invocation: CopilotToolInvocation) -> CopilotToolRun:
    return CopilotToolRun(
        id=invocation.id,
        tool_name=invocation.tool_name,
        status=invocation.status,
        requires_approval=invocation.requires_approval,
        arguments=invocation.arguments,
        result=invocation.result,
        error=invocation.error,
        created_at=invocation.created_at,
        completed_at=invocation.completed_at,
    )


def _approval_public(invocation: CopilotToolInvocation) -> CopilotApproval:
    label = WRITE_TOOL_LABELS.get(invocation.tool_name, invocation.tool_name)
    return CopilotApproval(
        id=invocation.id,
        tool_name=invocation.tool_name,
        status=invocation.status,
        arguments=invocation.arguments,
        summary=label,
        created_at=invocation.created_at,
    )


def _conversation(
    db: Session, actor: User, context: CopilotPageContext, conversation_id: str | None
) -> CopilotConversation:
    if conversation_id:
        row = db.execute(
            select(CopilotConversation).where(
                CopilotConversation.id == conversation_id,
                CopilotConversation.user_id == actor.id,
            )
        ).scalar_one_or_none()
        if row is None:
            raise ApiError(
                status_code=404,
                code="COPILOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found.",
            )
        row.context = context.model_dump(by_alias=True)
        row.updated_at = _now()
        return row
    row = CopilotConversation(
        id=str(uuid4()),
        user_id=actor.id,
        title="",
        context=context.model_dump(by_alias=True),
    )
    db.add(row)
    db.flush()
    return row


def _add_message(
    db: Session,
    conversation: CopilotConversation,
    *,
    role: str,
    content: str,
    payload: dict[str, Any] | None = None,
) -> CopilotMessage:
    message = CopilotMessage(
        id=str(uuid4()),
        conversation_id=conversation.id,
        role=role,
        content=content,
        payload=payload,
    )
    db.add(message)
    conversation.updated_at = _now()
    db.flush()
    return message


def _history(db: Session, conversation: CopilotConversation) -> list[dict[str, str]]:
    limit = get_settings().copilot_history_limit
    if limit <= 0:
        return []
    rows = (
        db.execute(
            select(CopilotMessage)
            .where(CopilotMessage.conversation_id == conversation.id)
            .order_by(CopilotMessage.created_at.desc(), CopilotMessage.id.desc())
            .limit(limit)
        )
        .scalars()
        .all()
    )
    return [
        {"role": message.role.lower(), "content": message.content}
        for message in reversed(list(rows))
    ]


def _arguments_with_context(
    tool: Tool, arguments: dict[str, Any], context: CopilotPageContext
) -> dict[str, Any]:
    result = dict(arguments)
    properties = (tool.inputSchema or {}).get("properties", {})
    if "pump_id" in properties and not result.get("pump_id") and context.selected_pump_id:
        result["pump_id"] = context.selected_pump_id
    if "sensor_id" in properties and not result.get("sensor_id") and context.selected_sensor_id:
        result["sensor_id"] = context.selected_sensor_id
    if "alert_id" in properties and not result.get("alert_id") and context.selected_alert_id:
        result["alert_id"] = context.selected_alert_id
    return result


def _validate_arguments(
    tool: Tool,
    arguments: dict[str, Any],
    *,
    actor: User,
) -> dict[str, Any]:
    display = dict(arguments)
    display.pop("actor_id", None)
    if tool.name in WRITE_TOOL_NAMES:
        if tool.name in {
            "pumpverity_acknowledge_alert",
            "pumpverity_mark_alert_reviewed",
            "pumpverity_add_engineering_note",
        }:
            alert_id = display.get("alert_id")
            if not alert_id:
                raise ValueError("A selected alert is required for this action.")
        if tool.name == "pumpverity_generate_monitoring_report" and not display.get("pump_id"):
            raise ValueError("A selected pump is required to generate a report.")
    server_arguments = {**display, "actor_id": actor.id}
    schema = deepcopy(tool.inputSchema or {})
    schema.setdefault("type", "object")
    schema["additionalProperties"] = False
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(server_arguments), key=lambda item: item.path)
    if errors:
        raise ValueError("; ".join(error.message for error in errors[:3]))
    return display


def _find_tool(tools: list[Tool], name: str) -> Tool | None:
    return next((tool for tool in tools if tool.name == name), None)


def _approval_key(conversation_id: str, tool_name: str, arguments: dict[str, Any]) -> str:
    payload = json.dumps(
        {"conversation": conversation_id, "tool": tool_name, "arguments": arguments},
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _pending_approval(
    db: Session,
    conversation: CopilotConversation,
    *,
    actor: User,
    tool_name: str,
    arguments: dict[str, Any],
) -> CopilotToolInvocation:
    key = _approval_key(conversation.id, tool_name, arguments)
    existing = db.execute(
        select(CopilotToolInvocation).where(
            CopilotToolInvocation.idempotency_key == key,
            CopilotToolInvocation.actor_user_id == actor.id,
        )
    ).scalar_one_or_none()
    if existing is not None and existing.status in {"PENDING_APPROVAL", "EXECUTED"}:
        return existing
    if existing is not None:
        key = f"{key[:120]}-{uuid4()}"
    row = CopilotToolInvocation(
        id=str(uuid4()),
        conversation_id=conversation.id,
        actor_user_id=actor.id,
        tool_name=tool_name,
        arguments=arguments,
        requires_approval=True,
        status="PENDING_APPROVAL",
        idempotency_key=key,
    )
    db.add(row)
    db.flush()
    return row


def _read_invocation(
    db: Session,
    conversation: CopilotConversation,
    *,
    actor: User,
    tool_name: str,
    arguments: dict[str, Any],
) -> CopilotToolInvocation:
    row = CopilotToolInvocation(
        id=str(uuid4()),
        conversation_id=conversation.id,
        actor_user_id=actor.id,
        tool_name=tool_name,
        arguments=arguments,
        requires_approval=False,
        status="EXECUTING",
    )
    db.add(row)
    db.flush()
    return row


def _actions_for_results(
    *,
    role: RoleName,
    intent: str,
    results: list[dict[str, Any]],
    context: CopilotPageContext,
    approval: CopilotApproval | None,
) -> list[CopilotAction]:
    actions: list[CopilotAction] = []
    seen: set[tuple[str, str]] = set()

    def add(action: CopilotAction) -> None:
        key = (action.type.value, json.dumps(action.payload, sort_keys=True))
        if key not in seen:
            seen.add(key)
            actions.append(action)

    alert = next(
        (
            item["result"]
            for item in results
            if item["name"] == "pumpverity_get_alert_details" and item["status"] == "EXECUTED"
        ),
        None,
    )
    pump = next(
        (
            item["result"]
            for item in results
            if item["status"] == "EXECUTED"
            and isinstance(item.get("result"), dict)
            and item["result"].get("pump_id")
        ),
        None,
    )
    alert_id = (
        alert["alert_id"]
        if alert
        else context.selected_alert_id
        if intent in {"explain_alert", "alert_details", "missing_alert_context"}
        else None
    )
    pump_id = pump["pump_id"] if pump else context.selected_pump_id if intent else None
    sensor_id = context.selected_sensor_id
    if alert_id and role in {
        RoleName.ADMINISTRATOR,
        RoleName.ENGINEER,
        RoleName.REVIEWER,
    }:
        add(
            CopilotAction(
                type=CopilotActionType.OPEN_ALERT_DETAILS,
                payload={"alertId": alert_id},
            )
        )
    if pump_id and _can_path(role, "/monitoring"):
        add(
            CopilotAction(
                type=CopilotActionType.NAVIGATE_TO_SCREEN,
                payload={"path": "/monitoring", "pumpId": pump_id},
            )
        )
    if pump_id:
        add(
            CopilotAction(
                type=CopilotActionType.OPEN_HISTORICAL_TRENDS,
                payload={"pumpId": pump_id, "sensorId": sensor_id},
            )
        )
    if pump_id and sensor_id and _can_path(role, "/sensors"):
        add(
            CopilotAction(
                type=CopilotActionType.HIGHLIGHT_SENSOR,
                payload={"pumpId": pump_id, "sensorId": sensor_id},
            )
        )
    if approval is not None:
        add(
            CopilotAction(
                type=CopilotActionType.SHOW_CONFIRMATION_DIALOG,
                payload={"approvalId": approval.id},
            )
        )
    return actions[:4]


def _suggestions(intent: str) -> list[str]:
    mapping = {
        "explain_alert": [
            "What evidence is missing?",
            "Show sensor health",
            "Open historical trends",
        ],
        "pump_status": ["Why was the latest decision uncertain?", "Show sensor health"],
        "sensor_health": ["Show the vibration summary", "Explain validation issues"],
        "vibration": ["Show sensor health", "Open historical trends"],
        "fault_history": ["Explain the latest event", "Open Alerts & Review"],
        "model_evaluation": ["Is this metric synthetic?", "Explain uncertainty"],
        "explain_uncertainty": ["Show sensor health", "Show fault history"],
        "generate_report": ["Show sensor health", "Explain data provenance"],
    }
    return mapping.get(intent, ["What is the current monitoring status?"])


async def _status(
    actor: User,
) -> CopilotStatus:
    settings = get_settings()
    provider = build_provider()
    if not settings.copilot_enabled:
        return CopilotStatus(
            enabled=False,
            provider=provider.name,
            model=provider.model,
            provider_configured=provider_status(provider)["configured"],
            mcp_available=False,
            mcp_transport=settings.mcp_transport,
            tool_count=0,
            message="The Copilot is disabled; monitoring continues normally.",
        )
    try:
        async with get_mcp_client().connect() as session:
            tools = await session.list_tools()
        return CopilotStatus(
            enabled=True,
            provider=provider.name,
            model=provider.model,
            provider_configured=provider_status(provider)["configured"],
            mcp_available=True,
            mcp_transport=settings.mcp_transport,
            tool_count=len(tools),
            message=(
                "Copilot is ready with authorised MCP tools."
                if provider.name == "deterministic"
                else (
                    "Copilot planner is configured; final responses remain grounded "
                    "in tool results."
                )
            ),
        )
    except Exception as exc:
        logger.warning("copilot_status_mcp_unavailable", extra={"error": str(exc)})
        return CopilotStatus(
            enabled=True,
            provider=provider.name,
            model=provider.model,
            provider_configured=provider_status(provider)["configured"],
            mcp_available=False,
            mcp_transport=settings.mcp_transport,
            tool_count=0,
            message="MCP tools are unavailable. Monitoring remains operational.",
        )


async def get_status(actor: User) -> CopilotStatus:
    return await _status(actor)


async def chat(
    db: Session,
    *,
    actor: User,
    message: str,
    context: CopilotPageContext,
    conversation_id: str | None,
) -> CopilotChatResponse:
    settings = get_settings()
    if not settings.copilot_enabled:
        raise ApiError(
            status_code=503, code="COPILOT_DISABLED", message="The Engineering Copilot is disabled."
        )
    conversation = _conversation(db, actor, context, conversation_id)
    if not conversation.title:
        conversation.title = message.strip()[:160] or "Engineering Copilot"
    _add_message(
        db,
        conversation,
        role="USER",
        content=message,
        payload={"context": context.model_dump(by_alias=True)},
    )
    role = _role(actor)
    provider = build_provider()
    plan: CopilotPlan | None = None
    mode = "deterministic" if provider.name == "deterministic" else "remote_llm"
    tool_runs: list[CopilotToolInvocation] = []
    approval: CopilotToolInvocation | None = None
    results: list[dict[str, Any]] = []
    mcp_available = False
    availability_message = "MCP tools are unavailable. Monitoring remains operational."

    try:
        async with get_mcp_client().connect() as session:
            tools = await session.list_tools()
            mcp_available = True
            writable: set[str] = set()
            if role in WRITE_ROLES:
                writable.update(
                    {
                        "pumpverity_acknowledge_alert",
                        "pumpverity_mark_alert_reviewed",
                        "pumpverity_add_engineering_note",
                    }
                )
            if role in REPORT_ROLES:
                writable.add("pumpverity_generate_monitoring_report")
            allowed = READ_TOOL_NAMES | writable
            available_tools = [tool for tool in tools if tool.name in allowed]
            try:
                plan = await provider.plan(
                    message=message,
                    context=context,
                    history=_history(db, conversation),
                    tools=available_tools,
                )
                availability_message = (
                    "Local grounded planner selected authorised MCP tools."
                    if provider.name == "deterministic"
                    else "Remote planner selected authorised MCP tools; the response is composed "
                    "from their results."
                )
            except ProviderUnavailableError as exc:
                mode = "deterministic_fallback"
                provider = DeterministicProvider()
                plan = await provider.plan(
                    message=message,
                    context=context,
                    history=[],
                    tools=available_tools,
                )
                availability_message = (
                    f"{exc} The local grounded planner is active; monitoring is unaffected."
                )
            plan.tool_calls = plan.tool_calls[: settings.copilot_max_tool_calls]
            for planned in plan.tool_calls:
                if planned.name not in allowed:
                    continue
                tool = _find_tool(tools, planned.name)
                if tool is None:
                    continue
                try:
                    display_arguments = _arguments_with_context(tool, planned.arguments, context)
                    display_arguments = _validate_arguments(tool, display_arguments, actor=actor)
                    if planned.name in WRITE_TOOL_NAMES:
                        if (
                            planned.name
                            in {
                                "pumpverity_acknowledge_alert",
                                "pumpverity_mark_alert_reviewed",
                                "pumpverity_add_engineering_note",
                            }
                            and display_arguments.get("alert_id") != context.selected_alert_id
                        ):
                            raise ValueError(
                                "Write actions are restricted to the alert selected in the UI."
                            )
                        if (
                            planned.name == "pumpverity_generate_monitoring_report"
                            and display_arguments.get("pump_id") != context.selected_pump_id
                        ):
                            raise ValueError(
                                "Report generation is restricted to the pump selected in the UI."
                            )
                        if approval is None:
                            approval = _pending_approval(
                                db,
                                conversation,
                                actor=actor,
                                tool_name=planned.name,
                                arguments=display_arguments,
                            )
                            tool_runs.append(approval)
                        continue
                    invocation = _read_invocation(
                        db,
                        conversation,
                        actor=actor,
                        tool_name=planned.name,
                        arguments=display_arguments,
                    )
                    try:
                        payload = await session.call_tool(
                            planned.name, {**display_arguments, "actor_id": actor.id}
                        )
                    except McpToolError as exc:
                        invocation.status = "FAILED"
                        invocation.error = str(exc)
                        invocation.completed_at = _now()
                        results.append(
                            {
                                "name": planned.name,
                                "status": "FAILED",
                                "error": str(exc),
                            }
                        )
                    else:
                        invocation.status = "EXECUTED"
                        invocation.result = payload
                        invocation.completed_at = _now()
                        results.append(
                            {
                                "name": planned.name,
                                "status": "EXECUTED",
                                "result": payload,
                            }
                        )
                    tool_runs.append(invocation)
                    db.flush()
                except ValueError as exc:
                    invocation = _read_invocation(
                        db,
                        conversation,
                        actor=actor,
                        tool_name=planned.name,
                        arguments=planned.arguments,
                    )
                    invocation.status = "FAILED"
                    invocation.error = f"Argument validation failed: {exc}"
                    invocation.completed_at = _now()
                    tool_runs.append(invocation)
                    results.append(
                        {
                            "name": planned.name,
                            "status": "FAILED",
                            "error": invocation.error,
                        }
                    )
                    db.flush()
    except McpUnavailableError as exc:
        logger.warning("copilot_mcp_unavailable", extra={"error": str(exc)})
        availability_message = (
            "MCP tools are unavailable. Monitoring and edge inference continue independently."
        )
    except Exception as exc:
        logger.exception("copilot_chat_failed", extra={"error": str(exc)})
        availability_message = (
            "The Copilot could not complete the tool plan. Monitoring remains operational."
        )

    approval_public = _approval_public(approval) if approval else None
    intent = plan.intent if plan else "general"
    assistant_text = summarize(
        intent=intent,
        results=results,
        context=context,
        pending_tool=(
            {
                "tool_name": approval.tool_name,
                "arguments": approval.arguments,
            }
            if approval
            else None
        ),
    )
    if (
        intent
        in {
            "acknowledge_alert",
            "mark_reviewed",
            "add_note",
            "generate_report",
        }
        and approval is None
        and mcp_available
    ):
        if intent == "generate_report" and role in REPORT_ROLES:
            assistant_text = "Select a pump before generating a report."
        elif role not in WRITE_ROLES:
            assistant_text = (
                "Your role can inspect monitoring evidence but cannot acknowledge alerts "
                "or append engineering reviews. The original prediction is unchanged."
            )
    if not mcp_available:
        assistant_text = (
            "The MCP tool layer is currently unavailable, so I cannot retrieve monitoring "
            "evidence or execute authorised actions. Local acquisition, validation, inference "
            "and alerts continue independently. Try again when the MCP service is reachable."
        )
    suggestions = (
        plan.suggested_questions if plan and plan.suggested_questions else _suggestions(intent)
    )
    actions = _actions_for_results(
        role=role,
        intent=intent,
        results=results,
        context=context,
        approval=approval_public,
    )
    assistant = _add_message(
        db,
        conversation,
        role="ASSISTANT",
        content=assistant_text,
        payload={
            "actions": [action.model_dump(mode="json", by_alias=True) for action in actions],
            "suggestedQuestions": suggestions[:3],
            "toolRunIds": [item.id for item in tool_runs],
            "approvalId": approval.id if approval else None,
        },
    )
    db.commit()
    availability = _availability(
        provider=provider,
        mode=mode if mcp_available else "unavailable",
        mcp_available=mcp_available,
        message=availability_message,
    )
    return CopilotChatResponse(
        conversation_id=conversation.id,
        assistant_message=CopilotAssistantMessage(
            id=assistant.id,
            content=assistant_text,
            actions=actions,
            suggested_questions=suggestions[:3],
            tool_run_ids=[item.id for item in tool_runs],
            approval_id=approval.id if approval else None,
            created_at=assistant.created_at,
        ),
        tool_runs=[_tool_run_public(item) for item in tool_runs],
        approval=approval_public,
        availability=availability,
    )


def _approval_result_message(tool_name: str, result: dict[str, Any]) -> str:
    if tool_name == "pumpverity_acknowledge_alert":
        return (
            f"The alert is now {result.get('status')}. The original AI prediction and model "
            "evidence were preserved."
        )
    if tool_name == "pumpverity_mark_alert_reviewed":
        return (
            "The engineering review was appended. It is an engineer judgement, not verified "
            "experimental ground truth, and the original prediction is unchanged."
        )
    if tool_name == "pumpverity_add_engineering_note":
        return (
            "The engineering note was appended. The original prediction and review trail remain "
            "intact."
        )
    if tool_name == "pumpverity_generate_monitoring_report":
        return (
            f"Monitoring report {str(result.get('report_id'))[:8]} was generated with SHA-256 "
            f"{str(result.get('report_sha256'))[:16]}... and explicit simulated-data disclosure."
        )
    return "The approved Copilot action completed."


async def approve(db: Session, *, actor: User, approval_id: str) -> CopilotApprovalDecisionResponse:
    invocation = db.execute(
        select(CopilotToolInvocation).where(
            CopilotToolInvocation.id == approval_id,
            CopilotToolInvocation.actor_user_id == actor.id,
            CopilotToolInvocation.requires_approval.is_(True),
        )
    ).scalar_one_or_none()
    if invocation is None:
        raise ApiError(
            status_code=404,
            code="COPILOT_APPROVAL_NOT_FOUND",
            message="Approval request not found.",
        )
    if invocation.status == "EXECUTED":
        return _approval_response(db, invocation, "Action was already executed.")
    if invocation.status != "PENDING_APPROVAL":
        raise ApiError(
            status_code=409,
            code="COPILOT_APPROVAL_NOT_PENDING",
            message="This approval is not pending.",
        )
    allowed_roles = (
        REPORT_ROLES
        if invocation.tool_name == "pumpverity_generate_monitoring_report"
        else WRITE_ROLES
    )
    if _role(actor) not in allowed_roles:
        raise ApiError(
            status_code=403, code="FORBIDDEN", message="Your role cannot approve this action."
        )
    provider = build_provider()
    try:
        async with get_mcp_client().connect() as session:
            tools = await session.list_tools()
            tool = _find_tool(tools, invocation.tool_name)
            if tool is None or invocation.tool_name not in WRITE_TOOL_NAMES:
                raise ValueError("The approved tool is not available.")
            _validate_arguments(tool, invocation.arguments, actor=actor)
            invocation.status = "EXECUTING"
            db.commit()
            payload = await session.call_tool(
                invocation.tool_name, {**invocation.arguments, "actor_id": actor.id}
            )
    except (McpUnavailableError, McpToolError, ValueError) as exc:
        invocation.status = "FAILED"
        invocation.error = str(exc)
        invocation.completed_at = _now()
        db.commit()
        raise ApiError(
            status_code=502,
            code="COPILOT_APPROVAL_FAILED",
            message=f"The approved action failed and no success is claimed: {exc}",
        ) from exc
    invocation.status = "EXECUTED"
    invocation.result = payload
    invocation.error = None
    invocation.completed_at = _now()
    text = _approval_result_message(invocation.tool_name, payload)
    actions = _completion_actions(actor, invocation, payload)
    conversation = (
        db.get(CopilotConversation, invocation.conversation_id)
        if invocation.conversation_id
        else None
    )
    if conversation is not None:
        _add_message(
            db,
            conversation,
            role="ASSISTANT",
            content=text,
            payload={
                "actions": [action.model_dump(mode="json", by_alias=True) for action in actions],
                "toolRunIds": [invocation.id],
                "approvalId": invocation.id,
            },
        )
    db.commit()
    availability = _availability(
        provider=provider,
        mode="deterministic" if provider.name == "deterministic" else "remote_llm",
        mcp_available=True,
        message="Approved MCP write completed and was revalidated server-side.",
    )
    return CopilotApprovalDecisionResponse(
        approval=_approval_public(invocation),
        tool_run=_tool_run_public(invocation),
        actions=actions,
        message=text,
        availability=availability,
    )


def _completion_actions(
    actor: User, invocation: CopilotToolInvocation, payload: dict[str, Any]
) -> list[CopilotAction]:
    role = _role(actor)
    actions: list[CopilotAction] = []
    if invocation.tool_name in {
        "pumpverity_acknowledge_alert",
        "pumpverity_mark_alert_reviewed",
        "pumpverity_add_engineering_note",
    } and role in {
        RoleName.ADMINISTRATOR,
        RoleName.ENGINEER,
        RoleName.REVIEWER,
    }:
        alert_id = invocation.arguments.get("alert_id")
        if alert_id:
            actions.append(
                CopilotAction(
                    type=CopilotActionType.OPEN_ALERT_DETAILS,
                    payload={"alertId": alert_id},
                )
            )
    if invocation.tool_name == "pumpverity_generate_monitoring_report" and payload.get("report_id"):
        actions.append(
            CopilotAction(
                type=CopilotActionType.OPEN_REPORT,
                payload={"reportId": payload["report_id"]},
            )
        )
    return actions


def _approval_response(
    db: Session, invocation: CopilotToolInvocation, message: str
) -> CopilotApprovalDecisionResponse:
    provider = build_provider()
    actor = db.get(User, invocation.actor_user_id)
    actions = _completion_actions(actor, invocation, invocation.result or {}) if actor else []
    return CopilotApprovalDecisionResponse(
        approval=_approval_public(invocation),
        tool_run=_tool_run_public(invocation),
        actions=actions,
        message=message,
        availability=_availability(
            provider=provider,
            mode="deterministic" if provider.name == "deterministic" else "remote_llm",
            mcp_available=True,
            message="Approval is already complete; no duplicate action was executed.",
        ),
    )


async def reject(db: Session, *, actor: User, approval_id: str) -> CopilotApprovalDecisionResponse:
    invocation = db.execute(
        select(CopilotToolInvocation).where(
            CopilotToolInvocation.id == approval_id,
            CopilotToolInvocation.actor_user_id == actor.id,
            CopilotToolInvocation.requires_approval.is_(True),
        )
    ).scalar_one_or_none()
    if invocation is None:
        raise ApiError(
            status_code=404,
            code="COPILOT_APPROVAL_NOT_FOUND",
            message="Approval request not found.",
        )
    if invocation.status == "REJECTED":
        return _approval_response(db, invocation, "Approval was already rejected; no action ran.")
    if invocation.status != "PENDING_APPROVAL":
        raise ApiError(
            status_code=409,
            code="COPILOT_APPROVAL_NOT_PENDING",
            message="This approval is not pending.",
        )
    invocation.status = "REJECTED"
    invocation.error = "Rejected by the authenticated user."
    invocation.completed_at = _now()
    if invocation.conversation_id:
        conversation = db.get(CopilotConversation, invocation.conversation_id)
        if conversation is not None:
            _add_message(
                db,
                conversation,
                role="ASSISTANT",
                content="The proposed action was rejected. No operational record was changed.",
                payload={"toolRunIds": [invocation.id], "approvalId": invocation.id},
            )
    db.commit()
    provider = build_provider()
    return CopilotApprovalDecisionResponse(
        approval=_approval_public(invocation),
        tool_run=_tool_run_public(invocation),
        actions=[],
        message="Rejected. No write was executed.",
        availability=_availability(
            provider=provider,
            mode="deterministic" if provider.name == "deterministic" else "remote_llm",
            mcp_available=True,
            message="Write rejected; monitoring remains unaffected.",
        ),
    )


async def run_direct_tool(
    db: Session,
    *,
    actor: User,
    tool_name: str,
    arguments: dict[str, Any],
    context: CopilotPageContext,
    conversation_id: str | None,
) -> CopilotToolResponse:
    if tool_name not in READ_TOOL_NAMES:
        raise ApiError(
            status_code=403,
            code="COPILOT_TOOL_NOT_ALLOWED",
            message="Direct UI invocation is restricted to read-only Copilot tools.",
        )
    conversation = None
    if conversation_id:
        conversation = db.execute(
            select(CopilotConversation).where(
                CopilotConversation.id == conversation_id,
                CopilotConversation.user_id == actor.id,
            )
        ).scalar_one_or_none()
        if conversation is None:
            raise ApiError(
                status_code=404,
                code="COPILOT_CONVERSATION_NOT_FOUND",
                message="Conversation not found.",
            )
    try:
        async with get_mcp_client().connect() as session:
            tools = await session.list_tools()
            tool = _find_tool(tools, tool_name)
            if tool is None:
                raise ApiError(
                    status_code=404,
                    code="COPILOT_TOOL_NOT_FOUND",
                    message="Approved MCP tool not found.",
                )
            display_arguments = _validate_arguments(
                tool,
                _arguments_with_context(tool, arguments, context),
                actor=actor,
            )
            if conversation is not None:
                invocation = _read_invocation(
                    db,
                    conversation,
                    actor=actor,
                    tool_name=tool_name,
                    arguments=display_arguments,
                )
            else:
                invocation = CopilotToolInvocation(
                    id=str(uuid4()),
                    conversation_id=None,
                    actor_user_id=actor.id,
                    tool_name=tool_name,
                    arguments=display_arguments,
                    requires_approval=False,
                    status="EXECUTING",
                )
                db.add(invocation)
                db.flush()
            try:
                payload = await session.call_tool(
                    tool_name, {**display_arguments, "actor_id": actor.id}
                )
            except McpToolError as exc:
                invocation.status = "FAILED"
                invocation.error = str(exc)
                invocation.completed_at = _now()
                db.commit()
                raise ApiError(
                    status_code=502, code="COPILOT_TOOL_FAILED", message=str(exc)
                ) from exc
            invocation.status = "EXECUTED"
            invocation.result = payload
            invocation.completed_at = _now()
            db.commit()
    except ValueError as exc:
        raise ApiError(
            status_code=422,
            code="COPILOT_TOOL_ARGUMENTS_INVALID",
            message=f"The tool arguments were rejected: {exc}",
        ) from exc
    except McpUnavailableError as exc:
        raise ApiError(
            status_code=503,
            code="COPILOT_MCP_UNAVAILABLE",
            message="MCP tools are unavailable; monitoring remains operational.",
        ) from exc
    result = payload if isinstance(payload, dict) else {}
    actions = _direct_actions(actor, tool_name, result, context)
    return CopilotToolResponse(
        conversation_id=conversation.id if conversation else None,
        tool_run=_tool_run_public(invocation),
        actions=actions,
    )


def _direct_actions(
    actor: User,
    tool_name: str,
    result: dict[str, Any],
    context: CopilotPageContext,
) -> list[CopilotAction]:
    role = _role(actor)
    actions: list[CopilotAction] = []
    if tool_name == "pumpverity_get_sensor_health" and result.get("pump_id"):
        actions.append(
            CopilotAction(
                type=CopilotActionType.HIGHLIGHT_SENSOR,
                payload={
                    "pumpId": result["pump_id"],
                    "sensorId": context.selected_sensor_id,
                },
            )
        )
    if result.get("pump_id") and _can_path(role, "/monitoring"):
        actions.append(
            CopilotAction(
                type=CopilotActionType.NAVIGATE_TO_SCREEN,
                payload={"path": "/monitoring", "pumpId": result["pump_id"]},
            )
        )
    return actions


def get_conversation(
    db: Session, *, actor: User, conversation_id: str
) -> CopilotConversationSchema:
    conversation = db.execute(
        select(CopilotConversation).where(
            CopilotConversation.id == conversation_id,
            CopilotConversation.user_id == actor.id,
        )
    ).scalar_one_or_none()
    if conversation is None:
        raise ApiError(
            status_code=404,
            code="COPILOT_CONVERSATION_NOT_FOUND",
            message="Conversation not found.",
        )
    messages = (
        db.execute(
            select(CopilotMessage)
            .where(CopilotMessage.conversation_id == conversation.id)
            .order_by(CopilotMessage.created_at.asc())
        )
        .scalars()
        .all()
    )
    invocations = (
        db.execute(
            select(CopilotToolInvocation)
            .where(CopilotToolInvocation.conversation_id == conversation.id)
            .order_by(CopilotToolInvocation.created_at.asc())
        )
        .scalars()
        .all()
    )
    message_items = []
    for message in messages:
        payload = message.payload or {}
        actions = [
            CopilotAction.model_validate(action)
            for action in payload.get("actions", [])
            if isinstance(action, dict)
        ]
        message_items.append(
            CopilotConversationMessage(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=message.created_at,
                actions=actions,
                approval_id=payload.get("approvalId"),
            )
        )
    pending = [_approval_public(item) for item in invocations if item.status == "PENDING_APPROVAL"]
    return CopilotConversationSchema(
        id=conversation.id,
        title=conversation.title,
        context=conversation.context,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        messages=message_items,
        tool_runs=[_tool_run_public(item) for item in invocations],
        pending_approvals=pending,
    )

