import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import SessionLocal, get_db
from app.schemas.monitoring import LiveSnapshot, MonitoringOverview
from app.schemas.predictions import PredictionPublic
from app.services import monitoring as monitoring_service
from app.services import predictions as prediction_service

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

SSE_POLL_SECONDS = 1.0
SSE_HEARTBEAT_SECONDS = 15.0


def _sse_message(event: str, data: dict[str, Any], event_id: str | None = None) -> str:
    lines = []
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    lines.append(f"data: {json.dumps(data, separators=(',', ':'))}")
    return "\n".join(lines) + "\n\n"


def _poll_windows(
    *,
    pump_id: str,
    sensor_id: str | None,
    since: datetime,
) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        windows = monitoring_service.windows_since(
            db, pump_id=pump_id, sensor_id=sensor_id, since=since
        )
        results = []
        for window in windows:
            results.append(
                {
                    "window_id": window.id,
                    "created_at": monitoring_service.as_utc(window.created_at),
                    "event": monitoring_service.stream_window_event(window),
                }
            )
        return results


def _poll_predictions(
    *,
    pump_id: str,
    sensor_id: str | None,
    since: datetime,
) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        predictions = prediction_service.predictions_since(
            db, pump_id=pump_id, sensor_id=sensor_id, since=since
        )
        results = []
        for prediction in predictions:
            payload = PredictionPublic.from_prediction(prediction)
            results.append(
                {
                    "prediction_id": prediction.id,
                    "inferred_at": monitoring_service.as_utc(prediction.inferred_at),
                    "payload": payload.model_dump(mode="json"),
                }
            )
        return results


@router.get(
    "/overview",
    response_model=MonitoringOverview,
    summary="Monitoring overview for the dashboard",
)
def overview(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonitoringOverview:
    return monitoring_service.get_overview(db)


@router.get(
    "/live",
    response_model=LiveSnapshot,
    summary="Latest persisted windows and sensor state for a pump",
)
def live_snapshot(
    pump_id: str = Query(min_length=1, max_length=36),
    sensor_id: str | None = Query(default=None, max_length=36),
    limit: int = Query(default=25, ge=1, le=100),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LiveSnapshot:
    return monitoring_service.get_live_snapshot(
        db, pump_id=pump_id, sensor_id=sensor_id, limit=limit
    )


@router.get(
    "/stream",
    summary="Authenticated Server-Sent Events stream for new windows",
    response_class=StreamingResponse,
)
async def stream(
    request: Request,
    pump_id: str = Query(min_length=1, max_length=36),
    sensor_id: str | None = Query(default=None, max_length=36),
    max_events: int | None = Query(default=None, ge=1, le=100),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    monitoring_service.resolve_pump_sensor(db, pump_id=pump_id, sensor_id=sensor_id)

    async def event_generator():
        since = datetime.now(UTC)
        prediction_since = since
        seen: set[str] = set()
        seen_predictions: set[str] = set()
        sent = 0
        last_heartbeat = time.monotonic()

        initial_heartbeat = {
            "event_id": str(uuid4()),
            "event_type": "heartbeat",
            "occurred_at": datetime.now(UTC).isoformat(),
            "payload_version": 1,
            "pump_id": pump_id,
            "payload": {"status": "connected"},
        }
        yield _sse_message("heartbeat", initial_heartbeat)
        sent += 1
        if max_events is not None and sent >= max_events:
            return

        while True:
            if await request.is_disconnected():
                break

            try:
                new_windows = await run_in_threadpool(
                    _poll_windows,
                    pump_id=pump_id,
                    sensor_id=sensor_id,
                    since=since,
                )
            except Exception:
                new_windows = []

            for item in new_windows:
                window_id = item["window_id"]
                created_at = item["created_at"]
                if created_at is not None and created_at > since:
                    since = created_at
                if window_id in seen:
                    continue
                seen.add(window_id)
                event = item["event"]
                envelope = {
                    "event_id": window_id,
                    "event_type": event["event_type"],
                    "occurred_at": event["occurred_at"],
                    "pump_id": event["pump_id"],
                    "payload_version": event["payload_version"],
                    "payload": event["payload"],
                }
                yield _sse_message(event["event_type"], envelope, window_id)
                sent += 1
                if max_events is not None and sent >= max_events:
                    return

            try:
                new_predictions = await run_in_threadpool(
                    _poll_predictions,
                    pump_id=pump_id,
                    sensor_id=sensor_id,
                    since=prediction_since,
                )
            except Exception:
                new_predictions = []

            for item in new_predictions:
                prediction_id = item["prediction_id"]
                inferred_at = item["inferred_at"]
                if inferred_at is not None and inferred_at > prediction_since:
                    prediction_since = inferred_at
                if prediction_id in seen_predictions:
                    continue
                seen_predictions.add(prediction_id)
                payload = item["payload"]
                envelope = {
                    "event_id": prediction_id,
                    "event_type": "prediction",
                    "occurred_at": payload.get("inferred_at"),
                    "pump_id": payload.get("pump_id"),
                    "payload_version": 1,
                    "payload": payload,
                }
                yield _sse_message("prediction", envelope, prediction_id)
                sent += 1
                if max_events is not None and sent >= max_events:
                    return

            now_monotonic = time.monotonic()
            if now_monotonic - last_heartbeat >= SSE_HEARTBEAT_SECONDS:
                heartbeat_id = str(uuid4())
                yield _sse_message(
                    "heartbeat",
                    {
                        "event_id": heartbeat_id,
                        "event_type": "heartbeat",
                        "occurred_at": datetime.now(UTC).isoformat(),
                        "payload_version": 1,
                        "pump_id": pump_id,
                        "payload": {"status": "connected"},
                    },
                )
                last_heartbeat = now_monotonic
                sent += 1
                if max_events is not None and sent >= max_events:
                    return

            if len(seen) > 1000:
                seen = set(list(seen)[-200:])
            if len(seen_predictions) > 1000:
                seen_predictions = set(list(seen_predictions)[-200:])
            await asyncio.sleep(SSE_POLL_SECONDS)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
