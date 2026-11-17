from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import (
    access_token_expires_in,
    create_access_token,
    create_refresh_token,
    verify_dummy_password,
    verify_password,
)
from app.db.models import User
from app.domain.enums import RoleName

settings = get_settings()


def find_user_by_identifier(db: Session, identifier: str) -> User | None:
    normalized = identifier.strip().lower()
    if not normalized:
        return None
    stmt = (
        select(User)
        .options(joinedload(User.role))
        .where(
            or_(
                func.lower(User.email) == normalized,
                func.lower(User.username) == normalized,
            )
        )
    )
    return db.execute(stmt).scalar_one_or_none()


def authenticate_user(db: Session, identifier: str, password: str) -> User | None:
    user = find_user_by_identifier(db, identifier)
    if user is None:
        verify_dummy_password(password)
        return None
    if not verify_password(password, user.password_hash):
        return None
    if not user.is_active:
        return None
    return user


def issue_token_pair(user: User) -> tuple[str, str, int]:
    role = RoleName(user.role.name)
    access = create_access_token(user.id, role.value, user.token_version)
    refresh = create_refresh_token(user.id, role.value, user.token_version)
    return access, refresh, access_token_expires_in()
