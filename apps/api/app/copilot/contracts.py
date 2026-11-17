from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.domain.enums import RoleName

READ_TOOL_NAMES = {
    "pumpverity_get_monitoring_overview",
    "pumpverity_get_pump_status",
    "pumpverity_get_sensor_health",
    "pumpverity_get_latest_prediction",
    "pumpverity_get_fault_history",
    "pumpverity_get_vibration_summary",
    "pumpverity_get_model_evaluation",
    "pumpverity_get_alert_details",
    "pumpverity_get_edge_connectivity",
}

WRITE_TOOL_NAMES = {
    "pumpverity_acknowledge_alert",
    "pumpverity_mark_alert_reviewed",
    "pumpverity_add_engineering_note",
    "pumpverity_generate_monitoring_report",
}

READ_ROLES = {
    RoleName.ADMINISTRATOR,
    RoleName.ENGINEER,
    RoleName.RESEARCHER,
    RoleName.REVIEWER,
}

WRITE_ROLES = {
    RoleName.ADMINISTRATOR,
    RoleName.ENGINEER,
    RoleName.REVIEWER,
}

REPORT_ROLES = {
    RoleName.ADMINISTRATOR,
    RoleName.ENGINEER,
    RoleName.RESEARCHER,
    RoleName.REVIEWER,
}

SCREEN_NAMES = {
    "Login",
    "Dashboard",
    "Pump Registry",
    "Live Monitoring",
    "AI Analysis",
    "Alerts & Review",
    "Historical Trends",
    "Reports & Exports",
    "Model Registry",
    "Sensor Health",
    "System Settings",
    "User Management",
}


class CopilotPageContext(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    route: str = Field(default="/dashboard", max_length=300)
    screen_name: str = Field(default="Dashboard", max_length=80)
    selected_pump_id: str | None = Field(default=None, max_length=36)
    selected_sensor_id: str | None = Field(default=None, max_length=36)
    selected_alert_id: str | None = Field(default=None, max_length=36)
    active_model_version: str | None = Field(default=None, max_length=40)
    operating_regime: str | None = Field(default=None, max_length=40)
    monitoring_mode: Literal["SIMULATED", "EXPERIMENTAL"] = "SIMULATED"
    connectivity_status: str = Field(default="NO_LIVE_CHANNEL", max_length=48)

    @field_validator("route")
    @classmethod
    def validate_route(cls, value: str) -> str:
        if not value.startswith("/") or value.startswith("//"):
            raise ValueError("route must be an application-relative path")
        if "://" in value or "\\" in value:
            raise ValueError("route must not be an external URL")
        return value

    @field_validator("screen_name")
    @classmethod
    def validate_screen_name(cls, value: str) -> str:
        if value not in SCREEN_NAMES:
            raise ValueError("unknown application screen")
        return value


class CopilotActionType(StrEnum):
    NAVIGATE_TO_SCREEN = "NAVIGATE_TO_SCREEN"
    SELECT_PUMP = "SELECT_PUMP"
    OPEN_ALERT_DETAILS = "OPEN_ALERT_DETAILS"
    HIGHLIGHT_SENSOR = "HIGHLIGHT_SENSOR"
    OPEN_HISTORICAL_TRENDS = "OPEN_HISTORICAL_TRENDS"
    SET_MONITORING_TIME_RANGE = "SET_MONITORING_TIME_RANGE"
    OPEN_REPORT = "OPEN_REPORT"
    SHOW_CONFIRMATION_DIALOG = "SHOW_CONFIRMATION_DIALOG"


class CopilotAction(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    type: CopilotActionType
    payload: dict[str, Any] = Field(default_factory=dict)


class PlannedToolCall(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    arguments: dict[str, Any] = Field(default_factory=dict)


class CopilotPlan(BaseModel):
    intent: str = Field(default="general", max_length=80)
    tool_calls: list[PlannedToolCall] = Field(default_factory=list)
    suggested_questions: list[str] = Field(default_factory=list)


ALLOWED_NAVIGATION_PATHS = {
    "/dashboard",
    "/monitoring",
    "/analysis",
    "/alerts",
    "/pumps",
    "/sensors",
    "/history",
    "/reports",
    "/models",
    "/settings",
    "/users",
}
