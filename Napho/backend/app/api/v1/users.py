from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_org, get_current_user, require_roles
from app.database import get_db
from app.models.role import Role, UserRole
from app.models.user import User, UserOrgMembership
from app.schemas.user import UserMeOut, UserOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


def _user_to_out(user: User, db: Session, org_id: str | None = None) -> UserOut:
    """Convert a User ORM object to UserOut, attaching roles."""
    query = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
    )
    if org_id:
        query = query.filter(UserRole.org_id == org_id)
    roles = [row[0] for row in query.all()]

    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        phone=user.phone,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        roles=roles,
    )


@router.get("/me", response_model=UserMeOut)
def get_my_profile(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserMeOut:
    """Return the current user's full profile."""
    from app.services.auth_service import _get_primary_org_id

    org_id = _get_primary_org_id(current_user, db)
    query = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == current_user.id)
    )
    roles = [row[0] for row in query.all()]

    membership = None
    if org_id:
        membership = db.query(UserOrgMembership).filter(
            UserOrgMembership.user_id == current_user.id,
            UserOrgMembership.org_id == org_id,
        ).first()

    return UserMeOut(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        phone=current_user.phone,
        is_active=current_user.is_active,
        last_login_at=current_user.last_login_at,
        created_at=current_user.created_at,
        roles=roles,
        org_id=org_id,
        department=membership.department if membership else None,
        designation=membership.designation if membership else None,
        employee_code=membership.employee_code if membership else None,
    )


@router.get("", response_model=list[UserOut])
def list_users(
    current_user=Depends(require_roles("admin", "approver")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    """Return all users in the current organisation (admin/approver only)."""
    memberships = (
        db.query(UserOrgMembership)
        .filter(
            UserOrgMembership.org_id == org.id,
            UserOrgMembership.is_active == True,  # noqa: E712
        )
        .all()
    )

    user_ids = [m.user_id for m in memberships]
    users = (
        db.query(User)
        .filter(
            User.id.in_(user_ids),
            User.deleted_at.is_(None),
        )
        .order_by(User.name)
        .all()
    )

    return [_user_to_out(u, db, org.id) for u in users]
