from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.logging import get_request_id
from app.db.models import AuditLog, User


def record_audit(
    db: Session,
    *,
    action: str,
    actor: User | None = None,
    actor_label: str | None = None,
    entity_type: str = "",
    entity_id: str | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    request: Request | None = None,
) -> AuditLog:
    request_id = get_request_id()
    ip_address = None
    user_agent = None
    if request is not None:
        request_id = getattr(request.state, "request_id", request_id)
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:255] or None

    entry = AuditLog(
        actor_user_id=actor.id if actor is not None else None,
        actor_label=actor_label or (actor.email if actor is not None else None),
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        before=before,
        after=after,
        ip_address=ip_address,
        user_agent=user_agent,
        request_id=request_id,
    )
    db.add(entry)
    return entry
