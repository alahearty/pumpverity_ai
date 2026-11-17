import logging
from datetime import UTC, datetime
from statistics import fmean

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from app.copilot.contracts import (
    READ_ROLES,
    REPORT_ROLES,
    WRITE_ROLES,
)
from app.copilot.outputs import (
    AlertDetailsOutput,
    AlertReviewSummary,
    EdgeConnectivityOutput,
    EvaluationEvidence,
    FaultEventSummary,
    FaultHistoryOutput,
    ModelEvaluationOutput,
    MonitoringOverviewOutput,
    PredictionEvidence,
    PumpSensorStatus,
    PumpStatusOutput,
    SensorHealthOutput,
    SensorHealthSummary,
    VibrationPoint,
    VibrationSummaryOutput,
    WriteResultOutput,
)
from app.copilot.runtime import session_scope
from app.core.errors import ApiError
from app.db.models import Pump, User
from app.domain.enums import ReviewAction, RoleName
from app.schemas.alerts import AlertPublic, AlertReviewCreate
from app.schemas.predictions import PredictionPublic
from app.services import alerts as alert_service
from app.services import equipment as equipment_service
from app.services import models as model_service
from app.services import monitoring as monitoring_service
from app.services import predictions as prediction_service
from app.services.audit import record_audit

logger = logging.getLogger("pumpverity.copilot.mcp")


def _now() -> datetime:
    return datetime.now(UTC)


def _utc(value: datetime | None) -> datetime | None:
    return monitoring_service.as_utc(value)


def _actor(db, actor_id: str, allowed: set[RoleName]) -> User:
    user = db.execute(
        select(User).options(joinedload(User.role)).where(User.id == actor_id)
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise ToolError("UNAUTHENTICATED: the Copilot actor is not an active user")
    role = RoleName(user.role.name)
    if role not in allowed:
        raise ToolError("FORBIDDEN: your role does not permit this Copilot tool")
    return user


def _resolve_pump(db, *, pump_id: str | None = None, pump_code: str | None = None) -> Pump:
    if bool(pump_id) == bool(pump_code):
        raise ToolError("PUMP_SELECTION_REQUIRED: provide exactly one of pump_id or pump_code")
    try:
        if pump_id:
            return equipment_service.get_pump_or_404(db, pump_id)
        pump = db.execute(
            select(Pump).where(func.lower(Pump.pump_code) == (pump_code or "").lower())
        ).scalar_one_or_none()
        if pump is None:
            raise ToolError(f"PUMP_NOT_FOUND: no pump matches {pump_code}")
        return equipment_service.get_pump_or_404(db, pump.id)
    except ApiError as exc:
        raise ToolError(f"{exc.code}: {exc.message}") from exc


def _resolve_sensor_id(
    db,
    pump: Pump,
    *,
    sensor_id: str | None,
) -> str:
    _pump, sensor = monitoring_service.resolve_pump_sensor(db, pump_id=pump.id, sensor_id=sensor_id)
    return sensor.id


def _prediction_evidence(
    prediction: PredictionPublic | None,
    *,
    pump,
    sensor_id: str,
    sensor_code: str,
    message: str,
) -> PredictionEvidence:
    if prediction is None:
        return PredictionEvidence(
            available=False,
            pump_id=pump.id,
            pump_code=pump.pump_code,
            sensor_id=sensor_id,
            sensor_code=sensor_code,
            message=message,
            generated_at=_now(),
        )
    return PredictionEvidence(
        available=True,
        pump_id=pump.id,
        pump_code=pump.pump_code,
        sensor_id=sensor_id,
        sensor_code=sensor_code,
        prediction_id=prediction.id,
        decision=prediction.decision,
        equipment_condition=prediction.equipment_condition,
        data_quality=prediction.data_quality,
        decision_score=prediction.decision_score,
        uncertainty_score=prediction.uncertainty_score,
        explanation=prediction.explanation,
        model_name=prediction.model.name if prediction.model else None,
        model_version=prediction.model.version if prediction.model else None,
        model_runtime=prediction.model.runtime.value if prediction.model else None,
        window_start=_utc(prediction.window_start),
        window_end=_utc(prediction.window_end),
        scenario=prediction.scenario,
        features=prediction.features,
        provenance=prediction.data_provenance,
        inferred_at=_utc(prediction.inferred_at),
        generated_at=_now(),
        message=message,
    )


def _latest_prediction(db, *, pump: Pump, sensor_id: str) -> PredictionPublic | None:
    predictions, _total = prediction_service.list_predictions(
        db,
        page=1,
        page_size=1,
        pump_id=pump.id,
        sensor_id=sensor_id,
    )
    if not predictions:
        return None
    return PredictionPublic.from_prediction(predictions[0])


def _sensor_health_summary(health) -> SensorHealthSummary:
    return SensorHealthSummary(
        sensor_id=health.sensor_id,
        sensor_code=health.sensor_code,
        sensor_type=health.sensor_type,
        is_active=health.is_active,
        sampling_rate_hz=health.sampling_rate_hz,
        sampling_status=health.sampling_status,
        latest_quality=health.latest_quality,
        total_windows=health.total_windows,
        valid_windows=health.valid_windows,
        invalid_windows=health.invalid_windows,
        missing_window_gaps=health.missing_window_gaps,
        freshness_seconds=health.freshness_seconds,
        last_valid_reading_at=_utc(health.last_valid_reading_at),
        latest_rms_g=health.latest_rms,
        latest_peak_g=health.latest_peak_abs,
        provenance=health.provenance,
        connection_state=health.connection_state,
        validation_issues=health.latest_validation_issues,
    )


def _alert_prediction(alert) -> PredictionEvidence | None:
    if alert.prediction is None:
        return None
    prediction = PredictionPublic.from_prediction(alert.prediction)
    return _prediction_evidence(
        prediction,
        pump=alert.pump,
        sensor_id=alert.sensor_id,
        sensor_code=alert.sensor.sensor_code,
        message="Prediction evidence retained by the alert.",
    )


def _register_read_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="pumpverity_get_monitoring_overview",
        description=(
            "Return the authorised monitoring overview: equipment, active alerts, latest window, "
            "active model, evaluation provenance and data mode. Use when no pump is selected."
        ),
    )
    def get_monitoring_overview(actor_id: str) -> MonitoringOverviewOutput:
        """Return the current aggregate monitoring state with explicit provenance."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            overview = monitoring_service.get_overview(db)
            return MonitoringOverviewOutput(
                pumps_total=overview.pumps_total,
                pumps_active=overview.pumps_active,
                sensors_total=overview.sensors_total,
                active_alerts=overview.active_alerts,
                windows_total=overview.windows_total,
                valid_windows=overview.valid_windows,
                invalid_windows=overview.invalid_windows,
                equipment_condition=overview.equipment_condition,
                condition_available=overview.condition_available,
                data_quality=overview.data_quality,
                data_mode=overview.data_mode,
                active_model_name=overview.active_model.name if overview.active_model else None,
                active_model_version=(
                    overview.active_model.version if overview.active_model else None
                ),
                latest_evaluation_f1=(
                    overview.latest_evaluation.macro_f1 if overview.latest_evaluation else None
                ),
                latest_evaluation_provenance=(
                    overview.latest_evaluation.data_provenance
                    if overview.latest_evaluation
                    else None
                ),
                latest_window_at=_utc(overview.latest_window.window_end)
                if overview.latest_window
                else None,
                latest_prediction_decision=(
                    overview.latest_prediction.decision if overview.latest_prediction else None
                ),
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_get_pump_status",
        description=(
            "Return a pump's status, sensor summary, latest condition evidence and provenance. "
            "Provide either the internal pump_id or pump_code."
        ),
    )
    def get_pump_status(
        actor_id: str,
        pump_id: str | None = None,
        pump_code: str | None = None,
    ) -> PumpStatusOutput:
        """Read pump status without changing any record."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            pump = _resolve_pump(db, pump_id=pump_id, pump_code=pump_code)
            snapshot = monitoring_service.get_live_snapshot(db, pump_id=pump.id, limit=10)
            health = monitoring_service.list_sensor_health(db, pump_id=pump.id)
            sensors = [
                PumpSensorStatus(
                    sensor_id=item.sensor_id,
                    sensor_code=item.sensor_code,
                    sensor_type=item.sensor_type,
                    is_active=item.is_active,
                    sampling_rate_hz=item.sampling_rate_hz,
                    sampling_status=item.sampling_status,
                    latest_quality=item.latest_quality,
                    latest_rms_g=item.latest_rms,
                    invalid_windows=item.invalid_windows,
                    missing_window_gaps=item.missing_window_gaps,
                    last_valid_reading_at=_utc(item.last_valid_reading_at),
                    provenance=item.provenance,
                )
                for item in health
            ]
            latest = snapshot.latest_window
            return PumpStatusOutput(
                pump_id=pump.id,
                pump_code=pump.pump_code,
                pump_name=pump.name,
                pump_status=pump.status.value,
                location=pump.location,
                rated_speed_rpm=pump.rated_speed_rpm,
                sensors=sensors,
                equipment_condition=snapshot.equipment_condition,
                condition_available=snapshot.condition_available,
                data_quality=snapshot.data_quality,
                latest_prediction_decision=(
                    snapshot.latest_prediction.decision if snapshot.latest_prediction else None
                ),
                latest_window_at=_utc(latest.window_end) if latest else None,
                data_provenance=latest.data_provenance if latest else None,
                data_mode=snapshot.data_mode,
                edge_connectivity=(
                    snapshot.edge_connectivity.value
                    if snapshot.edge_connectivity
                    else "NO_LIVE_CHANNEL"
                ),
                edge_note=snapshot.edge_note,
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_get_sensor_health",
        description=(
            "Return sensor validity, freshness, missing-gap and validation-issue diagnostics. "
            "This is signal quality, not a machine fault diagnosis."
        ),
    )
    def get_sensor_health(
        actor_id: str,
        pump_id: str | None = None,
        pump_code: str | None = None,
        sensor_id: str | None = None,
    ) -> SensorHealthOutput:
        """Read sensor diagnostic state without inferring an equipment fault."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            pump = _resolve_pump(db, pump_id=pump_id, pump_code=pump_code)
            health = monitoring_service.list_sensor_health(db, pump_id=pump.id)
            if sensor_id is not None:
                health = [item for item in health if item.sensor_id == sensor_id]
                if not health:
                    raise ToolError("SENSOR_NOT_FOUND: sensor does not belong to this pump")
            sensors = [_sensor_health_summary(item) for item in health]
            return SensorHealthOutput(
                available=bool(sensors),
                pump_id=pump.id,
                pump_code=pump.pump_code,
                sensors=sensors,
                message=(
                    "Sensor diagnostics retrieved from persisted windows."
                    if sensors
                    else "No sensor is registered for this pump."
                ),
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_get_latest_prediction",
        description=(
            "Return the latest persisted AI prediction with decision, uncertainty, model version, "
            "window interval and provenance. Scores are not failure probabilities."
        ),
    )
    def get_latest_prediction(
        actor_id: str,
        pump_id: str | None = None,
        pump_code: str | None = None,
        sensor_id: str | None = None,
    ) -> PredictionEvidence:
        """Read the latest prediction without generating or altering inference."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            pump = _resolve_pump(db, pump_id=pump_id, pump_code=pump_code)
            resolved_sensor_id = _resolve_sensor_id(db, pump, sensor_id=sensor_id)
            _pump, sensor = monitoring_service.resolve_pump_sensor(
                db, pump_id=pump.id, sensor_id=resolved_sensor_id
            )
            prediction = _latest_prediction(db, pump=pump, sensor_id=sensor.id)
            return _prediction_evidence(
                prediction,
                pump=pump,
                sensor_id=sensor.id,
                sensor_code=sensor.sensor_code,
                message=(
                    "Latest persisted prediction retrieved."
                    if prediction
                    else "No persisted prediction exists for this sensor."
                ),
            )

    @mcp.tool(
        name="pumpverity_get_fault_history",
        description=(
            "Return recent fault, uncertain and sensor-invalid alert events for a pump with "
            "status, model identity and provenance."
        ),
    )
    def get_fault_history(
        actor_id: str,
        pump_id: str | None = None,
        pump_code: str | None = None,
        sensor_id: str | None = None,
        limit: int = 20,
    ) -> FaultHistoryOutput:
        """Read historical alert-backed condition events."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            pump = _resolve_pump(db, pump_id=pump_id, pump_code=pump_code)
            bounded_limit = max(1, min(limit, 50))
            items, total = alert_service.list_alerts(
                db,
                page=1,
                page_size=bounded_limit,
                pump_id=pump.id,
                sensor_id=sensor_id,
            )
            events = []
            for item in items:
                public = AlertPublic.from_alert(item)
                events.append(
                    FaultEventSummary(
                        alert_id=public.id,
                        category=public.category,
                        severity=public.severity,
                        status=public.status,
                        title=public.title,
                        decision=public.decision,
                        window_start=_utc(public.window_start),
                        window_end=_utc(public.window_end),
                        created_at=_utc(public.created_at) or public.created_at,
                        model_name=public.model_name,
                        model_version=public.model_version,
                        review_count=public.review_count,
                        provenance=public.data_provenance,
                    )
                )
            return FaultHistoryOutput(
                available=bool(events),
                pump_id=pump.id,
                pump_code=pump.pump_code,
                events=events,
                total_events=total,
                message=(
                    "Recent alert-backed condition events retrieved."
                    if events
                    else "No alert-backed condition events exist for this pump."
                ),
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_get_vibration_summary",
        description=(
            "Return an aggregated vibration summary in g units from persisted windows, including "
            "valid/invalid counts, range, latest peak and provenance. Raw waveform is not returned."
        ),
    )
    def get_vibration_summary(
        actor_id: str,
        pump_id: str | None = None,
        pump_code: str | None = None,
        sensor_id: str | None = None,
        limit: int = 50,
    ) -> VibrationSummaryOutput:
        """Read an aggregated vibration trend, never a bare number without a unit."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            pump = _resolve_pump(db, pump_id=pump_id, pump_code=pump_code)
            bounded_limit = max(5, min(limit, 100))
            snapshot = monitoring_service.get_live_snapshot(
                db, pump_id=pump.id, sensor_id=sensor_id, limit=bounded_limit
            )
            windows = snapshot.recent_windows
            valid = [window for window in windows if window.quality_status == "VALID"]
            rms_values = [window.rms for window in valid if window.rms is not None]
            latest_valid = next(
                (window for window in reversed(windows) if window.quality_status == "VALID"),
                None,
            )
            units = snapshot.latest_window.units if snapshot.latest_window else None
            if units not in {None, "g"}:
                units = "g"
            points = [
                VibrationPoint(
                    timestamp=_utc(window.window_start) or window.window_start,
                    rms_g=window.rms,
                    peak_g=window.peak_abs,
                    quality=window.quality_status,
                    provenance=window.data_provenance,
                    scenario=window.scenario,
                )
                for window in windows
            ]
            return VibrationSummaryOutput(
                available=bool(windows),
                pump_id=pump.id,
                pump_code=pump.pump_code,
                sensor_id=snapshot.sensor_id,
                sensor_code=snapshot.sensor_code,
                units="g",
                sampling_rate_hz=(
                    snapshot.latest_window.sampling_rate_hz
                    if snapshot.latest_window
                    else snapshot.sensor_health.sampling_rate_hz
                ),
                window_count=len(windows),
                valid_window_count=len(valid),
                invalid_window_count=len(windows) - len(valid),
                latest_rms_g=latest_valid.rms if latest_valid else None,
                mean_rms_g=fmean(rms_values) if rms_values else None,
                min_rms_g=min(rms_values) if rms_values else None,
                max_rms_g=max(rms_values) if rms_values else None,
                latest_peak_g=latest_valid.peak_abs if latest_valid else None,
                latest_window_at=(_utc(windows[-1].window_end) if windows else None),
                provenance=windows[-1].data_provenance if windows else None,
                points=points,
                message=(
                    "Vibration summary computed from persisted windows in g."
                    if windows
                    else "No persisted windows exist for this sensor."
                ),
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_get_model_evaluation",
        description=(
            "Return a model version and its latest evaluation evidence. Synthetic metrics are "
            "never real-pump accuracy claims. If model_id is omitted, the active model is used."
        ),
    )
    def get_model_evaluation(actor_id: str, model_id: str | None = None) -> ModelEvaluationOutput:
        """Read model metadata and evaluation evidence without executing a model."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            model = (
                model_service.get_model_or_404(db, model_id)
                if model_id
                else model_service.get_active_model(db)
            )
            if model is None:
                return ModelEvaluationOutput(
                    available=False,
                    model_id=None,
                    model_code=None,
                    name=None,
                    version=None,
                    status=None,
                    runtime=None,
                    training_dataset_version=None,
                    evaluation_dataset=None,
                    feature_contract=None,
                    evaluation=None,
                    message="No active model exists. Register, validate and activate one first.",
                    generated_at=_now(),
                )
            evaluations = model_service.sorted_evaluations(model)
            latest = evaluations[0] if evaluations else None
            evaluation = (
                EvaluationEvidence(
                    dataset_name=latest.dataset_name,
                    dataset_version=latest.dataset_version,
                    provenance=latest.data_provenance,
                    protocol=latest.evaluation_protocol,
                    sample_count=latest.sample_count,
                    balanced_accuracy=latest.balanced_accuracy,
                    macro_f1=latest.macro_f1,
                    is_verified=latest.is_verified,
                    evaluated_at=_utc(latest.evaluated_at) or latest.evaluated_at,
                    metrics=latest.metrics,
                    notes=latest.notes,
                )
                if latest
                else None
            )
            return ModelEvaluationOutput(
                available=True,
                model_id=model.id,
                model_code=model.model_code,
                name=model.name,
                version=model.version,
                status=model.status.value,
                runtime=model.runtime.value,
                training_dataset_version=model.training_dataset_version,
                evaluation_dataset=model.evaluation_dataset,
                feature_contract=model.feature_contract,
                evaluation=evaluation,
                message=(
                    "Model evaluation evidence retrieved."
                    if evaluation
                    else "The model has no evaluation evidence."
                ),
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_get_alert_details",
        description=(
            "Return an alert, its retained prediction evidence and ordered engineer reviews. "
            "Engineer reviews are not verified ground truth."
        ),
    )
    def get_alert_details(actor_id: str, alert_id: str) -> AlertDetailsOutput:
        """Read alert evidence without changing its review state."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            try:
                alert = alert_service.get_alert_or_404(db, alert_id)
            except ApiError as exc:
                raise ToolError(f"{exc.code}: {exc.message}") from exc
            reviews = [
                AlertReviewSummary(
                    review_id=review.id,
                    reviewer_name=review.reviewer.full_name
                    if review.reviewer
                    else "Unknown reviewer",
                    action=review.action.value,
                    reviewed_label=review.reviewed_label,
                    notes=review.notes,
                    label_source=review.label_source.value,
                    is_verified_ground_truth=review.is_verified_ground_truth,
                    created_at=_utc(review.created_at) or review.created_at,
                )
                for review in sorted(alert.reviews, key=lambda item: item.created_at)[:50]
            ]
            return AlertDetailsOutput(
                alert_id=alert.id,
                pump_id=alert.pump_id,
                pump_code=alert.pump.pump_code,
                sensor_id=alert.sensor_id,
                sensor_code=alert.sensor.sensor_code,
                category=alert.category,
                severity=alert.severity,
                status=alert.status,
                title=alert.title,
                description=alert.description,
                provenance=alert.data_provenance,
                assigned_reviewer_name=(
                    alert.assigned_reviewer.full_name if alert.assigned_reviewer else None
                ),
                acknowledged_at=_utc(alert.acknowledged_at),
                closed_at=_utc(alert.closed_at),
                created_at=_utc(alert.created_at) or alert.created_at,
                prediction=_alert_prediction(alert),
                reviews=reviews,
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_get_edge_connectivity",
        description=(
            "Return data mode, buffering state and last reading times. API connectivity is not "
            "physical edge-device connectivity."
        ),
    )
    def get_edge_connectivity(
        actor_id: str,
        pump_id: str | None = None,
        pump_code: str | None = None,
    ) -> EdgeConnectivityOutput:
        """Read connectivity/synchronisation state without probing hardware."""
        with session_scope() as db:
            _actor(db, actor_id, READ_ROLES)
            pump = _resolve_pump(db, pump_id=pump_id, pump_code=pump_code)
            snapshot = monitoring_service.get_live_snapshot(db, pump_id=pump.id, limit=10)
            return EdgeConnectivityOutput(
                pump_id=pump.id,
                pump_code=pump.pump_code,
                edge_connectivity=(
                    snapshot.edge_connectivity.value
                    if snapshot.edge_connectivity
                    else "NO_LIVE_CHANNEL"
                ),
                data_mode=snapshot.data_mode,
                buffering_state=snapshot.buffering_state,
                last_window_at=(
                    _utc(snapshot.latest_window.window_end) if snapshot.latest_window else None
                ),
                last_valid_window_at=(
                    _utc(snapshot.sensor_health.last_valid_reading_at)
                    if snapshot.sensor_health
                    else None
                ),
                api_note=snapshot.edge_note,
                generated_at=_now(),
            )


def _register_write_tools(mcp: FastMCP) -> None:
    @mcp.tool(
        name="pumpverity_acknowledge_alert",
        description=(
            "Acknowledge an alert as the authenticated engineer/reviewer. This changes workflow "
            "state only; the original prediction is preserved."
        ),
    )
    def acknowledge_alert(actor_id: str, alert_id: str) -> WriteResultOutput:
        """Acknowledge an alert after explicit user approval."""
        with session_scope() as db:
            actor = _actor(db, actor_id, WRITE_ROLES)
            try:
                alert = alert_service.acknowledge_alert(db, alert_id, actor, None)
            except ApiError as exc:
                raise ToolError(f"{exc.code}: {exc.message}") from exc
            record_audit(
                db,
                action="COPILOT_TOOL_COMPLETED",
                actor=actor,
                entity_type="alert",
                entity_id=alert.id,
                after={"tool": "pumpverity_acknowledge_alert", "status": alert.status.value},
            )
            db.commit()
            return WriteResultOutput(
                success=True,
                action="ACKNOWLEDGE_ALERT",
                target_id=alert.id,
                status=alert.status.value,
                message="Alert acknowledged. Original AI prediction retained.",
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_mark_alert_reviewed",
        description=(
            "Append an engineering review to an alert with notes. This does not confirm a fault "
            "or create verified ground truth."
        ),
    )
    def mark_alert_reviewed(actor_id: str, alert_id: str, notes: str) -> WriteResultOutput:
        """Mark an alert reviewed after explicit user approval."""
        with session_scope() as db:
            actor = _actor(db, actor_id, WRITE_ROLES)
            try:
                review = alert_service.create_review(
                    db,
                    AlertReviewCreate(
                        alert_id=alert_id,
                        action=ReviewAction.REVIEW,
                        notes=notes,
                    ),
                    actor,
                    None,
                )
                alert = alert_service.get_alert_or_404(db, alert_id)
            except ApiError as exc:
                raise ToolError(f"{exc.code}: {exc.message}") from exc
            record_audit(
                db,
                action="COPILOT_TOOL_COMPLETED",
                actor=actor,
                entity_type="alert",
                entity_id=alert.id,
                after={"tool": "pumpverity_mark_alert_reviewed", "review_id": review.id},
            )
            db.commit()
            return WriteResultOutput(
                success=True,
                action="MARK_ALERT_REVIEWED",
                target_id=alert.id,
                status=alert.status.value,
                review_id=review.id,
                message=(
                    "Engineering review appended. It is not verified experimental ground truth."
                ),
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_add_engineering_note",
        description=(
            "Append an engineering note to an alert. This changes no AI prediction and does not "
            "confirm a label."
        ),
    )
    def add_engineering_note(actor_id: str, alert_id: str, notes: str) -> WriteResultOutput:
        """Append an engineering note after explicit user approval."""
        with session_scope() as db:
            actor = _actor(db, actor_id, WRITE_ROLES)
            try:
                review = alert_service.create_review(
                    db,
                    AlertReviewCreate(
                        alert_id=alert_id,
                        action=ReviewAction.ADD_NOTE,
                        notes=notes,
                    ),
                    actor,
                    None,
                )
                alert = alert_service.get_alert_or_404(db, alert_id)
            except ApiError as exc:
                raise ToolError(f"{exc.code}: {exc.message}") from exc
            record_audit(
                db,
                action="COPILOT_TOOL_COMPLETED",
                actor=actor,
                entity_type="alert",
                entity_id=alert.id,
                after={"tool": "pumpverity_add_engineering_note", "review_id": review.id},
            )
            db.commit()
            return WriteResultOutput(
                success=True,
                action="ADD_ENGINEERING_NOTE",
                target_id=alert.id,
                status=alert.status.value,
                review_id=review.id,
                message="Engineering note appended. The prediction remains unchanged.",
                generated_at=_now(),
            )

    @mcp.tool(
        name="pumpverity_generate_monitoring_report",
        description=(
            "Generate a traceable JSON monitoring report for a pump from persisted data. The "
            "report explicitly discloses simulated provenance."
        ),
    )
    def generate_monitoring_report(
        actor_id: str,
        pump_id: str | None = None,
        pump_code: str | None = None,
    ) -> WriteResultOutput:
        """Generate a report artifact after explicit user approval."""
        from app.services import reports as report_service

        with session_scope() as db:
            actor = _actor(db, actor_id, REPORT_ROLES)
            pump = _resolve_pump(db, pump_id=pump_id, pump_code=pump_code)
            try:
                report = report_service.generate_monitoring_report(db, pump=pump, actor=actor)
            except ApiError as exc:
                raise ToolError(f"{exc.code}: {exc.message}") from exc
            record_audit(
                db,
                action="COPILOT_TOOL_COMPLETED",
                actor=actor,
                entity_type="report_job",
                entity_id=report["report_id"],
                after={"tool": "pumpverity_generate_monitoring_report"},
            )
            db.commit()
            return WriteResultOutput(
                success=True,
                action="GENERATE_MONITORING_REPORT",
                target_id=report["report_id"],
                status=report["status"],
                report_id=report["report_id"],
                report_path=report["file_name"],
                report_sha256=report["sha256"],
                includes_simulated_data=report["includes_simulated_data"],
                message="Monitoring report generated with provenance disclosure.",
                generated_at=_now(),
            )


def create_mcp_server() -> FastMCP:
    mcp = FastMCP(
        name="PUMPVERITY Engineering Copilot MCP",
        instructions=(
            "Read-only monitoring and controlled engineering-review tools for PUMPVERITY AI. "
            "All data is provenance-labelled. Never treat model scores as failure probabilities "
            "or engineer reviews as verified ground truth."
        ),
        stateless_http=True,
        json_response=True,
        streamable_http_path="/mcp",
    )
    _register_read_tools(mcp)
    _register_write_tools(mcp)
    return mcp


mcp_server = create_mcp_server()
