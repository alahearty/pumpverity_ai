from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.db.models import ReportJob
from app.domain.enums import ReportStatus, ReportType


class ReportPublic(BaseModel):
    id: str
    report_type: ReportType
    status: ReportStatus
    requested_by_name: str | None
    parameters: dict[str, Any]
    includes_simulated_data: bool
    file_name: str | None
    file_sha256: str | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None

    @classmethod
    def from_job(cls, job: ReportJob) -> "ReportPublic":
        return cls(
            id=job.id,
            report_type=job.report_type,
            status=job.status,
            requested_by_name=job.requested_by.full_name if job.requested_by else None,
            parameters=job.parameters,
            includes_simulated_data=job.includes_simulated_data,
            file_name=job.file_path,
            file_sha256=job.file_sha256,
            error_message=job.error_message,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
