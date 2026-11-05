from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
    verify_token,
)
from app.models.base import new_uuid
from app.models.organization import Organization
from app.models.role import Role, UserRole
from app.models.user import User, UserOrgMembership
from app.schemas.auth import RegisterRequest, UserTokenInfo

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_roles(user: User, db: Session, org_id: str | None = None) -> list[str]:
    """Return role names for a user, optionally scoped to an org."""
    query = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
    )
    if org_id:
        query = query.filter(UserRole.org_id == org_id)
    return [row[0] for row in query.all()]


def _get_primary_org_id(user: User, db: Session) -> str | None:
    """Return the org_id of the user's first active membership."""
    membership = (
        db.query(UserOrgMembership)
        .filter(
            UserOrgMembership.user_id == user.id,
            UserOrgMembership.is_active == True,  # noqa: E712
        )
        .order_by(UserOrgMembership.created_at)
        .first()
    )
    return membership.org_id if membership else None


def _build_token_payload(user: User, db: Session, org_id: str | None = None) -> dict:
    """Build the JWT payload dict for a user."""
    if org_id is None:
        org_id = _get_primary_org_id(user, db)

    roles = _get_user_roles(user, db, org_id)
    return {
        "sub": user.id,
        "email": user.email,
        "org_id": org_id,
        "roles": roles,
    }


def _build_token_info(user: User, db: Session, org_id: str | None = None) -> UserTokenInfo:
    if org_id is None:
        org_id = _get_primary_org_id(user, db)
    roles = _get_user_roles(user, db, org_id)
    return UserTokenInfo(
        id=user.id,
        email=user.email,
        name=user.name,
        roles=roles,
        org_id=org_id,
        avatar_url=user.avatar_url,
    )


# ---------------------------------------------------------------------------
# Public service functions
# ---------------------------------------------------------------------------

def login(email: str, password: str, db: Session) -> dict:
    """Authenticate a user by email + password.

    Returns:
        dict with access_token, refresh_token, user (UserTokenInfo).

    Raises:
        UnauthorizedError – if credentials are invalid or account is inactive.
    """
    user = db.query(User).filter(
        User.email == email.lower().strip(),
        User.deleted_at.is_(None),
    ).first()

    if user is None or not verify_password(password, user.password_hash):
        raise UnauthorizedError(detail="Incorrect email or password")

    if not user.is_active:
        raise UnauthorizedError(detail="Account is inactive")

    # Update last login
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)

    payload = _build_token_payload(user, db)
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    logger.info("User %s logged in successfully", user.email)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _build_token_info(user, db),
    }


def register(data: RegisterRequest, db: Session) -> dict:
    """Register a new user.

    - If org_id is provided, joins that org.
    - Otherwise joins the default demo org if it exists, or creates a personal org.
    - Assigns the "employee" role.

    Returns:
        Same shape as login().

    Raises:
        ConflictError – if the email is already registered.
    """
    email = data.email.lower().strip()

    existing = db.query(User).filter(User.email == email).first()
    if existing is not None:
        raise ConflictError(detail="An account with that email already exists")

    # Resolve org
    org_id = data.org_id
    if org_id:
        org = db.query(Organization).filter(
            Organization.id == org_id,
            Organization.deleted_at.is_(None),
        ).first()
        if org is None:
            from app.core.exceptions import NotFoundError
            raise NotFoundError("Organisation")
    else:
        # Fall back to the seed demo org if it exists
        org = db.query(Organization).filter(
            Organization.deleted_at.is_(None),
            Organization.is_active == True,  # noqa: E712
        ).order_by(Organization.created_at).first()

        if org is None:
            # Create a personal org
            org = Organization(
                id=new_uuid(),
                name=f"{data.name}'s Organisation",
                slug=f"org-{new_uuid()[:8]}",
                country_code="IN",
                currency_code="INR",
                fiscal_year_start_month=4,
                settings="{}",
                plan="free",
                is_active=True,
            )
            db.add(org)
            db.flush()

        org_id = org.id

    # Create user
    user = User(
        id=new_uuid(),
        email=email,
        name=data.name,
        password_hash=hash_password(data.password),
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Membership
    membership = UserOrgMembership(
        id=new_uuid(),
        user_id=user.id,
        org_id=org_id,
        is_active=True,
    )
    db.add(membership)
    db.flush()

    # Assign "employee" role (system role with org_id=None)
    employee_role = db.query(Role).filter(
        Role.name == "employee",
        Role.org_id.is_(None),
    ).first()

    if employee_role:
        user_role = UserRole(
            id=new_uuid(),
            user_id=user.id,
            org_id=org_id,
            role_id=employee_role.id,
        )
        db.add(user_role)

    db.commit()
    db.refresh(user)

    payload = _build_token_payload(user, db, org_id=org_id)
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    logger.info("New user registered: %s (org_id=%s)", user.email, org_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": _build_token_info(user, db, org_id=org_id),
    }


def refresh_access_token(refresh_token: str, db: Session) -> str:
    """Verify a refresh token and issue a new access token.

    Returns:
        New access_token string.

    Raises:
        UnauthorizedError – if the token is invalid or the user no longer exists.
    """
    payload = verify_token(refresh_token)
    if payload.get("type") != "refresh":
        raise UnauthorizedError(detail="Invalid token type")

    user_id = payload.get("sub")
    user = db.query(User).filter(
        User.id == user_id,
        User.deleted_at.is_(None),
        User.is_active == True,  # noqa: E712
    ).first()

    if user is None:
        raise UnauthorizedError(detail="User not found")

    token_payload = _build_token_payload(user, db)
    return create_access_token(token_payload)
