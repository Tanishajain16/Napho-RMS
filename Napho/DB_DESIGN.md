# Database Design — Reimbursement Management System
> Role: Senior Database Architect
> Philosophy: Multi-tenant, event-sourced history, policy-driven approvals, horizontally extensible

---

## Design Principles

1. **Multi-tenancy first** — every row is scoped to an `org_id`; tenant isolation at the data layer
2. **Soft deletes everywhere** — `deleted_at` instead of hard deletes for audit trails
3. **Event-sourced claim history** — never mutate claim state, always append a history row
4. **Policy engine** — spending limits, category rules, approval chains are data, not code
5. **Extensible roles** — RBAC via `permissions` table, not hardcoded role checks
6. **UUID primary keys** — avoids enumeration attacks, safe across distributed shards
7. **Immutable audit log** — `audit_logs` table is append-only, never updated
8. **Nullable vs required** — only make fields nullable when business logic truly allows absence

---

## Entity Relationship Overview

```
Organizations
    ├── Users (members)
    │     ├── UserRoles
    │     └── UserOrgMemberships
    ├── ExpenseCategories (tree)
    ├── ExpensePolicies
    │     └── PolicyRules
    ├── ApprovalChains
    │     └── ApprovalSteps
    ├── Claims
    │     ├── ClaimItems
    │     ├── ClaimAttachments
    │     ├── ClaimHistory (event log)
    │     ├── ClaimComments
    │     └── ClaimApprovals (per step)
    ├── Notifications
    └── AuditLogs
```

---

## Table Definitions

### 1. `organizations`
Root tenant entity. Every other table references this.

```sql
CREATE TABLE organizations (
    id              TEXT PRIMARY KEY,           -- UUID
    name            TEXT NOT NULL,
    slug            TEXT NOT NULL UNIQUE,       -- URL-safe identifier, e.g. "acme-corp"
    logo_url        TEXT,
    country_code    TEXT NOT NULL DEFAULT 'IN', -- ISO 3166-1 alpha-2
    currency_code   TEXT NOT NULL DEFAULT 'INR',-- ISO 4217
    fiscal_year_start_month INTEGER DEFAULT 4,  -- April for India
    settings        TEXT DEFAULT '{}',          -- JSON blob for org-level config
    plan            TEXT DEFAULT 'free',        -- free | starter | pro | enterprise
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at      TEXT
);
```

**Extension points:** `settings` JSON holds feature flags, branding, locale. `plan` gates feature access.

---

### 2. `users`
Identity store. Kept separate from org membership to support multi-org users.

```sql
CREATE TABLE users (
    id              TEXT PRIMARY KEY,           -- UUID
    email           TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    avatar_url      TEXT,
    password_hash   TEXT,                       -- NULL if SSO only
    phone           TEXT,
    is_active       INTEGER DEFAULT 1,
    last_login_at   TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at      TEXT
);
```

---

### 3. `user_org_memberships`
Joins users to organizations. One user can belong to many orgs (e.g., contractor across companies).

```sql
CREATE TABLE user_org_memberships (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    employee_code   TEXT,                       -- HR system ID
    department      TEXT,
    designation     TEXT,
    manager_id      TEXT REFERENCES users(id),  -- direct manager
    join_date       TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, org_id)
);
```

---

### 4. `roles`
System-level roles. Orgs can define custom roles later.

```sql
CREATE TABLE roles (
    id              TEXT PRIMARY KEY,
    org_id          TEXT REFERENCES organizations(id), -- NULL = system-wide role
    name            TEXT NOT NULL,              -- employee | approver | finance | admin
    description     TEXT,
    is_system       INTEGER DEFAULT 0,          -- system roles can't be deleted
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(org_id, name)
);
```

**Seed data:**
```
system:employee  — can create/submit claims
system:approver  — can review claims
system:finance   — can mark as paid, view all
system:admin     — full org management
```

---

### 5. `user_roles`
Many-to-many: user → roles within an org.

```sql
CREATE TABLE user_roles (
    id              TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL REFERENCES users(id),
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    role_id         TEXT NOT NULL REFERENCES roles(id),
    granted_by      TEXT REFERENCES users(id),
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(user_id, org_id, role_id)
);
```

---

### 6. `permissions`
Fine-grained permission map for roles (future RBAC extension).

```sql
CREATE TABLE permissions (
    id              TEXT PRIMARY KEY,
    role_id         TEXT NOT NULL REFERENCES roles(id),
    resource        TEXT NOT NULL,              -- claims | users | reports | policies
    action          TEXT NOT NULL,              -- create | read | update | delete | approve
    conditions      TEXT DEFAULT '{}',          -- JSON: e.g. {"own_only": true}
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(role_id, resource, action)
);
```

---

### 7. `expense_categories`
Hierarchical (tree) structure via `parent_id`. Org-scoped.

```sql
CREATE TABLE expense_categories (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    parent_id       TEXT REFERENCES expense_categories(id), -- NULL = root
    name            TEXT NOT NULL,
    code            TEXT NOT NULL,              -- short code: TRAVEL, MEAL, EQUIP
    description     TEXT,
    icon            TEXT,                       -- icon name for UI
    requires_receipt INTEGER DEFAULT 1,
    max_amount      REAL,                       -- per-claim limit, NULL = unlimited
    is_active       INTEGER DEFAULT 1,
    sort_order      INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(org_id, code)
);
```

**Example hierarchy:**
```
Travel (TRAVEL)
  ├── Flight (FLIGHT)
  ├── Hotel (HOTEL)
  └── Local Conveyance (LOCAL)
Food & Meals (FOOD)
  ├── Team Lunch (TEAM_MEAL)
  └── Client Entertainment (CLIENT_ENT)
Office Supplies (OFFICE)
Equipment (EQUIP)
```

---

### 8. `expense_policies`
Per-org spending rules. Can be scoped by role, department, or category.

```sql
CREATE TABLE expense_policies (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    name            TEXT NOT NULL,
    description     TEXT,
    is_active       INTEGER DEFAULT 1,
    priority        INTEGER DEFAULT 0,          -- higher = evaluated first
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 9. `policy_rules`
Individual rules within a policy (e.g., "Flight max ₹15,000 per trip").

```sql
CREATE TABLE policy_rules (
    id              TEXT PRIMARY KEY,
    policy_id       TEXT NOT NULL REFERENCES expense_policies(id),
    category_id     TEXT REFERENCES expense_categories(id), -- NULL = all categories
    role_id         TEXT REFERENCES roles(id),              -- NULL = all roles
    department      TEXT,                                   -- NULL = all departments
    max_amount      REAL,
    max_items       INTEGER,                                -- max line items
    requires_receipt_above REAL,                           -- receipt required if > X
    requires_approval_above REAL,                          -- auto-approve if below
    period          TEXT DEFAULT 'per_claim',              -- per_claim | per_day | per_month
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### 10. `approval_chains`
Configurable multi-step approval workflows per org/category/amount.

```sql
CREATE TABLE approval_chains (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    name            TEXT NOT NULL,
    category_id     TEXT REFERENCES expense_categories(id), -- NULL = all
    min_amount      REAL DEFAULT 0,
    max_amount      REAL,                                   -- NULL = no upper limit
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### 11. `approval_steps`
Ordered steps within a chain.

```sql
CREATE TABLE approval_steps (
    id              TEXT PRIMARY KEY,
    chain_id        TEXT NOT NULL REFERENCES approval_chains(id),
    step_order      INTEGER NOT NULL,
    approver_type   TEXT NOT NULL,    -- specific_user | role | manager | department_head
    approver_id     TEXT,             -- user_id if specific_user
    approver_role   TEXT,             -- role name if role-based
    timeout_hours   INTEGER DEFAULT 48,
    on_timeout      TEXT DEFAULT 'escalate', -- escalate | auto_approve | auto_reject
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(chain_id, step_order)
);
```

---

### 12. `claims`
Core entity. State machine: `draft → submitted → under_review → approved/rejected → paid`.

```sql
CREATE TABLE claims (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    claimant_id     TEXT NOT NULL REFERENCES users(id),
    claim_number    TEXT NOT NULL,              -- human-readable: ORG-2024-00042
    title           TEXT NOT NULL,
    description     TEXT,
    category_id     TEXT REFERENCES expense_categories(id),
    status          TEXT NOT NULL DEFAULT 'draft',
                    -- draft | submitted | under_review | approved | partially_approved
                    -- | rejected | paid | cancelled
    claimed_amount  REAL NOT NULL DEFAULT 0,    -- sum of claim_items.amount
    approved_amount REAL,                       -- set after approval (supports partial)
    paid_amount     REAL,
    currency_code   TEXT NOT NULL DEFAULT 'INR',
    expense_date    TEXT NOT NULL,              -- date of expense (not submission)
    submitted_at    TEXT,
    approved_at     TEXT,
    paid_at         TEXT,
    rejection_reason TEXT,
    current_step_id TEXT REFERENCES approval_steps(id), -- active approval step
    chain_id        TEXT REFERENCES approval_chains(id),
    policy_id       TEXT REFERENCES expense_policies(id),
    metadata        TEXT DEFAULT '{}',          -- extensible JSON
    version         INTEGER DEFAULT 1,          -- optimistic locking
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at      TEXT,
    UNIQUE(org_id, claim_number)
);
```

**State machine transitions:**
```
draft        → submitted       (by claimant, when all required fields present)
submitted    → under_review    (by approver, starts review)
submitted    → rejected        (direct reject without full review)
under_review → approved        (all steps approved, full amount)
under_review → partially_approved (approved with reduced amount)
under_review → rejected        (any step rejects)
approved     → paid            (by finance role)
partially_approved → paid      (by finance role)
rejected     → draft           (claimant edits and resubmits)
draft        → cancelled       (claimant withdraws)
submitted    → cancelled       (claimant withdraws before review starts)
```

---

### 13. `claim_items`
Line items within a claim (e.g., individual receipts).

```sql
CREATE TABLE claim_items (
    id              TEXT PRIMARY KEY,
    claim_id        TEXT NOT NULL REFERENCES claims(id),
    category_id     TEXT REFERENCES expense_categories(id),
    description     TEXT NOT NULL,
    amount          REAL NOT NULL,
    quantity        INTEGER DEFAULT 1,
    unit_price      REAL,
    expense_date    TEXT,
    vendor_name     TEXT,
    receipt_required INTEGER DEFAULT 1,
    approved_amount REAL,                       -- for partial approval at item level
    notes           TEXT,
    sort_order      INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### 14. `claim_attachments`
Receipts, invoices, supporting documents.

```sql
CREATE TABLE claim_attachments (
    id              TEXT PRIMARY KEY,
    claim_id        TEXT NOT NULL REFERENCES claims(id),
    claim_item_id   TEXT REFERENCES claim_items(id), -- optional item-level attachment
    uploaded_by     TEXT NOT NULL REFERENCES users(id),
    file_name       TEXT NOT NULL,
    file_size       INTEGER,                    -- bytes
    mime_type       TEXT,
    storage_key     TEXT NOT NULL,              -- S3 key / local path
    storage_provider TEXT DEFAULT 'local',      -- local | s3 | gcs
    is_receipt      INTEGER DEFAULT 1,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at      TEXT
);
```

---

### 15. `claim_history`
Immutable event log — every state change appends a row. Never updated or deleted.

```sql
CREATE TABLE claim_history (
    id              TEXT PRIMARY KEY,
    claim_id        TEXT NOT NULL REFERENCES claims(id),
    actor_id        TEXT NOT NULL REFERENCES users(id),
    action          TEXT NOT NULL,
                    -- created | edited | submitted | cancelled | review_started
                    -- | approved | partially_approved | rejected | paid | resubmitted
                    -- | comment_added | attachment_added | step_escalated
    from_status     TEXT,
    to_status       TEXT,
    from_amount     REAL,
    to_amount       REAL,                       -- captures partial approval changes
    comment         TEXT,                       -- reason/note for this action
    metadata        TEXT DEFAULT '{}',          -- step_id, policy_rule triggered, etc.
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
-- No UPDATE or DELETE ever on this table
```

---

### 16. `claim_approvals`
One row per approval step per claim. Tracks who approved/rejected each step.

```sql
CREATE TABLE claim_approvals (
    id              TEXT PRIMARY KEY,
    claim_id        TEXT NOT NULL REFERENCES claims(id),
    step_id         TEXT NOT NULL REFERENCES approval_steps(id),
    approver_id     TEXT REFERENCES users(id),  -- actual user who acted
    status          TEXT DEFAULT 'pending',     -- pending | approved | partially_approved | rejected | skipped | escalated
    claimed_amount  REAL,                       -- amount at time of review
    approved_amount REAL,                       -- may differ (partial approval)
    comment         TEXT,
    decided_at      TEXT,
    due_at          TEXT,                       -- SLA deadline
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(claim_id, step_id)
);
```

---

### 17. `claim_comments`
Threaded discussion on a claim (not part of formal approval flow).

```sql
CREATE TABLE claim_comments (
    id              TEXT PRIMARY KEY,
    claim_id        TEXT NOT NULL REFERENCES claims(id),
    parent_id       TEXT REFERENCES claim_comments(id), -- threading
    author_id       TEXT NOT NULL REFERENCES users(id),
    body            TEXT NOT NULL,
    is_internal     INTEGER DEFAULT 0,          -- 1 = approver-only, hidden from claimant
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now')),
    deleted_at      TEXT
);
```

---

### 18. `notifications`
In-app notification queue.

```sql
CREATE TABLE notifications (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL REFERENCES organizations(id),
    user_id         TEXT NOT NULL REFERENCES users(id),
    type            TEXT NOT NULL,              -- claim_submitted | claim_approved | claim_rejected | payment_done | reminder
    title           TEXT NOT NULL,
    body            TEXT,
    entity_type     TEXT,                       -- claim | user | policy
    entity_id       TEXT,
    is_read         INTEGER DEFAULT 0,
    read_at         TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

### 19. `audit_logs`
System-wide append-only audit trail for compliance.

```sql
CREATE TABLE audit_logs (
    id              TEXT PRIMARY KEY,
    org_id          TEXT REFERENCES organizations(id),
    actor_id        TEXT REFERENCES users(id),
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     TEXT NOT NULL,
    old_value       TEXT,                       -- JSON snapshot before change
    new_value       TEXT,                       -- JSON snapshot after change
    ip_address      TEXT,
    user_agent      TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## Indexes

```sql
-- Claims lookup
CREATE INDEX idx_claims_org_claimant   ON claims(org_id, claimant_id);
CREATE INDEX idx_claims_org_status     ON claims(org_id, status);
CREATE INDEX idx_claims_submitted_at   ON claims(submitted_at);

-- History & approvals
CREATE INDEX idx_claim_history_claim   ON claim_history(claim_id, created_at);
CREATE INDEX idx_claim_approvals_step  ON claim_approvals(claim_id, step_id);

-- Notifications
CREATE INDEX idx_notifications_user    ON notifications(user_id, is_read);

-- Audit
CREATE INDEX idx_audit_resource        ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_actor           ON audit_logs(actor_id, created_at);

-- Categories
CREATE INDEX idx_categories_org_parent ON expense_categories(org_id, parent_id);
```

---

## Extensibility Roadmap

| Future Feature | How DB supports it |
|---|---|
| Multi-currency | `currency_code` on claims + exchange rate table |
| Recurring expenses | `recurrence_rule` field on claims |
| Budget tracking | `budgets` table linked to categories + dept |
| Mobile receipts | `claim_attachments.storage_provider` = 's3' |
| SSO / SAML | `oauth_providers` table linked to users |
| Approval delegation | `approval_delegations` table (out-of-office) |
| Expense analytics | Dedicated read model / materialized views |
| Webhooks | `webhook_endpoints` + `webhook_deliveries` tables |
| Tags / Labels | `claim_tags` many-to-many table |
| Cost centers | `cost_centers` table, FK on claims |
| Tax handling | `tax_codes` table, on claim_items |
| Mileage claims | `claim_items.type = mileage`, rate table |

---

## Seed Reference Data

```sql
-- Default org for development
INSERT INTO organizations VALUES ('org_dev', 'Napho Demo', 'napho-demo', NULL, 'IN', 'INR', 4, '{}', 'pro', 1, datetime('now'), datetime('now'), NULL);

-- System roles
INSERT INTO roles VALUES ('role_employee', NULL, 'employee', 'Can create and submit claims', 1, datetime('now'));
INSERT INTO roles VALUES ('role_approver', NULL, 'approver', 'Can review and approve claims', 1, datetime('now'));
INSERT INTO roles VALUES ('role_finance',  NULL, 'finance',  'Can mark claims as paid', 1, datetime('now'));
INSERT INTO roles VALUES ('role_admin',    NULL, 'admin',    'Full organization management', 1, datetime('now'));

-- Root expense categories for org_dev
INSERT INTO expense_categories VALUES ('cat_travel', 'org_dev', NULL, 'Travel', 'TRAVEL', 'All travel expenses', 'plane', 1, NULL, 1, 1, datetime('now'), datetime('now'));
INSERT INTO expense_categories VALUES ('cat_food',   'org_dev', NULL, 'Food & Meals', 'FOOD', 'Meals and entertainment', 'utensils', 1, 5000, 1, 2, datetime('now'), datetime('now'));
INSERT INTO expense_categories VALUES ('cat_office', 'org_dev', NULL, 'Office Supplies', 'OFFICE', NULL, 'package', 0, 2000, 1, 3, datetime('now'), datetime('now'));
INSERT INTO expense_categories VALUES ('cat_equip',  'org_dev', NULL, 'Equipment', 'EQUIP', NULL, 'monitor', 1, NULL, 1, 4, datetime('now'), datetime('now'));
```
