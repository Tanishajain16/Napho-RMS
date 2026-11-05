# Product Requirements Document
## Reimbursement Management System — P0 Features
> Role: Senior Product Manager
> Version: 1.0 | Date: 2026-11-03 | Status: Ready for Engineering

---

## Executive Summary

Napho RMS is an internal tool that eliminates paper-based/email-driven reimbursement workflows. Employees submit expense claims digitally; approvers review and decide through a structured flow; finance marks payment done. The system provides full visibility, audit trail, and policy enforcement out of the box.

**P0 = Must ship. No launch without these.**

---

## Personas

### 1. Aryan — The Employee
- Submits 3–5 expense claims per month (travel, meals, supplies)
- Currently uses WhatsApp + Excel to submit claims
- Frustrated by: no status visibility, losing receipts, resubmitting the same thing twice
- **Job to be done:** "Submit my expense and know when I'll get paid — without chasing anyone."

### 2. Priya — The Approver (Team Lead)
- Reviews 10–20 claims/week across her 8-person team
- Currently gets claims over email with no context
- Frustrated by: missing receipts, unclear claim descriptions, no way to add comments
- **Job to be done:** "Review and decide on claims quickly with all the context I need."

### 3. Rahul — Finance / Admin
- Marks approved claims as paid after funds transfer
- Needs a single view of all approved-but-unpaid claims
- **Job to be done:** "See what's approved and mark things paid in bulk."

---

## P0 Features

---

### FEAT-01: Mocked Authentication & Role Selection

**Problem:** The system needs user context (who is submitting, who is approving) without building real auth infrastructure.

**Solution:** A simple login screen with pre-seeded demo users. No real passwords required — select a user from a list.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-01-1 | Visitor | Select a demo user and log in | I can experience the system from that user's perspective |
| US-01-2 | Logged-in user | See my name and role in the header | I know which account I'm using |
| US-01-3 | Logged-in user | Log out and switch users | I can test different role flows |

**Acceptance Criteria:**
- [ ] Login page shows list of 4–6 seeded demo users (mix of employee/approver/finance roles)
- [ ] Selecting a user sets session context (JWT or session cookie)
- [ ] Header shows user avatar, name, role badge at all times
- [ ] Logout clears session and returns to login screen
- [ ] Unauthenticated routes redirect to login
- [ ] Role-based navigation: employees see "My Claims"; approvers see "Review Queue"

**Seeded Users (demo):**

| Name | Role | Notes |
|---|---|---|
| Aryan Mehta | Employee | Regular submitter |
| Sneha Kapoor | Employee | Has rejected claims to demonstrate resubmission |
| Priya Sharma | Approver | Reviews Aryan's team |
| Rahul Verma | Finance + Approver | Can approve and mark paid |
| Admin User | Admin | Can manage org settings |

**Out of scope:** Real password auth, OAuth, email verification, 2FA.

---

### FEAT-02: Claim Creation (Draft)

**Problem:** Employees need a structured way to capture expense details with supporting documents.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-02-1 | Employee | Create a new expense claim | I can start documenting my expense |
| US-02-2 | Employee | Add multiple line items to one claim | I can bundle related expenses (e.g., a business trip) |
| US-02-3 | Employee | Save a claim as draft | I can come back and complete it later |
| US-02-4 | Employee | Edit a draft claim | I can correct mistakes before submitting |
| US-02-5 | Employee | Delete a draft claim | I can remove claims I no longer need |
| US-02-6 | Employee | Upload receipts / attachments | I can provide proof of expense |

**Claim Fields:**

| Field | Type | Required | Notes |
|---|---|---|---|
| Title | Text | Yes | e.g., "Mumbai Business Trip - Oct 2024" |
| Category | Select | Yes | From expense_categories tree |
| Expense Date | Date | Yes | Date of actual expense, not submission |
| Description | Textarea | No | Context / purpose of expense |
| Line Items | Array | Yes (min 1) | See below |
| Attachments | Files | Conditional | Required if category.requires_receipt = true |

**Line Item Fields:**

| Field | Required | Notes |
|---|---|---|
| Description | Yes | What was purchased |
| Amount (₹) | Yes | Must be > 0 |
| Category | No | Can override parent claim category |
| Expense Date | No | Defaults to claim date |
| Vendor | No | Name of vendor/merchant |

**Acceptance Criteria:**
- [ ] "New Claim" CTA visible on employee dashboard
- [ ] Multi-step or single form — one page preferred for P0
- [ ] At least 1 line item required; can add up to 20 items
- [ ] Claim total auto-calculated from line items (read-only field)
- [ ] Draft auto-saved every 30 seconds (or on blur)
- [ ] File upload: accept PDF, JPG, PNG; max 10MB per file; max 5 files
- [ ] Category picker shows icon + name in hierarchical dropdown
- [ ] Date picker prevents future dates
- [ ] Character limits: title ≤ 100, description ≤ 500, item description ≤ 200
- [ ] Draft saved confirmation toast on manual save

**Validation Rules:**
- Amount must be positive number, max 2 decimal places
- Expense date must not be in the future
- Title cannot be blank on save
- Cannot have duplicate identical line items (same description + amount + date = warn user)

**Edge Cases:**
- Navigating away from unsaved form → show "unsaved changes" prompt
- Session expiry mid-fill → restore from local draft on return
- File upload fails → show error inline, allow retry without losing form data

---

### FEAT-03: Claim Submission

**Problem:** Employee needs to formally submit a draft claim for review, triggering the approval workflow.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-03-1 | Employee | Submit a draft claim | It enters the approval workflow |
| US-03-2 | Employee | See a confirmation before submitting | I know it's a final action |
| US-03-3 | Employee | Cancel a submitted claim (before review starts) | I can withdraw if I made an error |

**Acceptance Criteria:**
- [ ] "Submit Claim" button visible only on draft claims
- [ ] Pre-submission validation runs: all required fields, at least 1 item, receipt if required
- [ ] Confirmation modal shows claim summary (title, amount, category) before submit
- [ ] On submission: status → `submitted`, `submitted_at` timestamp set, history row appended
- [ ] Approver(s) receive in-app notification (bell icon)
- [ ] Employee sees claim status change to "Submitted" immediately
- [ ] Cancel button available while status = `submitted` AND no approver has started review
- [ ] Cancel moves status → `cancelled`; shows toast confirmation

**Validation before submit:**
- Title, expense_date, category, at least 1 item — all present
- All items have description and amount > 0
- If category requires receipt → at least 1 attachment present
- Total claimed_amount > 0

**Edge Cases:**
- Double-submit (click Submit twice rapidly) → idempotency check, only one submission recorded
- Submitting with no items → blocked with inline error, not toast
- Network failure during submit → retry prompt, status not changed

---

### FEAT-04: Employee Claims Dashboard

**Problem:** Employees have no visibility into the status of their claims.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-04-1 | Employee | See all my claims in one list | I can track every expense I've submitted |
| US-04-2 | Employee | Filter claims by status | I can quickly find pending or rejected claims |
| US-04-3 | Employee | See a status badge on each claim | I know at a glance where each claim stands |
| US-04-4 | Employee | Open a claim to see full details | I can review what I submitted and any comments |
| US-04-5 | Employee | See summary stats at the top | I know my total pending/approved amounts |

**Dashboard Layout:**

```
┌─────────────────────────────────────────────────┐
│  Summary Cards: [Pending ₹X] [Approved ₹X] [Paid ₹X]  │
├─────────────────────────────────────────────────┤
│  Filter: All | Draft | Submitted | Approved | Rejected | Paid  │
├─────────────────────────────────────────────────┤
│  Claim Card: Title | Amount | Status | Date | Action →  │
│  ...                                             │
└─────────────────────────────────────────────────┘
```

**Status Badge Colors:**
- Draft → Gray
- Submitted → Blue
- Under Review → Yellow/Amber
- Approved → Green
- Partially Approved → Teal
- Rejected → Red
- Paid → Purple/Indigo

**Acceptance Criteria:**
- [ ] Default sort: most recently updated first
- [ ] Status filter tabs above the list
- [ ] Each claim card shows: title, category icon, claimed amount, status badge, submitted date
- [ ] Empty state for each filter with relevant illustration
- [ ] Pagination or infinite scroll (20 per page for P0)
- [ ] Clicking a card opens Claim Detail page
- [ ] Summary cards show totals for current month by default
- [ ] "New Claim" FAB visible on mobile

---

### FEAT-05: Claim Detail View

**Problem:** Both employees and approvers need a full picture of a claim — items, attachments, history, and comments.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-05-1 | Employee | See all details of my claim | I know exactly what I submitted |
| US-05-2 | Employee | See the approval timeline | I know what stage my claim is at |
| US-05-3 | Employee | Read approver comments | I understand why a claim was rejected |
| US-05-4 | Approver | See full claim details before deciding | I have everything I need to approve/reject |
| US-05-5 | Both | View/download attachments | I can review receipts |

**Page Sections:**
1. **Header** — Claim number, title, status badge, claimed amount, submitted date
2. **Claim Info** — Category, expense date, description, claimant info
3. **Line Items Table** — Description, amount, vendor, date; total row at bottom
4. **Attachments** — Thumbnail grid with view/download
5. **Approval Timeline** — Step-by-step visual: Submitted → Under Review → Approved/Rejected
6. **Activity / Comments** — Chronological feed of all actions + comments

**Acceptance Criteria:**
- [ ] Claim number displayed prominently (e.g., NAPHO-2024-0042)
- [ ] Line items in a table with subtotals if multiple categories
- [ ] Attachment thumbnails; click to open full screen / download
- [ ] Timeline shows each history event with actor, timestamp, and note
- [ ] Rejected claims show rejection reason prominently (not buried in timeline)
- [ ] Approved amount vs claimed amount shown side-by-side (for partial approvals)
- [ ] "Edit & Resubmit" CTA visible only on rejected claims (for the claimant)
- [ ] Back button / breadcrumb to return to dashboard

---

### FEAT-06: Approver Review Queue

**Problem:** Approvers have no consolidated view of claims waiting for their action.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-06-1 | Approver | See all claims pending my review | I can action them efficiently |
| US-06-2 | Approver | See claim age / days waiting | I can prioritize older claims |
| US-06-3 | Approver | Filter by status / date range | I can manage my queue |
| US-06-4 | Approver | Open a claim for full review | I can see all details before deciding |
| US-06-5 | Approver | See claims I've previously reviewed | I can refer back to past decisions |

**Queue Layout:**
```
┌──────────────────────────────────────────────────────┐
│  [Pending Review N] [Approved] [Rejected]             │
├──────────────────────────────────────────────────────┤
│  Sort: Oldest First ▾   Filter: All Categories ▾      │
├──────────────────────────────────────────────────────┤
│  Row: Claimant | Title | Amount | Category | Days Waiting | Action  │
└──────────────────────────────────────────────────────┘
```

**Acceptance Criteria:**
- [ ] Separate navigation item "Review Queue" for approver role
- [ ] Default view: pending claims, oldest first
- [ ] "Days waiting" counter shown in amber > 2 days, red > 5 days
- [ ] Quick action buttons inline: [Approve] [Reject] — opens modal without full page nav
- [ ] "View Details" opens full Claim Detail page
- [ ] Badge count on nav item shows pending count
- [ ] Empty state: "All caught up! No pending claims." with illustration

---

### FEAT-07: Approve / Reject Action

**Problem:** Approvers need a structured way to make decisions with accountability.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-07-1 | Approver | Approve a claim in full | It moves to paid queue |
| US-07-2 | Approver | Reject a claim with a reason | The employee knows what to fix |
| US-07-3 | Approver | Approve a partial amount | I can approve a fair portion |
| US-07-4 | Approver | Add a comment with my decision | Context is preserved in history |

**Approve Flow:**
1. Click "Approve" → Modal opens
2. Confirm amount (pre-filled with claimed amount, editable for partial)
3. Add optional comment
4. Click "Confirm Approval" → status → `approved` or `partially_approved`

**Reject Flow:**
1. Click "Reject" → Modal opens
2. Rejection reason (required, textarea)
3. Click "Confirm Rejection" → status → `rejected`

**Acceptance Criteria:**
- [ ] Approve modal shows: claimed amount, approved amount field (editable), comment textarea
- [ ] Approved amount defaults to claimed amount
- [ ] Approved amount cannot exceed claimed amount
- [ ] Approved amount must be > 0
- [ ] Reject modal requires a reason (min 10 characters)
- [ ] Both actions require confirmation (no single-click approval)
- [ ] On approve: history row added, notification sent to claimant, status updated
- [ ] On reject: history row added, rejection_reason saved, notification to claimant
- [ ] Partial approval (approved amount < claimed amount): status = `partially_approved`
- [ ] Approver cannot act on a claim they submitted (self-approval prevention)
- [ ] Approver cannot act on same claim twice

**Edge Cases:**
- Approved amount = 0 → blocked with error "Approved amount must be greater than 0"
- Approver tries to approve already-approved claim → show "Already actioned" message
- Network failure during approval → optimistic UI reverts, shows error

---

### FEAT-08: Reject → Edit → Resubmit Flow

**Problem:** Employees need to correct and resubmit rejected claims without creating duplicates.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-08-1 | Employee | Edit a rejected claim | I can fix the issues raised by the approver |
| US-08-2 | Employee | Resubmit the edited claim | It goes back for approval |
| US-08-3 | Employee | See the rejection reason while editing | I know what to fix |

**Acceptance Criteria:**
- [ ] Rejected claims show "Edit & Resubmit" button (not "New Claim")
- [ ] Clicking it opens the claim form pre-filled with existing data
- [ ] Rejection reason shown as a banner at top of edit form
- [ ] Editing moves status from `rejected` → `draft`
- [ ] Resubmitting moves status → `submitted` (not creating a new claim)
- [ ] All history preserved — resubmissions visible in activity timeline
- [ ] Approver can see previous rejection + resubmission history in timeline
- [ ] Cannot resubmit without making at least one change (prevent no-op resubmissions)

---

### FEAT-09: Mark as Paid

**Problem:** Finance needs to close the loop by marking approved claims as paid after funds transfer.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-09-1 | Finance | See all approved / partially-approved claims | I know what's pending payment |
| US-09-2 | Finance | Mark a claim as paid | The record reflects the payment was made |
| US-09-3 | Finance | Add a payment reference | There's a link between our records and the bank transfer |

**Acceptance Criteria:**
- [ ] Finance role sees "Payment Queue" view (filter: approved + partially_approved)
- [ ] "Mark as Paid" button on each approved claim
- [ ] Payment modal asks for: payment date (default today), optional payment reference
- [ ] On confirm: status → `paid`, `paid_at` timestamp set, `paid_amount` = `approved_amount`
- [ ] Employee receives in-app notification "Your claim NAPHO-0042 has been paid"
- [ ] Paid claims move out of payment queue
- [ ] Cannot mark already-paid claim as paid again

---

### FEAT-10: In-App Notifications

**Problem:** Users don't know when action is needed or when their claim status changes.

**User Stories:**

| ID | As a... | I want to... | So that... |
|---|---|---|---|
| US-10-1 | Any user | See a notification badge on the bell icon | I know there's something new |
| US-10-2 | Any user | Click the bell to see all notifications | I can see what changed |
| US-10-3 | Any user | Mark notifications as read | The badge clears |

**Notification Triggers:**

| Event | Who gets notified |
|---|---|
| Claim submitted | Approver(s) in approval chain |
| Claim approved | Claimant |
| Claim partially approved | Claimant |
| Claim rejected | Claimant |
| Claim paid | Claimant |
| Claim cancelled | Approver (if was under review) |

**Acceptance Criteria:**
- [ ] Bell icon in header with unread count badge (max display: 99+)
- [ ] Dropdown panel shows last 20 notifications with timestamp
- [ ] Each notification is clickable and navigates to relevant claim
- [ ] "Mark all as read" button in dropdown
- [ ] Unread notifications have highlighted background
- [ ] Notification count updates on the same page without full refresh (polling every 30s for P0)

---

## Non-Functional Requirements (P0)

| Category | Requirement |
|---|---|
| **Performance** | Dashboard load < 2s on localhost |
| **Reliability** | No data loss on page refresh (draft persistence) |
| **Security** | Users can only access their own claims; approvers only see their org's claims |
| **Usability** | Core flows completable without documentation |
| **Auditability** | Every state change logged with actor + timestamp |
| **Error handling** | All API errors show human-readable message (no raw 500 errors) |

---

## Out of Scope for P0

- Real payment integration
- Email notifications (in-app only)
- Mobile app (responsive web is sufficient)
- Multi-org support in the UI (DB supports it; UI is single-org)
- Bulk approve/reject
- Export to CSV/Excel
- Advanced analytics / reports
- Approval delegation (out-of-office)
- Budget tracking

---

## Success Metrics (Post-Launch)

| Metric | Target |
|---|---|
| Claim submission completion rate | > 80% of started claims get submitted |
| Approver response time | Median < 24 hours |
| Rejection rate | < 20% (indicates policy clarity) |
| Resubmission success rate | > 90% of resubmitted claims approved |
| Time to paid | P50 < 3 business days |

---

## Open Questions / Decisions Needed

| # | Question | Owner | Priority |
|---|---|---|---|
| 1 | Is partial approval in scope for P0 or P1? | PM + Eng | High |
| 2 | Should cancelled claims be recoverable? | PM | Medium |
| 3 | File storage: local filesystem OK for demo, S3 for prod? | Eng | Low |
| 4 | Should approvers be able to edit claim amounts directly, or only approve/reject? | PM | High |
| 5 | Notification polling interval — 30s acceptable or need WebSocket? | Eng | Low |
