"""Presentation-mode scenario control.

The browser never generates data. It records which simulated scenario the presenter wants; the
separately running edge demo driver polls this state, generates provenance-tagged SIMULATED
windows through the normal acquisition/prediction API, and reports a heartbeat. Disabled unless
``PETROSENSE_DEMO_MODE=true``.
"""

from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.services.audit import record_audit

router = APIRouter(prefix="/demo", tags=["Demo"])

DRIVER_STALE_AFTER = timedelta(seconds=10)

PRESETS: list[dict[str, Any]] = [
    {
        "code": "normal",
        "label": "Healthy operation",
        "description": "Baseline running-speed vibration with low broadband noise.",
        "expected_outcome": "NORMAL",
        "scenario": "normal",
        "custom_amplitude_g": None,
    },
    {
        "code": "imbalance",
        "label": "Rotor imbalance",
        "description": "Elevated 1x running-speed component typical of mass imbalance.",
        "expected_outcome": "FAULT",
        "scenario": "imbalance",
        "custom_amplitude_g": None,
    },
    {
        "code": "cavitation",
        "label": "Cavitation",
        "description": "Broadband high-frequency energy with impulsive bursts.",
        "expected_outcome": "FAULT",
        "scenario": "cavitation",
        "custom_amplitude_g": None,
    },
    {
        "code": "weak_anomaly",
        "label": "Weak anomaly",
        "description": "Low-amplitude abnormal component; the model should abstain, not guess.",
        "expected_outcome": "UNCERTAIN",
        "scenario": "custom_abnormal",
        "custom_amplitude_g": 0.01,
    },
    {
        "code": "sensor_disconnect",
        "label": "Sensor disconnect",
        "description": "Flat-line signal; inference must be suppressed, not reported as healthy.",
        "expected_outcome": "SENSOR_INVALID",
        "scenario": "sensor_disconnect",
        "custom_amplitude_g": None,
    },
]
PRESET_CODES = {preset["code"] for preset in PRESETS}


class DemoControlUpdate(BaseModel):
    preset: str | None = Field(default=None, max_length=40)
    pump_code: str | None = Field(default=None, max_length=64)
    paused: bool | None = None


class DemoHeartbeat(BaseModel):
    preset: str | None = Field(default=None, max_length=40)
    pump_code: str | None = Field(default=None, max_length=64)
    session_id: str | None = Field(default=None, max_length=36)
    windows_streamed: int = Field(default=0, ge=0)
    last_decision: str | None = Field(default=None, max_length=32)
    message: str | None = Field(default=None, max_length=300)


class _DemoState:
    def __init__(self) -> None:
        self.lock = Lock()
        self.preset = "normal"
        self.pump_code: str | None = None
        self.paused = False
        self.updated_at = datetime.now(UTC)
        self.updated_by: str | None = None
        self.heartbeat: dict[str, Any] | None = None
        self.heartbeat_at: datetime | None = None


_state = _DemoState()


def _require_demo_mode() -> None:
    if not get_settings().demo_mode:
        raise ApiError(
            status_code=404,
            code="DEMO_MODE_DISABLED",
            message="Presentation mode is not enabled on this deployment.",
        )


def _snapshot() -> dict[str, Any]:
    enabled = get_settings().demo_mode
    with _state.lock:
        driver_online = (
            _state.heartbeat_at is not None
            and datetime.now(UTC) - _state.heartbeat_at < DRIVER_STALE_AFTER
        )
        return {
            "enabled": enabled,
            "preset": _state.preset,
            "pump_code": _state.pump_code,
            "paused": _state.paused,
            "updated_at": _state.updated_at.isoformat(),
            "updated_by": _state.updated_by,
            "driver_online": driver_online,
            "driver": _state.heartbeat,
            "driver_heartbeat_at": (
                _state.heartbeat_at.isoformat() if _state.heartbeat_at else None
            ),
            "presets": PRESETS if enabled else [],
        }


@router.get("/control", summary="Presentation-mode scenario state")
def get_control(_: User = Depends(get_current_user)) -> dict[str, Any]:
    return _snapshot()


@router.put("/control", summary="Select the simulated scenario streamed by the demo driver")
def update_control(
    payload: DemoControlUpdate,
    request: Request,
    user: User = Depends(require_roles(RoleName.ENGINEER)),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    _require_demo_mode()
    if payload.preset is not None and payload.preset not in PRESET_CODES:
        raise ApiError(
            status_code=422,
            code="UNKNOWN_PRESET",
            message=f"Unknown demo preset '{payload.preset}'.",
        )
    with _state.lock:
        before = {"preset": _state.preset, "pump_code": _state.pump_code, "paused": _state.paused}
        if payload.preset is not None:
            _state.preset = payload.preset
        if payload.pump_code is not None:
            _state.pump_code = payload.pump_code.strip().upper() or None
        if payload.paused is not None:
            _state.paused = payload.paused
        _state.updated_at = datetime.now(UTC)
        _state.updated_by = user.email
        after = {"preset": _state.preset, "pump_code": _state.pump_code, "paused": _state.paused}
    record_audit(
        db,
        action="DEMO_SCENARIO_CHANGED",
        actor=user,
        entity_type="demo_control",
        before=before,
        after=after,
        request=request,
    )
    db.commit()
    return _snapshot()


@router.post("/heartbeat", summary="Demo driver liveness report")
def heartbeat(
    payload: DemoHeartbeat,
    _: User = Depends(require_roles(RoleName.ENGINEER)),
) -> dict[str, Any]:
    _require_demo_mode()
    with _state.lock:
        _state.heartbeat = payload.model_dump()
        _state.heartbeat_at = datetime.now(UTC)
    return _snapshot()
