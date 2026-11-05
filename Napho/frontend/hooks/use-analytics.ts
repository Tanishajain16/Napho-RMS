import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { OrgAnalytics } from "@/lib/types"

export function useAnalytics() {
  return useQuery<OrgAnalytics>({
    queryKey: ["analytics"],
    queryFn: () => api.get("/analytics/overview").then((r) => r.data),
  })
}
