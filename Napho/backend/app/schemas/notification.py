from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: str
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


class NotificationListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[NotificationOut]
    unread_count: int
