from typing import Any

from pydantic import BaseModel, Field


class MessageResponse(BaseModel):
    message: str


class Page[T](BaseModel):
    items: list[T]
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)


class ErrorInfo(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    details: list[dict[str, Any]] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    error: ErrorInfo
