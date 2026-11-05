from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, new_uuid

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class AuditLog(Base):
    """Append-only compliance log — never update or delete rows."""

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    org_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    old_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    new_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now(), index=True
    )

    # Relationships
    organization: Mapped[Optional["Organization"]] = relationship(
        "Organization", back_populates="audit_logs"
    )
    actor: Mapped[Optional["User"]] = relationship(
        "User", back_populates="audit_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id!r} action={self.action!r} "
            f"resource_type={self.resource_type!r} resource_id={self.resource_id!r}>"
        )
