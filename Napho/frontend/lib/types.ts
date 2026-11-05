export type ClaimStatus =
  | "draft" | "submitted" | "under_review"
  | "approved" | "partially_approved"
  | "rejected" | "paid" | "cancelled"

export interface User {
  id: string
  email: string
  name: string
  avatar_url?: string
  roles: string[]
  org_id?: string
}

export interface Category {
  id: string
  name: string
  code: string
  icon?: string
  children?: Category[]
}

export interface ClaimItem {
  id: string
  description: string
  amount: number
  approved_amount?: number
  vendor_name?: string
  expense_date?: string
  category?: Category
}

export interface ClaimHistory {
  id: string
  action: string
  from_status?: string
  to_status?: string
  comment?: string
  actor: { name: string; email: string }
  created_at: string
}

export interface Attachment {
  id: string
  file_name: string
  file_size?: number
  mime_type?: string
  url: string
}

export interface Claim {
  id: string
  claim_number: string
  title: string
  description?: string
  status: ClaimStatus
  claimed_amount: number
  approved_amount?: number
  paid_amount?: number
  currency_code: string
  expense_date: string
  submitted_at?: string
  approved_at?: string
  paid_at?: string
  rejection_reason?: string
  category?: Category
  claimant: { id: string; name: string; email: string }
  created_at: string
  updated_at: string
  /** Viewer-specific approval info (Review Queue / claim detail) */
  can_act?: boolean | null
  my_decision?: "approved" | "partially_approved" | "rejected" | null
  my_approved_amount?: number | null
  my_decided_at?: string | null
}

export interface ApprovalStep {
  id: string
  level: string
  approver_name?: string
  status: "pending" | "approved" | "rejected" | "skipped"
  approved_amount?: number
  comment?: string
  acted_at?: string
}

export interface AdminApprovalStep {
  id: string
  step_order: number
  approver_type: string
  approver_id?: string
  approver_name?: string
  approver_role?: string
  timeout_hours: number
}

export interface ApprovalChain {
  id: string
  name: string
  min_amount: number
  max_amount?: number
  is_active: boolean
  category_id?: string
  steps: AdminApprovalStep[]
  claim_count: number
  created_at: string
}

export interface ClaimDetail extends Claim {
  items: ClaimItem[]
  attachments: Attachment[]
  history: ClaimHistory[]
  approvals?: ApprovalStep[]
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_more: boolean
}

export interface ClaimStats {
  pending_count: number
  pending_amount: number
  approved_count: number
  approved_amount: number
  paid_count: number
  paid_amount: number
  rejected_count: number
  rejected_amount?: number
}

export interface Notification {
  id: string
  type: string
  title: string
  body?: string
  is_read: boolean
  entity_id?: string
  entity_type?: string
  created_at: string
}

export interface OrgAnalytics {
  total_claims: number
  total_amount_claimed: number
  total_amount_approved: number
  total_amount_paid: number
  claims_by_status: Record<string, number>
  claims_by_category: Array<{ name: string; amount: number; count: number }>
  spending_by_month: Array<{ month: string; amount: number; count: number }>
  top_claimants: Array<{ name: string; email: string; total_claimed: number; count: number }>
  approval_rate: number
  avg_approval_days: number
}

export interface AdminUser {
  id: string
  email: string
  name: string
  is_active: boolean
  roles: string[]
  created_at: string
  total_claims?: number
  claim_count?: number
  department?: string
  designation?: string
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
}
