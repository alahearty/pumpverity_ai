import json
import logging
from abc import ABC, abstractmethod
from typing import Any

import httpx
from mcp.types import Tool

from app.copilot.contracts import (
    READ_TOOL_NAMES,
    WRITE_TOOL_NAMES,
    CopilotPageContext,
    CopilotPlan,
    PlannedToolCall,
)
from app.core.config import get_settings

logger = logging.getLogger("pumpverity.copilot.provider")


class ProviderUnavailableError(RuntimeError):
    pass


class CopilotProvider(ABC):
    name: str
    model: str | None = None

    @abstractmethod
    async def plan(
        self,
        *,
        message: str,
        context: CopilotPageContext,
        history: list[dict[str, str]],
        tools: list[Tool],
    ) -> CopilotPlan:
        raise NotImplementedError


class DeterministicProvider(CopilotProvider):
    name = "deterministic"
    model = "grounded-local-planner"

    async def plan(
        self,
        *,
        message: str,
        context: CopilotPageContext,
        history: list[dict[str, str]],
        tools: list[Tool],
    ) -> CopilotPlan:
        del history
        available = {tool.name for tool in tools}
        text = message.lower().strip()
        calls: list[PlannedToolCall] = []
        pump_args = {"pump_id": context.selected_pump_id} if context.selected_pump_id else {}
        sensor_args = (
            {**pump_args, "sensor_id": context.selected_sensor_id}
            if pump_args and context.selected_sensor_id
            else pump_args
        )
        selected_alert = context.selected_alert_id

        def add(name: str, arguments: dict[str, Any] | None = None) -> None:
            if name not in available:
                return
            if any(call.name == name for call in calls):
                return
            calls.append(PlannedToolCall(name=name, arguments=arguments or {}))

        intent = "general"
        if any(word in text for word in ("acknowledge", "ack ")):
            if selected_alert:
                add("pumpverity_acknowledge_alert", {"alert_id": selected_alert})
                intent = "acknowledge_alert"
            else:
                intent = "missing_alert_context"
        elif "report" in text:
            if pump_args:
                add("pumpverity_generate_monitoring_report", pump_args)
                intent = "generate_report"
            else:
                intent = "missing_pump_context"
        elif "add note" in text or "engineering note" in text:
            if selected_alert:
                add(
                    "pumpverity_add_engineering_note",
                    {
                        "alert_id": selected_alert,
                        "notes": _review_note(message),
                    },
                )
                intent = "add_note"
            else:
                intent = "missing_alert_context"
        elif ("mark" in text and "reviewed" in text) or any(
            phrase in text
            for phrase in ("mark as reviewed", "review this", "review the alert")
        ):
            if selected_alert:
                add(
                    "pumpverity_mark_alert_reviewed",
                    {
                        "alert_id": selected_alert,
                        "notes": _review_note(message),
                    },
                )
                intent = "mark_reviewed"
            else:
                intent = "missing_alert_context"
        elif any(
            phrase in text
            for phrase in (
                "how do i",
                "how to",
                "help me",
                "what can you do",
                "roles",
                "permission",
            )
        ):
            intent = "app_help"
        elif any(word in text for word in ("uncertain", "why", "abstain")) and selected_alert:
            add("pumpverity_get_alert_details", {"alert_id": selected_alert})
            if pump_args:
                add("pumpverity_get_latest_prediction", sensor_args)
                add("pumpverity_get_sensor_health", sensor_args)
            add("pumpverity_get_model_evaluation")
            intent = "explain_alert"
        elif any(word in text for word in ("uncertain", "uncertainty", "abstain", "abstention")):
            if pump_args:
                add("pumpverity_get_latest_prediction", sensor_args)
                add("pumpverity_get_fault_history", pump_args)
            intent = "explain_uncertainty"
        elif any(word in text for word in ("sensor", "diagnostic", "disconnect", "invalid")):
            if pump_args:
                add("pumpverity_get_sensor_health", sensor_args)
                add("pumpverity_get_latest_prediction", sensor_args)
                intent = "sensor_health"
            else:
                add("pumpverity_get_monitoring_overview")
                intent = "sensor_health_overview"
        elif any(word in text for word in ("vibration", "rms", "waveform", "signal")):
            if pump_args:
                add("pumpverity_get_vibration_summary", sensor_args)
                intent = "vibration"
            else:
                intent = "missing_pump_context"
        elif any(word in text for word in ("history", "fault history", "trend", "events")):
            if pump_args:
                add("pumpverity_get_fault_history", pump_args)
                intent = "fault_history"
            else:
                add("pumpverity_get_monitoring_overview")
                intent = "fault_history_overview"
        elif any(word in text for word in ("model", "evaluation", "accuracy", "f1", "metric")):
            add("pumpverity_get_model_evaluation")
            intent = "model_evaluation"
        elif any(word in text for word in ("connectivity", "offline", "sync", "buffer", "online")):
            if pump_args:
                add("pumpverity_get_edge_connectivity", pump_args)
                intent = "connectivity"
            else:
                add("pumpverity_get_monitoring_overview")
                intent = "connectivity_overview"
        elif "alert" in text:
            if selected_alert:
                add("pumpverity_get_alert_details", {"alert_id": selected_alert})
                intent = "alert_details"
            elif pump_args:
                add("pumpverity_get_fault_history", pump_args)
                intent = "fault_history"
            else:
                add("pumpverity_get_monitoring_overview")
                intent = "alert_overview"
        elif pump_args:
            add("pumpverity_get_pump_status", pump_args)
            add("pumpverity_get_latest_prediction", sensor_args)
            intent = "pump_status"
        else:
            add("pumpverity_get_monitoring_overview")
            intent = "overview"

        return CopilotPlan(
            intent=intent,
            tool_calls=calls[:5],
            suggested_questions=_suggestions(intent),
        )


def _review_note(message: str) -> str:
    lowered = message.lower()
    for marker in ("note:", "notes:", "review note:", "because"):
        index = lowered.find(marker)
        if index >= 0:
            note = message[index + len(marker) :].strip(" .")
            if len(note) >= 3:
                return note[:4000]
    return (
        "Reviewed through the Engineering Copilot after inspecting the retained prediction "
        "and available sensor evidence."
    )


def _suggestions(intent: str) -> list[str]:
    mapping = {
        "explain_alert": [
            "What evidence is missing?",
            "Show sensor health",
            "Open historical trends",
        ],
        "pump_status": [
            "Why was the latest decision uncertain?",
            "Show sensor health",
            "Open Live Monitoring",
        ],
        "sensor_health": [
            "Explain the validation issues",
            "Show the vibration summary",
            "Is the latest reading fresh?",
        ],
        "vibration": [
            "How many windows are invalid?",
            "Show sensor health",
            "Open historical trends",
        ],
        "fault_history": ["Explain the latest event", "Open Alerts & Review"],
        "model_evaluation": [
            "Is this metric synthetic?",
            "What is the active model?",
            "Explain uncertainty",
        ],
        "connectivity": ["Is there a physical edge channel?", "Show data provenance"],
        "explain_uncertainty": ["Show sensor health", "Show fault history"],
    }
    return mapping.get(intent, ["What is the current monitoring status?"])


class OpenAICompatibleProvider(CopilotProvider):
    name = "openai_compatible"

    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.copilot_model
        self.base_url = settings.copilot_base_url.rstrip("/")
        self.api_key = (
            settings.copilot_api_key.get_secret_value()
            if settings.copilot_api_key is not None
            else ""
        )
        self.timeout = settings.copilot_timeout_seconds

    async def plan(
        self,
        *,
        message: str,
        context: CopilotPageContext,
        history: list[dict[str, str]],
        tools: list[Tool],
    ) -> CopilotPlan:
        if not self.base_url or not self.api_key:
            raise ProviderUnavailableError(
                "The configured LLM provider has no base URL or API key."
            )
        tool_catalog = [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema,
                "write_requires_confirmation": tool.name in WRITE_TOOL_NAMES,
            }
            for tool in tools
        ]
        system_prompt = (
            "You are a tool planner for PUMPVERITY AI, a pump condition-monitoring research "
            "prototype. Return JSON only with keys intent, tool_calls and suggested_questions. "
            "Each tool call must be one of the approved MCP tools and arguments must satisfy its "
            "JSON schema. Never invent readings, alerts, models or hardware state. Do not put "
            "actor_id in arguments. Write tools are proposals and will require separate user "
            "confirmation. Use only read tools unless the user explicitly asks for the write "
            "action. Prefer the selected pump/alert context. Do not answer with free-form "
            "diagnostic claims; the backend composes the grounded response."
        )
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "message": message,
                            "context": context.model_dump(by_alias=True),
                            "history": history[-12:],
                            "approved_tools": tool_catalog,
                        },
                        default=str,
                    ),
                },
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
                response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            parsed = json.loads(_strip_json_fence(content))
            plan = CopilotPlan.model_validate(parsed)
        except Exception as exc:
            logger.warning("llm_provider_failed", extra={"error": str(exc)})
            raise ProviderUnavailableError("The configured LLM provider is unavailable.") from exc
        allowed = READ_TOOL_NAMES | WRITE_TOOL_NAMES
        plan.tool_calls = [call for call in plan.tool_calls if call.name in allowed][:5]
        return plan


def _strip_json_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    return text.strip()


def build_provider() -> CopilotProvider:
    settings = get_settings()
    if settings.copilot_provider == "openai_compatible":
        return OpenAICompatibleProvider()
    return DeterministicProvider()


def provider_status(provider: CopilotProvider) -> dict[str, Any]:
    return {
        "provider": provider.name,
        "model": provider.model,
        "configured": not (
            isinstance(provider, OpenAICompatibleProvider)
            and (not provider.base_url or not provider.api_key)
        ),
    }

