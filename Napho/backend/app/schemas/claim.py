from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.claim_history import ClaimHistoryOut
from app.schemas.claim_item import ClaimItemCreate, ClaimItemOut


# ---------------------------------------------------------------------------
# Nested summary schemas used inside ClaimOut / ClaimDetail
# ---------------------------------------------------------------------------

class ClaimantInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    avatar_url: str | None = None


class CategoryInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    icon: str | None = None
    code: str


class AttachmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_name: str
    file_size: int | None = None
    mime_type: str | None = None
    storage_key: str
    is_receipt: bool
    created_at: datetime

    @property
    def url(self) -> str:
        return f"/uploads/{self.storage_key}"


class ApprovalInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    claimed_amount: float | None = None
    approved_amount: float | None = None
    comment: str | None = None
    decided_at: datetime | None = None
    due_at: datetime | None = None
    approver_id: str | None = None


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ClaimCreate(BaseModel):
    title: str = Field(min_length=1, max_length=512)
    description: str | None = None
    category_id: str | None = None
    expense_date: date
    items: list[ClaimItemCreate] = Field(min_length=1)


class ClaimUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = None
    category_id: str | None = None
    expense_date: date | None = None
    items: list[ClaimItemCreate] | None = None


class ApproveRequest(BaseModel):
    approved_amount: Annotated[float, Field(gt=0)]
    comment: str | None = None


class RejectRequest(BaseModel):
    reason: str = Field(min_length=10, max_length=2048)


class MarkPaidRequest(BaseModel):
    payment_date: date | None = None
    payment_reference: str | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ClaimOut(BaseModel):
    """Summary view used in list endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    claim_number: str
    title: str
    status: str
    claimed_amount: float
    approved_amount: float | None = None
    paid_amount: float | None = None
    currency_code: str
    expense_date: date
    submitted_at: datetime | None = None
    approved_at: datetime | None = None
    paid_at: datetime | None = None
    rejection_reason: str | None = None
    version: int
    category: CategoryInfo | None = None
    claimant: ClaimantInfo | None = None
    created_at: datetime
    updated_at: datetime
    # Viewer-specific approval info (filled on Review Queue / claim detail; None elsewhere)
    can_act: bool | None = None                 # viewer may approve/reject at the current level
    my_decision: str | None = None              # "approved" | "partially_approved" | "rejected"
    my_approved_amount: float | None = None
    my_decided_at: datetime | None = None

    @field_validator("claimed_amount", "approved_amount", "paid_amount", mode="before")
    @classmethod
    def round_amounts(cls, v: float | None) -> float | None:
        if v is not None:
            return round(v, 2)
        return v


class ClaimDetail(ClaimOut):
    """Full view including line items, attachments, history, approvals."""

    description: str | None = None
    items: list[ClaimItemOut] = []
    attachments: list[AttachmentOut] = []
    history: list[ClaimHistoryOut] = []
    approvals: list[ApprovalInfo] = []


class ClaimStatsResponse(BaseModel):
    """Dashboard aggregate stats."""

    model_config = ConfigDict(from_attributes=True)

    pending_count: int
    pending_amount: float
    approved_count: int
    approved_amount: float
    paid_count: int
    paid_amount: float
    rejected_count: int
    rejected_amount: float = 0.0
