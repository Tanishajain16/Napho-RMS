from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_org, get_current_user
from app.database import get_db
from app.services import chat_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: list[ChatMessage] = []


class ChatResponse(BaseModel):
    reply: str
    tool_calls_made: list[str] = []


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    current_user=Depends(get_current_user),
    org=Depends(get_current_org),
    db: Session = Depends(get_db),
) -> ChatResponse:
    """Agentic chat endpoint. Available to all authenticated users."""
    import anthropic

    from app.config import settings

    if not settings.ANTHROPIC_API_KEY.strip():
        raise HTTPException(
            status_code=503,
            detail="The AI assistant isn't set up: ANTHROPIC_API_KEY is missing on the server. "
                   "Add it to backend/.env and restart the backend.",
        )

    history = [{"role": msg.role, "content": msg.content} for msg in body.conversation_history]

    try:
        result = chat_service.process_message(
            user=current_user,
            org_id=org.id,
            message=body.message,
            history=history,
            db=db,
        )
    except anthropic.AuthenticationError:
        logger.warning("Chat failed: Anthropic API key rejected")
        raise HTTPException(503, "The AI assistant's API key was rejected. Check ANTHROPIC_API_KEY in backend/.env.")
    except anthropic.PermissionDeniedError:
        logger.warning("Chat failed: Anthropic API key lacks permission")
        raise HTTPException(503, "The AI assistant's API key doesn't have access to this model.")
    except anthropic.RateLimitError:
        raise HTTPException(429, "The AI assistant is busy right now. Please try again in a moment.")
    except anthropic.APIConnectionError:
        logger.exception("Chat failed: cannot reach Anthropic API")
        raise HTTPException(503, "The AI assistant can't reach its service. Check the server's internet connection.")
    except anthropic.APIStatusError as exc:
        logger.exception("Chat failed: Anthropic API error %s", exc.status_code)
        raise HTTPException(502, "The AI service returned an error. Please try again.")

    return ChatResponse(
        reply=result["reply"],
        tool_calls_made=result["tool_calls_made"],
    )
