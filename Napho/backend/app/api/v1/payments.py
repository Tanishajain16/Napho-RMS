from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, selectinload

from app.api.v1.claims import _claim_to_out
from app.core.dependencies import get_current_org, require_roles
from app.database import get_db
from app.models.claim import Claim
from app.schemas.claim import ClaimOut
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/payments", tags=["Payments"])

# Payments tabs → claim statuses (org-wide; independent of who approved what)
READY_STATUSES = ("approved", "partially_approved")   # fully through the approval chain, not paid yet
PAID_STATUSES = ("paid",)
TAB_STATUSES = {
    "ready": READY_STATUSES,
    "paid": PAID_STATUSES,
    "all": READY_STATUSES + PAID_STATUSES,
}


@router.get("", response_model=PaginatedResponse[ClaimOut])
def list_payments(
    tab: str = Query(default="ready", description="ready | paid | all"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles("finance", "admin")),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ClaimOut]:
    """Claims for the finance Payments page.

    - **ready**: approved / partially approved claims waiting to be paid (oldest approval first)
    - **paid**: claims already paid (most recent payment first)
    - **all**: both
    """
    statuses = TAB_STATUSES.get(tab)
    if statuses is None:
        raise HTTPException(status_code=422, detail="tab must be one of: ready, paid, all")

    query = (
        db.query(Claim)
        .options(selectinload(Claim.claimant), selectinload(Claim.category))
        .filter(
            Claim.org_id == org.id,
            Claim.deleted_at.is_(None),
            Claim.status.in_(statuses),
        )
    )

    if tab == "ready":
        query = query.order_by(Claim.approved_at.asc())
    elif tab == "paid":
        query = query.order_by(Claim.paid_at.desc())
    else:
        # ready-to-pay first, then paid (newest first)
        query = query.order_by(Claim.paid_at.isnot(None), Claim.paid_at.desc(), Claim.approved_at.asc())

    total = query.count()
    claims = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedResponse(
        items=[_claim_to_out(c) for c in claims],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )
