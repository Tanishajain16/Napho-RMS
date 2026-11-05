from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.expense_category import ExpenseCategory
    from app.models.expense_policy import ExpensePolicy
    from app.models.approval_chain import ApprovalChain, ApprovalStep


class Claim(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "claims"
    __table_args__ = (
        UniqueConstraint("org_id", "claim_number", name="uq_claim_org_number"),
        Index("ix_claims_org_claimant", "org_id", "claimant_id"),
        Index("ix_claims_org_status", "org_id", "status"),
        Index("ix_claims_submitted_at", "submitted_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claimant_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_number: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="draft", index=True)
    claimed_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    approved_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    paid_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    currency_code: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    expense_date: Mapped[date] = mapped_column(Date, nullable=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    current_step_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("approval_steps.id", ondelete="SET NULL"), nullable=True
    )
    chain_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("approval_chains.id", ondelete="SET NULL"), nullable=True
    )
    policy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("expense_policies.id", ondelete="SET NULL"), nullable=True
    )
    metadata_: Mapped[str] = mapped_column("metadata_", Text, nullable=False, default="{}")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    idempotency_key: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True, unique=True, index=True
    )

    # Relationships
    organization: Mapped["Organization"] = relationship("Organization", back_populates="claims")
    claimant: Mapped["User"] = relationship(
        "User", foreign_keys=[claimant_id], back_populates="claims"
    )
    category: Mapped[Optional["ExpenseCategory"]] = relationship(
        "ExpenseCategory", back_populates="claims"
    )
    policy: Mapped[Optional["ExpensePolicy"]] = relationship(
        "ExpensePolicy", back_populates="claims"
    )
    chain: Mapped[Optional["ApprovalChain"]] = relationship(
        "ApprovalChain", back_populates="claims"
    )
    current_step: Mapped[Optional["ApprovalStep"]] = relationship(
        "ApprovalStep",
        foreign_keys=[current_step_id],
        back_populates="current_claims",
    )
    items: Mapped[list["ClaimItem"]] = relationship(
        "ClaimItem", back_populates="claim", cascade="all, delete-orphan",
        order_by="ClaimItem.sort_order",
    )
    attachments: Mapped[list["ClaimAttachment"]] = relationship(
        "ClaimAttachment", back_populates="claim", cascade="all, delete-orphan"
    )
    history: Mapped[list["ClaimHistory"]] = relationship(
        "ClaimHistory", back_populates="claim", cascade="all, delete-orphan",
        order_by="ClaimHistory.created_at",
    )
    approvals: Mapped[list["ClaimApproval"]] = relationship(
        "ClaimApproval", back_populates="claim", cascade="all, delete-orphan"
    )
    comments: Mapped[list["ClaimComment"]] = relationship(
        "ClaimComment",
        foreign_keys="ClaimComment.claim_id",
        back_populates="claim",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Claim id={self.id!r} claim_number={self.claim_number!r} "
            f"status={self.status!r} amount={self.claimed_amount!r}>"
        )


class ClaimItem(Base, TimestampMixin):
    __tablename__ = "claim_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(1024), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    unit_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expense_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    vendor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    receipt_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approved_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="items")
    category: Mapped[Optional["ExpenseCategory"]] = relationship(
        "ExpenseCategory", back_populates="claim_items"
    )
    attachments: Mapped[list["ClaimAttachment"]] = relationship(
        "ClaimAttachment", back_populates="claim_item"
    )

    def __repr__(self) -> str:
        return (
            f"<ClaimItem id={self.id!r} claim_id={self.claim_id!r} "
            f"description={self.description!r} amount={self.amount!r}>"
        )


class ClaimAttachment(Base):
    __tablename__ = "claim_attachments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    claim_item_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("claim_items.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    storage_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="local")
    is_receipt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="attachments")
    claim_item: Mapped[Optional["ClaimItem"]] = relationship(
        "ClaimItem", back_populates="attachments"
    )
    uploaded_by_user: Mapped["User"] = relationship(
        "User", back_populates="uploaded_attachments"
    )

    def __repr__(self) -> str:
        return (
            f"<ClaimAttachment id={self.id!r} claim_id={self.claim_id!r} "
            f"file_name={self.file_name!r}>"
        )


class ClaimHistory(Base):
    """Append-only audit trail — never update or delete rows."""

    __tablename__ = "claim_history"
    __table_args__ = (
        Index("ix_claim_history_claim_created", "claim_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    from_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    to_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    from_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    to_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    metadata_: Mapped[str] = mapped_column("metadata_", Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="history")
    actor: Mapped["User"] = relationship("User", back_populates="claim_histories")

    def __repr__(self) -> str:
        return (
            f"<ClaimHistory id={self.id!r} claim_id={self.claim_id!r} "
            f"action={self.action!r}>"
        )


class ClaimApproval(Base):
    __tablename__ = "claim_approvals"
    __table_args__ = (
        UniqueConstraint("claim_id", "step_id", name="uq_claim_approval_step"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("approval_steps.id", ondelete="CASCADE"), nullable=False
    )
    approver_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    claimed_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    approved_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    due_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="approvals")
    step: Mapped["ApprovalStep"] = relationship(
        "ApprovalStep", back_populates="claim_approvals"
    )
    approver: Mapped[Optional["User"]] = relationship(
        "User", back_populates="claim_approvals"
    )

    def __repr__(self) -> str:
        return (
            f"<ClaimApproval id={self.id!r} claim_id={self.claim_id!r} "
            f"status={self.status!r}>"
        )


class ClaimComment(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "claim_comments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    claim_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("claims.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("claim_comments.id", ondelete="SET NULL"),
        nullable=True,
    )
    author_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Relationships
    claim: Mapped["Claim"] = relationship(
        "Claim", foreign_keys=[claim_id], back_populates="comments"
    )
    parent: Mapped[Optional["ClaimComment"]] = relationship(
        "ClaimComment",
        remote_side="ClaimComment.id",
        back_populates="replies",
    )
    replies: Mapped[list["ClaimComment"]] = relationship(
        "ClaimComment", back_populates="parent"
    )
    author: Mapped["User"] = relationship("User", back_populates="claim_comments")

    def __repr__(self) -> str:
        return (
            f"<ClaimComment id={self.id!r} claim_id={self.claim_id!r} "
            f"author_id={self.author_id!r}>"
        )
