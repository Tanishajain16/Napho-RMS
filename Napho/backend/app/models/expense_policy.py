from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.expense_category import ExpenseCategory
    from app.models.role import Role
    from app.models.claim import Claim


class ExpensePolicy(Base, TimestampMixin):
    __tablename__ = "expense_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="expense_policies"
    )
    rules: Mapped[list["PolicyRule"]] = relationship(
        "PolicyRule", back_populates="policy", cascade="all, delete-orphan"
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="policy"
    )

    def __repr__(self) -> str:
        return f"<ExpensePolicy id={self.id!r} name={self.name!r} org_id={self.org_id!r}>"


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("expense_policies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("expense_categories.id", ondelete="SET NULL"), nullable=True
    )
    role_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="SET NULL"), nullable=True
    )
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    max_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    max_items: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    requires_receipt_above: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    requires_approval_above: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    period: Mapped[str] = mapped_column(String(50), nullable=False, default="per_claim")
    created_at: Mapped[datetime] = mapped_column(
        String, nullable=False, default=lambda: datetime.utcnow().isoformat()
    )

    # Relationships
    policy: Mapped["ExpensePolicy"] = relationship("ExpensePolicy", back_populates="rules")
    category: Mapped[Optional["ExpenseCategory"]] = relationship(
        "ExpenseCategory", back_populates="policy_rules"
    )
    role: Mapped[Optional["Role"]] = relationship("Role")

    def __repr__(self) -> str:
        return (
            f"<PolicyRule id={self.id!r} policy_id={self.policy_id!r} "
            f"period={self.period!r}>"
        )
