from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import verify_token
from app.database import get_db

logger = logging.getLogger(__name__)

# OAuth2 scheme – token URL is used by the OpenAPI docs "Authorize" button
# (/auth/token accepts the OAuth2 form body Swagger sends; /auth/login is JSON for the frontend)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Verify the bearer token and return the authenticated User object.

    Raises:
        UnauthorizedError – if the token is invalid or the user is not found/active.
    """
    from app.models.user import User  # local import to avoid circular deps

    payload = verify_token(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise UnauthorizedError()

    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
    ).first()

    if user is None:
        raise UnauthorizedError(detail="User not found")

    if not user.is_active:
        raise UnauthorizedError(detail="User account is inactive")

    return user


def _get_user_role_names(user: Any, db: Session, org_id: str | None = None) -> list[str]:
    """Return the list of role names the user holds (optionally within an org)."""
    from app.models.role import UserRole, Role  # local import

    query = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
    )
    if org_id:
        query = query.filter(UserRole.org_id == org_id)

    return [row[0] for row in query.all()]


def require_roles(*roles: str) -> Callable:
    """Return a FastAPI dependency that enforces the user has at least one of *roles*.

    Usage::

        @router.get("/admin-only", dependencies=[Depends(require_roles("admin"))])
        def admin_view(): ...
    """

    def dependency(
        current_user=Depends(get_current_user),
        db: Session = Depends(get_db),
    ):
        user_roles = _get_user_role_names(current_user, db)
        if not any(r in user_roles for r in roles):
            raise ForbiddenError(
                detail=f"This action requires one of the following roles: {', '.join(roles)}"
            )
        return current_user

    return dependency


def get_current_org(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the primary Organisation the current user belongs to.

    Picks the first active membership ordered by creation time.

    Raises:
        UnauthorizedError – if the user has no organisation membership.
    """
    from app.models.organization import Organization
    from app.models.user import UserOrgMembership

    membership = (
        db.query(UserOrgMembership)
        .filter(
            UserOrgMembership.user_id == current_user.id,
            UserOrgMembership.is_active == True,  # noqa: E712
        )
        .order_by(UserOrgMembership.created_at)
        .first()
    )
    if membership is None:
        raise UnauthorizedError(detail="User has no active organisation membership")

    org = db.query(Organization).filter(Organization.id == membership.org_id).first()
    if org is None:
        raise UnauthorizedError(detail="Organisation not found")

    return org
