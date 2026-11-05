from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.schemas.auth import (
    AccessTokenResponse,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserTokenInfo,
)
from app.schemas.common import MessageResponse
from app.schemas.user import UserMeOut
from app.services import auth_service
from app.services.auth_service import _build_token_info, _get_primary_org_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(
    body: RegisterRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Register a new user and return tokens."""
    result = auth_service.register(body, db)
    return TokenResponse(**result)


@router.post("/login", response_model=TokenResponse)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Authenticate and return tokens + user info."""
    result = auth_service.login(body.email, body.password, db)
    return TokenResponse(**result)


@router.post("/token", response_model=TokenResponse, summary="Login (OAuth2 form — used by Swagger Authorize)")
def token(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """OAuth2 password-flow login. Same as `/login`, but takes form fields
    (`username` = email, `password`) so the Swagger UI **Authorize** button works."""
    result = auth_service.login(form.username, form.password, db)
    return TokenResponse(**result)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(
    body: RefreshRequest,
    db: Session = Depends(get_db),
) -> AccessTokenResponse:
    """Exchange a refresh token for a new access token."""
    access_token = auth_service.refresh_access_token(body.refresh_token, db)
    return AccessTokenResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
def logout(
    current_user=Depends(get_current_user),
) -> MessageResponse:
    """Logout endpoint (stateless JWT — client must discard tokens)."""
    logger.info("User %s logged out", current_user.email)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserMeOut)
def me(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserMeOut:
    """Return the currently authenticated user's profile."""
    from app.models.user import UserOrgMembership
    from app.models.role import UserRole, Role

    org_id = _get_primary_org_id(current_user, db)
    roles = [
        row[0]
        for row in (
            db.query(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .filter(UserRole.user_id == current_user.id)
            .all()
        )
    ]

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
