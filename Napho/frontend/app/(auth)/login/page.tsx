"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { motion } from "framer-motion"
import { Eye, EyeOff, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { useAuthStore } from "@/lib/auth"
import { getApiError } from "@/lib/api"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
})
type Form = z.infer<typeof schema>

const DEMO_USERS = [
  { email: "admin@napho.com",  role: "Admin",    color: "text-purple-400" },
  { email: "aryan@napho.com",  role: "Employee", color: "text-blue-400" },
  { email: "sneha@napho.com",  role: "Employee", color: "text-blue-400" },
  { email: "rohit@napho.com",  role: "Employee", color: "text-blue-400" },
  { email: "priya@napho.com",  role: "Approver", color: "text-amber-400" },
  { email: "rahul@napho.com",  role: "Finance",  color: "text-emerald-400" },
]

export default function LoginPage() {
  const router = useRouter()
  const login = useAuthStore((s) => s.login)
  const [show, setShow] = useState(false)
  const [demoLoading, setDemoLoading] = useState<string | null>(null)

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<Form>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: Form) => {
    try {
      await login(data.email, data.password)
      router.push("/dashboard")
    } catch (err: unknown) {
      toast.error(getApiError(err, "Invalid credentials"))
    }
  }

  const handleDemo = async (email: string) => {
    setDemoLoading(email)
    try {
      await login(email, "password123")
      router.push("/dashboard")
    } catch {
      toast.error("Demo login failed")
    } finally {
      setDemoLoading(null)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
    >
      {/* Logo */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-primary mb-4">
          <span className="text-primary-foreground font-bold text-xl">N</span>
        </div>
        <h1 className="text-2xl font-bold text-foreground">Napho RMS</h1>
        <p className="text-muted-foreground text-sm mt-1">Reimbursement Management</p>
      </div>

      <Card className="border-border/40 shadow-2xl shadow-black/50">
        <CardHeader className="pb-4">
          <CardTitle>Welcome back</CardTitle>
          <CardDescription>Sign in to your account to continue</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@company.com"
                {...register("email")}
                className={errors.email ? "border-destructive" : ""}
              />
              {errors.email && (
                <p className="text-xs text-destructive">{errors.email.message}</p>
              )}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={show ? "text" : "password"}
                  placeholder="••••••••"
                  {...register("password")}
                  className={`pr-10 ${errors.password ? "border-destructive" : ""}`}
                />
                <button
                  type="button"
                  onClick={() => setShow((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
                >
                  {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="text-xs text-destructive">{errors.password.message}</p>
              )}
            </div>

            <Button type="submit" className="w-full" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Signing in…
                </>
              ) : (
                "Sign in"
              )}
            </Button>
          </form>

          {/* Demo accounts */}
          <div className="mt-5 space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-px flex-1 bg-border" />
              <p className="text-xs text-muted-foreground">Demo accounts</p>
              <div className="h-px flex-1 bg-border" />
            </div>
            <div className="grid grid-cols-2 gap-1.5">
              {DEMO_USERS.map((u) => (
                <button
                  key={u.email}
                  type="button"
                  onClick={() => {
                    setValue("email", u.email)
                    setValue("password", "password123")
                    handleDemo(u.email)
                  }}
                  disabled={!!demoLoading}
                  className="flex items-center justify-between px-3 py-2 rounded-md bg-muted hover:bg-accent transition-colors text-xs disabled:opacity-50"
                >
                  <span className="text-foreground font-medium truncate">{u.email.split("@")[0]}</span>
                  <span className={`flex items-center gap-1.5 shrink-0 ml-2 font-medium ${u.color}`}>
                    {demoLoading === u.email && (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    )}
                    {u.role}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <p className="text-center text-sm text-muted-foreground mt-5">
            No account?{" "}
            <Link href="/register" className="text-primary hover:underline font-medium">
              Register
            </Link>
          </p>
        </CardContent>
      </Card>
    </motion.div>
  )
}
