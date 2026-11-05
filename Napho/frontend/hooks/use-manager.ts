import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"

export interface TeamMember {
  name: string
  email: string
  pending: number
  approved: number
  rejected: number
  paid: number
  total_claims: number
  total_claimed: number
}

export interface ManagerStats {
  pending_count: number
  approved_this_month: number
  approved_amount_this_month: number
  rejected_count: number
  total_processed: number
  team_breakdown: TeamMember[]
}

export function useManagerStats() {
  return useQuery<ManagerStats>({
    queryKey: ["manager", "stats"],
    queryFn: () => api.get("/approvals/stats").then((r) => r.data),
  })
}
