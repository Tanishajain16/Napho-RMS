import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { Claim, ClaimDetail, ClaimStats, PaginatedResponse } from "@/lib/types"

export function useClaimsList(status?: string, page = 1) {
  return useQuery<PaginatedResponse<Claim>>({
    queryKey: ["claims", status, page],
    queryFn: () =>
      api.get("/claims", { params: { status, page, page_size: 20 } }).then((r) => r.data),
  })
}

export function useClaimDetail(id: string) {
  return useQuery<ClaimDetail>({
    queryKey: ["claims", id],
    queryFn: () => api.get(`/claims/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

/** scope "mine" = own claims; "org" = whole organisation (approver/finance/admin only) */
export function useClaimStats(scope: "mine" | "org" = "mine", enabled = true) {
  return useQuery<ClaimStats>({
    queryKey: ["claims", "stats", scope],
    queryFn: () => api.get("/claims/stats", { params: { scope } }).then((r) => r.data),
    enabled,
  })
}

export function useCreateClaim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: unknown) => api.post("/claims", data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["claims"] }),
  })
}

export function useUpdateClaim(id: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: unknown) => api.put(`/claims/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["claims"] }),
  })
}

export function useSubmitClaim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/claims/${id}/submit`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["claims"] }),
  })
}

export function useDeleteClaim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/claims/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["claims"] }),
  })
}

export function useCancelClaim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/claims/${id}/cancel`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["claims"] }),
  })
}

export function useResubmitClaim() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/claims/${id}/resubmit`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["claims"] }),
  })
}
