import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { AdminUser, ApprovalChain } from "@/lib/types"

export function useAdminUsers() {
  return useQuery<AdminUser[]>({
    queryKey: ["admin", "users"],
    queryFn: () => api.get("/admin/users").then((r) => r.data),
  })
}

export function useUpdateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string; roles?: string[]; is_active?: boolean; name?: string }) =>
      api.put(`/admin/users/${id}`, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  })
}

export function useCreateUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { name: string; email: string; password: string; roles: string[] }) =>
      api.post("/admin/users", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
  })
}

export function useApprovalChains() {
  return useQuery<ApprovalChain[]>({
    queryKey: ["admin", "chains"],
    queryFn: () => api.get("/admin/approval-chains").then((r) => r.data),
  })
}

export function useCreateChain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      name: string
      min_amount?: number
      max_amount?: number
      is_active?: boolean
      steps?: {
        step_order: number
        approver_type: string
        approver_id?: string
        approver_role?: string
        timeout_hours?: number
      }[]
    }) => api.post("/admin/approval-chains", body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "chains"] }),
  })
}

export function useUpdateChain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      ...body
    }: {
      id: string
      name?: string
      min_amount?: number
      max_amount?: number
      is_active?: boolean
    }) => api.put(`/admin/approval-chains/${id}`, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "chains"] }),
  })
}

export function useDeleteChain() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) =>
      api.delete(`/admin/approval-chains/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "chains"] }),
  })
}

export function useAddStep() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      chainId,
      ...body
    }: {
      chainId: string
      step_order: number
      approver_type: string
      approver_id?: string
      approver_role?: string
      timeout_hours?: number
    }) => api.post(`/admin/approval-chains/${chainId}/steps`, body).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "chains"] }),
  })
}

export function useDeleteStep() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ chainId, stepId }: { chainId: string; stepId: string }) =>
      api.delete(`/admin/approval-chains/${chainId}/steps/${stepId}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "chains"] }),
  })
}
