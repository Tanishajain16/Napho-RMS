from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_org, require_roles
from app.database import get_db
from app.models.claim import Claim, ClaimApproval
from app.models.expense_category import ExpenseCategory
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/overview")
def analytics_overview(
    current_user=Depends(require_roles("admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> dict:
    """Return org-level analytics. Admin only."""
    org_id = org.id

    base = db.query(Claim).filter(
        Claim.org_id == org_id,
        Claim.deleted_at.is_(None),
    )

    # ---- Totals ----
    total_claims = base.count()

    total_amount_claimed = (
        db.query(func.sum(Claim.claimed_amount))
        .filter(Claim.org_id == org_id, Claim.deleted_at.is_(None))
        .scalar() or 0.0
    )

    total_amount_approved = (
        db.query(func.sum(Claim.approved_amount))
        .filter(
            Claim.org_id == org_id,
            Claim.deleted_at.is_(None),
            Claim.status.in_(["approved", "partially_approved", "paid"]),
        )
        .scalar() or 0.0
    )

    total_amount_paid = (
        db.query(func.sum(Claim.paid_amount))
        .filter(
            Claim.org_id == org_id,
            Claim.deleted_at.is_(None),
            Claim.status == "paid",
        )
        .scalar() or 0.0
    )

    # ---- Claims by status ----
    status_rows = (
        db.query(Claim.status, func.count(Claim.id))
        .filter(Claim.org_id == org_id, Claim.deleted_at.is_(None))
        .group_by(Claim.status)
        .all()
    )
    claims_by_status = {row[0]: row[1] for row in status_rows}

    # ---- Claims by category ----
    cat_rows = (
        db.query(
            ExpenseCategory.name,
            func.sum(Claim.claimed_amount),
            func.count(Claim.id),
        )
        .join(ExpenseCategory, Claim.category_id == ExpenseCategory.id, isouter=True)
        .filter(Claim.org_id == org_id, Claim.deleted_at.is_(None))
        .group_by(ExpenseCategory.name)
        .all()
    )
    claims_by_category = [
        {"name": row[0] or "Uncategorized", "amount": round(row[1] or 0.0, 2), "count": row[2]}
        for row in cat_rows
    ]

    # ---- Spending by month ----
    # Use submitted_at for month bucketing; SQLite strftime
    month_rows = (
        db.query(
            func.strftime("%Y-%m", Claim.submitted_at).label("month"),
            func.sum(Claim.claimed_amount),
            func.count(Claim.id),
        )
        .filter(
            Claim.org_id == org_id,
            Claim.deleted_at.is_(None),
            Claim.submitted_at.isnot(None),
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    spending_by_month = [
        {"month": row[0], "amount": round(row[1] or 0.0, 2), "count": row[2]}
        for row in month_rows
    ]

    # ---- Top claimants ----
    claimant_rows = (
        db.query(
            User.name,
            User.email,
            func.sum(Claim.claimed_amount),
            func.count(Claim.id),
        )
        .join(User, Claim.claimant_id == User.id)
        .filter(Claim.org_id == org_id, Claim.deleted_at.is_(None))
        .group_by(User.id)
        .order_by(func.sum(Claim.claimed_amount).desc())
        .limit(10)
        .all()
    )
    top_claimants = [
        {
            "name": row[0],
            "email": row[1],
            "total_claimed": round(row[2] or 0.0, 2),
            "count": row[3],
        }
        for row in claimant_rows
    ]

    # ---- Approval rate ----
    # % of non-rejected claims (approved + partially_approved + paid) over total submitted
    submitted_count = base.filter(
        Claim.status.in_(["submitted", "under_review", "approved", "partially_approved", "paid", "rejected"])
    ).count()
    approved_count = base.filter(
        Claim.status.in_(["approved", "partially_approved", "paid"])
    ).count()
    approval_rate = round((approved_count / submitted_count * 100) if submitted_count > 0 else 0.0, 2)

    # ---- Average approval days ----
    approved_rows = (
        db.query(Claim.submitted_at, Claim.approved_at)
        .filter(
            Claim.org_id == org_id,
            Claim.deleted_at.is_(None),
            Claim.submitted_at.isnot(None),
            Claim.approved_at.isnot(None),
        )
        .all()
    )

    if approved_rows:
        total_days = 0.0
        valid = 0
        for submitted_at, approved_at in approved_rows:
            try:
                if isinstance(submitted_at, str):
                    submitted_at = datetime.fromisoformat(submitted_at)
                if isinstance(approved_at, str):
                    approved_at = datetime.fromisoformat(approved_at)
                diff = (approved_at - submitted_at).total_seconds() / 86400.0
                if diff >= 0:
                    total_days += diff
                    valid += 1
            except Exception:
                pass
        avg_approval_days = round(total_days / valid, 2) if valid > 0 else 0.0
    else:
        avg_approval_days = 0.0

    return {
        "total_claims": total_claims,
        "total_amount_claimed": round(total_amount_claimed, 2),
        "total_amount_approved": round(total_amount_approved, 2),
        "total_amount_paid": round(total_amount_paid, 2),
        "claims_by_status": claims_by_status,
        "claims_by_category": claims_by_category,
        "spending_by_month": spending_by_month,
        "top_claimants": top_claimants,
        "approval_rate": approval_rate,
        "avg_approval_days": avg_approval_days,
    }
