import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { PaginatedResponse, Claim } from "@/lib/types"

export function useApprovalQueue(status = "pending", page = 1) {
  return useQuery<PaginatedResponse<Claim>>({
    queryKey: ["approvals", "queue", status, page],
    queryFn: () =>
      api.get("/approvals/queue", { params: { status, page } }).then((r) => r.data),
  })
}

export function useApproveClaim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, approved_amount, comment }: { id: string; approved_amount: number; comment?: string }) =>
      api.post(`/approvals/${id}/approve`, { approved_amount, comment }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["claims"] })
      qc.invalidateQueries({ queryKey: ["approvals"] })
    },
  })
}

export function useRejectClaim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.post(`/approvals/${id}/reject`, { reason }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["claims"] })
      qc.invalidateQueries({ queryKey: ["approvals"] })
    },
  })
}

/** Finance Payments page: "ready" (approved, unpaid) | "paid" | "all" — org-wide. */
export function usePayments(tab: "ready" | "paid" | "all", page = 1) {
  return useQuery<PaginatedResponse<Claim>>({
    queryKey: ["payments", tab, page],
    queryFn: () =>
      api.get("/payments", { params: { tab, page, page_size: 50 } }).then((r) => r.data),
  })
}

export function useMarkPaid() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, payment_reference }: { id: string; payment_reference?: string }) =>
      api.post(`/approvals/${id}/mark-paid`, { payment_reference }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["claims"] })
      qc.invalidateQueries({ queryKey: ["payments"] })   // move claim Ready to pay -> Paid
      qc.invalidateQueries({ queryKey: ["approvals"] })
    },
  })
}
