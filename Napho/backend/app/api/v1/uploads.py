from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_org, get_current_user
from app.database import get_db
from app.schemas.common import MessageResponse
from app.services import upload_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims", tags=["Uploads"])


class AttachmentResponse:
    """Response shape for uploaded attachments."""
    pass


@router.post("/{claim_id}/attachments")
async def upload_attachment(
    claim_id: str,
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> dict:
    """Upload a receipt/attachment to a claim."""
    attachment = await upload_service.save_attachment(
        claim_id=claim_id,
        file=file,
        uploader=current_user,
        org_id=org.id,
        db=db,
    )
    return {
        "id": attachment.id,
        "file_name": attachment.file_name,
        "file_size": attachment.file_size,
        "mime_type": attachment.mime_type,
        "url": f"/uploads/{attachment.storage_key}",
        "is_receipt": attachment.is_receipt,
        "created_at": attachment.created_at.isoformat(),
    }


@router.delete("/{claim_id}/attachments/{attachment_id}", response_model=MessageResponse)
def delete_attachment(
    claim_id: str,
    attachment_id: str,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Delete an attachment from a draft claim."""
    upload_service.delete_attachment(
        claim_id=claim_id,
        attachment_id=attachment_id,
        current_user=current_user,
        org_id=org.id,
        db=db,
    )
    return MessageResponse(message="Attachment deleted successfully")
