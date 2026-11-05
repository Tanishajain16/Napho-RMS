from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.base import new_uuid
from app.models.claim import Claim
from app.models.notification import Notification
from app.models.role import Role, UserRole
from app.models.user import User

logger = logging.getLogger(__name__)


def _create_notification(
    db: Session,
    org_id: str,
    user_id: str,
    notif_type: str,
    title: str,
    body: str | None,
    entity_id: str | None = None,
    entity_type: str = "claim",
) -> Notification:
    notif = Notification(
        id=new_uuid(),
        org_id=org_id,
        user_id=user_id,
        type=notif_type,
        title=title,
        body=body,
        entity_type=entity_type,
        entity_id=entity_id,
        is_read=False,
    )
    db.add(notif)
    return notif


def _get_approvers_in_org(org_id: str, db: Session) -> list[User]:
    """Return all active users with 'approver' role in the given org."""
    rows = (
        db.query(User)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .filter(
            UserRole.org_id == org_id,
            Role.name == "approver",
            User.is_active == True,  # noqa: E712
            User.deleted_at.is_(None),
        )
        .all()
    )
    return rows


def notify_approvers_of_submission(claim: Claim, db: Session) -> None:
    """Notify all approvers in the org that a claim has been submitted."""
    approvers = _get_approvers_in_org(claim.org_id, db)
    claimant_name = claim.claimant.name if claim.claimant else "Someone"
    body = (
        f"{claimant_name} submitted '{claim.title}' for "
        f"₹{claim.claimed_amount:,.2f} (#{claim.claim_number})."
    )
    for approver in approvers:
        if approver.id == claim.claimant_id:
            continue  # don't notify the submitter
        _create_notification(
            db,
            org_id=claim.org_id,
            user_id=approver.id,
            notif_type="claim_submitted",
            title="New claim awaiting your approval",
            body=body,
            entity_id=claim.id,
        )
    logger.info(
        "Notified %d approver(s) of claim submission %s", len(approvers), claim.claim_number
    )


def notify_claimant_of_approval(claim: Claim, approver: User, db: Session) -> None:
    """Notify the claimant that their claim has been approved."""
    amount = claim.approved_amount or 0.0
    if claim.status == "partially_approved":
        title = "Your claim has been partially approved"
        body = (
            f"Your claim '{claim.title}' was partially approved for "
            f"₹{amount:,.2f} (claimed ₹{claim.claimed_amount:,.2f})."
        )
        notif_type = "claim_partially_approved"
    else:
        title = "Your claim has been approved"
        body = (
            f"Your claim '{claim.title}' for ₹{amount:,.2f} was approved by "
            f"{approver.name}."
        )
        notif_type = "claim_approved"

    _create_notification(
        db,
        org_id=claim.org_id,
        user_id=claim.claimant_id,
        notif_type=notif_type,
        title=title,
        body=body,
        entity_id=claim.id,
    )
    logger.info("Notified claimant %s of approval for claim %s", claim.claimant_id, claim.claim_number)


def notify_claimant_of_rejection(claim: Claim, approver: User, reason: str, db: Session) -> None:
    """Notify the claimant that their claim has been rejected."""
    _create_notification(
        db,
        org_id=claim.org_id,
        user_id=claim.claimant_id,
        notif_type="claim_rejected",
        title="Your claim has been rejected",
        body=(
            f"Your claim '{claim.title}' was rejected by {approver.name}. "
            f"Reason: {reason}"
        ),
        entity_id=claim.id,
    )
    logger.info("Notified claimant %s of rejection for claim %s", claim.claimant_id, claim.claim_number)


def notify_claimant_of_payment(claim: Claim, db: Session) -> None:
    """Notify the claimant that their claim has been paid."""
    amount = claim.paid_amount or claim.approved_amount or 0.0
    _create_notification(
        db,
        org_id=claim.org_id,
        user_id=claim.claimant_id,
        notif_type="payment_done",
        title="Payment processed",
        body=(
            f"Payment of ₹{amount:,.2f} for '{claim.title}' "
            f"(#{claim.claim_number}) has been processed."
        ),
        entity_id=claim.id,
    )
    logger.info("Notified claimant %s of payment for claim %s", claim.claimant_id, claim.claim_number)
