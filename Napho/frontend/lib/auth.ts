import { create } from "zustand"
import { api } from "./api"
import type { User } from "./types"

interface AuthState {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  initialize: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: true,

  login: async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password })
    localStorage.setItem("napho_access_token", data.access_token)
    localStorage.setItem("napho_refresh_token", data.refresh_token)
    document.cookie = `napho_token=1; path=/; max-age=${60 * 60 * 24 * 7}`
    set({ user: data.user })
  },

  logout: () => {
    localStorage.removeItem("napho_access_token")
    localStorage.removeItem("napho_refresh_token")
    document.cookie = "napho_token=; path=/; max-age=0"
    set({ user: null })
  },

  initialize: async () => {
    const token = localStorage.getItem("napho_access_token")
    if (!token) {
      // No token — wipe cookie so middleware stops redirecting to /dashboard
      document.cookie = "napho_token=; path=/; max-age=0"
      set({ isLoading: false })
      return
    }
    try {
      const { data } = await api.get("/auth/me")
      set({ user: data, isLoading: false })
    } catch {
      localStorage.removeItem("napho_access_token")
      localStorage.removeItem("napho_refresh_token")
      document.cookie = "napho_token=; path=/; max-age=0"
      set({ user: null, isLoading: false })
    }
  },
}))
