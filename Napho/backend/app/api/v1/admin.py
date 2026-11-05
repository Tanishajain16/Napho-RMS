from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_org, require_roles, _get_user_role_names
from app.core.security import hash_password
from app.database import get_db
from app.models.approval_chain import ApprovalChain, ApprovalStep
from app.models.base import new_uuid
from app.models.claim import Claim
from app.models.role import Role, UserRole
from app.models.user import User, UserOrgMembership

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    is_active: bool
    roles: list[str]
    created_at: Optional[str] = None
    claim_count: int = 0
    department: Optional[str] = None
    designation: Optional[str] = None

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    roles: list[str] = []
    department: Optional[str] = None
    designation: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _user_to_out(
    user: User,
    org_id: str,
    db: Session,
    claim_count: int = 0,
    department: Optional[str] = None,
    designation: Optional[str] = None,
) -> UserOut:
    roles = _get_user_role_names(user, db, org_id)
    created_at = None
    if hasattr(user, "created_at") and user.created_at:
        if isinstance(user.created_at, str):
            created_at = user.created_at
        else:
            created_at = user.created_at.isoformat()
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        roles=roles,
        created_at=created_at,
        claim_count=claim_count,
        department=department,
        designation=designation,
    )


def _sync_roles(user: User, org_id: str, role_names: list[str], db: Session) -> None:
    """Sync the user's roles in the org to exactly the given role_names list."""
    # Get all valid roles
    available_roles = db.query(Role).filter(Role.name.in_(role_names)).all()
    valid_role_ids = {r.id for r in available_roles}

    # Remove roles not in new list
    existing_user_roles = db.query(UserRole).filter(
        UserRole.user_id == user.id,
        UserRole.org_id == org_id,
    ).all()

    for ur in existing_user_roles:
        if ur.role_id not in valid_role_ids:
            db.delete(ur)

    # Add missing roles
    existing_role_ids = {ur.role_id for ur in existing_user_roles}
    for role in available_roles:
        if role.id not in existing_role_ids:
            new_ur = UserRole(
                id=new_uuid(),
                user_id=user.id,
                org_id=org_id,
                role_id=role.id,
            )
            db.add(new_ur)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/users", response_model=list[UserOut])
def list_users(
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    """List all users in the org with their roles, claim counts, and membership details."""
    memberships = db.query(UserOrgMembership).filter(
        UserOrgMembership.org_id == org.id,
    ).all()

    user_ids = [m.user_id for m in memberships]
    users = db.query(User).filter(User.id.in_(user_ids)).all()

    # Build membership lookup: user_id -> (department, designation)
    membership_map: dict[str, UserOrgMembership] = {m.user_id: m for m in memberships}

    # Query claim counts per user (non-deleted claims in this org)
    claim_counts_rows = (
        db.query(Claim.claimant_id, func.count(Claim.id).label("cnt"))
        .filter(Claim.org_id == org.id, Claim.deleted_at.is_(None))
        .group_by(Claim.claimant_id)
        .all()
    )
    claim_count_map: dict[str, int] = {row.claimant_id: row.cnt for row in claim_counts_rows}

    result = []
    for u in users:
        mem = membership_map.get(u.id)
        result.append(
            _user_to_out(
                u,
                org.id,
                db,
                claim_count=claim_count_map.get(u.id, 0),
                department=mem.department if mem else None,
                designation=mem.designation if mem else None,
            )
        )
    return result


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> UserOut:
    """Create a new user and add them to the org."""
    # Check email uniqueness
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{body.email}' already exists",
        )

    user = User(
        id=new_uuid(),
        email=body.email,
        name=body.name,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    db.flush()

    # Add org membership
    membership = UserOrgMembership(
        id=new_uuid(),
        user_id=user.id,
        org_id=org.id,
        department=body.department,
        designation=body.designation,
        employee_code=f"EMP-{user.id[:6].upper()}",
        is_active=True,
    )
    db.add(membership)
    db.flush()

    # Assign roles
    if body.roles:
        _sync_roles(user, org.id, body.roles, db)

    db.commit()
    db.refresh(user)
    logger.info("Admin %s created user %s", current_user.email, user.email)
    return _user_to_out(user, org.id, db)


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    body: UserUpdate,
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> UserOut:
    """Update a user's name, active status, or roles."""
    # Verify user is in this org
    membership = db.query(UserOrgMembership).filter(
        UserOrgMembership.user_id == user_id,
        UserOrgMembership.org_id == org.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.name is not None:
        user.name = body.name

    if body.is_active is not None:
        user.is_active = body.is_active
        membership.is_active = body.is_active

    if body.roles is not None:
        _sync_roles(user, org.id, body.roles, db)

    db.commit()
    db.refresh(user)
    logger.info("Admin %s updated user %s", current_user.email, user.email)
    return _user_to_out(user, org.id, db)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def deactivate_user(
    user_id: str,
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    """Soft-delete (deactivate) a user."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot deactivate themselves",
        )

    membership = db.query(UserOrgMembership).filter(
        UserOrgMembership.user_id == user_id,
        UserOrgMembership.org_id == org.id,
    ).first()
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = False
    membership.is_active = False
    db.commit()
    logger.info("Admin %s deactivated user %s", current_user.email, user.email)


# ---------------------------------------------------------------------------
# Approval Chain Schemas
# ---------------------------------------------------------------------------

class StepOut(BaseModel):
    id: str
    step_order: int
    approver_type: str  # "user" or "role"
    approver_id: Optional[str] = None
    approver_name: Optional[str] = None  # filled from User.name if approver_id set
    approver_role: Optional[str] = None
    timeout_hours: int

    model_config = {"from_attributes": True}


class ChainOut(BaseModel):
    id: str
    name: str
    min_amount: float
    max_amount: Optional[float]
    is_active: bool
    category_id: Optional[str] = None
    steps: list[StepOut] = []
    claim_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}


class StepCreate(BaseModel):
    step_order: int
    approver_type: str  # "user" or "role"
    approver_id: Optional[str] = None
    approver_role: Optional[str] = None
    timeout_hours: int = 48


class ChainCreate(BaseModel):
    name: str
    min_amount: float = 0.0
    max_amount: Optional[float] = None
    is_active: bool = True
    steps: list[StepCreate] = []


class ChainUpdate(BaseModel):
    name: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    is_active: Optional[bool] = None


# ---------------------------------------------------------------------------
# Approval Chain Helpers
# ---------------------------------------------------------------------------

def _build_step_out(step: ApprovalStep, db: Session) -> StepOut:
    approver_name: Optional[str] = None
    if step.approver_id:
        approver_user = db.query(User).filter(User.id == step.approver_id).first()
        if approver_user:
            approver_name = approver_user.name
    return StepOut(
        id=step.id,
        step_order=step.step_order,
        approver_type=step.approver_type,
        approver_id=step.approver_id,
        approver_name=approver_name,
        approver_role=step.approver_role,
        timeout_hours=step.timeout_hours,
    )


def _build_chain_out(chain: ApprovalChain, db: Session) -> ChainOut:
    claim_count = (
        db.query(func.count(Claim.id))
        .filter(Claim.chain_id == chain.id, Claim.deleted_at.is_(None))
        .scalar()
        or 0
    )
    steps = [_build_step_out(s, db) for s in sorted(chain.steps, key=lambda s: s.step_order)]
    created_at = chain.created_at
    if not isinstance(created_at, str):
        created_at = created_at.isoformat()
    return ChainOut(
        id=chain.id,
        name=chain.name,
        min_amount=chain.min_amount,
        max_amount=chain.max_amount,
        is_active=chain.is_active,
        category_id=chain.category_id,
        steps=steps,
        claim_count=claim_count,
        created_at=created_at,
    )


# ---------------------------------------------------------------------------
# Approval Chain Endpoints
# ---------------------------------------------------------------------------

@router.get("/approval-chains", response_model=list[ChainOut])
def list_approval_chains(
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> list[ChainOut]:
    """List all approval chains for the org with steps and claim counts."""
    chains = db.query(ApprovalChain).filter(ApprovalChain.org_id == org.id).all()
    return [_build_chain_out(c, db) for c in chains]


@router.post("/approval-chains", response_model=ChainOut, status_code=status.HTTP_201_CREATED)
def create_approval_chain(
    body: ChainCreate,
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ChainOut:
    """Create a new approval chain with optional steps."""
    chain = ApprovalChain(
        id=new_uuid(),
        org_id=org.id,
        name=body.name,
        min_amount=body.min_amount,
        max_amount=body.max_amount,
        is_active=body.is_active,
    )
    db.add(chain)
    db.flush()

    for step_data in body.steps:
        step = ApprovalStep(
            id=new_uuid(),
            chain_id=chain.id,
            step_order=step_data.step_order,
            approver_type=step_data.approver_type,
            approver_id=step_data.approver_id,
            approver_role=step_data.approver_role,
            timeout_hours=step_data.timeout_hours,
        )
        db.add(step)

    db.commit()
    db.refresh(chain)
    logger.info("Admin %s created approval chain %s", current_user.email, chain.id)
    return _build_chain_out(chain, db)


@router.put("/approval-chains/{chain_id}", response_model=ChainOut)
def update_approval_chain(
    chain_id: str,
    body: ChainUpdate,
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ChainOut:
    """Update an approval chain's metadata."""
    chain = db.query(ApprovalChain).filter(
        ApprovalChain.id == chain_id,
        ApprovalChain.org_id == org.id,
    ).first()
    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval chain not found")

    if body.name is not None:
        chain.name = body.name
    if body.min_amount is not None:
        chain.min_amount = body.min_amount
    if body.max_amount is not None:
        chain.max_amount = body.max_amount
    if body.is_active is not None:
        chain.is_active = body.is_active

    db.commit()
    db.refresh(chain)
    logger.info("Admin %s updated approval chain %s", current_user.email, chain.id)
    return _build_chain_out(chain, db)


@router.delete("/approval-chains/{chain_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_approval_chain(
    chain_id: str,
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> None:
    """Delete an approval chain if no active claims reference it."""
    chain = db.query(ApprovalChain).filter(
        ApprovalChain.id == chain_id,
        ApprovalChain.org_id == org.id,
    ).first()
    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval chain not found")

    active_claim_count = (
        db.query(func.count(Claim.id))
        .filter(
            Claim.chain_id == chain_id,
            Claim.deleted_at.is_(None),
            Claim.status.in_(["submitted", "under_review"]),
        )
        .scalar()
        or 0
    )
    if active_claim_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete chain: {active_claim_count} active claim(s) are using it",
        )

    db.delete(chain)
    db.commit()
    logger.info("Admin %s deleted approval chain %s", current_user.email, chain_id)


@router.post("/approval-chains/{chain_id}/steps", response_model=ChainOut)
def add_step_to_chain(
    chain_id: str,
    body: StepCreate,
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ChainOut:
    """Add a step to an existing approval chain."""
    chain = db.query(ApprovalChain).filter(
        ApprovalChain.id == chain_id,
        ApprovalChain.org_id == org.id,
    ).first()
    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval chain not found")

    step = ApprovalStep(
        id=new_uuid(),
        chain_id=chain.id,
        step_order=body.step_order,
        approver_type=body.approver_type,
        approver_id=body.approver_id,
        approver_role=body.approver_role,
        timeout_hours=body.timeout_hours,
    )
    db.add(step)
    db.commit()
    db.refresh(chain)
    logger.info("Admin %s added step to chain %s", current_user.email, chain_id)
    return _build_chain_out(chain, db)


@router.delete("/approval-chains/{chain_id}/steps/{step_id}", response_model=ChainOut)
def delete_step_from_chain(
    chain_id: str,
    step_id: str,
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ChainOut:
    """Remove a step from an approval chain."""
    chain = db.query(ApprovalChain).filter(
        ApprovalChain.id == chain_id,
        ApprovalChain.org_id == org.id,
    ).first()
    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval chain not found")

    step = db.query(ApprovalStep).filter(
        ApprovalStep.id == step_id,
        ApprovalStep.chain_id == chain_id,
    ).first()
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Step not found")

    db.delete(step)
    db.commit()
    db.refresh(chain)
    logger.info("Admin %s deleted step %s from chain %s", current_user.email, step_id, chain_id)
    return _build_chain_out(chain, db)
