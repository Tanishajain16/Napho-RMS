from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, new_uuid

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.expense_category import ExpenseCategory
    from app.models.user import User
    from app.models.claim import Claim, ClaimApproval


class ApprovalChain(Base):
    __tablename__ = "approval_chains"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    min_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    max_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        String, nullable=False, default=lambda: datetime.utcnow().isoformat()
    )

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="approval_chains"
    )
    category: Mapped[Optional["ExpenseCategory"]] = relationship(
        "ExpenseCategory", back_populates="approval_chains"
    )
    steps: Mapped[list["ApprovalStep"]] = relationship(
        "ApprovalStep", back_populates="chain", cascade="all, delete-orphan",
        order_by="ApprovalStep.step_order",
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="chain"
    )

    def __repr__(self) -> str:
        return f"<ApprovalChain id={self.id!r} name={self.name!r} org_id={self.org_id!r}>"


class ApprovalStep(Base):
    __tablename__ = "approval_steps"
    __table_args__ = (
        UniqueConstraint("chain_id", "step_order", name="uq_step_chain_order"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    chain_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("approval_chains.id", ondelete="CASCADE"), nullable=False, index=True
    )
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_type: Mapped[str] = mapped_column(String(50), nullable=False)
    approver_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    approver_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    timeout_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=48)
    on_timeout: Mapped[str] = mapped_column(String(50), nullable=False, default="escalate")
    created_at: Mapped[datetime] = mapped_column(
        String, nullable=False, default=lambda: datetime.utcnow().isoformat()
    )

    # Relationships
    chain: Mapped["ApprovalChain"] = relationship("ApprovalChain", back_populates="steps")
    approver: Mapped[Optional["User"]] = relationship("User")
    claim_approvals: Mapped[list["ClaimApproval"]] = relationship(
        "ClaimApproval", back_populates="step"
    )
    current_claims: Mapped[list["Claim"]] = relationship(
        "Claim",
        foreign_keys="Claim.current_step_id",
        back_populates="current_step",
    )

    def __repr__(self) -> str:
        return (
            f"<ApprovalStep id={self.id!r} chain_id={self.chain_id!r} "
            f"step_order={self.step_order!r} approver_type={self.approver_type!r}>"
        )
