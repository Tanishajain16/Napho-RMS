import { useQuery } from "@tanstack/react-query"
import { api } from "@/lib/api"
import type { Category } from "@/lib/types"

export function useCategories() {
  return useQuery<Category[]>({
    queryKey: ["categories"],
    queryFn: () => api.get("/categories").then((r) => r.data),
    staleTime: Infinity,
  })
}
