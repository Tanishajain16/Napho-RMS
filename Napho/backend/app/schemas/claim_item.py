from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ClaimItemCreate(BaseModel):
    description: str = Field(min_length=1, max_length=1024)
    amount: Annotated[float, Field(gt=0)]
    quantity: int = Field(default=1, ge=1)
    unit_price: float | None = None
    expense_date: date | None = None
    vendor_name: str | None = Field(default=None, max_length=255)
    category_id: str | None = None
    notes: str | None = None
    sort_order: int = 0


class ClaimItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_id: str
    description: str
    amount: float
    quantity: int
    unit_price: float | None = None
    expense_date: date | None = None
    vendor_name: str | None = None
    category_id: str | None = None
    receipt_required: bool
    approved_amount: float | None = None
    notes: str | None = None
    sort_order: int
    created_at: datetime

    @field_validator("amount", "approved_amount", mode="before")
    @classmethod
    def round_amounts(cls, v: float | None) -> float | None:
        if v is not None:
            return round(v, 2)
        return v
