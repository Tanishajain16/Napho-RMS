"use client"

import { QueryClientProvider } from "@tanstack/react-query"
import { Toaster } from "sonner"
import { queryClient } from "@/lib/query-client"
import { useEffect } from "react"
import { useAuthStore } from "@/lib/auth"

function AuthInitializer() {
  const initialize = useAuthStore((s) => s.initialize)
  useEffect(() => { initialize() }, [initialize])
  return null
}

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthInitializer />
      {children}
      <Toaster position="bottom-right" richColors closeButton />
    </QueryClientProvider>
  )
}
