from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.common import Page
from app.schemas.reports import ReportPublic
from app.services import reports as report_service

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("", response_model=Page[ReportPublic], summary="List generated reports")
def list_reports(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Page[ReportPublic]:
    jobs, total = report_service.list_report_jobs(db, page=page, page_size=page_size)
    return Page[ReportPublic](
        items=[ReportPublic.from_job(job) for job in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{report_id}", response_model=ReportPublic, summary="Get report metadata")
def get_report(
    report_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReportPublic:
    return ReportPublic.from_job(report_service.get_report_or_404(db, report_id))


@router.get("/{report_id}/download", summary="Download a generated report")
def download_report(
    report_id: str,
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    job = report_service.get_report_or_404(db, report_id)
    path = report_service.report_file(job)
    return FileResponse(
        path,
        media_type="application/json",
        filename=job.file_path or f"{report_id}.json",
    )
