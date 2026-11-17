import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.models import Pump, ReportJob, User
from app.domain.enums import ReportStatus, ReportType
from app.schemas.alerts import AlertPublic
from app.services import alerts as alert_service
from app.services import monitoring as monitoring_service
from app.services.audit import record_audit


def generate_monitoring_report(
    db: Session,
    *,
    pump: Pump,
    actor: User,
) -> dict:
    settings = get_settings()
    snapshot = monitoring_service.get_live_snapshot(db, pump_id=pump.id, limit=100)
    alerts, alert_total = alert_service.list_alerts(
        db,
        page=1,
        page_size=100,
        pump_id=pump.id,
    )
    generated_at = datetime.now(UTC)
    alert_items = []
    for alert in alerts:
        public = AlertPublic.from_alert(alert)
        alert_items.append(
            {
                "alert_id": public.id,
                "category": public.category.value,
                "severity": public.severity.value,
                "status": public.status.value,
                "title": public.title,
                "prediction_id": public.prediction_id,
                "signal_window_id": public.signal_window_id,
                "decision": public.decision.value if public.decision else None,
                "model_name": public.model_name,
                "model_version": public.model_version,
                "data_provenance": public.data_provenance.value,
                "review_count": public.review_count,
                "created_at": public.created_at.isoformat(),
            }
        )
    includes_simulated = any(
        window.data_provenance.value == "SIMULATED" for window in snapshot.recent_windows
    ) or any(alert.data_provenance.value == "SIMULATED" for alert in alerts)
    report = {
        "report_type": ReportType.MONITORING_SUMMARY.value,
        "generated_at": generated_at.isoformat(),
        "requested_by": actor.full_name,
        "pump": {
            "pump_id": pump.id,
            "pump_code": pump.pump_code,
            "name": pump.name,
            "location": pump.location,
            "rated_speed_rpm": pump.rated_speed_rpm,
            "status": pump.status.value,
        },
        "data_mode": snapshot.data_mode,
        "includes_simulated_data": includes_simulated,
        "provenance_notice": (
            "This report contains persisted data with explicit provenance. Simulated records are "
            "not experimental measurements, industrial diagnoses or verified ground truth."
        ),
        "connectivity": {
            "edge_connectivity": snapshot.edge_connectivity.value
            if snapshot.edge_connectivity
            else "NO_LIVE_CHANNEL",
            "edge_note": snapshot.edge_note,
            "buffering_state": snapshot.buffering_state,
        },
        "latest_prediction": (
            snapshot.latest_prediction.model_dump(mode="json")
            if snapshot.latest_prediction
            else None
        ),
        "sensor_health": snapshot.sensor_health.model_dump(mode="json"),
        "recent_windows": [
            window.model_dump(mode="json") for window in snapshot.recent_windows[-100:]
        ],
        "alerts": {
            "total": alert_total,
            "returned": len(alert_items),
            "items": alert_items,
        },
    }
    report_id = str(uuid4())
    reports_dir = Path(settings.reports_directory)
    reports_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"monitoring-{report_id}.json"
    path = reports_dir / file_name
    content = json.dumps(report, indent=2, ensure_ascii=True)
    encoded = content.encode("utf-8")
    path.write_bytes(encoded)
    digest = hashlib.sha256(encoded).hexdigest()
    job = ReportJob(
        id=report_id,
        report_type=ReportType.MONITORING_SUMMARY,
        status=ReportStatus.COMPLETED,
        requested_by_id=actor.id,
        parameters={"pump_id": pump.id, "pump_code": pump.pump_code},
        includes_simulated_data=includes_simulated,
        file_path=file_name,
        file_sha256=digest,
        created_at=generated_at,
        started_at=generated_at,
        completed_at=datetime.now(UTC),
    )
    db.add(job)
    db.flush()
    record_audit(
        db,
        action="REPORT_GENERATED",
        actor=actor,
        entity_type="report_job",
        entity_id=report_id,
        after={
            "report_type": ReportType.MONITORING_SUMMARY.value,
            "file_sha256": digest,
            "includes_simulated_data": includes_simulated,
        },
    )
    db.commit()
    if not path.exists():
        raise ApiError(
            status_code=500,
            code="REPORT_FILE_MISSING",
            message="Report file could not be stored.",
        )
    return {
        "report_id": report_id,
        "status": job.status.value,
        "file_name": file_name,
        "sha256": digest,
        "includes_simulated_data": includes_simulated,
        "generated_at": generated_at,
    }


def list_report_jobs(
    db: Session, *, page: int, page_size: int
) -> tuple[list[ReportJob], int]:
    total = int(db.execute(select(func.count(ReportJob.id))).scalar_one())
    jobs = (
        db.execute(
            select(ReportJob)
            .options(joinedload(ReportJob.requested_by))
            .order_by(ReportJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return list(jobs), total


def get_report_or_404(db: Session, report_id: str) -> ReportJob:
    job = db.execute(
        select(ReportJob)
        .options(joinedload(ReportJob.requested_by))
        .where(ReportJob.id == report_id)
    ).scalar_one_or_none()
    if job is None:
        raise ApiError(status_code=404, code="REPORT_NOT_FOUND", message="Report not found.")
    return job


def report_file(job: ReportJob) -> Path:
    if not job.file_path:
        raise ApiError(
            status_code=409,
            code="REPORT_FILE_UNAVAILABLE",
            message="This report has no generated file.",
        )
    base = Path(get_settings().reports_directory).resolve()
    candidate = (base / job.file_path).resolve()
    if base not in candidate.parents or not candidate.is_file():
        raise ApiError(
            status_code=404,
            code="REPORT_FILE_NOT_FOUND",
            message="The report file is not available.",
        )
    return candidate

