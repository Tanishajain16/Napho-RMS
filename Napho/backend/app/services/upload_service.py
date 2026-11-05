from __future__ import annotations

import logging
import os
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.models.base import new_uuid
from app.models.claim import Claim, ClaimAttachment, ClaimHistory
from app.models.user import User
from app.services.claim_service import _append_history

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE  # 10 MB


def _get_upload_path(claim_id: str, filename: str) -> tuple[str, str]:
    """Return (absolute_filesystem_path, storage_key).

    storage_key is relative to UPLOAD_DIR and used as the URL path component.
    """
    safe_name = f"{uuid.uuid4().hex}_{Path(filename).name}"
    storage_key = f"{claim_id}/{safe_name}"
    abs_path = os.path.join(settings.UPLOAD_DIR, claim_id, safe_name)
    return abs_path, storage_key


async def save_attachment(
    claim_id: str,
    file: UploadFile,
    uploader: User,
    org_id: str,
    db: Session,
) -> ClaimAttachment:
    """Validate, save, and record a file attachment for a claim."""
    # Load claim
    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.org_id == org_id,
        Claim.deleted_at.is_(None),
    ).first()

    if claim is None:
        raise NotFoundError("Claim")

    # Permission: owner or privileged
    from app.core.dependencies import _get_user_role_names
    user_roles = _get_user_role_names(uploader, db, org_id)
    is_privileged = any(r in user_roles for r in ("approver", "finance", "admin"))

    if claim.claimant_id != uploader.id and not is_privileged:
        raise ForbiddenError("You do not have permission to upload attachments to this claim")

    # Read file content to check size
    content = await file.read()
    file_size = len(content)

    if file_size > MAX_FILE_SIZE:
        raise ValidationError(
            f"File size ({file_size / 1_048_576:.1f} MB) exceeds the maximum allowed "
            f"size of {MAX_FILE_SIZE / 1_048_576:.0f} MB"
        )

    mime_type = file.content_type or ""
    if mime_type not in ALLOWED_MIME_TYPES:
        raise ValidationError(
            f"File type '{mime_type}' is not allowed. "
            f"Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
        )

    original_filename = file.filename or "upload"
    abs_path, storage_key = _get_upload_path(claim_id, original_filename)

    # Ensure directory exists
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    # Write file
    with open(abs_path, "wb") as fh:
        fh.write(content)

    # Create DB record
    attachment = ClaimAttachment(
        id=new_uuid(),
        claim_id=claim_id,
        uploaded_by=uploader.id,
        file_name=original_filename,
        file_size=file_size,
        mime_type=mime_type,
        storage_key=storage_key,
        storage_provider="local",
        is_receipt=True,
    )
    db.add(attachment)

    _append_history(
        claim, uploader, action="attachment_added",
        from_status=claim.status, to_status=claim.status,
        comment=f"Attachment added: {original_filename}",
        db=db,
    )

    db.commit()
    db.refresh(attachment)
    logger.info(
        "Attachment %s saved for claim %s by user %s",
        storage_key, claim_id, uploader.email,
    )
    return attachment


def delete_attachment(
    claim_id: str,
    attachment_id: str,
    current_user: User,
    org_id: str,
    db: Session,
) -> None:
    """Soft-delete an attachment (owner only, draft claims only)."""
    import datetime as dt

    claim = db.query(Claim).filter(
        Claim.id == claim_id,
        Claim.org_id == org_id,
        Claim.deleted_at.is_(None),
    ).first()

    if claim is None:
        raise NotFoundError("Claim")

    if claim.claimant_id != current_user.id:
        raise ForbiddenError("Only the claim owner can delete attachments")

    if claim.status != "draft":
        raise ConflictError("Attachments can only be deleted from draft claims")

    attachment = db.query(ClaimAttachment).filter(
        ClaimAttachment.id == attachment_id,
        ClaimAttachment.claim_id == claim_id,
        ClaimAttachment.deleted_at.is_(None),
    ).first()

    if attachment is None:
        raise NotFoundError("Attachment")

    # Soft delete
    attachment.deleted_at = dt.datetime.now(dt.timezone.utc)

    # Attempt to remove physical file
    abs_path = os.path.join(settings.UPLOAD_DIR, attachment.storage_key)
    try:
        if os.path.exists(abs_path):
            os.remove(abs_path)
    except OSError as exc:
        logger.warning("Could not delete physical file %s: %s", abs_path, exc)

    _append_history(
        claim, current_user, action="attachment_deleted",
        from_status=claim.status, to_status=claim.status,
        comment=f"Attachment deleted: {attachment.file_name}",
        db=db,
    )

    db.commit()
    logger.info(
        "Attachment %s soft-deleted from claim %s by user %s",
        attachment_id, claim_id, current_user.email,
    )
