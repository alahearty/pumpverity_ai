from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app import __version__
from app.api.deps import get_current_user
from app.core.config import get_settings
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName

router = APIRouter(tags=["System"])
settings = get_settings()


@router.get("/health", summary="Liveness and database readiness")
def health(db: Session = Depends(get_db)):
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    payload = {
        "status": "ok" if database_status == "ok" else "degraded",
        "service": settings.project_name,
        "version": __version__,
        "environment": settings.environment,
        "database": database_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if database_status != "ok":
        return JSONResponse(status_code=503, content=payload)
    return payload


@router.get("/system/info", summary="Non-sensitive runtime information")
def system_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, object]:
    return {
        "project": settings.project_name,
        "version": __version__,
        "environment": settings.environment,
        "api_prefix": settings.api_v1_prefix,
        "auth_scheme": "access-token + httpOnly refresh cookie",
        "access_token_minutes": settings.access_token_minutes,
        "refresh_token_days": settings.refresh_token_days,
        "database_dialect": db.bind.dialect.name if db.bind is not None else "unknown",
        "role": RoleName(current_user.role.name).value,
        "data_mode": "research-prototype",
    }
