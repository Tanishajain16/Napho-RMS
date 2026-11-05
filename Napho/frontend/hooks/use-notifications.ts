import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { Notification } from "@/lib/types"

interface NotifResponse { items: Notification[]; unread_count: number }

export function useNotifications() {
  return useQuery<NotifResponse>({
    queryKey: ["notifications"],
    queryFn: () => api.get("/notifications").then((r) => r.data),
    refetchInterval: 30_000,
  })
}

export function useMarkAllRead() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post("/notifications/read-all").then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["notifications"] }),
  })
}
