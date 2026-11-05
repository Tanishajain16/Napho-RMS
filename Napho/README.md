# Napho — Reimbursement Management System

## Quick Start
```bash
chmod +x start.sh
./start.sh
```
Then open http://localhost:3000

## Demo Credentials
| Role | Email | Password |
|---|---|---|
| Employee | aryan@napho.com | password123 |
| Employee | sneha@napho.com | password123 |
| Approver | priya@napho.com | password123 |
| Finance + Approver | rahul@napho.com | password123 |
| Admin | admin@napho.com | password123 |

## Manual Setup

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python seed.py             # seed demo data
uvicorn app.main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm run dev
```
App: http://localhost:3000

## Tech Stack
- **Backend**: Python 3.9+, FastAPI, SQLAlchemy 2.0, SQLite, Alembic
- **Frontend**: Next.js 16, TypeScript, Shadcn/ui, Tailwind CSS v4, Framer Motion
- **Auth**: JWT (access + refresh tokens), bcrypt password hashing
- **Database**: SQLite (napho.db) — no external DB needed

## Features
- Real JWT authentication (register/login/logout/refresh)
- Full claim lifecycle: Draft → Submit → Review → Approve/Reject → Paid
- Partial approval support (approve less than claimed amount)
- Role-based access control: Employee, Approver, Finance, Admin
- Real-time notifications (polling every 30s)
- File attachments (PDF/JPG/PNG)
- Audit trail for every state change
- Resubmission flow for rejected claims

## Data Model
See DB_DESIGN.md for full schema documentation.

## API
Full OpenAPI docs at http://localhost:8000/docs

Key endpoints:
- `POST /api/v1/auth/login` — login
- `POST /api/v1/auth/register` — register
- `GET /api/v1/claims` — list claims
- `POST /api/v1/claims` — create claim
- `POST /api/v1/claims/{id}/submit` — submit for approval
- `GET /api/v1/approvals/queue` — approval queue
- `POST /api/v1/approvals/{id}/approve` — approve claim
- `POST /api/v1/approvals/{id}/reject` — reject claim
- `POST /api/v1/approvals/{id}/mark-paid` — mark as paid
- `GET /api/v1/claims/stats` — dashboard stats

## Python Version Note
The backend requires Python 3.9+. If you encounter `TypeError: unsupported operand type(s) for |` errors,
ensure `eval_type_backport` is installed (it's in requirements.txt).

## AI Tools Used
Claude Code (claude-sonnet-4-6) via the Claude Code CLI was used to:
- Design the database schema (19 tables, multi-tenant, event-sourced)
- Build the FastAPI backend (auth, CRUD, approval workflow)
- Build the Next.js frontend (all pages, components, animations)
- Integration and debugging

## Known Limitations
- SQLite (not suitable for production multi-tenant use — switch to PostgreSQL)
- File uploads stored locally (switch to S3 for production)
- Notifications via polling (switch to WebSocket for production)
- Single-org UI (DB supports multi-tenant but UI assumes one org)
- No email notifications (in-app only)

## Assumptions
- One organization ("Napho Technologies") for the demo
- Approval chain: all claims go to anyone with the "approver" role
- Expense date cannot be in the future
- Partial approval: approver can approve any amount from ₹1 to the full claimed amount
