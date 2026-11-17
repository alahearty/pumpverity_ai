from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any, Literal

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

settings = get_settings()
_password_hash = PasswordHash.recommended()

_DUMMY_HASH = _password_hash.hash("petrosense-dummy-password-not-for-login")


class InvalidTokenError(Exception):
    """Raised when a JWT is missing, malformed, expired or of the wrong type."""


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hash.verify(password, password_hash)
    except Exception:
        return False


def verify_dummy_password(password: str) -> None:
    """Spend comparable time when an account does not exist (limited timing mitigation)."""
    _password_hash.verify(password, _DUMMY_HASH)


def _create_token(
    *,
    subject: str,
    role: str,
    token_version: int,
    token_type: Literal["access", "refresh"],
    expires_delta: timedelta,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "ver": token_version,
        "type": token_type,
        "jti": token_urlsafe(16),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str, role: str, token_version: int) -> str:
    return _create_token(
        subject=subject,
        role=role,
        token_version=token_version,
        token_type="access",
        expires_delta=timedelta(minutes=settings.access_token_minutes),
    )


def create_refresh_token(subject: str, role: str, token_version: int) -> str:
    return _create_token(
        subject=subject,
        role=role,
        token_version=token_version,
        token_type="refresh",
        expires_delta=timedelta(days=settings.refresh_token_days),
    )


def decode_token(token: str, expected_type: Literal["access", "refresh"]) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub", "type"]},
        )
    except jwt.InvalidTokenError as exc:
        raise InvalidTokenError("Token is invalid or expired") from exc
    if payload.get("type") != expected_type:
        raise InvalidTokenError("Unexpected token type")
    return payload


def access_token_expires_in() -> int:
    return settings.access_token_minutes * 60
