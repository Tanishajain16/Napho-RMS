"use client"

import { useState, useRef, useEffect } from "react"
import { motion } from "framer-motion"
import {
  ResponsiveContainer,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Area,
  AreaChart,
  BarChart,
  Bar,
  Cell,
  PieChart,
  Pie,
  Legend,
} from "recharts"
import { TrendingUp, IndianRupee, CheckCircle2, Wallet, Percent, AlertTriangle, FileText, Clock, Sparkles, Send, Loader2 } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { useAnalytics } from "@/hooks/use-analytics"
import { useAuthStore } from "@/lib/auth"
import { formatINR } from "@/lib/utils"
import { api, getApiError } from "@/lib/api"
import type { OrgAnalytics } from "@/lib/types"

const CHART_COLORS = [
  "#6366f1", "#8b5cf6", "#ec4899", "#f43f5e",
  "#f59e0b", "#10b981", "#06b6d4", "#3b82f6",
]

const STATUS_COLORS: Record<string, string> = {
  draft: "#94a3b8",
  submitted: "#3b82f6",
  under_review: "#f59e0b",
  approved: "#10b981",
  partially_approved: "#06b6d4",
  rejected: "#ef4444",
  paid: "#8b5cf6",
}

const STATUS_LABEL: Record<string, string> = {
  draft: "Draft",
  submitted: "Submitted",
  under_review: "Under Review",
  approved: "Approved",
  partially_approved: "Partial",
  rejected: "Rejected",
  paid: "Paid",
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.08 },
  },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

function KpiCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string
  value: string
  icon: React.ElementType
  color: string
}) {
  return (
    <motion.div variants={itemVariants}>
      <Card className="border-border/40">
        <CardContent className="p-5">
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-muted-foreground">{label}</p>
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
              <Icon className="h-4 w-4 text-white" />
            </div>
          </div>
          <p className="text-2xl font-bold tabular-nums text-foreground">{value}</p>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function AnalyticsSkeleton() {
  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6">
      <Skeleton className="h-9 w-56" />
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
        {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-72 rounded-xl" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <Skeleton className="h-72 rounded-xl" />
        <Skeleton className="h-64 rounded-xl" />
      </div>
    </div>
  )
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-card border border-border/60 rounded-lg px-3 py-2 shadow-lg text-sm">
      <p className="text-muted-foreground mb-1">{label}</p>
      <p className="font-semibold text-foreground">{formatINR(payload[0].value)}</p>
    </div>
  )
}

function StatusTooltip({ active, payload }: { active?: boolean; payload?: Array<{ name: string; value: number; payload: { color: string } }> }) {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-card border border-border/60 rounded-lg px-3 py-2 shadow-lg text-sm">
      <p className="font-semibold text-foreground">{payload[0].name}</p>
      <p className="text-muted-foreground">{payload[0].value} claims</p>
    </div>
  )
}

const QUICK_QUESTIONS = [
  "Which category had the highest spend?",
  "What's our approval rate trend?",
  "Who are the top 3 claimants?",
  "How much is pending payment?",
  "What's the average claim amount?",
]

function buildAnalyticsContext(data: OrgAnalytics): string {
  const categoryLines = data.claims_by_category
    .map((c) => `  ${c.name}: ₹${c.amount.toLocaleString("en-IN")} (${c.count} claims)`)
    .join("\n")
  const monthLines = data.spending_by_month
    .map((m) => `  ${m.month}: ₹${m.amount.toLocaleString("en-IN")} (${m.count} claims)`)
    .join("\n")
  const topLines = data.top_claimants
    .slice(0, 5)
    .map((c, i) => `  ${i + 1}. ${c.name} — ₹${c.total_claimed.toLocaleString("en-IN")} (${c.count} claims)`)
    .join("\n")
  const statusLines = Object.entries(data.claims_by_status)
    .map(([s, n]) => `  ${s}: ${n}`)
    .join("\n")

  return `Here is the current org-level analytics data:
Total claims: ${data.total_claims}
Total claimed: ₹${data.total_amount_claimed.toLocaleString("en-IN")}
Total approved: ₹${data.total_amount_approved.toLocaleString("en-IN")}
Total paid: ₹${data.total_amount_paid.toLocaleString("en-IN")}
Approval rate: ${data.approval_rate}%
Avg approval days: ${data.avg_approval_days}

Claims by status:
${statusLines}

Spending by category:
${categoryLines}

Monthly spending:
${monthLines}

Top claimants:
${topLines}

Based on this data, please answer the following question:`
}

interface AiMessage { role: "user" | "assistant"; content: string }

function AIInsightsPanel({ data }: { data: OrgAnalytics }) {
  const [input, setInput] = useState("")
  const [messages, setMessages] = useState<AiMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<AiMessage[]>([])
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  const ask = async (question: string) => {
    if (!question.trim() || loading) return
    const contextualMessage = `${buildAnalyticsContext(data)} ${question}`
    const userMsg: AiMessage = { role: "user", content: question }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setLoading(true)
    try {
      const { data: res } = await api.post("/chat", {
        message: contextualMessage,
        conversation_history: history.slice(-6),
      })
      const assistantMsg: AiMessage = { role: "assistant", content: res.reply }
      setMessages((prev) => [...prev, assistantMsg])
      setHistory((prev) => [...prev, userMsg, assistantMsg])
    } catch (err: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Sorry — ${getApiError(err, "I could not process that question. Please try again.")}` },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div variants={itemVariants}>
      <Card className="border-border/40">
        <CardHeader className="pb-2 pt-5 px-5">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-primary" />
            AI Analyst
            <span className="text-[10px] font-normal text-muted-foreground bg-primary/10 text-primary px-1.5 py-0.5 rounded-full">
              Ask anything about your data
            </span>
          </CardTitle>
        </CardHeader>
        <CardContent className="px-5 pb-5 space-y-4">
          {/* Quick questions */}
          {messages.length === 0 && (
            <div className="flex flex-wrap gap-2">
              {QUICK_QUESTIONS.map((q) => (
                <button
                  key={q}
                  onClick={() => ask(q)}
                  disabled={loading}
                  className="text-xs px-3 py-1.5 rounded-full border border-border/50 bg-muted/40 hover:bg-muted hover:border-primary/40 text-muted-foreground hover:text-foreground transition-all disabled:opacity-40"
                >
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Messages */}
          {messages.length > 0 && (
            <div className="space-y-3 max-h-72 overflow-y-auto pr-1">
              {messages.map((m, i) => (
                <div
                  key={i}
                  className={`flex gap-2.5 ${m.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {m.role === "assistant" && (
                    <div className="w-6 h-6 rounded-full bg-primary/15 flex items-center justify-center shrink-0 mt-0.5">
                      <Sparkles className="h-3 w-3 text-primary" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                      m.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted/60 text-foreground border border-border/40"
                    }`}
                  >
                    {m.content}
                  </div>
                </div>
              ))}
              {loading && (
                <div className="flex gap-2.5">
                  <div className="w-6 h-6 rounded-full bg-primary/15 flex items-center justify-center shrink-0">
                    <Sparkles className="h-3 w-3 text-primary" />
                  </div>
                  <div className="bg-muted/60 border border-border/40 rounded-xl px-3 py-2 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:0ms]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:150ms]" />
                    <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/60 animate-bounce [animation-delay:300ms]" />
                  </div>
                </div>
              )}
              <div ref={bottomRef} />
            </div>
          )}

          {/* Input */}
          <div className="flex gap-2">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && ask(input)}
              placeholder="Ask about spending, approvals, trends…"
              disabled={loading}
              className="flex-1 text-xs bg-muted/40 border border-border/50 rounded-lg px-3 py-2 text-foreground placeholder:text-muted-foreground/60 focus:outline-none focus:ring-1 focus:ring-primary/50 focus:border-primary/50 transition-colors disabled:opacity-50"
            />
            <button
              onClick={() => ask(input)}
              disabled={!input.trim() || loading}
              className="w-8 h-8 rounded-lg bg-primary hover:bg-primary/90 disabled:opacity-40 flex items-center justify-center transition-all shrink-0"
            >
              {loading ? (
                <Loader2 className="h-3.5 w-3.5 text-primary-foreground animate-spin" />
              ) : (
                <Send className="h-3.5 w-3.5 text-primary-foreground" />
              )}
            </button>
          </div>

          {messages.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {QUICK_QUESTIONS.slice(0, 3).map((q) => (
                <button
                  key={q}
                  onClick={() => ask(q)}
                  disabled={loading}
                  className="text-[11px] px-2.5 py-1 rounded-full border border-border/40 bg-muted/30 hover:bg-muted text-muted-foreground hover:text-foreground transition-all disabled:opacity-40"
                >
                  {q}
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default function AnalyticsPage() {
  const { user } = useAuthStore()
  const { data, isLoading, error } = useAnalytics()

  const isAdmin = user?.roles.includes("admin")

  if (!isAdmin) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-32 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">Access denied. Admins only.</p>
      </div>
    )
  }

  if (isLoading) return <AnalyticsSkeleton />

  if (error || !data) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-32 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">Failed to load analytics</p>
      </div>
    )
  }

  const statusData = Object.entries(data.claims_by_status).map(([status, count]) => ({
    name: STATUS_LABEL[status] ?? status,
    value: count,
    color: STATUS_COLORS[status] ?? "#94a3b8",
  }))

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="space-y-6"
      >
        {/* Header */}
        <motion.div variants={itemVariants}>
          <h1 className="text-2xl font-bold text-foreground">Analytics</h1>
          <p className="text-sm text-muted-foreground mt-0.5">Organization spending overview</p>
        </motion.div>

        {/* KPI cards — 6 metrics */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
          <KpiCard
            label="Total Claims"
            value={data.total_claims.toString()}
            icon={FileText}
            color="bg-sky-500"
          />
          <KpiCard
            label="Total Claimed"
            value={formatINR(data.total_amount_claimed)}
            icon={IndianRupee}
            color="bg-blue-500"
          />
          <KpiCard
            label="Total Approved"
            value={formatINR(data.total_amount_approved)}
            icon={CheckCircle2}
            color="bg-emerald-500"
          />
          <KpiCard
            label="Total Paid"
            value={formatINR(data.total_amount_paid)}
            icon={Wallet}
            color="bg-violet-500"
          />
          <KpiCard
            label="Approval Rate"
            value={`${Math.round(data.approval_rate)}%`}
            icon={Percent}
            color="bg-amber-500"
          />
          <KpiCard
            label="Avg Approval"
            value={`${data.avg_approval_days.toFixed(1)}d`}
            icon={Clock}
            color="bg-rose-500"
          />
        </div>

        {/* Charts row 1 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          {/* Monthly Spending line chart */}
          <motion.div variants={itemVariants}>
            <Card className="border-border/40">
              <CardHeader className="pb-2 pt-5 px-5">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  Monthly Spending
                </CardTitle>
              </CardHeader>
              <CardContent className="px-2 pb-4">
                <ResponsiveContainer width="100%" height={220}>
                  <AreaChart data={data.spending_by_month} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
                    <defs>
                      <linearGradient id="spendGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.4} />
                    <XAxis
                      dataKey="month"
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                      width={48}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                      type="monotone"
                      dataKey="amount"
                      stroke="#6366f1"
                      strokeWidth={2.5}
                      fill="url(#spendGradient)"
                      dot={false}
                      activeDot={{ r: 4, fill: "#6366f1" }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>

          {/* Spending by category bar chart */}
          <motion.div variants={itemVariants}>
            <Card className="border-border/40">
              <CardHeader className="pb-2 pt-5 px-5">
                <CardTitle className="text-sm font-semibold">Spending by Category</CardTitle>
              </CardHeader>
              <CardContent className="px-2 pb-4">
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart
                    data={data.claims_by_category}
                    layout="vertical"
                    margin={{ top: 0, right: 16, bottom: 0, left: 0 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" strokeOpacity={0.4} horizontal={false} />
                    <XAxis
                      type="number"
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`}
                    />
                    <YAxis
                      type="category"
                      dataKey="name"
                      tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }}
                      axisLine={false}
                      tickLine={false}
                      width={130}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Bar dataKey="amount" radius={[0, 4, 4, 0]}>
                      {data.claims_by_category.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Charts row 2: Status donut + Top Claimants */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
          {/* Claims by Status donut */}
          <motion.div variants={itemVariants} className="lg:col-span-2">
            <Card className="border-border/40 h-full">
              <CardHeader className="pb-2 pt-5 px-5">
                <CardTitle className="text-sm font-semibold">Claims by Status</CardTitle>
              </CardHeader>
              <CardContent className="px-2 pb-4">
                {statusData.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-16">No data yet</p>
                ) : (
                  <ResponsiveContainer width="100%" height={220}>
                    <PieChart>
                      <Pie
                        data={statusData}
                        cx="50%"
                        cy="45%"
                        innerRadius={55}
                        outerRadius={80}
                        paddingAngle={2}
                        dataKey="value"
                      >
                        {statusData.map((entry, index) => (
                          <Cell key={`slice-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip content={<StatusTooltip />} />
                      <Legend
                        iconType="circle"
                        iconSize={8}
                        formatter={(value) => (
                          <span style={{ fontSize: 11, color: "hsl(var(--muted-foreground))" }}>{value}</span>
                        )}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Top Claimants table */}
          <motion.div variants={itemVariants} className="lg:col-span-3">
            <Card className="border-border/40 h-full">
              <CardHeader className="pb-2 pt-5 px-5">
                <CardTitle className="text-sm font-semibold">Top Claimants</CardTitle>
              </CardHeader>
              <CardContent className="px-5 pb-5">
                {data.top_claimants.length === 0 ? (
                  <p className="text-sm text-muted-foreground text-center py-6">No data yet</p>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b border-border/50">
                          <th className="text-left text-xs text-muted-foreground font-medium pb-3 w-8">#</th>
                          <th className="text-left text-xs text-muted-foreground font-medium pb-3">Name</th>
                          <th className="text-right text-xs text-muted-foreground font-medium pb-3">Claimed</th>
                          <th className="text-right text-xs text-muted-foreground font-medium pb-3">Count</th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.top_claimants.map((claimant, i) => (
                          <tr key={claimant.email} className="border-b border-border/30 last:border-0 hover:bg-muted/30 transition-colors">
                            <td className="py-3 text-muted-foreground font-mono text-xs">{i + 1}</td>
                            <td className="py-3">
                              <div className="flex items-center gap-2.5">
                                <Avatar className="h-7 w-7 shrink-0">
                                  <AvatarFallback className="bg-primary/20 text-primary text-xs font-semibold">
                                    {claimant.name[0].toUpperCase()}
                                  </AvatarFallback>
                                </Avatar>
                                <div className="min-w-0">
                                  <p className="font-medium text-foreground truncate">{claimant.name}</p>
                                  <p className="text-xs text-muted-foreground truncate">{claimant.email}</p>
                                </div>
                              </div>
                            </td>
                            <td className="py-3 text-right font-semibold tabular-nums text-xs">{formatINR(claimant.total_claimed)}</td>
                            <td className="py-3 text-right text-muted-foreground tabular-nums">{claimant.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* AI Analyst */}
        <AIInsightsPanel data={data} />

      </motion.div>
    </div>
  )
}
