from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_optional_current_user
from app.core.config import get_settings
from app.core.errors import ApiError
from app.core.security import InvalidTokenError, decode_token
from app.db.models import User, utcnow
from app.db.session import get_db
from app.domain.enums import RoleName
from app.schemas.auth import LoginRequest, TokenResponse, UserPublic
from app.schemas.common import MessageResponse
from app.services.audit import record_audit
from app.services.auth import authenticate_user, issue_token_pair

router = APIRouter(prefix="/auth", tags=["Authentication"])
settings = get_settings()


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=token,
        max_age=settings.refresh_token_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        path=settings.refresh_cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate with email/username and password",
)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    user = authenticate_user(db, payload.identifier, payload.password)
    if user is None:
        record_audit(
            db,
            action="AUTH_LOGIN_FAILED",
            actor_label=payload.identifier.strip()[:255],
            entity_type="user",
            request=request,
        )
        db.commit()
        raise ApiError(
            status_code=401,
            code="INVALID_CREDENTIALS",
            message="Invalid email/username or password.",
        )

    user.last_login_at = utcnow()
    record_audit(
        db,
        action="AUTH_LOGIN_SUCCEEDED",
        actor=user,
        entity_type="user",
        entity_id=user.id,
        request=request,
    )
    db.commit()

    access, refresh, expires_in = issue_token_pair(user)
    _set_refresh_cookie(response, refresh)
    return TokenResponse(
        access_token=access,
        expires_in=expires_in,
        user=UserPublic.from_user(user),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange the HttpOnly refresh cookie for a new access token",
)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> TokenResponse:
    token = request.cookies.get(settings.refresh_cookie_name)
    if not token:
        raise ApiError(
            status_code=401,
            code="SESSION_EXPIRED",
            message="No active session was found.",
        )
    try:
        payload = decode_token(token, "refresh")
    except InvalidTokenError as exc:
        raise ApiError(
            status_code=401,
            code="SESSION_EXPIRED",
            message="Session expired. Please sign in again.",
        ) from exc

    user = db.get(User, payload.get("sub"))
    if user is None or not user.is_active or payload.get("ver") != user.token_version:
        raise ApiError(
            status_code=401,
            code="SESSION_EXPIRED",
            message="Session expired. Please sign in again.",
        )

    access, new_refresh, expires_in = issue_token_pair(user)
    _set_refresh_cookie(response, new_refresh)
    return TokenResponse(
        access_token=access,
        expires_in=expires_in,
        user=UserPublic.from_user(user),
    )


@router.post("/logout", response_model=MessageResponse, summary="End the current session")
def logout(
    request: Request,
    response: Response,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
) -> MessageResponse:
    _clear_refresh_cookie(response)
    if current_user is not None:
        record_audit(
            db,
            action="AUTH_LOGOUT",
            actor=current_user,
            entity_type="user",
            entity_id=current_user.id,
            request=request,
        )
        db.commit()
    return MessageResponse(message="Signed out.")


@router.get("/me", response_model=UserPublic, summary="Return the authenticated account")
def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    return UserPublic.from_user(current_user)


@router.get("/roles", summary="List the roles supported by this deployment")
def list_roles(current_user: User = Depends(get_current_user)) -> list[dict[str, str]]:
    return [
        {"value": RoleName.ADMINISTRATOR.value, "label": "Administrator"},
        {"value": RoleName.ENGINEER.value, "label": "Engineer"},
        {"value": RoleName.RESEARCHER.value, "label": "Researcher"},
        {"value": RoleName.REVIEWER.value, "label": "Reviewer"},
    ]
