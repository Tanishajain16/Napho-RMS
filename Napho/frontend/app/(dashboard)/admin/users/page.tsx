"use client"

import { useState, useRef, useEffect } from "react"
import { motion } from "framer-motion"
import {
  Plus,
  Search,
  Users,
  UserCheck,
  ShieldCheck,
  FileText,
  Loader2,
  AlertTriangle,
  Sparkles,
  Send,
  ShieldAlert,
} from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Skeleton } from "@/components/ui/skeleton"
import { Label } from "@/components/ui/label"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { useAdminUsers, useUpdateUser, useCreateUser } from "@/hooks/use-admin"
import { useAuthStore } from "@/lib/auth"
import { api, getApiError } from "@/lib/api"
import { formatDate } from "@/lib/utils"
import type { AdminUser } from "@/lib/types"

// ─── Constants ────────────────────────────────────────────────────────────────

const AVAILABLE_ROLES = ["employee", "approver", "finance", "admin"] as const

const ROLE_BADGE: Record<string, { label: string; className: string }> = {
  employee: { label: "Employee", className: "bg-blue-500/15 text-blue-400 border-blue-500/30" },
  approver: { label: "Approver", className: "bg-amber-500/15 text-amber-400 border-amber-500/30" },
  finance:  { label: "Finance",  className: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30" },
  admin:    { label: "Admin",    className: "bg-purple-500/15 text-purple-400 border-purple-500/30" },
}

const ROLE_FILTERS = ["All", "Employee", "Approver", "Finance", "Admin"] as const
type RoleFilter = (typeof ROLE_FILTERS)[number]

const QUICK_QUESTIONS = [
  "Who are my approvers?",
  "Which users have the most claims?",
  "Show me inactive users",
  "How many employees do we have?",
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function getInitials(name: string): string {
  return name
    .split(" ")
    .map((w) => w[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)
}

function RoleBadge({ role }: { role: string }) {
  const cfg = ROLE_BADGE[role] ?? { label: role, className: "bg-muted text-muted-foreground border-border" }
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium border ${cfg.className}`}
    >
      {cfg.label}
    </span>
  )
}

// ─── KPI Card ─────────────────────────────────────────────────────────────────

function KpiCard({
  icon: Icon,
  label,
  value,
}: {
  icon: React.ElementType
  label: string
  value: string | number
}) {
  return (
    <Card className="border-border/40">
      <CardContent className="p-4 flex items-start gap-3">
        <div className="mt-0.5 p-2 rounded-lg bg-primary/10">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div>
          <p className="text-xs text-muted-foreground font-medium">{label}</p>
          <p className="text-2xl font-bold text-foreground leading-tight mt-0.5">{value}</p>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Invite User Dialog ────────────────────────────────────────────────────────

function InviteDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const createUser = useCreateUser()
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    roles: ["employee"] as string[],
  })

  const toggleRole = (role: string) => {
    setForm((f) => ({
      ...f,
      roles: f.roles.includes(role) ? f.roles.filter((r) => r !== role) : [...f.roles, role],
    }))
  }

  const handleSubmit = async () => {
    if (!form.name || !form.email || !form.password) {
      toast.error("Name, email and password are required")
      return
    }
    if (form.roles.length === 0) {
      toast.error("At least one role is required")
      return
    }
    try {
      await createUser.mutateAsync(form)
      toast.success("User invited successfully")
      setForm({ name: "", email: "", password: "", roles: ["employee"] })
      onClose()
    } catch {
      toast.error("Failed to invite user")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md border-border/60 bg-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Plus className="h-4 w-4 text-primary" />
            Invite User
          </DialogTitle>
          <DialogDescription>Create a new user account in your organization.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="space-y-2">
            <Label htmlFor="invite-name">Full name</Label>
            <Input
              id="invite-name"
              placeholder="Jane Smith"
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="invite-email">Email</Label>
            <Input
              id="invite-email"
              type="email"
              placeholder="jane@company.com"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="invite-password">Password</Label>
            <Input
              id="invite-password"
              type="password"
              placeholder="Temporary password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            />
          </div>
          <div className="space-y-2">
            <Label>Roles</Label>
            <div className="flex flex-wrap gap-2">
              {AVAILABLE_ROLES.map((role) => (
                <button
                  key={role}
                  type="button"
                  onClick={() => toggleRole(role)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                    form.roles.includes(role)
                      ? "bg-primary/15 text-primary border-primary/40"
                      : "bg-muted/50 text-muted-foreground border-border/50 hover:bg-muted"
                  }`}
                >
                  {ROLE_BADGE[role]?.label ?? role}
                </button>
              ))}
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={onClose} disabled={createUser.isPending}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={createUser.isPending}>
            {createUser.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Inviting…
              </>
            ) : (
              "Invite User"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Edit Roles Dialog ─────────────────────────────────────────────────────────

function EditRolesDialog({
  user,
  open,
  onClose,
}: {
  user: AdminUser
  open: boolean
  onClose: () => void
}) {
  const updateUser = useUpdateUser()
  const [selectedRoles, setSelectedRoles] = useState<string[]>(user.roles)

  useEffect(() => {
    if (open) setSelectedRoles(user.roles)
  }, [open, user.roles])

  const toggleRole = (role: string) => {
    setSelectedRoles((prev) =>
      prev.includes(role) ? prev.filter((r) => r !== role) : [...prev, role]
    )
  }

  const handleSave = async () => {
    if (selectedRoles.length === 0) {
      toast.error("At least one role is required")
      return
    }
    try {
      await updateUser.mutateAsync({ id: user.id, roles: selectedRoles })
      toast.success("Roles updated")
      onClose()
    } catch {
      toast.error("Failed to update roles")
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-sm border-border/60 bg-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-primary" />
            Edit Roles
          </DialogTitle>
          <DialogDescription className="line-clamp-1">{user.name}</DialogDescription>
        </DialogHeader>

        <div className="py-3 space-y-2">
          {AVAILABLE_ROLES.map((role) => {
            const checked = selectedRoles.includes(role)
            const cfg = ROLE_BADGE[role]
            return (
              <label
                key={role}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border cursor-pointer transition-all ${
                  checked
                    ? "bg-primary/10 border-primary/30"
                    : "bg-muted/30 border-border/40 hover:bg-muted/60"
                }`}
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleRole(role)}
                  className="w-4 h-4 rounded accent-primary"
                />
                <span
                  className={`text-sm font-medium ${
                    checked ? "text-foreground" : "text-muted-foreground"
                  }`}
                >
                  {cfg.label}
                </span>
              </label>
            )
          })}
        </div>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={onClose} disabled={updateUser.isPending}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={updateUser.isPending}>
            {updateUser.isPending ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
            Save roles
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── User Row ──────────────────────────────────────────────────────────────────

function UserRow({ user, index }: { user: AdminUser; index: number }) {
  const updateUser = useUpdateUser()
  const [editRolesOpen, setEditRolesOpen] = useState(false)

  const handleToggleActive = async () => {
    try {
      await updateUser.mutateAsync({ id: user.id, is_active: !user.is_active })
      toast.success(user.is_active ? "User deactivated" : "User activated")
    } catch {
      toast.error("Failed to update user")
    }
  }

  return (
    <>
      <tr className="border-b border-border/30 last:border-0 hover:bg-muted/20 transition-colors group">
        {/* # */}
        <td className="py-3 pl-4 pr-3 text-xs text-muted-foreground tabular-nums w-10">
          {index + 1}
        </td>

        {/* User */}
        <td className="py-3 pr-4">
          <div className="flex items-center gap-3">
            <Avatar className="h-8 w-8 shrink-0">
              <AvatarFallback className="bg-primary/15 text-primary text-xs font-semibold">
                {getInitials(user.name)}
              </AvatarFallback>
            </Avatar>
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{user.name}</p>
              <p className="text-xs text-muted-foreground truncate">{user.email}</p>
              {user.department && (
                <span className="text-[10px] text-muted-foreground/70 font-medium uppercase tracking-wide">
                  {user.department}
                </span>
              )}
            </div>
          </div>
        </td>

        {/* Roles */}
        <td className="py-3 pr-4">
          <div className="flex flex-wrap gap-1">
            {user.roles.map((r) => (
              <RoleBadge key={r} role={r} />
            ))}
          </div>
        </td>

        {/* Claims */}
        <td className="py-3 pr-4 text-sm tabular-nums">
          <span className={user.claim_count ? "text-foreground" : "text-muted-foreground/50"}>
            {user.claim_count ?? 0}
          </span>
        </td>

        {/* Status */}
        <td className="py-3 pr-4">
          <span
            className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-[11px] font-medium border ${
              user.is_active
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                : "bg-muted/50 text-muted-foreground border-border/40"
            }`}
          >
            <span
              className={`w-1.5 h-1.5 rounded-full ${
                user.is_active ? "bg-emerald-400" : "bg-muted-foreground"
              }`}
            />
            {user.is_active ? "Active" : "Inactive"}
          </span>
        </td>

        {/* Joined */}
        <td className="py-3 pr-4 text-xs text-muted-foreground hidden lg:table-cell whitespace-nowrap">
          {formatDate(user.created_at)}
        </td>

        {/* Actions */}
        <td className="py-3 pl-2 pr-4">
          <div className="flex items-center gap-1 justify-end opacity-0 group-hover:opacity-100 transition-opacity">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2.5 text-xs"
              onClick={() => setEditRolesOpen(true)}
            >
              Edit roles
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-7 px-2.5 text-xs ${
                user.is_active
                  ? "text-muted-foreground hover:text-destructive"
                  : "text-emerald-400 hover:text-emerald-300"
              }`}
              onClick={handleToggleActive}
              disabled={updateUser.isPending}
            >
              {updateUser.isPending ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : user.is_active ? (
                "Deactivate"
              ) : (
                "Activate"
              )}
            </Button>
          </div>
        </td>
      </tr>

      <EditRolesDialog user={user} open={editRolesOpen} onClose={() => setEditRolesOpen(false)} />
    </>
  )
}

// ─── Typing Indicator ─────────────────────────────────────────────────────────

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2 rounded-xl bg-muted/50 w-fit">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
          transition={{ duration: 0.8, delay: i * 0.15, repeat: Infinity }}
        />
      ))}
    </div>
  )
}

// ─── AI Assistant Panel ────────────────────────────────────────────────────────

interface ChatMessage {
  role: "user" | "assistant"
  content: string
}

function AiAssistantPanel({ users }: { users: AdminUser[] }) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, isTyping])

  const buildContext = () => {
    const lines = users.map((u) =>
      `- ${u.name} (${u.email}): roles=[${u.roles.join(", ")}], claims=${u.claim_count ?? 0}, active=${u.is_active}${u.department ? `, dept=${u.department}` : ""}${u.designation ? `, title=${u.designation}` : ""}`
    )
    return `You are an AI assistant for a team expense management app. Here is the current user roster:\n\n${lines.join("\n")}\n\nAnswer questions about these users concisely.`
  }

  const sendMessage = async (question: string) => {
    const q = question.trim()
    if (!q || isTyping) return

    const userMsg: ChatMessage = { role: "user", content: q }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setIsTyping(true)

    const history = [...messages, userMsg]
    const contextualMessage = `${buildContext()}\n\nQuestion: ${q}`

    try {
      const { data } = await api.post("/chat", {
        message: contextualMessage,
        conversation_history: history.slice(-6),
      })
      // backend returns { reply, tool_calls_made }
      const reply = data?.reply || "I couldn't find an answer to that."
      setMessages((prev) => [...prev, { role: "assistant", content: reply }])
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Sorry — ${getApiError(err, "I ran into an error. Please try again.")}` },
      ])
    } finally {
      setIsTyping(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  return (
    <Card className="border-border/40">
      <CardHeader className="pb-3 pt-5 px-5">
        <CardTitle className="flex items-center gap-2 text-base font-semibold">
          <Sparkles className="h-4 w-4 text-primary" />
          AI Assistant
        </CardTitle>
        <p className="text-xs text-muted-foreground">
          Ask anything about your team members
        </p>
      </CardHeader>

      <CardContent className="px-5 pb-5 space-y-4">
        {/* Quick questions */}
        {messages.length === 0 && (
          <div className="flex flex-wrap gap-2">
            {QUICK_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                disabled={isTyping}
                className="px-3 py-1.5 rounded-full text-xs font-medium border border-border/50 bg-muted/40 text-muted-foreground hover:bg-muted hover:text-foreground transition-all disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {/* Messages */}
        {messages.length > 0 && (
          <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted/50 text-muted-foreground"
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <TypingIndicator />
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}

        {/* Input */}
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your team…"
            className="flex-1 h-9 text-sm"
            disabled={isTyping}
          />
          <Button
            size="sm"
            className="h-9 px-3 shrink-0"
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || isTyping}
          >
            {isTyping ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Page ──────────────────────────────────────────────────────────────────────

export default function AdminUsersPage() {
  const { user: currentUser } = useAuthStore()
  const { data: users, isLoading, error } = useAdminUsers()
  const [search, setSearch] = useState("")
  const [roleFilter, setRoleFilter] = useState<RoleFilter>("All")
  const [inviteOpen, setInviteOpen] = useState(false)

  const isAdmin = currentUser?.roles.includes("admin")

  if (!isAdmin) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-32 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">Access denied. Admins only.</p>
      </div>
    )
  }

  const allUsers = users ?? []

  // KPI calculations
  const totalMembers = allUsers.length
  const activeCount = allUsers.filter((u) => u.is_active).length
  const approverCount = allUsers.filter((u) => u.roles.includes("approver")).length
  const activeUsers = allUsers.filter((u) => u.is_active)
  const avgClaims =
    activeUsers.length > 0
      ? (activeUsers.reduce((sum, u) => sum + (u.claim_count ?? 0), 0) / activeUsers.length).toFixed(1)
      : "0.0"

  // Filtering
  const filtered = allUsers.filter((u) => {
    const matchesSearch =
      u.name.toLowerCase().includes(search.toLowerCase()) ||
      u.email.toLowerCase().includes(search.toLowerCase())
    const matchesRole =
      roleFilter === "All" || u.roles.includes(roleFilter.toLowerCase())
    return matchesSearch && matchesRole
  })

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="flex items-center justify-between gap-4"
      >
        <div>
          <h1 className="text-2xl font-bold text-foreground">User Management</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Manage team members, roles, and access
          </p>
        </div>
        <Button size="sm" onClick={() => setInviteOpen(true)} className="shrink-0">
          <Plus className="h-4 w-4 mr-1.5" />
          Invite User
        </Button>
      </motion.div>

      {/* KPI Bar */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.05, duration: 0.25 }}
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        {isLoading ? (
          [...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)
        ) : (
          <>
            <KpiCard icon={Users} label="Total Members" value={totalMembers} />
            <KpiCard icon={UserCheck} label="Active" value={activeCount} />
            <KpiCard icon={ShieldCheck} label="Approvers" value={approverCount} />
            <KpiCard icon={FileText} label="Avg Claims" value={avgClaims} />
          </>
        )}
      </motion.div>

      {/* Main Table Card */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.25 }}
      >
        <Card className="border-border/40">
          {/* Search + Filter Row */}
          <CardHeader className="pb-3 pt-5 px-5">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              {/* Search */}
              <div className="relative flex-1 max-w-xs">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search by name or email…"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="pl-9 h-9"
                />
              </div>

              {/* Role Filter Buttons */}
              <div className="flex items-center gap-1 flex-wrap">
                {ROLE_FILTERS.map((f) => (
                  <button
                    key={f}
                    onClick={() => setRoleFilter(f)}
                    className={`px-2.5 py-1 rounded-md text-xs font-medium border transition-all ${
                      roleFilter === f
                        ? "bg-primary/15 text-primary border-primary/40"
                        : "bg-transparent text-muted-foreground border-border/40 hover:bg-muted/50"
                    }`}
                  >
                    {f}
                  </button>
                ))}
              </div>

              {/* Count */}
              {users && (
                <p className="text-xs text-muted-foreground whitespace-nowrap sm:ml-auto">
                  {filtered.length} of {allUsers.length} users
                </p>
              )}
            </div>
          </CardHeader>

          <CardContent className="px-5 pb-5">
            {isLoading ? (
              <div className="space-y-3">
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} className="h-14 rounded-lg" />
                ))}
              </div>
            ) : error ? (
              <div className="flex flex-col items-center py-12 text-muted-foreground gap-2">
                <AlertTriangle className="h-8 w-8 opacity-40" />
                <p className="text-sm">Failed to load users</p>
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center py-12 text-muted-foreground gap-2">
                <Search className="h-8 w-8 opacity-30" />
                <p className="text-sm">
                  {search || roleFilter !== "All" ? "No users match your filters" : "No users yet"}
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-border/50">
                      <th className="text-left text-xs text-muted-foreground font-medium pb-3 pl-4 pr-3 w-10">
                        #
                      </th>
                      <th className="text-left text-xs text-muted-foreground font-medium pb-3 pr-4">
                        User
                      </th>
                      <th className="text-left text-xs text-muted-foreground font-medium pb-3 pr-4">
                        Roles
                      </th>
                      <th className="text-left text-xs text-muted-foreground font-medium pb-3 pr-4">
                        Claims
                      </th>
                      <th className="text-left text-xs text-muted-foreground font-medium pb-3 pr-4">
                        Status
                      </th>
                      <th className="text-left text-xs text-muted-foreground font-medium pb-3 pr-4 hidden lg:table-cell">
                        Joined
                      </th>
                      <th className="text-right text-xs text-muted-foreground font-medium pb-3 pr-4">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {filtered.map((u, i) => (
                      <UserRow key={u.id} user={u} index={i} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </motion.div>

      {/* AI Assistant Panel */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15, duration: 0.25 }}
      >
        <AiAssistantPanel users={allUsers} />
      </motion.div>

      <InviteDialog open={inviteOpen} onClose={() => setInviteOpen(false)} />
    </div>
  )
}
