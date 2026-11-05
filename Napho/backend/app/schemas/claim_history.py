from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ActorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str


class ClaimHistoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    action: str
    from_status: str | None = None
    to_status: str | None = None
    from_amount: float | None = None
    to_amount: float | None = None
    comment: str | None = None
    actor: ActorInfo | None = None
    created_at: datetime
