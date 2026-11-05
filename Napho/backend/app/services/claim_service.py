from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.approval_chain import ApprovalChain, ApprovalStep
from app.models.base import new_uuid
from app.models.claim import Claim, ClaimApproval, ClaimAttachment, ClaimHistory, ClaimItem
from app.models.expense_category import ExpenseCategory
from app.models.user import User
from app.schemas.claim import ClaimCreate, ClaimUpdate

logger = logging.getLogger(__name__)

# Statuses that are considered "active" for sequential numbering
_TERMINAL_STATUSES = {"cancelled"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_claim_full(claim_id: str, db: Session) -> Claim | None:
    """Load a claim with all relationships eagerly."""
    return (
        db.query(Claim)
        .options(
            selectinload(Claim.claimant),
            selectinload(Claim.category),
            selectinload(Claim.items),
            selectinload(Claim.attachments),
            selectinload(Claim.history).selectinload(ClaimHistory.actor),
            selectinload(Claim.approvals),
        )
        .filter(Claim.id == claim_id, Claim.deleted_at.is_(None))
        .first()
    )


def _append_history(
    claim: Claim,
    actor: User,
    action: str,
    db: Session,
    from_status: str | None = None,
    to_status: str | None = None,
    comment: str | None = None,
    from_amount: float | None = None,
    to_amount: float | None = None,
) -> ClaimHistory:
    entry = ClaimHistory(
        id=new_uuid(),
        claim_id=claim.id,
        actor_id=actor.id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        from_amount=from_amount,
        to_amount=to_amount,
        comment=comment,
        metadata_="{}",
        created_at=datetime.now(timezone.utc),
    )
    db.add(entry)
    return entry


# ---------------------------------------------------------------------------
# Sequential claim number
# ---------------------------------------------------------------------------

def get_next_claim_number(org_id: str, db: Session) -> str:
    """Return the next NAPHO-YYYY-NNNNN claim number for the given org.

    Uses a SELECT MAX + 1 approach which is safe under SQLite's
    serialisable transaction semantics.
    """
    year = datetime.now(timezone.utc).year
    prefix = f"NAPHO-{year}-"

    # Find the highest existing sequential number for this org and year
    existing = (
        db.query(Claim.claim_number)
        .filter(
            Claim.org_id == org_id,
            Claim.claim_number.like(f"{prefix}%"),
        )
        .all()
    )

    max_seq = 0
    for (number,) in existing:
        try:
            seq = int(number[len(prefix):])
            if seq > max_seq:
                max_seq = seq
        except (ValueError, IndexError):
            pass

    next_seq = max_seq + 1
    return f"{prefix}{next_seq:05d}"


# ---------------------------------------------------------------------------
# Amount computation
# ---------------------------------------------------------------------------

def compute_claimed_amount(claim_id: str, db: Session) -> float:
    """Sum all ClaimItem.amount values for the given claim."""
    result = (
        db.query(func.sum(ClaimItem.amount))
        .filter(ClaimItem.claim_id == claim_id)
        .scalar()
    )
    return round(result or 0.0, 2)


# ---------------------------------------------------------------------------
# Submission validation
# ---------------------------------------------------------------------------

def validate_claim_for_submission(claim: Claim, db: Session) -> None:
    """Raise ValidationError/ConflictError if the claim cannot be submitted."""
    if not claim.title or not claim.title.strip():
        raise ValidationError("Claim must have a title")

    if not claim.expense_date:
        raise ValidationError("Claim must have an expense date")

    items = db.query(ClaimItem).filter(ClaimItem.claim_id == claim.id).all()
    if not items:
        raise ValidationError("Claim must have at least one item")

    for item in items:
        if item.amount <= 0:
            raise ValidationError(
                f"Item '{item.description}' has an invalid amount (must be > 0)"
            )

    # Check if the category requires a receipt
    if claim.category_id:
        category = db.query(ExpenseCategory).filter(
            ExpenseCategory.id == claim.category_id
        ).first()
        if category and category.requires_receipt:
            active_attachments = [
                a for a in
                db.query(ClaimAttachment).filter(
                    ClaimAttachment.claim_id == claim.id,
                    ClaimAttachment.deleted_at.is_(None),
                ).all()
            ]
            if not active_attachments:
                raise ValidationError(
                    f"Category '{category.name}' requires at least one receipt attachment"
                )


# ---------------------------------------------------------------------------
# Approval chain matching
# ---------------------------------------------------------------------------

def find_approval_chain(claim: Claim, db: Session) -> Optional[ApprovalChain]:
    """Find the best-matching active ApprovalChain for this claim.

    Matching logic (priority order):
    1. Chain that matches both category_id AND amount range.
    2. Chain that matches amount range with no category restriction.
    3. Any active chain in the org (catch-all).
    """
    amount = claim.claimed_amount

    chains = (
        db.query(ApprovalChain)
        .filter(
            ApprovalChain.org_id == claim.org_id,
            ApprovalChain.is_active == True,  # noqa: E712
        )
        .options(selectinload(ApprovalChain.steps))
        .all()
    )

    if not chains:
        return None

    def amount_matches(chain: ApprovalChain) -> bool:
        if amount < chain.min_amount:
            return False
        if chain.max_amount is not None and amount > chain.max_amount:
            return False
        return True

    # Priority 1: category + amount match
    if claim.category_id:
        for chain in chains:
            if chain.category_id == claim.category_id and amount_matches(chain):
                return chain

    # Priority 2: amount match, no category restriction
    for chain in chains:
        if chain.category_id is None and amount_matches(chain):
            return chain

    # Priority 3: any active chain
    return chains[0]


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def create_claim(data: ClaimCreate, claimant: User, org_id: str, db: Session) -> Claim:
    """Create a new claim in draft status."""
    from app.core.dependencies import _get_user_role_names

    # Admins manage the system; they don't file claims (unless also given the employee role).
    roles = _get_user_role_names(claimant, db, org_id)
    if "admin" in roles and "employee" not in roles:
        raise ForbiddenError("Admins cannot create claims")

    claim_number = get_next_claim_number(org_id, db)

    claim = Claim(
        id=new_uuid(),
        org_id=org_id,
        claimant_id=claimant.id,
        claim_number=claim_number,
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        expense_date=data.expense_date,
        status="draft",
        currency_code="INR",
        claimed_amount=0.0,
        version=1,
        metadata_="{}",
    )
    db.add(claim)
    db.flush()

    # Create items
    total = 0.0
    for idx, item_data in enumerate(data.items):
        item = ClaimItem(
            id=new_uuid(),
            claim_id=claim.id,
            category_id=item_data.category_id,
            description=item_data.description,
            amount=item_data.amount,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            expense_date=item_data.expense_date,
            vendor_name=item_data.vendor_name,
            notes=item_data.notes,
            sort_order=item_data.sort_order or idx,
            receipt_required=True,
        )
        db.add(item)
        total += item_data.amount

    claim.claimed_amount = round(total, 2)

    # Initial history entry
    _append_history(
        claim, claimant, action="created",
        from_status=None, to_status="draft",
        to_amount=claim.claimed_amount,
        db=db,
    )

    db.commit()
    db.refresh(claim)

    logger.info("Created claim %s for user %s", claim.claim_number, claimant.email)
    return _load_claim_full(claim.id, db)


def get_claim(claim_id: str, current_user: User, org_id: str, db: Session) -> Claim:
    """Load a claim, enforcing ownership/org access."""
    from app.core.dependencies import _get_user_role_names

    claim = _load_claim_full(claim_id, db)
    if claim is None or claim.org_id != org_id:
        raise NotFoundError("Claim")

    if claim.claimant_id == current_user.id:
        return claim

    # Someone else's claim: plain employees never see it.
    user_roles = _get_user_role_names(current_user, db, org_id)
    is_privileged = any(r in user_roles for r in ("approver", "finance", "admin"))
    if not is_privileged:
        raise ForbiddenError("You do not have access to this claim")

    # Approvers/finance/admin may open others' claims (to review / pay them),
    # but an unsubmitted draft is private to its owner.
    if claim.status == "draft":
        raise NotFoundError("Claim")

    return claim


def list_claims(
    current_user: User,
    org_id: str,
    db: Session,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "updated_at_desc",
) -> tuple[list[Claim], int]:
    """Return (claims, total_count) of the current user's OWN claims.

    This backs the "My Claims" page and the dashboard, so it is always scoped to the
    logged-in user — regardless of role. Approvers/finance/admin reach other people's
    claims through /approvals/queue, payments and analytics instead.
    """
    query = (
        db.query(Claim)
        .options(
            selectinload(Claim.claimant),
            selectinload(Claim.category),
        )
        .filter(
            Claim.org_id == org_id,
            Claim.deleted_at.is_(None),
            Claim.claimant_id == current_user.id,
        )
    )

    if status_filter:
        # Accepts one status or a comma-separated list, e.g. "submitted,under_review"
        statuses = [s.strip() for s in status_filter.split(",") if s.strip()]
        query = query.filter(Claim.status.in_(statuses))

    total = query.count()

    # Sorting
    if sort == "updated_at_desc":
        query = query.order_by(Claim.updated_at.desc())
    elif sort == "updated_at_asc":
        query = query.order_by(Claim.updated_at.asc())
    elif sort == "submitted_at_desc":
        query = query.order_by(Claim.submitted_at.desc())
    elif sort == "amount_desc":
        query = query.order_by(Claim.claimed_amount.desc())
    else:
        query = query.order_by(Claim.updated_at.desc())

    offset = (page - 1) * page_size
    claims = query.offset(offset).limit(page_size).all()

    return claims, total


def update_claim(
    claim_id: str,
    data: ClaimUpdate,
    current_user: User,
    org_id: str,
    db: Session,
) -> Claim:
    """Update a claim (only owner, only draft or rejected)."""
    claim = _load_claim_full(claim_id, db)
    if claim is None or claim.org_id != org_id:
        raise NotFoundError("Claim")

    if claim.claimant_id != current_user.id:
        raise ForbiddenError("Only the claim owner can edit this claim")

    if claim.status not in ("draft", "rejected"):
        raise ConflictError(
            f"Cannot edit a claim with status '{claim.status}'. "
            "Only draft or rejected claims can be edited."
        )

    old_status = claim.status

    if data.title is not None:
        claim.title = data.title
    if data.description is not None:
        claim.description = data.description
    if data.category_id is not None:
        claim.category_id = data.category_id
    if data.expense_date is not None:
        claim.expense_date = data.expense_date

    # If the claim was rejected, revert to draft on edit
    if claim.status == "rejected":
        claim.status = "draft"
        claim.rejection_reason = None

    if data.items is not None:
        # Delete existing items
        db.query(ClaimItem).filter(ClaimItem.claim_id == claim.id).delete()
        db.flush()

        total = 0.0
        for idx, item_data in enumerate(data.items):
            item = ClaimItem(
                id=new_uuid(),
                claim_id=claim.id,
                category_id=item_data.category_id,
                description=item_data.description,
                amount=item_data.amount,
                quantity=item_data.quantity,
                unit_price=item_data.unit_price,
                expense_date=item_data.expense_date,
                vendor_name=item_data.vendor_name,
                notes=item_data.notes,
                sort_order=item_data.sort_order or idx,
                receipt_required=True,
            )
            db.add(item)
            total += item_data.amount

        claim.claimed_amount = round(total, 2)

    claim.version += 1

    _append_history(
        claim, current_user, action="edited",
        from_status=old_status, to_status=claim.status,
        to_amount=claim.claimed_amount,
        db=db,
    )

    db.commit()
    db.refresh(claim)
    logger.info("Claim %s updated by %s", claim.claim_number, current_user.email)
    return _load_claim_full(claim.id, db)


def delete_claim(
    claim_id: str,
    current_user: User,
    org_id: str,
    db: Session,
) -> None:
    """Soft-delete a draft claim (owner only)."""
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.org_id == org_id,
        Claim.deleted_at.is_(None),
    ).first()

    if claim is None:
        raise NotFoundError("Claim")

    if claim.claimant_id != current_user.id:
        raise ForbiddenError("Only the claim owner can delete this claim")

    if claim.status != "draft":
        raise ConflictError("Only draft claims can be deleted")

    _append_history(
        claim, current_user, action="cancelled",
        from_status=claim.status, to_status="cancelled",
        db=db,
    )

    claim.deleted_at = datetime.now(timezone.utc)
    db.commit()
    logger.info("Claim %s soft-deleted by %s", claim.claim_number, current_user.email)


def submit_claim(
    claim_id: str,
    current_user: User,
    org_id: str,
    db: Session,
    idempotency_key: str | None = None,
) -> Claim:
    """Submit a draft claim for approval.

    Idempotent: if the claim is already submitted, returns current state.
    """
    claim = _load_claim_full(claim_id, db)
    if claim is None or claim.org_id != org_id:
        raise NotFoundError("Claim")

    if claim.claimant_id != current_user.id:
        raise ForbiddenError("Only the claim owner can submit this claim")

    # Idempotency: if already submitted, return current state
    if claim.status == "submitted":
        return claim

    if claim.status != "draft":
        raise ConflictError(
            f"Cannot submit a claim with status '{claim.status}'. "
            "Only draft claims can be submitted."
        )

    # Store idempotency key if provided
    if idempotency_key:
        # Check if the key already exists on another claim
        existing_idem = db.query(Claim).filter(
            Claim.idempotency_key == idempotency_key,
            Claim.id != claim_id,
        ).first()
        if existing_idem:
            return _load_claim_full(existing_idem.id, db)
        claim.idempotency_key = idempotency_key

    # Validate
    validate_claim_for_submission(claim, db)

    now = datetime.now(timezone.utc)
    old_status = claim.status
    claim.status = "submitted"
    claim.submitted_at = now

    # Find and attach approval chain
    chain = find_approval_chain(claim, db)
    if chain:
        claim.chain_id = chain.id
        # Create ClaimApproval rows for each step
        for step in chain.steps:
            existing_approval = db.query(ClaimApproval).filter(
                ClaimApproval.claim_id == claim.id,
                ClaimApproval.step_id == step.id,
            ).first()
            if existing_approval is None:
                approval = ClaimApproval(
                    id=new_uuid(),
                    claim_id=claim.id,
                    step_id=step.id,
                    approver_id=step.approver_id,  # may be None for role-based
                    status="pending",
                    claimed_amount=claim.claimed_amount,
                )
                db.add(approval)

        # Set current_step to first step
        if chain.steps:
            first_step = min(chain.steps, key=lambda s: s.step_order)
            claim.current_step_id = first_step.id

    _append_history(
        claim, current_user, action="submitted",
        from_status=old_status, to_status="submitted",
        to_amount=claim.claimed_amount,
        comment="Submitted for approval.",
        db=db,
    )

    db.flush()

    # Notify approvers
    from app.services.notification_service import notify_approvers_of_submission
    notify_approvers_of_submission(claim, db)

    db.commit()
    db.refresh(claim)
    logger.info("Claim %s submitted by %s", claim.claim_number, current_user.email)
    return _load_claim_full(claim.id, db)


def cancel_claim(
    claim_id: str,
    current_user: User,
    org_id: str,
    db: Session,
) -> Claim:
    """Cancel a draft or unreviewed submitted claim (owner only)."""
    claim = _load_claim_full(claim_id, db)
    if claim is None or claim.org_id != org_id:
        raise NotFoundError("Claim")

    if claim.claimant_id != current_user.id:
        raise ForbiddenError("Only the claim owner can cancel this claim")

    if claim.status not in ("draft", "submitted"):
        raise ConflictError(
            f"Cannot cancel a claim with status '{claim.status}'"
        )

    # If submitted, ensure no approver has acted yet
    if claim.status == "submitted":
        acted = db.query(ClaimApproval).filter(
            ClaimApproval.claim_id == claim.id,
            ClaimApproval.status != "pending",
        ).first()
        if acted:
            raise ConflictError(
                "Cannot cancel a claim that has already been reviewed by an approver"
            )

    old_status = claim.status
    claim.status = "cancelled"

    _append_history(
        claim, current_user, action="cancelled",
        from_status=old_status, to_status="cancelled",
        db=db,
    )

    db.commit()
    db.refresh(claim)
    logger.info("Claim %s cancelled by %s", claim.claim_number, current_user.email)
    return _load_claim_full(claim.id, db)


def resubmit_claim(
    claim_id: str,
    current_user: User,
    org_id: str,
    db: Session,
) -> Claim:
    """Resubmit a rejected claim."""
    claim = _load_claim_full(claim_id, db)
    if claim is None or claim.org_id != org_id:
        raise NotFoundError("Claim")

    if claim.claimant_id != current_user.id:
        raise ForbiddenError("Only the claim owner can resubmit this claim")

    if claim.status != "rejected":
        raise ConflictError(
            f"Cannot resubmit a claim with status '{claim.status}'. "
            "Only rejected claims can be resubmitted."
        )

    now = datetime.now(timezone.utc)
    old_status = claim.status
    claim.status = "submitted"
    claim.submitted_at = now
    claim.rejection_reason = None

    # Reset claim_approvals to pending
    db.query(ClaimApproval).filter(
        ClaimApproval.claim_id == claim.id,
    ).update({"status": "pending", "decided_at": None, "approved_amount": None, "comment": None})

    _append_history(
        claim, current_user, action="resubmitted",
        from_status=old_status, to_status="submitted",
        to_amount=claim.claimed_amount,
        comment="Resubmitted for approval.",
        db=db,
    )

    db.flush()

    from app.services.notification_service import notify_approvers_of_submission
    notify_approvers_of_submission(claim, db)

    db.commit()
    db.refresh(claim)
    logger.info("Claim %s resubmitted by %s", claim.claim_number, current_user.email)
    return _load_claim_full(claim.id, db)


def get_claim_stats(current_user: User, org_id: str, db: Session, scope: str = "mine") -> dict:
    """Return dashboard stats.

    scope="mine" (default): the current user's OWN claims — any role.
    scope="org": all claims in the organisation — approver / finance / admin only
                 (their dashboard overview; drafts are excluded as they're private).
    """
    from app.core.dependencies import _get_user_role_names

    filters = [Claim.org_id == org_id, Claim.deleted_at.is_(None)]
    if scope == "org":
        roles = _get_user_role_names(current_user, db, org_id)
        if not any(r in roles for r in ("approver", "finance", "admin")):
            raise ForbiddenError("Organisation-wide stats are only available to approvers, finance and admins")
    else:
        filters.append(Claim.claimant_id == current_user.id)

    base_query = db.query(Claim).filter(*filters)

    def _sum_amount(status_list: list[str], amount_field) -> float:
        result = (
            db.query(func.sum(amount_field))
            .filter(*filters, Claim.status.in_(status_list))
            .scalar()
        )
        return round(result or 0.0, 2)

    def _count(status_list: list[str]) -> int:
        return base_query.filter(Claim.status.in_(status_list)).count()

    return {
        "pending_count": _count(["submitted", "under_review"]),
        "pending_amount": _sum_amount(["submitted", "under_review"], Claim.claimed_amount),
        "approved_count": _count(["approved", "partially_approved"]),
        "approved_amount": _sum_amount(["approved", "partially_approved"], Claim.approved_amount),
        "paid_count": _count(["paid"]),
        "paid_amount": _sum_amount(["paid"], Claim.paid_amount),
        "rejected_count": _count(["rejected"]),
        "rejected_amount": _sum_amount(["rejected"], Claim.claimed_amount),
    }
