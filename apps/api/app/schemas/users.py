from pydantic import BaseModel

from app.domain.enums import RoleName
from app.schemas.auth import UserPublic


class UserListFilters(BaseModel):
    q: str | None = None
    role: RoleName | None = None
    is_active: bool | None = None
    page: int = 1
    page_size: int = 25


__all__ = ["UserListFilters", "UserPublic"]
