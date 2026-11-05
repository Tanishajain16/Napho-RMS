from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.exceptions import ForbiddenError, NotFoundError
from app.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationListResponse, NotificationOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    """Return the current user's notifications (newest first, max 50)."""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .limit(50)
        .all()
    )

    unread_count = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .count()
    )

    items = [
        NotificationOut(
            id=n.id,
            type=n.type,
            title=n.title,
            body=n.body,
            entity_type=n.entity_type,
            entity_id=n.entity_id,
            is_read=n.is_read,
            read_at=n.read_at,
            created_at=n.created_at,
        )
        for n in notifications
    ]

    return NotificationListResponse(items=items, unread_count=unread_count)


@router.post("/read-all")
def mark_all_read(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Mark all of the current user's notifications as read."""
    now = datetime.now(timezone.utc)
    updated = (
        db.query(Notification)
        .filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        .update({"is_read": True, "read_at": now})
    )
    db.commit()
    logger.info("Marked %d notifications as read for user %s", updated, current_user.id)
    return {"updated": updated}


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_one_read(
    notification_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationOut:
    """Mark a single notification as read."""
    notif = db.query(Notification).filter(
        Notification.id == notification_id,
    ).first()

    if notif is None:
        raise NotFoundError("Notification")

    if notif.user_id != current_user.id:
        raise ForbiddenError("You do not have access to this notification")

    now = datetime.now(timezone.utc)
    notif.is_read = True
    notif.read_at = now
    db.commit()
    db.refresh(notif)

    return NotificationOut(
        id=notif.id,
        type=notif.type,
        title=notif.title,
        body=notif.body,
        entity_type=notif.entity_type,
        entity_id=notif.entity_id,
        is_read=notif.is_read,
        read_at=notif.read_at,
        created_at=notif.created_at,
    )
