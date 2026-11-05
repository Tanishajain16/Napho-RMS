from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, new_uuid

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.role import UserRole
    from app.models.claim import Claim, ClaimHistory, ClaimApproval, ClaimComment, ClaimAttachment
    from app.models.notification import Notification
    from app.models.audit_log import AuditLog


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Relationships
    memberships: Mapped[list["UserOrgMembership"]] = relationship(
        "UserOrgMembership",
        foreign_keys="UserOrgMembership.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    subordinate_memberships: Mapped[list["UserOrgMembership"]] = relationship(
        "UserOrgMembership",
        foreign_keys="UserOrgMembership.manager_id",
        back_populates="manager",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", foreign_keys="UserRole.user_id", back_populates="user"
    )
    granted_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", foreign_keys="UserRole.granted_by", back_populates="granted_by_user"
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim", foreign_keys="Claim.claimant_id", back_populates="claimant"
    )
    claim_histories: Mapped[list["ClaimHistory"]] = relationship(
        "ClaimHistory", back_populates="actor"
    )
    claim_approvals: Mapped[list["ClaimApproval"]] = relationship(
        "ClaimApproval", back_populates="approver"
    )
    claim_comments: Mapped[list["ClaimComment"]] = relationship(
        "ClaimComment", back_populates="author"
    )
    uploaded_attachments: Mapped[list["ClaimAttachment"]] = relationship(
        "ClaimAttachment", back_populates="uploaded_by_user"
    )
    notifications: Mapped[list["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        "AuditLog", back_populates="actor"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id!r} email={self.email!r} name={self.name!r}>"


class UserOrgMembership(Base, TimestampMixin):
    __tablename__ = "user_org_memberships"
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", name="uq_user_org"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    employee_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    designation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    manager_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    join_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="memberships"
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="memberships"
    )
    manager: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[manager_id], back_populates="subordinate_memberships"
    )

    def __repr__(self) -> str:
        return (
            f"<UserOrgMembership id={self.id!r} user_id={self.user_id!r} "
            f"org_id={self.org_id!r}>"
        )
