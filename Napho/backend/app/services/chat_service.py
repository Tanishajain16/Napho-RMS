from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, date as date_type
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

MODEL = "claude-haiku-4-5-20251001"
MAX_HISTORY = 10


# ---------------------------------------------------------------------------
# System prompts
# ---------------------------------------------------------------------------

_PLAIN_TEXT_INSTRUCTION = (
    " Always reply in plain conversational sentences. "
    "Do not use markdown — no asterisks, no hyphens for bullets, no headers, no backticks, no tables. "
    "Use Indian Rupee symbol ₹ for amounts, not dollar signs. "
    "Keep responses concise and friendly. "
    "When describing claims, always state the claim number, title, claimed amount, approved amount (if any), and status. "
    "For partial approvals, clearly say how much was approved and how much was not approved. "
    "For multi-step approvals, name each approver by name (e.g. L1 approved by Priya Sharma, L2 pending with Rahul Verma). "
    "Before creating a claim, always confirm the title, amount, and category with the user. "
    "Never invent data — only report what the tools return."
)

SYSTEM_PROMPTS = {
    "employee": (
        "You are a helpful AI assistant for Napho RMS, a reimbursement management system. "
        "Help the employee check their claim status, understand approvals, and submit new claims. "
        "When asked about pending, approved, rejected, or paid claims always call get_my_claim_summary first for totals, "
        "then get_my_claims if the user wants a list. "
        "When the user wants to create a claim, ask for the title, amount, category, and date if not provided, "
        "then call create_claim once you have the required fields. "
        "After creating, ask if they want to submit it now — if yes, call submit_draft_claim with the returned claim_id. "
        "When the user asks to submit a saved draft, first call get_my_claims with status=draft to find the claim, then call submit_draft_claim."
        + _PLAIN_TEXT_INSTRUCTION
    ),
    "approver": (
        "You are a helpful AI assistant for Napho RMS. Help the approver manage their review queue, "
        "check pending claims, and approve or reject them on request. "
        "Always call get_pending_approvals before listing claims to review."
        + _PLAIN_TEXT_INSTRUCTION
    ),
    "admin": (
        "You are a helpful AI assistant for Napho RMS with full access to all organizational data. "
        "You can help with: org analytics and spending patterns, user management (roles, claim counts, departments), "
        "approval chain configuration (who approves at L1/L2/L3), looking up specific users' claims, "
        "and answering any reimbursement-related questions. "
        "When asked about users, call get_all_users. For approval workflows, call get_approval_chains. "
        "For a specific user's claims, call get_user_claims with their email. "
        "For org-wide numbers, call get_org_analytics."
        + _PLAIN_TEXT_INSTRUCTION
    ),
    "finance": (
        "You are a helpful AI assistant for Napho RMS. Help the finance team process payments, "
        "review approved claims, and track payment history."
        + _PLAIN_TEXT_INSTRUCTION
    ),
}


# ---------------------------------------------------------------------------
# Tool definitions per role
# ---------------------------------------------------------------------------

def _tools_for_roles(roles: list[str]) -> list[dict]:
    tools = [
        {
            "name": "get_my_claim_summary",
            "description": (
                "Get a summary of the current user's claims grouped by status — "
                "how many are pending, approved, rejected, paid, and their total amounts. "
                "Call this whenever the user asks about their overall claim status or totals."
            ),
            "input_schema": {"type": "object", "properties": {}},
        },
        {
            "name": "get_my_claims",
            "description": "Get a list of the current user's claims. Optionally filter by status.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status: draft, submitted, under_review, approved, partially_approved, rejected, paid",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of claims to return (default 10)",
                        "default": 10,
                    },
                },
            },
        },
        {
            "name": "get_claim_detail",
            "description": "Get full detail of a single claim by its ID, including approval chain info.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "The claim ID"},
                },
                "required": ["claim_id"],
            },
        },
        {
            "name": "create_claim",
            "description": (
                "Create a new expense claim as a draft on behalf of the current user. "
                "Ask for any missing required fields (title, amount, category_name) before calling. "
                "After creating, offer to submit it immediately or leave as draft."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Brief title for the expense (e.g. 'Team lunch', 'Flight to Delhi')"},
                    "amount": {"type": "number", "description": "Total amount in INR"},
                    "category_name": {
                        "type": "string",
                        "description": "Expense category. Options: Travel, Food & Meals, Office Supplies, Equipment, Flight, Hotel, Local Transport, Team Lunch, Client Entertainment",
                    },
                    "description": {"type": "string", "description": "Optional longer description of the expense"},
                    "expense_date": {"type": "string", "description": "Date of expense in YYYY-MM-DD format (defaults to today)"},
                },
                "required": ["title", "amount", "category_name"],
            },
        },
        {
            "name": "submit_draft_claim",
            "description": (
                "Submit a saved draft claim for approval. "
                "Use this after create_claim if the user confirms they want to submit immediately, "
                "or when the user asks to submit a specific draft by claim number or ID."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string", "description": "The claim ID (not claim number)"},
                },
                "required": ["claim_id"],
            },
        },
    ]

    # Admins (without the employee role) have no "My Claims" / "New Claim":
    # drop the personal claim tools, keep get_claim_detail for looking up claims.
    if "admin" in roles and "employee" not in roles:
        personal = {"get_my_claim_summary", "get_my_claims", "create_claim", "submit_draft_claim"}
        tools = [t for t in tools if t["name"] not in personal]

    if any(r in roles for r in ("approver", "admin")):
        tools += [
            {
                "name": "get_pending_approvals",
                "description": "Get claims waiting for approval in the approver's queue.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum claims to return (default 10)",
                            "default": 10,
                        },
                    },
                },
            },
            {
                "name": "approve_claim",
                "description": "Approve a claim with an approved amount and optional comment.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string", "description": "Claim ID to approve"},
                        "approved_amount": {"type": "number", "description": "Amount to approve"},
                        "comment": {"type": "string", "description": "Optional approval comment"},
                    },
                    "required": ["claim_id", "approved_amount"],
                },
            },
            {
                "name": "reject_claim",
                "description": "Reject a claim with a reason.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "claim_id": {"type": "string", "description": "Claim ID to reject"},
                        "reason": {"type": "string", "description": "Reason for rejection (min 10 chars)"},
                    },
                    "required": ["claim_id", "reason"],
                },
            },
        ]

    if "admin" in roles:
        tools += [
            {
                "name": "get_org_analytics",
                "description": "Get analytics overview for the organization.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_all_users",
                "description": "Get all users in the organization with their roles, claim counts, and department.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_approval_chains",
                "description": (
                    "Get all approval chains configured for the organization. "
                    "Each chain shows its steps (L1, L2, L3 approvers by name), "
                    "amount range, active status, and how many claims use it."
                ),
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_user_claims",
                "description": "Get claims for a specific user by their email address.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "email": {"type": "string", "description": "The user's email address"},
                        "status": {"type": "string", "description": "Optional status filter"},
                        "limit": {"type": "integer", "description": "Max results (default 10)", "default": 10},
                    },
                    "required": ["email"],
                },
            },
        ]

    return tools


# ---------------------------------------------------------------------------
# Tool executors
# ---------------------------------------------------------------------------

def _execute_tool(
    tool_name: str,
    tool_input: dict,
    user: User,
    org_id: str,
    roles: list[str],
    db: Session,
) -> Any:
    """Execute a tool call and return a JSON-serialisable result."""

    if tool_name == "get_my_claim_summary":
        from app.models.claim import Claim
        from sqlalchemy import func

        rows = (
            db.query(Claim.status, func.count(Claim.id), func.sum(Claim.claimed_amount), func.sum(Claim.approved_amount), func.sum(Claim.paid_amount))
            .filter(Claim.org_id == org_id, Claim.claimant_id == user.id, Claim.deleted_at.is_(None))
            .group_by(Claim.status)
            .all()
        )

        status_map: dict = {}
        for status, count, claimed, approved, paid in rows:
            status_map[status] = {
                "count": count,
                "claimed_amount": round(float(claimed or 0), 2),
                "approved_amount": round(float(approved or 0), 2) if approved else None,
                "paid_amount": round(float(paid or 0), 2) if paid else None,
            }

        pending_statuses = ["submitted", "under_review"]
        pending_count = sum(status_map.get(s, {}).get("count", 0) for s in pending_statuses)
        pending_amount = sum(status_map.get(s, {}).get("claimed_amount", 0) for s in pending_statuses)

        approved_statuses = ["approved", "partially_approved"]
        approved_count = sum(status_map.get(s, {}).get("count", 0) for s in approved_statuses)
        approved_amount = sum(status_map.get(s, {}).get("approved_amount", 0) or 0 for s in approved_statuses)

        rejected_count = status_map.get("rejected", {}).get("count", 0)
        rejected_amount = status_map.get("rejected", {}).get("claimed_amount", 0)

        paid_count = status_map.get("paid", {}).get("count", 0)
        paid_amount = status_map.get("paid", {}).get("paid_amount", 0) or 0

        draft_count = status_map.get("draft", {}).get("count", 0)
        total = sum(v.get("count", 0) for v in status_map.values())

        return {
            "total_claims": total,
            "draft": {"count": draft_count},
            "pending_approval": {"count": pending_count, "total_claimed": pending_amount},
            "approved": {"count": approved_count, "total_approved": approved_amount},
            "rejected": {"count": rejected_count, "total_claimed_rejected": rejected_amount},
            "paid": {"count": paid_count, "total_paid": paid_amount},
        }

    elif tool_name == "get_my_claims":
        from app.models.claim import Claim

        limit = int(tool_input.get("limit", 10))
        status_filter = tool_input.get("status")

        query = db.query(Claim).filter(
            Claim.org_id == org_id,
            Claim.claimant_id == user.id,
            Claim.deleted_at.is_(None),
        )
        if status_filter:
            if status_filter == "pending":
                query = query.filter(Claim.status.in_(["submitted", "under_review"]))
            else:
                query = query.filter(Claim.status == status_filter)

        claims = query.order_by(Claim.submitted_at.desc()).limit(limit).all()

        return [
            {
                "id": c.id,
                "claim_number": c.claim_number,
                "title": c.title,
                "status": c.status,
                "claimed_amount": c.claimed_amount,
                "approved_amount": c.approved_amount,
                "paid_amount": c.paid_amount,
                "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
                "approved_at": c.approved_at.isoformat() if c.approved_at else None,
                "not_approved_amount": round(c.claimed_amount - (c.approved_amount or 0), 2) if c.status == "partially_approved" else None,
            }
            for c in claims
        ]

    elif tool_name == "get_claim_detail":
        from app.services.claim_service import _load_claim_full

        claim_id = tool_input.get("claim_id", "")
        claim = _load_claim_full(claim_id, db)
        if not claim or claim.org_id != org_id:
            return {"error": "Claim not found"}

        if claim.claimant_id != user.id:
            if "admin" not in roles and "approver" not in roles:
                return {"error": "Access denied"}
            if claim.status == "draft":  # unsubmitted drafts are private to their owner
                return {"error": "Claim not found"}

        # Build approval chain detail
        approval_chain = []
        for a in sorted(claim.approvals or [], key=lambda x: (x.step.step_order if x.step else 0)):
            step = a.step
            approver_user = db.query(User).filter_by(id=a.approver_id).first() if a.approver_id else None
            approval_chain.append({
                "level": f"L{step.step_order}" if step else "L?",
                "approver_name": approver_user.name if approver_user else "Any approver",
                "status": a.status,
                "approved_amount": a.approved_amount,
                "comment": a.comment,
                "decided_at": a.decided_at.isoformat() if a.decided_at else None,
            })

        not_approved = None
        if claim.status == "partially_approved" and claim.approved_amount is not None:
            not_approved = round(claim.claimed_amount - claim.approved_amount, 2)

        return {
            "id": claim.id,
            "claim_number": claim.claim_number,
            "title": claim.title,
            "description": claim.description,
            "status": claim.status,
            "claimed_amount": claim.claimed_amount,
            "approved_amount": claim.approved_amount,
            "not_approved_amount": not_approved,
            "paid_amount": claim.paid_amount,
            "currency_code": claim.currency_code,
            "expense_date": str(claim.expense_date),
            "submitted_at": claim.submitted_at.isoformat() if claim.submitted_at else None,
            "approved_at": claim.approved_at.isoformat() if claim.approved_at else None,
            "rejection_reason": claim.rejection_reason,
            "approval_chain": approval_chain,
            "items": [
                {
                    "description": item.description,
                    "amount": item.amount,
                    "vendor_name": item.vendor_name,
                }
                for item in (claim.items or [])
            ],
        }

    elif tool_name == "create_claim":
        from app.models.expense_category import ExpenseCategory
        from app.services.claim_service import create_claim as svc_create
        from app.schemas.claim import ClaimCreate
        from app.schemas.claim_item import ClaimItemCreate

        title = tool_input.get("title", "").strip()
        amount_raw = tool_input.get("amount", 0)
        category_name = tool_input.get("category_name", "").strip()
        description = tool_input.get("description", "").strip() or None
        expense_date_str = tool_input.get("expense_date")

        if not title:
            return {"error": "Title is required to create a claim"}
        try:
            amount = float(amount_raw)
        except (TypeError, ValueError):
            return {"error": "Amount must be a number"}
        if amount <= 0:
            return {"error": "Amount must be greater than 0"}

        # Match category by name (case-insensitive partial match)
        all_cats = db.query(ExpenseCategory).filter(
            ExpenseCategory.org_id == org_id,
            ExpenseCategory.is_active == True,
        ).all()
        category = None
        if category_name and all_cats:
            name_lower = category_name.lower()
            for cat in all_cats:
                if name_lower in cat.name.lower() or cat.name.lower() in name_lower:
                    category = cat
                    break
            if category is None:
                # Fuzzy: pick first word match
                for cat in all_cats:
                    if any(w in cat.name.lower() for w in name_lower.split()):
                        category = cat
                        break
            if category is None and all_cats:
                category = all_cats[0]

        expense_date = date_type.today()
        if expense_date_str:
            try:
                expense_date = date_type.fromisoformat(expense_date_str)
            except Exception:
                pass

        try:
            claim_data = ClaimCreate(
                title=title,
                description=description,
                category_id=category.id if category else None,
                expense_date=expense_date,
                items=[ClaimItemCreate(
                    description=title,
                    amount=amount,
                    quantity=1,
                    unit_price=amount,
                    sort_order=0,
                )],
            )
            claim = svc_create(claim_data, user, org_id, db)
            db.commit()
            return {
                "success": True,
                "claim_id": claim.id,
                "claim_number": claim.claim_number,
                "title": claim.title,
                "claimed_amount": claim.claimed_amount,
                "category": category.name if category else "Uncategorized",
                "status": "draft",
                "next_step": "The claim has been saved as a draft. Go to My Claims in the dashboard to review and submit it for approval.",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    elif tool_name == "submit_draft_claim":
        from app.services.claim_service import submit_claim as svc_submit

        claim_id = tool_input.get("claim_id", "")
        try:
            claim = svc_submit(claim_id, user, org_id, db)
            db.commit()
            return {
                "success": True,
                "claim_number": claim.claim_number,
                "title": claim.title,
                "status": claim.status,
                "claimed_amount": claim.claimed_amount,
                "message": f"Claim {claim.claim_number} has been submitted for approval and is now awaiting review.",
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    elif tool_name == "get_pending_approvals":
        from app.services.approval_service import get_approval_queue

        limit = int(tool_input.get("limit", 10))
        claims, _ = get_approval_queue(user, org_id, db, page_size=limit)

        return [
            {
                "id": c.id,
                "claim_number": c.claim_number,
                "title": c.title,
                "status": c.status,
                "claimed_amount": c.claimed_amount,
                "claimant": c.claimant.name if c.claimant else None,
                "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
            }
            for c in claims
        ]

    elif tool_name == "approve_claim":
        from app.services.approval_service import approve_claim as svc_approve

        try:
            claim = svc_approve(
                claim_id=tool_input["claim_id"],
                approver=user,
                org_id=org_id,
                approved_amount=float(tool_input["approved_amount"]),
                comment=tool_input.get("comment"),
                db=db,
            )
            is_partial = claim.status == "partially_approved"
            return {
                "success": True,
                "claim_number": claim.claim_number,
                "status": claim.status,
                "approved_amount": claim.approved_amount,
                "not_approved_amount": round(claim.claimed_amount - (claim.approved_amount or 0), 2) if is_partial else None,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    elif tool_name == "reject_claim":
        from app.services.approval_service import reject_claim as svc_reject

        try:
            claim = svc_reject(
                claim_id=tool_input["claim_id"],
                approver=user,
                org_id=org_id,
                reason=tool_input["reason"],
                db=db,
            )
            return {
                "success": True,
                "claim_number": claim.claim_number,
                "status": claim.status,
            }
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    elif tool_name == "get_org_analytics":
        from app.models.claim import Claim
        from sqlalchemy import func

        total_claims = db.query(Claim).filter(
            Claim.org_id == org_id, Claim.deleted_at.is_(None)
        ).count()

        total_amount_claimed = (
            db.query(func.sum(Claim.claimed_amount))
            .filter(Claim.org_id == org_id, Claim.deleted_at.is_(None))
            .scalar() or 0.0
        )

        status_rows = (
            db.query(Claim.status, func.count(Claim.id))
            .filter(Claim.org_id == org_id, Claim.deleted_at.is_(None))
            .group_by(Claim.status)
            .all()
        )

        return {
            "total_claims": total_claims,
            "total_amount_claimed": round(total_amount_claimed, 2),
            "claims_by_status": {row[0]: row[1] for row in status_rows},
        }

    elif tool_name == "get_all_users":
        from app.models.user import UserOrgMembership
        from app.models.claim import Claim
        from sqlalchemy import func

        memberships = db.query(UserOrgMembership).filter(
            UserOrgMembership.org_id == org_id
        ).all()
        user_ids = [m.user_id for m in memberships]

        users = db.query(User).filter(User.id.in_(user_ids)).all()

        claim_counts = dict(
            db.query(Claim.claimant_id, func.count(Claim.id))
            .filter(Claim.org_id == org_id, Claim.deleted_at.is_(None))
            .group_by(Claim.claimant_id)
            .all()
        )

        from app.core.dependencies import _get_user_role_names
        from app.models.user import UserOrgMembership
        memberships_map = {
            m.user_id: m
            for m in db.query(UserOrgMembership).filter(UserOrgMembership.org_id == org_id).all()
        }
        from app.core.dependencies import _get_user_role_names
        return [
            {
                "id": u.id,
                "name": u.name,
                "email": u.email,
                "is_active": u.is_active,
                "roles": _get_user_role_names(u, db, org_id),
                "claim_count": claim_counts.get(u.id, 0),
                "department": memberships_map.get(u.id, None) and memberships_map[u.id].department,
                "designation": memberships_map.get(u.id, None) and memberships_map[u.id].designation,
            }
            for u in users
        ]

    elif tool_name == "get_approval_chains":
        from app.models.approval_chain import ApprovalChain, ApprovalStep
        from app.models.claim import Claim
        from sqlalchemy import func

        chains = db.query(ApprovalChain).filter(
            ApprovalChain.org_id == org_id
        ).all()

        chain_claim_counts = dict(
            db.query(Claim.chain_id, func.count(Claim.id))
            .filter(Claim.org_id == org_id, Claim.deleted_at.is_(None))
            .group_by(Claim.chain_id)
            .all()
        )

        result = []
        for chain in chains:
            steps_out = []
            for step in sorted(chain.steps, key=lambda s: s.step_order):
                approver_name = None
                if step.approver_id:
                    approver_user = db.query(User).filter_by(id=step.approver_id).first()
                    if approver_user:
                        approver_name = approver_user.name
                steps_out.append({
                    "level": f"L{step.step_order}",
                    "approver_type": step.approver_type,
                    "approver_name": approver_name,
                    "approver_role": step.approver_role,
                    "timeout_hours": step.timeout_hours,
                })
            result.append({
                "id": chain.id,
                "name": chain.name,
                "is_active": chain.is_active,
                "min_amount": chain.min_amount,
                "max_amount": chain.max_amount,
                "steps": steps_out,
                "claim_count": chain_claim_counts.get(chain.id, 0),
            })
        return result

    elif tool_name == "get_user_claims":
        from app.models.claim import Claim

        email = tool_input.get("email", "").strip()
        limit = int(tool_input.get("limit", 10))
        status_filter = tool_input.get("status")

        target_user = db.query(User).filter_by(email=email).first()
        if not target_user:
            return {"error": f"No user found with email {email}"}

        query = db.query(Claim).filter(
            Claim.org_id == org_id,
            Claim.claimant_id == target_user.id,
            Claim.deleted_at.is_(None),
        )
        if status_filter:
            query = query.filter(Claim.status == status_filter)

        claims = query.order_by(Claim.submitted_at.desc()).limit(limit).all()
        return {
            "user": {"name": target_user.name, "email": target_user.email},
            "claims": [
                {
                    "claim_number": c.claim_number,
                    "title": c.title,
                    "status": c.status,
                    "claimed_amount": c.claimed_amount,
                    "approved_amount": c.approved_amount,
                    "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
                }
                for c in claims
            ],
        }

    return {"error": f"Unknown tool: {tool_name}"}


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def process_message(
    user: User,
    org_id: str,
    message: str,
    history: list[dict],
    db: Session,
) -> dict:
    """Process a chat message using Claude with tool use."""
    import anthropic

    from app.core.dependencies import _get_user_role_names

    roles = _get_user_role_names(user, db, org_id)

    if "admin" in roles:
        system_prompt = SYSTEM_PROMPTS["admin"]
    elif "approver" in roles:
        system_prompt = SYSTEM_PROMPTS["approver"]
    elif "finance" in roles:
        system_prompt = SYSTEM_PROMPTS["finance"]
    else:
        system_prompt = SYSTEM_PROMPTS["employee"]

    tools = _tools_for_roles(roles)

    trimmed_history = history[-(MAX_HISTORY):]

    messages = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in trimmed_history
    ]
    messages.append({"role": "user", "content": message})

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    tool_calls_made: list[str] = []

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=system_prompt,
            tools=tools,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_calls_made.append(block.name)
                    result = _execute_tool(
                        tool_name=block.name,
                        tool_input=block.input,
                        user=user,
                        org_id=org_id,
                        roles=roles,
                        db=db,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result),
                    })

            messages.append({"role": "user", "content": tool_results})

        else:
            reply_text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    reply_text += block.text

            return {
                "reply": reply_text,
                "tool_calls_made": tool_calls_made,
            }
