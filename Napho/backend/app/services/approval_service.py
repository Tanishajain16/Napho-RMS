from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.base import new_uuid
from app.models.claim import Claim, ClaimApproval, ClaimHistory
from app.models.user import User
from app.services.claim_service import _append_history, _load_claim_full

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# "Whose turn is it?" — single source of truth used by approve/reject,
# the Review Queue tabs and the claim detail page.
# ---------------------------------------------------------------------------

def _assigned_user_id(approval: ClaimApproval) -> str | None:
    step = approval.step
    if step is not None and step.approver_type == "user":
        return approval.approver_id or step.approver_id
    return None


def _user_matches_step(
    claim: Claim, approval: ClaimApproval, user: User, roles: list[str]
) -> bool:
    """Is `user` an eligible approver for this approval row?

    - approver_type "user": only the specifically assigned person.
    - otherwise (role-based): the assigned person, or anyone holding the step's role —
      EXCEPT someone named on a later level of this claim (e.g. the L2 approver must not
      take L1, otherwise "one decision per person" would leave L2 with nobody to approve).
    """
    step = approval.step
    assigned = _assigned_user_id(approval)
    if assigned is not None:
        return assigned == user.id
    if approval.approver_id == user.id:
        return True
    if step is None or step.approver_role not in roles:
        return False
    for later in claim.approvals or []:
        if (
            later.step is not None
            and later.step.step_order > step.step_order
            and _assigned_user_id(later) == user.id
        ):
            return False
    return True


def _current_pending_approval(claim: Claim) -> ClaimApproval | None:
    """The approval row for the chain level the claim is currently waiting on."""
    pending = [a for a in (claim.approvals or []) if a.status == "pending"]
    if not pending:
        return None
    if claim.current_step_id:
        for a in pending:
            if a.step_id == claim.current_step_id:
                return a
    return min(pending, key=lambda a: a.step.step_order if a.step else 0)


def get_my_decision(claim: Claim, user: User) -> ClaimApproval | None:
    """The approval row this user already decided on this claim (latest), if any."""
    decided = [
        a for a in (claim.approvals or [])
        if a.approver_id == user.id and a.status in ("approved", "rejected")
    ]
    if not decided:
        return None
    return max(decided, key=lambda a: a.decided_at or datetime.min.replace(tzinfo=timezone.utc))


def get_actionable_approval(
    claim: Claim, user: User, roles: list[str]
) -> ClaimApproval | None:
    """Return the approval row `user` can act on right now, or None.

    Rules: claim is awaiting approval, it's not the user's own claim, the user has not
    already decided on this claim (one decision per person — keeps multi-level chains
    meaningful), and the user is eligible for the CURRENT level (levels go in order).
    """
    if claim.status not in ("submitted", "under_review"):
        return None
    if claim.claimant_id == user.id:
        return None
    if get_my_decision(claim, user) is not None:
        return None
    current = _current_pending_approval(claim)
    if current is not None and _user_matches_step(claim, current, user, roles):
        return current
    return None


def _get_pending_approval_for_user(claim: Claim, approver: User, db: Session) -> ClaimApproval | None:
    """Approval row this approver may act on now (see get_actionable_approval)."""
    from app.core.dependencies import _get_user_role_names
    roles = _get_user_role_names(approver, db, claim.org_id)
    return get_actionable_approval(claim, approver, roles)


def _get_next_step(claim: "Claim", current_step_id: str, db: Session):
    """Return the next ApprovalStep in the chain after current_step_id, or None if last."""
    from app.models.approval_chain import ApprovalStep

    if not claim.chain_id:
        return None

    # Get all steps for the chain ordered by step_order
    steps = (
        db.query(ApprovalStep)
        .filter(ApprovalStep.chain_id == claim.chain_id)
        .order_by(ApprovalStep.step_order)
        .all()
    )

    current_order = None
    for s in steps:
        if s.id == current_step_id:
            current_order = s.step_order
            break

    if current_order is None:
        return None

    for s in steps:
        if s.step_order > current_order:
            return s

    return None


def approve_claim(
    claim_id: str,
    approver: User,
    org_id: str,
    approved_amount: float,
    comment: str | None,
    db: Session,
) -> Claim:
    """Approve a claim step. Advances to next step if chain has more steps."""
    from app.models.base import new_uuid
    from app.models.claim import ClaimApproval

    claim = _load_claim_full(claim_id, db)
    if claim is None or claim.org_id != org_id:
        raise NotFoundError("Claim")

    if claim.status not in ("submitted", "under_review"):
        raise ConflictError(
            f"Cannot approve a claim with status '{claim.status}'. "
            "Only submitted or under_review claims can be approved."
        )

    if claim.claimant_id == approver.id:
        raise ForbiddenError("An approver cannot approve their own claim")

    if approved_amount <= 0:
        raise ValidationError("Approved amount must be greater than 0")

    if approved_amount > claim.claimed_amount:
        raise ConflictError(
            f"Approved amount ({approved_amount}) cannot exceed claimed amount "
            f"({claim.claimed_amount})"
        )

    # Find the approval row the current approver should act on
    approval_row = _get_pending_approval_for_user(claim, approver, db)
    if approval_row is None:
        if get_my_decision(claim, approver) is not None:
            raise ConflictError("You have already acted on this claim")
        raise ForbiddenError("You are not the approver for the current level of this claim")

    now = datetime.now(timezone.utc)
    old_status = claim.status

    # Update current approval row
    approval_row.status = "approved"
    approval_row.approved_amount = approved_amount
    approval_row.comment = comment
    approval_row.decided_at = now
    approval_row.approver_id = approver.id

    # Check if there is a next step in the chain
    next_step = _get_next_step(claim, approval_row.step_id, db)

    if next_step is not None:
        # More steps remain — advance to next step
        new_status = "under_review"
        action = "step_approved"

        claim.status = new_status
        claim.current_step_id = next_step.id
        # Do NOT set approved_at yet — not fully approved

        # Create a new pending ClaimApproval for the next step (if not already exists)
        existing_next = db.query(ClaimApproval).filter(
            ClaimApproval.claim_id == claim.id,
            ClaimApproval.step_id == next_step.id,
        ).first()
        if existing_next is None:
            next_approval = ClaimApproval(
                id=new_uuid(),
                claim_id=claim.id,
                step_id=next_step.id,
                approver_id=next_step.approver_id,  # may be None for role-based
                status="pending",
                claimed_amount=claim.claimed_amount,
            )
            db.add(next_approval)

        _append_history(
            claim, approver, action=action,
            from_status=old_status, to_status=new_status,
            from_amount=claim.claimed_amount,
            to_amount=approved_amount,
            comment=comment,
            db=db,
        )

        db.flush()
        db.commit()
        db.refresh(claim)
        logger.info(
            "Claim %s step approved by %s — advanced to next step (step_id: %s)",
            claim.claim_number, approver.email, next_step.id,
        )
        return _load_claim_full(claim.id, db)

    else:
        # Last step — fully approve the claim
        if approved_amount < claim.claimed_amount:
            new_status = "partially_approved"
            action = "partially_approved"
            not_approved = round(claim.claimed_amount - approved_amount, 2)
            claim.rejection_reason = (
                f"₹{not_approved:,.2f} of the claimed amount was not approved. "
                f"Only ₹{approved_amount:,.2f} out of ₹{claim.claimed_amount:,.2f} was sanctioned."
            )
        else:
            new_status = "approved"
            action = "approved"
            claim.rejection_reason = None

        claim.status = new_status
        claim.approved_amount = approved_amount
        claim.approved_at = now
        claim.current_step_id = None

        _append_history(
            claim, approver, action=action,
            from_status=old_status, to_status=new_status,
            from_amount=claim.claimed_amount,
            to_amount=approved_amount,
            comment=comment,
            db=db,
        )

        db.flush()

        from app.services.notification_service import notify_claimant_of_approval
        notify_claimant_of_approval(claim, approver, db)

        db.commit()
        db.refresh(claim)
        logger.info(
            "Claim %s %s by %s (amount: %s)",
            claim.claim_number, new_status, approver.email, approved_amount,
        )
        return _load_claim_full(claim.id, db)


def reject_claim(
    claim_id: str,
    approver: User,
    org_id: str,
    reason: str,
    db: Session,
) -> Claim:
    """Reject a submitted claim."""
    claim = _load_claim_full(claim_id, db)
    if claim is None or claim.org_id != org_id:
        raise NotFoundError("Claim")

    if claim.status not in ("submitted", "under_review"):
        raise ConflictError(
            f"Cannot reject a claim with status '{claim.status}'. "
            "Only submitted or under_review claims can be rejected."
        )

    if claim.claimant_id == approver.id:
        raise ForbiddenError("An approver cannot reject their own claim")

    if len(reason.strip()) < 10:
        raise ValidationError("Rejection reason must be at least 10 characters")

    approval_row = _get_pending_approval_for_user(claim, approver, db)
    if approval_row is None:
        if get_my_decision(claim, approver) is not None:
            raise ConflictError("You have already acted on this claim")
        raise ForbiddenError("You are not the approver for the current level of this claim")

    now = datetime.now(timezone.utc)
    old_status = claim.status

    approval_row.status = "rejected"
    approval_row.comment = reason
    approval_row.decided_at = now
    approval_row.approver_id = approver.id

    claim.status = "rejected"
    claim.rejection_reason = reason
    claim.current_step_id = None

    _append_history(
        claim, approver, action="rejected",
        from_status=old_status, to_status="rejected",
        from_amount=claim.claimed_amount,
        to_amount=0.0,
        comment=reason,
        db=db,
    )

    db.flush()

    from app.services.notification_service import notify_claimant_of_rejection
    notify_claimant_of_rejection(claim, approver, reason, db)

    db.commit()
    db.refresh(claim)
    logger.info("Claim %s rejected by %s", claim.claim_number, approver.email)
    return _load_claim_full(claim.id, db)


def mark_claim_paid(
    claim_id: str,
    finance_user: User,
    org_id: str,
    payment_date: date | None,
    payment_reference: str | None,
    db: Session,
) -> Claim:
    """Mark an approved claim as paid (finance role only)."""
    claim = _load_claim_full(claim_id, db)
    if claim is None or claim.org_id != org_id:
        raise NotFoundError("Claim")

    if claim.status not in ("approved", "partially_approved"):
        raise ConflictError(
            f"Cannot mark a claim with status '{claim.status}' as paid. "
            "Only approved or partially_approved claims can be marked as paid."
        )

    if claim.paid_at is not None:
        raise ConflictError("This claim has already been marked as paid")

    old_status = claim.status
    now = datetime.now(timezone.utc)

    paid_dt = datetime.combine(payment_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    ) if payment_date else now

    claim.status = "paid"
    claim.paid_at = paid_dt
    claim.paid_amount = claim.approved_amount

    comment = f"Payment processed."
    if payment_reference:
        comment += f" Reference: {payment_reference}"

    _append_history(
        claim, finance_user, action="paid",
        from_status=old_status, to_status="paid",
        from_amount=claim.approved_amount,
        to_amount=claim.approved_amount,
        comment=comment,
        db=db,
    )

    db.flush()

    from app.services.notification_service import notify_claimant_of_payment
    notify_claimant_of_payment(claim, db)

    db.commit()
    db.refresh(claim)
    logger.info("Claim %s marked as paid by %s", claim.claim_number, finance_user.email)
    return _load_claim_full(claim.id, db)


def get_approval_queue(
    approver: User,
    org_id: str,
    db: Session,
    status_filter: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Claim], int]:
    """Return (claims, total) for the approver's Review Queue tab.

    Tabs are based on THIS approver's involvement, not just the claim's overall status:
      - pending  : claims waiting for this user's decision at the current level
      - approved : claims this user approved (fully or partially) — even if the claim
                   has since moved on to the next level, been paid, etc.
      - rejected : claims this user rejected
      - all      : all of the above
    """
    from app.core.dependencies import _get_user_role_names
    from app.models.approval_chain import ApprovalStep  # noqa: F401  (ensures mapper loaded)

    roles = _get_user_role_names(approver, db, org_id)
    tab = status_filter or "pending"

    candidates = (
        db.query(Claim)
        .options(
            selectinload(Claim.claimant),
            selectinload(Claim.category),
            selectinload(Claim.approvals).selectinload(ClaimApproval.step),
        )
        .filter(
            Claim.org_id == org_id,
            Claim.deleted_at.is_(None),
            Claim.status != "draft",
            Claim.id.in_(db.query(ClaimApproval.claim_id)),
        )
        .all()
    )

    _epoch = datetime.min.replace(tzinfo=timezone.utc)

    def _aware(dt):
        if dt is None:
            return _epoch
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    pending, approved, rejected = [], [], []
    for claim in candidates:
        mine = get_my_decision(claim, approver)
        if mine is not None:
            (approved if mine.status == "approved" else rejected).append((claim, mine))
        elif get_actionable_approval(claim, approver, roles) is not None:
            pending.append(claim)

    # Pending: oldest submission first. Decided: most recent decision first.
    pending.sort(key=lambda c: _aware(c.submitted_at))
    by_decision = lambda pairs: [c for c, a in sorted(pairs, key=lambda p: _aware(p[1].decided_at), reverse=True)]

    if tab == "pending":
        result = pending
    elif tab == "approved":
        result = by_decision(approved)
    elif tab == "rejected":
        result = by_decision(rejected)
    else:  # "all"
        result = pending + by_decision(approved + rejected)

    total = len(result)
    offset = (page - 1) * page_size
    claims = result[offset: offset + page_size]

    return claims, total
