from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    icon: str | None = None
    requires_receipt: bool
    max_amount: float | None = None
    is_active: bool
    sort_order: int
    children: list["CategoryOut"] = []


# Resolve forward reference
CategoryOut.model_rebuild()
