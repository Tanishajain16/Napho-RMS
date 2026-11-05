"""
Import all models here so that SQLAlchemy's mapper registry and Alembic
autogenerate can discover every table in a single import.
"""

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, new_uuid  # noqa: F401

# Core entities (order matters: referenced tables must be imported first)
from app.models.organization import Organization  # noqa: F401
from app.models.user import User, UserOrgMembership  # noqa: F401
from app.models.role import Role, UserRole, Permission  # noqa: F401
from app.models.expense_category import ExpenseCategory  # noqa: F401
from app.models.expense_policy import ExpensePolicy, PolicyRule  # noqa: F401
from app.models.approval_chain import ApprovalChain, ApprovalStep  # noqa: F401
from app.models.claim import (  # noqa: F401
    Claim,
    ClaimItem,
    ClaimAttachment,
    ClaimHistory,
    ClaimApproval,
    ClaimComment,
)
from app.models.notification import Notification  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401

__all__ = [
    "Base",
    "TimestampMixin",
    "SoftDeleteMixin",
    "new_uuid",
    # Core
    "Organization",
    "User",
    "UserOrgMembership",
    "Role",
    "UserRole",
    "Permission",
    "ExpenseCategory",
    "ExpensePolicy",
    "PolicyRule",
    "ApprovalChain",
    "ApprovalStep",
    "Claim",
    "ClaimItem",
    "ClaimAttachment",
    "ClaimHistory",
    "ClaimApproval",
    "ClaimComment",
    "Notification",
    "AuditLog",
]
