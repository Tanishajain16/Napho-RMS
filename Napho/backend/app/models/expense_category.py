from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.expense_policy import PolicyRule
    from app.models.approval_chain import ApprovalChain
    from app.models.claim import Claim, ClaimItem


class ExpenseCategory(Base, TimestampMixin):
    __tablename__ = "expense_categories"
    __table_args__ = (
        UniqueConstraint("org_id", "code", name="uq_category_org_code"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    requires_receipt: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    max_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="expense_categories"
    )
    parent: Mapped[Optional["ExpenseCategory"]] = relationship(
        "ExpenseCategory", remote_side="ExpenseCategory.id", back_populates="children"
    )
    children: Mapped[list["ExpenseCategory"]] = relationship(
        "ExpenseCategory", back_populates="parent"
    )
    policy_rules: Mapped[list["PolicyRule"]] = relationship(
        "PolicyRule", back_populates="category"
    )
    approval_chains: Mapped[list["ApprovalChain"]] = relationship(
        "ApprovalChain", back_populates="category"
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="category"
    )
    claim_items: Mapped[list["ClaimItem"]] = relationship(
        "ClaimItem", back_populates="category"
    )

    def __repr__(self) -> str:
        return (
            f"<ExpenseCategory id={self.id!r} code={self.code!r} name={self.name!r}>"
        )
