from __future__ import annotations

import logging
import math
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_org, get_current_user
from app.database import get_db
from app.schemas.claim import (
    ClaimCreate,
    ClaimDetail,
    ClaimOut,
    ClaimStatsResponse,
    ClaimUpdate,
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.services import claim_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["Claims"])


def _viewer_approval_info(claim, user, roles: list[str]) -> dict:
    """Per-viewer approval fields: can the viewer act now, and what did they decide."""
    from app.services.approval_service import get_actionable_approval, get_my_decision

    info: dict = {"can_act": get_actionable_approval(claim, user, roles) is not None}
    mine = get_my_decision(claim, user)
    if mine is not None:
        if mine.status == "approved":
            partial = (
                mine.approved_amount is not None
                and mine.claimed_amount is not None
                and mine.approved_amount < mine.claimed_amount
            )
            info["my_decision"] = "partially_approved" if partial else "approved"
            info["my_approved_amount"] = mine.approved_amount
        else:
            info["my_decision"] = "rejected"
        info["my_decided_at"] = mine.decided_at
    return info


def _claim_to_detail(claim, **viewer_info) -> ClaimDetail:
    """Convert an ORM Claim to ClaimDetail, handling nested objects."""
    from app.schemas.claim import (
        ApprovalInfo,
        AttachmentOut,
        CategoryInfo,
        ClaimantInfo,
    )
    from app.schemas.claim_history import ActorInfo, ClaimHistoryOut
    from app.schemas.claim_item import ClaimItemOut

    claimant = None
    if claim.claimant:
        claimant = ClaimantInfo(
            id=claim.claimant.id,
            name=claim.claimant.name,
            email=claim.claimant.email,
            avatar_url=claim.claimant.avatar_url,
        )

    category = None
    if claim.category:
        category = CategoryInfo(
            id=claim.category.id,
            name=claim.category.name,
            icon=claim.category.icon,
            code=claim.category.code,
        )

    items = [
        ClaimItemOut(
            id=item.id,
            claim_id=item.claim_id,
            description=item.description,
            amount=item.amount,
            quantity=item.quantity,
            unit_price=item.unit_price,
            expense_date=item.expense_date,
            vendor_name=item.vendor_name,
            category_id=item.category_id,
            receipt_required=item.receipt_required,
            approved_amount=item.approved_amount,
            notes=item.notes,
            sort_order=item.sort_order,
            created_at=item.created_at,
        )
        for item in (claim.items or [])
    ]

    attachments = [
        AttachmentOut(
            id=att.id,
            file_name=att.file_name,
            file_size=att.file_size,
            mime_type=att.mime_type,
            storage_key=att.storage_key,
            is_receipt=att.is_receipt,
            created_at=att.created_at,
        )
        for att in (claim.attachments or [])
        if att.deleted_at is None
    ]

    history_entries = sorted(claim.history or [], key=lambda h: h.created_at)[-20:]
    history = [
        ClaimHistoryOut(
            id=h.id,
            action=h.action,
            from_status=h.from_status,
            to_status=h.to_status,
            from_amount=h.from_amount,
            to_amount=h.to_amount,
            comment=h.comment,
            actor=ActorInfo(
                id=h.actor.id,
                name=h.actor.name,
                email=h.actor.email,
            ) if h.actor else None,
            created_at=h.created_at,
        )
        for h in history_entries
    ]

    approvals = [
        ApprovalInfo(
            id=a.id,
            status=a.status,
            claimed_amount=a.claimed_amount,
            approved_amount=a.approved_amount,
            comment=a.comment,
            decided_at=a.decided_at,
            due_at=a.due_at,
            approver_id=a.approver_id,
        )
        for a in (claim.approvals or [])
    ]

    return ClaimDetail(
        id=claim.id,
        claim_number=claim.claim_number,
        title=claim.title,
        description=claim.description,
        status=claim.status,
        claimed_amount=claim.claimed_amount,
        approved_amount=claim.approved_amount,
        paid_amount=claim.paid_amount,
        currency_code=claim.currency_code,
        expense_date=claim.expense_date,
        submitted_at=claim.submitted_at,
        approved_at=claim.approved_at,
        paid_at=claim.paid_at,
        rejection_reason=claim.rejection_reason,
        version=claim.version,
        category=category,
        claimant=claimant,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        items=items,
        attachments=attachments,
        history=history,
        approvals=approvals,
        **viewer_info,
    )


def _claim_to_out(claim, **viewer_info) -> ClaimOut:
    """Convert an ORM Claim to ClaimOut (summary)."""
    from app.schemas.claim import CategoryInfo, ClaimantInfo

    claimant = None
    if claim.claimant:
        claimant = ClaimantInfo(
            id=claim.claimant.id,
            name=claim.claimant.name,
            email=claim.claimant.email,
            avatar_url=claim.claimant.avatar_url,
        )

    category = None
    if claim.category:
        category = CategoryInfo(
            id=claim.category.id,
            name=claim.category.name,
            icon=claim.category.icon,
            code=claim.category.code,
        )

    return ClaimOut(
        id=claim.id,
        claim_number=claim.claim_number,
        title=claim.title,
        status=claim.status,
        claimed_amount=claim.claimed_amount,
        approved_amount=claim.approved_amount,
        paid_amount=claim.paid_amount,
        currency_code=claim.currency_code,
        expense_date=claim.expense_date,
        submitted_at=claim.submitted_at,
        approved_at=claim.approved_at,
        paid_at=claim.paid_at,
        rejection_reason=claim.rejection_reason,
        version=claim.version,
        category=category,
        claimant=claimant,
        created_at=claim.created_at,
        updated_at=claim.updated_at,
        **viewer_info,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/stats", response_model=ClaimStatsResponse)
def get_stats(
    scope: str = Query(default="mine", pattern="^(mine|org)$",
                       description="mine = your own claims; org = whole organisation (approver/finance/admin)"),
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimStatsResponse:
    """Return aggregate claim statistics for dashboard."""
    stats = claim_service.get_claim_stats(current_user, org.id, db, scope=scope)
    return ClaimStatsResponse(**stats)


@router.get("", response_model=PaginatedResponse[ClaimOut])
def list_claims(
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort: str = Query(default="updated_at_desc"),
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> PaginatedResponse[ClaimOut]:
    """List claims for the current user (or all org claims for privileged roles)."""
    claims, total = claim_service.list_claims(
        current_user, org.id, db,
        status_filter=status,
        page=page,
        page_size=page_size,
        sort=sort,
    )
    return PaginatedResponse(
        items=[_claim_to_out(c) for c in claims],
        total=total,
        page=page,
        page_size=page_size,
        pages=max(1, math.ceil(total / page_size)),
    )


@router.post("", response_model=ClaimDetail, status_code=201)
def create_claim(
    body: ClaimCreate,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Create a new draft claim."""
    claim = claim_service.create_claim(body, current_user, org.id, db)
    return _claim_to_detail(claim)


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(
    claim_id: str,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Get full claim detail."""
    from app.core.dependencies import _get_user_role_names

    claim = claim_service.get_claim(claim_id, current_user, org.id, db)
    roles = _get_user_role_names(current_user, db, org.id)
    return _claim_to_detail(claim, **_viewer_approval_info(claim, current_user, roles))


@router.put("/{claim_id}", response_model=ClaimDetail)
def update_claim(
    claim_id: str,
    body: ClaimUpdate,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Update a draft or rejected claim."""
    claim = claim_service.update_claim(claim_id, body, current_user, org.id, db)
    return _claim_to_detail(claim)


@router.delete("/{claim_id}", response_model=MessageResponse)
def delete_claim(
    claim_id: str,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Soft-delete a draft claim."""
    claim_service.delete_claim(claim_id, current_user, org.id, db)
    return MessageResponse(message="Claim deleted successfully")


@router.post("/{claim_id}/submit", response_model=ClaimDetail)
def submit_claim(
    claim_id: str,
    x_idempotency_key: Annotated[str | None, Header()] = None,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Submit a draft claim for approval (idempotent)."""
    claim = claim_service.submit_claim(
        claim_id, current_user, org.id, db,
        idempotency_key=x_idempotency_key,
    )
    return _claim_to_detail(claim)


@router.post("/{claim_id}/cancel", response_model=ClaimDetail)
def cancel_claim(
    claim_id: str,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Cancel a draft or unreviewed submitted claim."""
    claim = claim_service.cancel_claim(claim_id, current_user, org.id, db)
    return _claim_to_detail(claim)


@router.post("/{claim_id}/resubmit", response_model=ClaimDetail)
def resubmit_claim(
    claim_id: str,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ClaimDetail:
    """Resubmit a rejected claim."""
    claim = claim_service.resubmit_claim(claim_id, current_user, org.id, db)
    return _claim_to_detail(claim)
