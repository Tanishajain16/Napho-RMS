from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response envelope."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    """Simple success message."""

    model_config = ConfigDict(from_attributes=True)

    message: str
    detail: str | None = None
