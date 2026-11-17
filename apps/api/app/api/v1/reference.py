from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.equipment import OperatingRegimePublic
from app.services.equipment import list_operating_regimes

router = APIRouter(tags=["Reference data"])


@router.get(
    "/operating-regimes",
    response_model=list[OperatingRegimePublic],
    summary="List operating regimes",
)
def get_operating_regimes(
    _current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[OperatingRegimePublic]:
    return [
        OperatingRegimePublic.model_validate(regime)
        for regime in list_operating_regimes(db)
    ]
