"""
seed.py — Idempotent database seed for the Napho RMS demo.

Run from the backend/ directory:
    python seed.py

Running it a second time is safe — it will not create duplicates.
"""

from __future__ import annotations

import sys
import os
from datetime import date, datetime, timedelta

# Make sure we can import `app` when running as a script from backend/
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.database import SessionLocal, init_db
from app.models import (
    AuditLog,
    ApprovalChain,
    ApprovalStep,
    Claim,
    ClaimApproval,
    ClaimHistory,
    ClaimItem,
    ExpenseCategory,
    Notification,
    Organization,
    Permission,
    Role,
    User,
    UserOrgMembership,
    UserRole,
    new_uuid,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def get_or_create(session: Session, model, filters: dict, defaults: dict | None = None):
    """Fetch an existing row or create a new one.  Returns (instance, created)."""
    obj = session.query(model).filter_by(**filters).first()
    if obj is not None:
        return obj, False
    kwargs = {**filters, **(defaults or {})}
    obj = model(**kwargs)
    session.add(obj)
    session.flush()
    return obj, True


# ---------------------------------------------------------------------------
# Seed functions
# ---------------------------------------------------------------------------

def seed_organization(session: Session) -> Organization:
    org, created = get_or_create(
        session,
        Organization,
        filters={"id": "org_napho_demo"},
        defaults={
            "name": "Napho Technologies",
            "slug": "napho-tech",
            "logo_url": None,
            "country_code": "IN",
            "currency_code": "INR",
            "fiscal_year_start_month": 4,
            "settings": "{}",
            "plan": "starter",
            "is_active": True,
        },
    )
    if created:
        print("Created org: Napho Technologies (org_napho_demo)")
    else:
        print("Org already exists — skipping.")
    return org


def seed_roles(session: Session) -> dict[str, Role]:
    role_defs = [
        {"name": "employee",  "description": "Regular employee who submits claims", "is_system": True},
        {"name": "approver",  "description": "Approves/rejects expense claims",      "is_system": True},
        {"name": "finance",   "description": "Finance team — marks claims as paid",  "is_system": True},
        {"name": "admin",     "description": "Full administrative access",            "is_system": True},
    ]
    roles: dict[str, Role] = {}
    created_count = 0
    for rd in role_defs:
        role, created = get_or_create(
            session,
            Role,
            filters={"org_id": None, "name": rd["name"]},
            defaults={"id": new_uuid(), "description": rd["description"], "is_system": rd["is_system"]},
        )
        roles[rd["name"]] = role
        if created:
            created_count += 1
    print(f"Created {created_count} system role(s) (skipped {len(role_defs) - created_count} existing).")

    # Attach basic permissions to each role
    permission_map = {
        "employee": [
            ("claims",   "create"),
            ("claims",   "read"),
            ("claims",   "update"),
        ],
        "approver": [
            ("claims",   "read"),
            ("claims",   "approve"),
            ("claims",   "update"),
            ("reports",  "read"),
        ],
        "finance": [
            ("claims",   "read"),
            ("claims",   "update"),
            ("reports",  "read"),
            ("reports",  "create"),
        ],
        "admin": [
            ("claims",   "create"),
            ("claims",   "read"),
            ("claims",   "update"),
            ("claims",   "delete"),
            ("claims",   "approve"),
            ("users",    "create"),
            ("users",    "read"),
            ("users",    "update"),
            ("users",    "delete"),
            ("reports",  "create"),
            ("reports",  "read"),
            ("policies", "create"),
            ("policies", "read"),
            ("policies", "update"),
            ("policies", "delete"),
        ],
    }
    perm_count = 0
    for role_name, perms in permission_map.items():
        role = roles[role_name]
        for resource, action in perms:
            p, created = get_or_create(
                session,
                Permission,
                filters={"role_id": role.id, "resource": resource, "action": action},
                defaults={"id": new_uuid(), "conditions": "{}"},
            )
            if created:
                perm_count += 1
    print(f"Created {perm_count} permission(s).")
    return roles


def seed_users(
    session: Session, org: Organization, roles: dict[str, Role]
) -> dict[str, User]:
    user_defs = [
        {
            "email": "aryan@napho.com",
            "name": "Aryan Mehta",
            "password": "password123",
            "roles": ["employee"],
            "department": "Engineering",
            "designation": "Software Engineer",
        },
        {
            "email": "sneha@napho.com",
            "name": "Sneha Kapoor",
            "password": "password123",
            "roles": ["employee"],
            "department": "Marketing",
            "designation": "Marketing Analyst",
        },
        {
            "email": "priya@napho.com",
            "name": "Priya Sharma",
            "password": "password123",
            "roles": ["approver"],
            "department": "Engineering",
            "designation": "Engineering Manager",
        },
        {
            "email": "rahul@napho.com",
            "name": "Rahul Verma",
            "password": "password123",
            "roles": ["finance", "approver"],
            "department": "Finance",
            "designation": "Finance Manager",
        },
        {
            "email": "admin@napho.com",
            "name": "Admin User",
            "password": "password123",
            "roles": ["admin"],
            "department": "Operations",
            "designation": "System Administrator",
        },
        {
            "email": "vivek@napho.com",
            "name": "Vivek Nair",
            "password": "password123",
            "roles": ["employee"],
            "department": "Engineering",
            "designation": "Frontend Developer",
        },
        {
            "email": "kavya@napho.com",
            "name": "Kavya Reddy",
            "password": "password123",
            "roles": ["employee"],
            "department": "Design",
            "designation": "UX Designer",
        },
        {
            "email": "amit@napho.com",
            "name": "Amit Singh",
            "password": "password123",
            "roles": ["employee"],
            "department": "Sales",
            "designation": "Sales Executive",
        },
        {
            "email": "deepa@napho.com",
            "name": "Deepa Pillai",
            "password": "password123",
            "roles": ["employee"],
            "department": "HR",
            "designation": "HR Manager",
        },
        {
            "email": "rohit@napho.com",
            "name": "Rohit Joshi",
            "password": "password123",
            "roles": ["employee"],
            "department": "Product",
            "designation": "Product Manager",
        },
    ]

    users: dict[str, User] = {}
    created_count = 0
    for ud in user_defs:
        user, created = get_or_create(
            session,
            User,
            filters={"email": ud["email"]},
            defaults={
                "id": new_uuid(),
                "name": ud["name"],
                "password_hash": hash_password(ud["password"]),
                "is_active": True,
            },
        )
        users[ud["email"]] = user
        if created:
            created_count += 1

        # Membership
        _, mem_created = get_or_create(
            session,
            UserOrgMembership,
            filters={"user_id": user.id, "org_id": org.id},
            defaults={
                "id": new_uuid(),
                "department": ud.get("department"),
                "designation": ud.get("designation"),
                "employee_code": f"EMP-{user.id[:6].upper()}",
                "join_date": date(2023, 1, 15),
                "is_active": True,
            },
        )

        # Role assignments
        for role_name in ud["roles"]:
            role = roles[role_name]
            get_or_create(
                session,
                UserRole,
                filters={"user_id": user.id, "org_id": org.id, "role_id": role.id},
                defaults={"id": new_uuid()},
            )

    print(f"Created {created_count} user(s) (skipped {len(user_defs) - created_count} existing).")
    return users


def seed_expense_categories(session: Session, org: Organization) -> dict[str, ExpenseCategory]:
    categories: dict[str, ExpenseCategory] = {}

    # Root categories
    root_defs = [
        {"code": "TRAVEL",  "name": "Travel",           "requires_receipt": True,  "max_amount": 50000.0, "icon": "airplane",   "sort_order": 1},
        {"code": "FOOD",    "name": "Food & Meals",      "requires_receipt": True,  "max_amount": 5000.0,  "icon": "utensils",   "sort_order": 2},
        {"code": "OFFICE",  "name": "Office Supplies",   "requires_receipt": True,  "max_amount": 10000.0, "icon": "briefcase",  "sort_order": 3},
        {"code": "EQUIP",   "name": "Equipment",         "requires_receipt": True,  "max_amount": 100000.0,"icon": "laptop",     "sort_order": 4},
    ]
    for rd in root_defs:
        cat, _ = get_or_create(
            session,
            ExpenseCategory,
            filters={"org_id": org.id, "code": rd["code"]},
            defaults={
                "id": new_uuid(),
                "name": rd["name"],
                "requires_receipt": rd["requires_receipt"],
                "max_amount": rd["max_amount"],
                "icon": rd["icon"],
                "sort_order": rd["sort_order"],
                "is_active": True,
                "parent_id": None,
            },
        )
        categories[rd["code"]] = cat

    # Child categories
    child_defs = [
        # Travel children
        {"parent": "TRAVEL", "code": "FLIGHT",    "name": "Flight",          "requires_receipt": True,  "max_amount": 30000.0, "sort_order": 1},
        {"parent": "TRAVEL", "code": "HOTEL",     "name": "Hotel",           "requires_receipt": True,  "max_amount": 15000.0, "sort_order": 2},
        {"parent": "TRAVEL", "code": "LOCAL",     "name": "Local Transport", "requires_receipt": False, "max_amount": 2000.0,  "sort_order": 3},
        # Food children
        {"parent": "FOOD",   "code": "TEAM_MEAL", "name": "Team Lunch",      "requires_receipt": True,  "max_amount": 3000.0,  "sort_order": 1},
        {"parent": "FOOD",   "code": "CLIENT_ENT","name": "Client Entertainment","requires_receipt": True,"max_amount": 5000.0, "sort_order": 2},
    ]
    for cd in child_defs:
        parent = categories[cd["parent"]]
        cat, _ = get_or_create(
            session,
            ExpenseCategory,
            filters={"org_id": org.id, "code": cd["code"]},
            defaults={
                "id": new_uuid(),
                "parent_id": parent.id,
                "name": cd["name"],
                "requires_receipt": cd["requires_receipt"],
                "max_amount": cd.get("max_amount"),
                "sort_order": cd["sort_order"],
                "is_active": True,
            },
        )
        categories[cd["code"]] = cat

    print(f"Created/verified {len(categories)} expense categories.")
    return categories


def seed_approval_chain(
    session: Session, org: Organization, roles: dict[str, Role]
) -> tuple[ApprovalChain, ApprovalStep]:
    chain, chain_created = get_or_create(
        session,
        ApprovalChain,
        filters={"org_id": org.id, "name": "Standard Approval"},
        defaults={
            "id": new_uuid(),
            "min_amount": 0.0,
            "max_amount": None,
            "is_active": True,
            "category_id": None,
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    # L1 step — priya@napho.com as explicit approver
    priya = session.query(User).filter_by(email="priya@napho.com").first()
    step_l1, step_l1_created = get_or_create(
        session,
        ApprovalStep,
        filters={"chain_id": chain.id, "step_order": 1},
        defaults={
            "id": new_uuid(),
            "approver_type": "user",
            "approver_id": priya.id if priya else None,
            "approver_role": "approver",
            "timeout_hours": 48,
            "on_timeout": "escalate",
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    # L2 step — rahul@napho.com as explicit approver
    rahul = session.query(User).filter_by(email="rahul@napho.com").first()
    step_l2, step_l2_created = get_or_create(
        session,
        ApprovalStep,
        filters={"chain_id": chain.id, "step_order": 2},
        defaults={
            "id": new_uuid(),
            "approver_type": "user",
            "approver_id": rahul.id if rahul else None,
            "approver_role": "approver",
            "timeout_hours": 48,
            "on_timeout": "escalate",
            "created_at": datetime.utcnow().isoformat(),
        },
    )

    status = "created" if chain_created else "already exists"
    l1_status = "created" if step_l1_created else "already exists"
    l2_status = "created" if step_l2_created else "already exists"
    print(f"Approval chain 'Standard Approval' {status}.")
    print(f"  L1 step (priya@napho.com) {l1_status}.")
    print(f"  L2 step (rahul@napho.com) {l2_status}.")
    return chain, step_l1


def _claim_number(org_id: str, seq: int) -> str:
    year = datetime.utcnow().year
    return f"NAPHO-{year}-{seq:05d}"


def seed_claims(
    session: Session,
    org: Organization,
    users: dict[str, User],
    categories: dict[str, ExpenseCategory],
    chain: ApprovalChain,
    step: ApprovalStep,
) -> None:
    aryan = users["aryan@napho.com"]
    sneha = users["sneha@napho.com"]
    priya = users["priya@napho.com"]
    vivek = users.get("vivek@napho.com")
    kavya = users.get("kavya@napho.com")
    amit = users.get("amit@napho.com")
    deepa = users.get("deepa@napho.com")
    rohit = users.get("rohit@napho.com")
    rahul = users["rahul@napho.com"]

    today = date.today()

    claim_defs = [
        # 1. Draft claim for Aryan
        {
            "id": "claim_aryan_draft_001",
            "org_id": org.id,
            "claimant_id": aryan.id,
            "claim_number": _claim_number(org.id, 1),
            "title": "Team offsite travel expenses",
            "description": "Travel and accommodation for quarterly offsite in Bangalore.",
            "category_id": categories["TRAVEL"].id,
            "status": "draft",
            "claimed_amount": 12500.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=5),
            "submitted_at": None,
            "approved_at": None,
            "paid_at": None,
            "rejection_reason": None,
            "current_step_id": None,
            "chain_id": chain.id,
            "history": [
                {
                    "action": "created",
                    "from_status": None,
                    "to_status": "draft",
                    "from_amount": None,
                    "to_amount": 12500.0,
                    "comment": "Claim created as draft.",
                    "actor_id": aryan.id,
                },
            ],
            "items": [
                {
                    "category_id": categories["FLIGHT"].id,
                    "description": "Return flight BLR-DEL",
                    "amount": 8500.0,
                    "quantity": 1,
                    "unit_price": 8500.0,
                    "vendor_name": "IndiGo",
                    "receipt_required": True,
                    "sort_order": 1,
                },
                {
                    "category_id": categories["HOTEL"].id,
                    "description": "2 nights hotel stay",
                    "amount": 4000.0,
                    "quantity": 2,
                    "unit_price": 2000.0,
                    "vendor_name": "OYO Rooms",
                    "receipt_required": True,
                    "sort_order": 2,
                },
            ],
        },
        # 2. Submitted claim for Aryan (pending review)
        {
            "id": "claim_aryan_submitted_002",
            "org_id": org.id,
            "claimant_id": aryan.id,
            "claim_number": _claim_number(org.id, 2),
            "title": "Client lunch — TechCorp",
            "description": "Business lunch with TechCorp stakeholders.",
            "category_id": categories["CLIENT_ENT"].id,
            "status": "submitted",
            "claimed_amount": 3200.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=10),
            "submitted_at": datetime.utcnow() - timedelta(days=9),
            "approved_at": None,
            "paid_at": None,
            "rejection_reason": None,
            "current_step_id": step.id,
            "chain_id": chain.id,
            "history": [
                {
                    "action": "created",
                    "from_status": None,
                    "to_status": "draft",
                    "from_amount": None,
                    "to_amount": 3200.0,
                    "comment": "Claim created.",
                    "actor_id": aryan.id,
                },
                {
                    "action": "submitted",
                    "from_status": "draft",
                    "to_status": "submitted",
                    "from_amount": None,
                    "to_amount": 3200.0,
                    "comment": "Submitted for approval.",
                    "actor_id": aryan.id,
                },
            ],
            "items": [
                {
                    "category_id": categories["CLIENT_ENT"].id,
                    "description": "Lunch at The Leela — 4 attendees",
                    "amount": 3200.0,
                    "quantity": 1,
                    "unit_price": 3200.0,
                    "vendor_name": "The Leela Restaurant",
                    "receipt_required": True,
                    "sort_order": 1,
                },
            ],
        },
        # 3. Approved claim for Sneha
        {
            "id": "claim_sneha_approved_003",
            "org_id": org.id,
            "claimant_id": sneha.id,
            "claim_number": _claim_number(org.id, 3),
            "title": "Marketing conference registration",
            "description": "Annual digital marketing summit registration fee.",
            "category_id": categories["OFFICE"].id,
            "status": "approved",
            "claimed_amount": 7500.0,
            "approved_amount": 7500.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=20),
            "submitted_at": datetime.utcnow() - timedelta(days=18),
            "approved_at": datetime.utcnow() - timedelta(days=16),
            "paid_at": None,
            "rejection_reason": None,
            "current_step_id": None,
            "chain_id": chain.id,
            "history": [
                {
                    "action": "created",
                    "from_status": None,
                    "to_status": "draft",
                    "from_amount": None,
                    "to_amount": 7500.0,
                    "comment": "Claim created.",
                    "actor_id": sneha.id,
                },
                {
                    "action": "submitted",
                    "from_status": "draft",
                    "to_status": "submitted",
                    "from_amount": None,
                    "to_amount": 7500.0,
                    "comment": "Submitted for approval.",
                    "actor_id": sneha.id,
                },
                {
                    "action": "approved",
                    "from_status": "submitted",
                    "to_status": "approved",
                    "from_amount": 7500.0,
                    "to_amount": 7500.0,
                    "comment": "Approved — valid conference registration.",
                    "actor_id": priya.id,
                },
            ],
            "items": [
                {
                    "category_id": categories["OFFICE"].id,
                    "description": "DigiSummit 2024 registration",
                    "amount": 7500.0,
                    "quantity": 1,
                    "unit_price": 7500.0,
                    "vendor_name": "DigiSummit Events Pvt Ltd",
                    "receipt_required": True,
                    "approved_amount": 7500.0,
                    "sort_order": 1,
                },
            ],
        },
        # 4. Rejected claim for Aryan
        {
            "id": "claim_aryan_rejected_004",
            "org_id": org.id,
            "claimant_id": aryan.id,
            "claim_number": _claim_number(org.id, 4),
            "title": "Personal accessories purchase",
            "description": "Wireless headphones for home use.",
            "category_id": categories["EQUIP"].id,
            "status": "rejected",
            "claimed_amount": 4999.0,
            "approved_amount": 0.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=30),
            "submitted_at": datetime.utcnow() - timedelta(days=28),
            "approved_at": None,
            "paid_at": None,
            "rejection_reason": "Personal use items are not reimbursable under company policy. Only work-specific equipment is covered.",
            "current_step_id": None,
            "chain_id": chain.id,
            "history": [
                {
                    "action": "created",
                    "from_status": None,
                    "to_status": "draft",
                    "from_amount": None,
                    "to_amount": 4999.0,
                    "comment": "Claim created.",
                    "actor_id": aryan.id,
                },
                {
                    "action": "submitted",
                    "from_status": "draft",
                    "to_status": "submitted",
                    "from_amount": None,
                    "to_amount": 4999.0,
                    "comment": None,
                    "actor_id": aryan.id,
                },
                {
                    "action": "rejected",
                    "from_status": "submitted",
                    "to_status": "rejected",
                    "from_amount": 4999.0,
                    "to_amount": 0.0,
                    "comment": "Personal use items are not reimbursable under company policy.",
                    "actor_id": priya.id,
                },
            ],
            "items": [
                {
                    "category_id": categories["EQUIP"].id,
                    "description": "Sony WH-1000XM5 Headphones",
                    "amount": 4999.0,
                    "quantity": 1,
                    "unit_price": 4999.0,
                    "vendor_name": "Amazon.in",
                    "receipt_required": True,
                    "approved_amount": 0.0,
                    "sort_order": 1,
                },
            ],
        },
        # 5. Paid claim for Sneha
        {
            "id": "claim_sneha_paid_005",
            "org_id": org.id,
            "claimant_id": sneha.id,
            "claim_number": _claim_number(org.id, 5),
            "title": "Team lunch — Q3 planning",
            "description": "Team lunch for quarterly planning session.",
            "category_id": categories["TEAM_MEAL"].id,
            "status": "paid",
            "claimed_amount": 2800.0,
            "approved_amount": 2800.0,
            "paid_amount": 2800.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=45),
            "submitted_at": datetime.utcnow() - timedelta(days=43),
            "approved_at": datetime.utcnow() - timedelta(days=41),
            "paid_at": datetime.utcnow() - timedelta(days=35),
            "rejection_reason": None,
            "current_step_id": None,
            "chain_id": chain.id,
            "history": [
                {
                    "action": "created",
                    "from_status": None,
                    "to_status": "draft",
                    "from_amount": None,
                    "to_amount": 2800.0,
                    "comment": "Claim created.",
                    "actor_id": sneha.id,
                },
                {
                    "action": "submitted",
                    "from_status": "draft",
                    "to_status": "submitted",
                    "from_amount": None,
                    "to_amount": 2800.0,
                    "comment": "Submitted for approval.",
                    "actor_id": sneha.id,
                },
                {
                    "action": "approved",
                    "from_status": "submitted",
                    "to_status": "approved",
                    "from_amount": 2800.0,
                    "to_amount": 2800.0,
                    "comment": "Approved — team meals are covered.",
                    "actor_id": priya.id,
                },
                {
                    "action": "paid",
                    "from_status": "approved",
                    "to_status": "paid",
                    "from_amount": 2800.0,
                    "to_amount": 2800.0,
                    "comment": "Payment processed via NEFT.",
                    "actor_id": users["rahul@napho.com"].id,
                },
            ],
            "items": [
                {
                    "category_id": categories["TEAM_MEAL"].id,
                    "description": "Team lunch — 7 members",
                    "amount": 2800.0,
                    "quantity": 7,
                    "unit_price": 400.0,
                    "vendor_name": "Barbeque Nation",
                    "receipt_required": True,
                    "approved_amount": 2800.0,
                    "sort_order": 1,
                },
            ],
        },
        # 6. Submitted travel claim for Vivek
        *([{
            "id": "claim_vivek_submitted_006",
            "org_id": org.id,
            "claimant_id": vivek.id,
            "claim_number": _claim_number(org.id, 101),
            "title": "Client site visit — Mumbai",
            "description": "Flight and accommodation for client visit in Mumbai.",
            "category_id": categories["TRAVEL"].id,
            "status": "submitted",
            "claimed_amount": 18500.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=3),
            "submitted_at": datetime.utcnow() - timedelta(days=2),
            "approved_at": None,
            "paid_at": None,
            "rejection_reason": None,
            "current_step_id": step.id,
            "chain_id": chain.id,
            "history": [
                {"action": "created", "from_status": None, "to_status": "draft", "from_amount": None, "to_amount": 18500.0, "comment": "Claim created.", "actor_id": vivek.id},
                {"action": "submitted", "from_status": "draft", "to_status": "submitted", "from_amount": None, "to_amount": 18500.0, "comment": "Submitted for approval.", "actor_id": vivek.id},
            ],
            "items": [
                {"category_id": categories["FLIGHT"].id, "description": "BOM-DEL return ticket", "amount": 12000.0, "quantity": 1, "unit_price": 12000.0, "vendor_name": "Air India", "receipt_required": True, "sort_order": 1},
                {"category_id": categories["HOTEL"].id, "description": "2 nights at Taj Lands End", "amount": 6500.0, "quantity": 2, "unit_price": 3250.0, "vendor_name": "Taj Hotels", "receipt_required": True, "sort_order": 2},
            ],
        }] if vivek else []),
        # 7. Approved equipment claim for Kavya
        *([{
            "id": "claim_kavya_approved_007",
            "org_id": org.id,
            "claimant_id": kavya.id,
            "claim_number": _claim_number(org.id, 102),
            "title": "Design workstation upgrade",
            "description": "MacBook Pro for design work — approved under equipment policy.",
            "category_id": categories["EQUIP"].id,
            "status": "approved",
            "claimed_amount": 55000.0,
            "approved_amount": 55000.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=25),
            "submitted_at": datetime.utcnow() - timedelta(days=24),
            "approved_at": datetime.utcnow() - timedelta(days=22),
            "paid_at": None,
            "rejection_reason": None,
            "current_step_id": None,
            "chain_id": chain.id,
            "history": [
                {"action": "created", "from_status": None, "to_status": "draft", "from_amount": None, "to_amount": 55000.0, "comment": None, "actor_id": kavya.id},
                {"action": "submitted", "from_status": "draft", "to_status": "submitted", "from_amount": None, "to_amount": 55000.0, "comment": None, "actor_id": kavya.id},
                {"action": "approved", "from_status": "submitted", "to_status": "approved", "from_amount": 55000.0, "to_amount": 55000.0, "comment": "Approved — within equipment policy.", "actor_id": priya.id},
            ],
            "items": [
                {"category_id": categories["EQUIP"].id, "description": "MacBook Pro 14-inch M3", "amount": 55000.0, "quantity": 1, "unit_price": 55000.0, "vendor_name": "Apple India", "receipt_required": True, "approved_amount": 55000.0, "sort_order": 1},
            ],
        }] if kavya else []),
        # 8. Submitted client entertainment for Amit
        *([{
            "id": "claim_amit_submitted_008",
            "org_id": org.id,
            "claimant_id": amit.id,
            "claim_number": _claim_number(org.id, 103),
            "title": "Client dinner — Q4 deal closure",
            "description": "Client dinner for closing the Q4 annual contract.",
            "category_id": categories["CLIENT_ENT"].id,
            "status": "submitted",
            "claimed_amount": 7200.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=4),
            "submitted_at": datetime.utcnow() - timedelta(days=3),
            "approved_at": None,
            "paid_at": None,
            "rejection_reason": None,
            "current_step_id": step.id,
            "chain_id": chain.id,
            "history": [
                {"action": "created", "from_status": None, "to_status": "draft", "from_amount": None, "to_amount": 7200.0, "comment": None, "actor_id": amit.id},
                {"action": "submitted", "from_status": "draft", "to_status": "submitted", "from_amount": None, "to_amount": 7200.0, "comment": None, "actor_id": amit.id},
            ],
            "items": [
                {"category_id": categories["CLIENT_ENT"].id, "description": "Dinner at ITC Maratha — 6 people", "amount": 7200.0, "quantity": 1, "unit_price": 7200.0, "vendor_name": "ITC Hotels", "receipt_required": True, "sort_order": 1},
            ],
        }] if amit else []),
        # 9. Rejected claim for Amit
        *([{
            "id": "claim_amit_rejected_009",
            "org_id": org.id,
            "claimant_id": amit.id,
            "claim_number": _claim_number(org.id, 104),
            "title": "Home office monitor",
            "description": "27-inch monitor for home office setup.",
            "category_id": categories["EQUIP"].id,
            "status": "rejected",
            "claimed_amount": 8999.0,
            "approved_amount": 0.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=35),
            "submitted_at": datetime.utcnow() - timedelta(days=33),
            "approved_at": None,
            "paid_at": None,
            "rejection_reason": "Home office equipment requires pre-approval and must be under ₹7,500 per item.",
            "current_step_id": None,
            "chain_id": chain.id,
            "history": [
                {"action": "created", "from_status": None, "to_status": "draft", "from_amount": None, "to_amount": 8999.0, "comment": None, "actor_id": amit.id},
                {"action": "submitted", "from_status": "draft", "to_status": "submitted", "from_amount": None, "to_amount": 8999.0, "comment": None, "actor_id": amit.id},
                {"action": "rejected", "from_status": "submitted", "to_status": "rejected", "from_amount": 8999.0, "to_amount": 0.0, "comment": "Exceeds limit without pre-approval.", "actor_id": priya.id},
            ],
            "items": [
                {"category_id": categories["EQUIP"].id, "description": "LG 27UK850-W 4K Monitor", "amount": 8999.0, "quantity": 1, "unit_price": 8999.0, "vendor_name": "Croma", "receipt_required": True, "approved_amount": 0.0, "sort_order": 1},
            ],
        }] if amit else []),
        # 10. Paid conference for Deepa
        *([{
            "id": "claim_deepa_paid_010",
            "org_id": org.id,
            "claimant_id": deepa.id,
            "claim_number": _claim_number(org.id, 105),
            "title": "HR Tech Summit 2024",
            "description": "Annual HR technology conference registration and travel.",
            "category_id": categories["OFFICE"].id,
            "status": "paid",
            "claimed_amount": 12000.0,
            "approved_amount": 12000.0,
            "paid_amount": 12000.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=55),
            "submitted_at": datetime.utcnow() - timedelta(days=52),
            "approved_at": datetime.utcnow() - timedelta(days=50),
            "paid_at": datetime.utcnow() - timedelta(days=44),
            "rejection_reason": None,
            "current_step_id": None,
            "chain_id": chain.id,
            "history": [
                {"action": "created", "from_status": None, "to_status": "draft", "from_amount": None, "to_amount": 12000.0, "comment": None, "actor_id": deepa.id},
                {"action": "submitted", "from_status": "draft", "to_status": "submitted", "from_amount": None, "to_amount": 12000.0, "comment": None, "actor_id": deepa.id},
                {"action": "approved", "from_status": "submitted", "to_status": "approved", "from_amount": 12000.0, "to_amount": 12000.0, "comment": "Approved — standard conference registration.", "actor_id": priya.id},
                {"action": "paid", "from_status": "approved", "to_status": "paid", "from_amount": 12000.0, "to_amount": 12000.0, "comment": "NEFT transfer completed.", "actor_id": rahul.id},
            ],
            "items": [
                {"category_id": categories["OFFICE"].id, "description": "HR Tech Summit registration fee", "amount": 8000.0, "quantity": 1, "unit_price": 8000.0, "vendor_name": "HR Tech India", "receipt_required": True, "approved_amount": 8000.0, "sort_order": 1},
                {"category_id": categories["FLIGHT"].id, "description": "BLR-DEL-BLR flight", "amount": 4000.0, "quantity": 1, "unit_price": 4000.0, "vendor_name": "IndiGo", "receipt_required": True, "approved_amount": 4000.0, "sort_order": 2},
            ],
        }] if deepa else []),
        # 11. Submitted hotel for Rohit
        *([{
            "id": "claim_rohit_submitted_011",
            "org_id": org.id,
            "claimant_id": rohit.id,
            "claim_number": _claim_number(org.id, 106),
            "title": "Product conference stay — Bangalore",
            "description": "Hotel accommodation for SaaSBoomi product conference.",
            "category_id": categories["HOTEL"].id,
            "status": "submitted",
            "claimed_amount": 9500.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=6),
            "submitted_at": datetime.utcnow() - timedelta(days=5),
            "approved_at": None,
            "paid_at": None,
            "rejection_reason": None,
            "current_step_id": step.id,
            "chain_id": chain.id,
            "history": [
                {"action": "created", "from_status": None, "to_status": "draft", "from_amount": None, "to_amount": 9500.0, "comment": None, "actor_id": rohit.id},
                {"action": "submitted", "from_status": "draft", "to_status": "submitted", "from_amount": None, "to_amount": 9500.0, "comment": None, "actor_id": rohit.id},
            ],
            "items": [
                {"category_id": categories["HOTEL"].id, "description": "Marriott Bangalore — 3 nights", "amount": 9500.0, "quantity": 3, "unit_price": 3166.67, "vendor_name": "Marriott", "receipt_required": True, "sort_order": 1},
            ],
        }] if rohit else []),
        # 12. Draft international flight for Rohit
        *([{
            "id": "claim_rohit_draft_012",
            "org_id": org.id,
            "claimant_id": rohit.id,
            "claim_number": _claim_number(org.id, 107),
            "title": "SF trip for investor meeting",
            "description": "Return flight for Series A investor meeting.",
            "category_id": categories["FLIGHT"].id,
            "status": "draft",
            "claimed_amount": 85000.0,
            "currency_code": "INR",
            "expense_date": today - timedelta(days=1),
            "submitted_at": None,
            "approved_at": None,
            "paid_at": None,
            "rejection_reason": None,
            "current_step_id": None,
            "chain_id": chain.id,
            "history": [
                {"action": "created", "from_status": None, "to_status": "draft", "from_amount": None, "to_amount": 85000.0, "comment": None, "actor_id": rohit.id},
            ],
            "items": [
                {"category_id": categories["FLIGHT"].id, "description": "BLR-SFO-BLR (economy)", "amount": 85000.0, "quantity": 1, "unit_price": 85000.0, "vendor_name": "United Airlines", "receipt_required": True, "sort_order": 1},
            ],
        }] if rohit else []),
    ]

    created_count = 0
    for cd in claim_defs:
        # Check if claim already exists by its fixed id
        existing = session.query(Claim).filter_by(id=cd["id"]).first()
        if existing is not None:
            continue

        # Pop sub-collections before constructing claim
        history_defs = cd.pop("history", [])
        item_defs = cd.pop("items", [])

        # Build claim
        claim = Claim(
            id=cd["id"],
            org_id=cd["org_id"],
            claimant_id=cd["claimant_id"],
            claim_number=cd["claim_number"],
            title=cd["title"],
            description=cd.get("description"),
            category_id=cd.get("category_id"),
            status=cd["status"],
            claimed_amount=cd.get("claimed_amount", 0.0),
            approved_amount=cd.get("approved_amount"),
            paid_amount=cd.get("paid_amount"),
            currency_code=cd.get("currency_code", "INR"),
            expense_date=cd["expense_date"],
            submitted_at=cd.get("submitted_at"),
            approved_at=cd.get("approved_at"),
            paid_at=cd.get("paid_at"),
            rejection_reason=cd.get("rejection_reason"),
            current_step_id=cd.get("current_step_id"),
            chain_id=cd.get("chain_id"),
            policy_id=cd.get("policy_id"),
            metadata_="{}",
            version=1,
        )
        session.add(claim)
        session.flush()

        # Claim items
        for item_d in item_defs:
            item = ClaimItem(
                id=new_uuid(),
                claim_id=claim.id,
                category_id=item_d.get("category_id"),
                description=item_d["description"],
                amount=item_d["amount"],
                quantity=item_d.get("quantity", 1),
                unit_price=item_d.get("unit_price"),
                expense_date=item_d.get("expense_date"),
                vendor_name=item_d.get("vendor_name"),
                receipt_required=item_d.get("receipt_required", True),
                approved_amount=item_d.get("approved_amount"),
                notes=item_d.get("notes"),
                sort_order=item_d.get("sort_order", 0),
            )
            session.add(item)

        # Claim history
        # Spread history timestamps slightly so ordering is deterministic
        base_ts = datetime.utcnow() - timedelta(days=50)
        for idx, hd in enumerate(history_defs):
            entry = ClaimHistory(
                id=new_uuid(),
                claim_id=claim.id,
                actor_id=hd["actor_id"],
                action=hd["action"],
                from_status=hd.get("from_status"),
                to_status=hd.get("to_status"),
                from_amount=hd.get("from_amount"),
                to_amount=hd.get("to_amount"),
                comment=hd.get("comment"),
                metadata_="{}",
                created_at=base_ts + timedelta(hours=idx),
            )
            session.add(entry)

        # If submitted, create a pending claim_approval row for the step
        if claim.status in ("submitted", "under_review"):
            approval = ClaimApproval(
                id=new_uuid(),
                claim_id=claim.id,
                step_id=step.id,
                approver_id=None,
                status="pending",
                claimed_amount=claim.claimed_amount,
                approved_amount=None,
                due_at=datetime.utcnow() + timedelta(hours=48),
            )
            session.add(approval)

        created_count += 1

    skipped = len(claim_defs) - created_count
    print(f"Created {created_count} claim(s) (skipped {skipped} existing).")


def seed_notifications(
    session: Session, org: Organization, users: dict[str, User]
) -> None:
    aryan = users["aryan@napho.com"]
    sneha = users["sneha@napho.com"]
    priya = users["priya@napho.com"]

    notif_defs = [
        {
            "id": "notif_aryan_submitted_001",
            "org_id": org.id,
            "user_id": priya.id,
            "type": "claim_submitted",
            "title": "New claim awaiting your approval",
            "body": "Aryan Mehta submitted 'Client lunch — TechCorp' for ₹3,200.",
            "entity_type": "claim",
            "entity_id": "claim_aryan_submitted_002",
            "is_read": False,
        },
        {
            "id": "notif_sneha_approved_001",
            "org_id": org.id,
            "user_id": sneha.id,
            "type": "claim_approved",
            "title": "Your claim has been approved",
            "body": "Your claim 'Marketing conference registration' for ₹7,500 was approved.",
            "entity_type": "claim",
            "entity_id": "claim_sneha_approved_003",
            "is_read": True,
        },
        {
            "id": "notif_aryan_rejected_001",
            "org_id": org.id,
            "user_id": aryan.id,
            "type": "claim_rejected",
            "title": "Your claim has been rejected",
            "body": "Your claim 'Personal accessories purchase' was rejected. Reason: Personal use items are not reimbursable.",
            "entity_type": "claim",
            "entity_id": "claim_aryan_rejected_004",
            "is_read": False,
        },
        {
            "id": "notif_sneha_paid_001",
            "org_id": org.id,
            "user_id": sneha.id,
            "type": "payment_done",
            "title": "Payment processed",
            "body": "Payment of ₹2,800 for 'Team lunch — Q3 planning' has been transferred to your account.",
            "entity_type": "claim",
            "entity_id": "claim_sneha_paid_005",
            "is_read": True,
        },
    ]

    created_count = 0
    from app.models import Notification
    for nd in notif_defs:
        _, created = get_or_create(
            session,
            Notification,
            filters={"id": nd["id"]},
            defaults={
                "org_id": nd["org_id"],
                "user_id": nd["user_id"],
                "type": nd["type"],
                "title": nd["title"],
                "body": nd.get("body"),
                "entity_type": nd.get("entity_type"),
                "entity_id": nd.get("entity_id"),
                "is_read": nd.get("is_read", False),
                "read_at": datetime.utcnow() if nd.get("is_read") else None,
            },
        )
        if created:
            created_count += 1

    print(f"Created {created_count} notification(s) (skipped {len(notif_defs) - created_count} existing).")


def seed_audit_logs(
    session: Session, org: Organization, users: dict[str, User]
) -> None:
    admin_user = users["admin@napho.com"]

    log_defs = [
        {
            "id": "audit_org_created_001",
            "org_id": org.id,
            "actor_id": admin_user.id,
            "action": "create",
            "resource_type": "organization",
            "resource_id": org.id,
            "old_value": None,
            "new_value": '{"name": "Napho Technologies", "slug": "napho-tech"}',
            "ip_address": "127.0.0.1",
            "user_agent": "seed-script/1.0",
        },
        {
            "id": "audit_claim_submitted_001",
            "org_id": org.id,
            "actor_id": users["aryan@napho.com"].id,
            "action": "submit",
            "resource_type": "claim",
            "resource_id": "claim_aryan_submitted_002",
            "old_value": '{"status": "draft"}',
            "new_value": '{"status": "submitted"}',
            "ip_address": "192.168.1.10",
            "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
        },
        {
            "id": "audit_claim_approved_001",
            "org_id": org.id,
            "actor_id": users["priya@napho.com"].id,
            "action": "approve",
            "resource_type": "claim",
            "resource_id": "claim_sneha_approved_003",
            "old_value": '{"status": "submitted"}',
            "new_value": '{"status": "approved", "approved_amount": 7500.0}',
            "ip_address": "192.168.1.20",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        },
    ]

    created_count = 0
    for ld in log_defs:
        _, created = get_or_create(
            session,
            AuditLog,
            filters={"id": ld["id"]},
            defaults={
                "org_id": ld["org_id"],
                "actor_id": ld["actor_id"],
                "action": ld["action"],
                "resource_type": ld["resource_type"],
                "resource_id": ld["resource_id"],
                "old_value": ld.get("old_value"),
                "new_value": ld.get("new_value"),
                "ip_address": ld.get("ip_address"),
                "user_agent": ld.get("user_agent"),
            },
        )
        if created:
            created_count += 1

    print(f"Created {created_count} audit log(s) (skipped {len(log_defs) - created_count} existing).")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("Napho RMS — Database Seed")
    print("=" * 60)

    print("\n[1/8] Initialising database (create_all)...")
    init_db()
    print("      Tables created / verified.")

    with SessionLocal() as session:
        print("\n[2/8] Seeding organization...")
        org = seed_organization(session)

        print("\n[3/8] Seeding system roles & permissions...")
        roles = seed_roles(session)

        print("\n[4/8] Seeding users...")
        users = seed_users(session, org, roles)

        print("\n[5/8] Seeding expense categories...")
        categories = seed_expense_categories(session, org)

        print("\n[6/8] Seeding approval chain...")
        chain, step = seed_approval_chain(session, org, roles)

        if os.getenv("SEED_SAMPLE_DATA", "true").lower() in ("0", "false", "no"):
            print("\n[7-8/8] SEED_SAMPLE_DATA disabled — skipping sample claims, notifications & audit logs.")
        else:
            print("\n[7/8] Seeding sample claims...")
            seed_claims(session, org, users, categories, chain, step)

            print("\n[8/8] Seeding notifications & audit logs...")
            seed_notifications(session, org, users)
            seed_audit_logs(session, org, users)

        session.commit()

    print("\n" + "=" * 60)
    print("Seed complete.")
    print("=" * 60)
    print("\nDemo credentials (all passwords: password123):")
    print("  aryan@napho.com   — employee")
    print("  sneha@napho.com   — employee")
    print("  vivek@napho.com   — employee")
    print("  kavya@napho.com   — employee")
    print("  amit@napho.com    — employee")
    print("  deepa@napho.com   — employee")
    print("  rohit@napho.com   — employee")
    print("  priya@napho.com   — approver")
    print("  rahul@napho.com   — finance + approver")
    print("  admin@napho.com   — admin")


if __name__ == "__main__":
    main()
