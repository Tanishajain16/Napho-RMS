"use client"

import { motion } from "framer-motion"
import { User, Mail, Shield, Building2, LogOut } from "lucide-react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { useAuthStore } from "@/lib/auth"

const ROLE_LABELS: Record<string, { label: string; className: string }> = {
  employee: { label: "Employee",  className: "bg-blue-500/10 text-blue-400 border-blue-500/30" },
  approver: { label: "Approver",  className: "bg-amber-500/10 text-amber-400 border-amber-500/30" },
  finance:  { label: "Finance",   className: "bg-violet-500/10 text-violet-400 border-violet-500/30" },
  admin:    { label: "Admin",     className: "bg-red-500/10 text-red-400 border-red-500/30" },
}

function RoleBadge({ role }: { role: string }) {
  const cfg = ROLE_LABELS[role] ?? { label: role, className: "bg-muted text-muted-foreground border-border" }
  return (
    <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium ${cfg.className}`}>
      {cfg.label}
    </span>
  )
}

function InfoRow({ icon: Icon, label, value }: { icon: React.ElementType; label: string; value: string }) {
  return (
    <div className="flex items-center gap-3 py-3">
      <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center shrink-0">
        <Icon className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-muted-foreground">{label}</p>
        <p className="text-sm font-medium text-foreground truncate mt-0.5">{value}</p>
      </div>
    </div>
  )
}

export default function SettingsPage() {
  const router = useRouter()
  const { user, logout } = useAuthStore()

  if (!user) return null

  const handleLogout = () => {
    logout()
    toast.success("Signed out")
    router.push("/login")
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mb-6"
      >
        <h1 className="text-2xl font-bold text-foreground">Settings</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Your account information and preferences
        </p>
      </motion.div>

      <div className="space-y-4">
        {/* Profile card */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.3 }}
        >
          <Card className="border-border/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Profile</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              {/* Avatar row */}
              <div className="flex items-center gap-4 pb-4 mb-2">
                <Avatar className="h-14 w-14">
                  <AvatarFallback className="bg-primary/20 text-primary text-xl font-bold">
                    {user.name[0].toUpperCase()}
                  </AvatarFallback>
                </Avatar>
                <div>
                  <p className="text-base font-bold text-foreground">{user.name}</p>
                  <p className="text-sm text-muted-foreground">{user.email}</p>
                  <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                    {user.roles.map((role) => (
                      <RoleBadge key={role} role={role} />
                    ))}
                  </div>
                </div>
              </div>

              <Separator className="mb-2" />

              <InfoRow icon={User}     label="Full name"     value={user.name} />
              <Separator />
              <InfoRow icon={Mail}     label="Email address" value={user.email} />
              <Separator />
              <InfoRow
                icon={Shield}
                label="Roles"
                value={user.roles.map((r) => ROLE_LABELS[r]?.label ?? r).join(", ")}
              />
              {user.org_id && (
                <>
                  <Separator />
                  <InfoRow icon={Building2} label="Organisation ID" value={user.org_id} />
                </>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Permissions card */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.3 }}
        >
          <Card className="border-border/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Permissions</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5 space-y-2">
              {[
                { key: "employee", label: "Submit & manage claims", enabled: user.roles.some((r) => ["employee", "admin"].includes(r)) },
                { key: "approver", label: "Review and approve claims", enabled: user.roles.some((r) => ["approver", "admin"].includes(r)) },
                { key: "finance",  label: "Process payments",         enabled: user.roles.some((r) => ["finance", "admin"].includes(r)) },
                { key: "admin",    label: "Full admin access",         enabled: user.roles.includes("admin") },
              ].map((p) => (
                <div key={p.key} className="flex items-center justify-between py-2">
                  <span className="text-sm text-muted-foreground">{p.label}</span>
                  <Badge
                    variant="outline"
                    className={
                      p.enabled
                        ? "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"
                        : "border-border text-muted-foreground/50"
                    }
                  >
                    {p.enabled ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        {/* Danger zone */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.3 }}
        >
          <Card className="border-border/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold text-muted-foreground">Session</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Sign out</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    End your current session
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  className="text-destructive border-destructive/30 hover:bg-destructive/10"
                  onClick={handleLogout}
                >
                  <LogOut className="h-3.5 w-3.5 mr-1.5" />
                  Sign out
                </Button>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
