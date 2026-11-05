from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Project-wide SQLAlchemy declarative base."""


# ---------------------------------------------------------------------------
# Mixins
# ---------------------------------------------------------------------------
class TimestampMixin:
    """Adds auto-managed ``created_at`` and ``updated_at`` columns."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=func.now(),
        onupdate=datetime.utcnow,
    )


class SoftDeleteMixin:
    """Adds an optional ``deleted_at`` timestamp for soft-delete support."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
def new_uuid() -> str:
    """Return a new UUID4 as a lowercase string."""
    return str(uuid.uuid4())
