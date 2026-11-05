from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, new_uuid

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_role_org_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    org_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="roles"
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", back_populates="role", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id!r} name={self.name!r} org_id={self.org_id!r}>"


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (
        UniqueConstraint("user_id", "org_id", "role_id", name="uq_user_org_role"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    org_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    granted_by: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", foreign_keys=[user_id], back_populates="user_roles"
    )
    organization: Mapped["Organization"] = relationship(
        "Organization", back_populates="user_roles"
    )
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")
    granted_by_user: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[granted_by], back_populates="granted_roles"
    )

    def __repr__(self) -> str:
        return (
            f"<UserRole id={self.id!r} user_id={self.user_id!r} "
            f"role_id={self.role_id!r}>"
        )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("role_id", "resource", "action", name="uq_permission_role_resource_action"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    conditions: Mapped[str] = mapped_column(String, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    # Relationships
    role: Mapped["Role"] = relationship("Role", back_populates="permissions")

    def __repr__(self) -> str:
        return (
            f"<Permission id={self.id!r} role_id={self.role_id!r} "
            f"resource={self.resource!r} action={self.action!r}>"
        )
