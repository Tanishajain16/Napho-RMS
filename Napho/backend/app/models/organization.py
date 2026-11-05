from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.user import UserOrgMembership
    from app.models.role import Role, UserRole
    from app.models.expense_category import ExpenseCategory
    from app.models.expense_policy import ExpensePolicy
    from app.models.approval_chain import ApprovalChain
    from app.models.claim import Claim
    from app.models.notification import Notification
    from app.models.audit_log import AuditLog


class Organization(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    country_code: Mapped[str] = mapped_column(String(10), nullable=False, default="IN")
    currency_code: Mapped[str] = mapped_column(String(10), nullable=False, default="INR")
    fiscal_year_start_month: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    settings: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    memberships: Mapped[list["UserOrgMembership"]] = relationship(
        "UserOrgMembership", back_populates="organization", cascade="all, delete-orphan"
    )
    roles: Mapped[list["Role"]] = relationship(
        "Role", back_populates="organization"
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="organization"
    )
    expense_categories: Mapped[list["ExpenseCategory"]] = relationship(
        "ExpenseCategory", back_populates="organization"
    )
    expense_policies: Mapped[list["ExpensePolicy"]] = relationship(
        "ExpensePolicy", back_populates="organization"
    )
    approval_chains: Mapped[list["ApprovalChain"]] = relationship(
        "ApprovalChain", back_populates="organization"
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", back_populates="organization"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="organization"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="organization"
    )

    def __repr__(self) -> str:
        return f"<Organization id={self.id!r} slug={self.slug!r} name={self.name!r}>"
