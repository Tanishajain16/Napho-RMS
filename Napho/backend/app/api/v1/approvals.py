from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_org, require_roles
from app.database import get_db
from app.models.claim import Claim, ClaimApproval
from app.models.user import User
from app.schemas.claim import ApproveRequest, ClaimDetail, ClaimOut, MarkPaidRequest, RejectRequest
from app.schemas.common import PaginatedResponse
from app.services import approval_service
from app.api.v1.claims import _claim_to_detail, _claim_to_out, _viewer_approval_info

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/approvals", tags=["Approvals"])


@router.get("/queue", response_model=PaginatedResponse[ClaimOut])
def get_approval_queue(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles("approver", "admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ClaimOut]:
    """Return claims for a Review Queue tab: pending | approved | rejected | all."""
    from app.core.dependencies import _get_user_role_names

    claims, total = approval_service.get_approval_queue(
        current_user, org.id, db,
        status_filter=status,
        page=page,
        page_size=page_size,
    )
    roles = _get_user_role_names(current_user, db, org.id)
    return PaginatedResponse(
        items=[_claim_to_out(c, **_viewer_approval_info(c, current_user, roles)) for c in claims],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.post("/{claim_id}/approve", response_model=ClaimDetail)
def approve_claim(
    claim_id: str,
    body: ApproveRequest,
    current_user=Depends(require_roles("approver", "admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Approve or partially approve a submitted claim."""
    claim = approval_service.approve_claim(
        claim_id, current_user, org.id,
        approved_amount=body.approved_amount,
        comment=body.comment,
        db=db,
    )
    return _claim_to_detail(claim)


@router.post("/{claim_id}/reject", response_model=ClaimDetail)
def reject_claim(
    claim_id: str,
    body: RejectRequest,
    current_user=Depends(require_roles("approver", "admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Reject a submitted claim."""
    claim = approval_service.reject_claim(
        claim_id, current_user, org.id,
        reason=body.reason,
        db=db,
    )
    return _claim_to_detail(claim)


@router.get("/stats")
def get_approver_stats(
    current_user=Depends(require_roles("approver", "admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> dict:
    """Return summary stats for the manager consolidated view."""
    org_id = org.id
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    base = [Claim.org_id == org_id, Claim.deleted_at.is_(None)]

    pending_count = (
        db.query(func.count(Claim.id))
        .filter(*base, Claim.status.in_(["submitted", "under_review"]))
        .scalar() or 0
    )

    approved_this_month = (
        db.query(func.count(Claim.id))
        .filter(
            *base,
            Claim.status.in_(["approved", "partially_approved", "paid"]),
            Claim.approved_at >= month_start,
        )
        .scalar() or 0
    )

    approved_amount_this_month = (
        db.query(func.sum(Claim.approved_amount))
        .filter(
            *base,
            Claim.status.in_(["approved", "partially_approved", "paid"]),
            Claim.approved_at >= month_start,
        )
        .scalar() or 0.0
    )

    rejected_count = (
        db.query(func.count(Claim.id))
        .filter(*base, Claim.status == "rejected")
        .scalar() or 0
    )

    total_processed = (
        db.query(func.count(Claim.id))
        .filter(*base, Claim.status.in_(["approved", "partially_approved", "paid", "rejected"]))
        .scalar() or 0
    )

    team_rows = (
        db.query(
            User.id,
            User.name,
            User.email,
            Claim.status,
            func.count(Claim.id),
            func.sum(Claim.claimed_amount),
        )
        .join(User, Claim.claimant_id == User.id)
        .filter(*base)
        .group_by(User.id, Claim.status)
        .all()
    )

    team_map: dict = {}
    for uid, name, email, status, count, amount in team_rows:
        if uid not in team_map:
            team_map[uid] = {
                "name": name, "email": email,
                "pending": 0, "approved": 0, "rejected": 0, "paid": 0,
                "total_claims": 0, "total_claimed": 0.0,
            }
        team_map[uid]["total_claims"] += count
        team_map[uid]["total_claimed"] += float(amount or 0.0)
        if status in ("submitted", "under_review"):
            team_map[uid]["pending"] += count
        elif status in ("approved", "partially_approved"):
            team_map[uid]["approved"] += count
        elif status == "rejected":
            team_map[uid]["rejected"] += count
        elif status == "paid":
            team_map[uid]["paid"] += count

    team_breakdown = sorted(
        [
            {**v, "total_claimed": round(v["total_claimed"], 2)}
            for v in team_map.values()
        ],
        key=lambda x: (x["pending"], x["total_claims"]),
        reverse=True,
    )

    return {
        "pending_count": pending_count,
        "approved_this_month": approved_this_month,
        "approved_amount_this_month": round(float(approved_amount_this_month), 2),
        "rejected_count": rejected_count,
        "total_processed": total_processed,
        "team_breakdown": team_breakdown,
    }


@router.post("/{claim_id}/mark-paid", response_model=ClaimDetail)
def mark_claim_paid(
    claim_id: str,
    body: MarkPaidRequest,
    current_user=Depends(require_roles("finance", "admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Mark an approved claim as paid (finance role only)."""
    claim = approval_service.mark_claim_paid(
        claim_id, current_user, org.id,
        payment_date=body.payment_date,
        payment_reference=body.payment_reference,
        db=db,
    )
    return _claim_to_detail(claim)
