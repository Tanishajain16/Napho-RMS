import axios from "axios"

type PydanticError = { msg: string; loc?: unknown[]; type?: string }

export function getApiError(err: unknown, fallback = "Something went wrong"): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (!detail) return fallback
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    return (detail as PydanticError[])
      .map((e) => e.msg ?? String(e))
      .join("; ")
  }
  return fallback
}

export const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1",
  headers: { "Content-Type": "application/json" },
})

api.interceptors.request.use((config) => {
  if (typeof window !== "undefined") {
    const token = localStorage.getItem("napho_access_token")
    if (token) config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refreshToken = localStorage.getItem("napho_refresh_token")
      if (refreshToken) {
        try {
          const { data } = await axios.post(
            `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/auth/refresh`,
            { refresh_token: refreshToken }
          )
          localStorage.setItem("napho_access_token", data.access_token)
          original.headers.Authorization = `Bearer ${data.access_token}`
          return api(original)
        } catch {
          localStorage.removeItem("napho_access_token")
          localStorage.removeItem("napho_refresh_token")
          if (typeof window !== "undefined") {
            document.cookie = "napho_token=; path=/; max-age=0"
            window.location.href = "/login"
          }
        }
      }
    }
    return Promise.reject(error)
  }
)
