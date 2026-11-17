from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import require_roles
from app.db.models import Role, User
from app.db.session import get_db
from app.domain.enums import RoleName
from app.schemas.auth import UserPublic
from app.schemas.common import Page

router = APIRouter(prefix="/users", tags=["Users"])

_ADMIN_ONLY = require_roles(RoleName.ADMINISTRATOR)


@router.get(
    "",
    response_model=Page[UserPublic],
    summary="List accounts (administrator only)",
)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    role: RoleName | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    _: User = Depends(_ADMIN_ONLY),
    db: Session = Depends(get_db),
) -> Page[UserPublic]:
    filters = []
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            or_(
                User.email.ilike(pattern),
                User.username.ilike(pattern),
                User.full_name.ilike(pattern),
            )
        )
    if role is not None:
        filters.append(Role.name == role)
    if is_active is not None:
        filters.append(User.is_active == is_active)

    count_stmt = select(func.count(User.id)).select_from(User)
    list_stmt = select(User).options(joinedload(User.role))
    if role is not None:
        count_stmt = count_stmt.join(Role, User.role_id == Role.id)
        list_stmt = list_stmt.join(Role, User.role_id == Role.id)
    if filters:
        count_stmt = count_stmt.where(*filters)
        list_stmt = list_stmt.where(*filters)

    total = db.execute(count_stmt).scalar_one()
    users = (
        db.execute(
            list_stmt.order_by(User.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .scalars()
        .all()
    )
    return Page[UserPublic](
        items=[UserPublic.from_user(user) for user in users],
        total=total,
        page=page,
        page_size=page_size,
    )
