from collections.abc import Callable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import ApiError
from app.core.security import InvalidTokenError, decode_token
from app.db.models import User
from app.db.session import get_db
from app.domain.enums import RoleName

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(message: str = "Authentication required.") -> ApiError:
    return ApiError(
        status_code=401,
        code="UNAUTHENTICATED",
        message=message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized()
    try:
        payload = decode_token(credentials.credentials, "access")
    except InvalidTokenError as exc:
        raise _unauthorized("Session expired or token invalid.") from exc

    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active:
        raise _unauthorized("Session expired or account unavailable.")
    if payload.get("ver") != user.token_version:
        raise _unauthorized("Session has been revoked.")
    return user


def get_optional_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    try:
        payload = decode_token(credentials.credentials, "access")
    except InvalidTokenError:
        return None
    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active or payload.get("ver") != user.token_version:
        return None
    return user


def require_roles(*roles: RoleName) -> Callable[..., User]:
    allowed = {role.value for role in roles}

    def dependency(user: User = Depends(get_current_user)) -> User:
        role = RoleName(user.role.name)
        if role.value not in allowed and role != RoleName.ADMINISTRATOR:
            raise ApiError(
                status_code=403,
                code="FORBIDDEN",
                message="Your role does not permit this action.",
            )
        return user

    return dependency
