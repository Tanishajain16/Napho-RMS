"use client"

import Link from "next/link"
import { motion } from "framer-motion"
import {
  Clock,
  CheckCircle2,
  XCircle,
  LayoutList,
  AlertTriangle,
  IndianRupee,
  ArrowRight,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { useManagerStats } from "@/hooks/use-manager"
import { useAuthStore } from "@/lib/auth"
import { formatINR } from "@/lib/utils"
import type { TeamMember } from "@/hooks/use-manager"

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.07 } },
}
const itemVariants = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.28 } },
}

function KpiCard({
  label,
  value,
  sub,
  icon: Icon,
  color,
}: {
  label: string
  value: string
  sub?: string
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
          {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
        </CardContent>
      </Card>
    </motion.div>
  )
}

function StatusPip({ count, color }: { count: number; color: string }) {
  if (count === 0) return <span className="text-xs text-muted-foreground/40">—</span>
  return (
    <span className={`inline-flex items-center justify-center min-w-[22px] h-5 rounded-full text-[11px] font-semibold tabular-nums px-1.5 ${color}`}>
      {count}
    </span>
  )
}

function TeamRow({ member, rank }: { member: TeamMember; rank: number }) {
  const initials = member.name.split(" ").map((p) => p[0]).join("").slice(0, 2).toUpperCase()
  const approvalRate =
    member.total_claims > 0
      ? Math.round(((member.approved + member.paid) / member.total_claims) * 100)
      : null

  return (
    <tr className="border-b border-border/30 last:border-0 hover:bg-muted/20 transition-colors">
      <td className="py-3 pr-3 w-8">
        <span className="text-xs text-muted-foreground/50 font-mono tabular-nums">{rank}</span>
      </td>
      <td className="py-3 pr-4">
        <div className="flex items-center gap-2.5">
          <Avatar className="h-7 w-7 shrink-0">
            <AvatarFallback className="bg-primary/15 text-primary text-[11px] font-semibold">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{member.name}</p>
            <p className="text-xs text-muted-foreground truncate">{member.email}</p>
          </div>
        </div>
      </td>
      <td className="py-3 pr-4 text-center">
        <StatusPip
          count={member.pending}
          color={member.pending > 0 ? "bg-amber-500/15 text-amber-400" : ""}
        />
      </td>
      <td className="py-3 pr-4 text-center">
        <StatusPip count={member.approved} color="bg-emerald-500/15 text-emerald-400" />
      </td>
      <td className="py-3 pr-4 text-center">
        <StatusPip count={member.rejected} color="bg-red-500/15 text-red-400" />
      </td>
      <td className="py-3 pr-4 text-center">
        <StatusPip count={member.paid} color="bg-violet-500/15 text-violet-400" />
      </td>
      <td className="py-3 pr-4 text-right tabular-nums text-sm font-medium">
        {formatINR(member.total_claimed)}
      </td>
      <td className="py-3 text-right">
        {approvalRate !== null && (
          <span className={`text-xs font-medium tabular-nums ${
            approvalRate >= 80 ? "text-emerald-400"
            : approvalRate >= 50 ? "text-amber-400"
            : "text-red-400"
          }`}>
            {approvalRate}%
          </span>
        )}
      </td>
    </tr>
  )
}

function ManagerSkeleton() {
  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <Skeleton className="h-9 w-52" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}
      </div>
      <Skeleton className="h-96 rounded-xl" />
    </div>
  )
}

export default function ManagerPage() {
  const { user } = useAuthStore()
  const { data, isLoading, error } = useManagerStats()

  const canAccess = user?.roles.includes("approver") || user?.roles.includes("admin")

  if (!canAccess) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-32 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">Access denied. Approver or admin only.</p>
      </div>
    )
  }

  if (isLoading) return <ManagerSkeleton />

  if (error || !data) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-32 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">Failed to load manager view</p>
      </div>
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="space-y-6"
      >
        {/* Header */}
        <motion.div variants={itemVariants} className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-foreground">Manager View</h1>
            <p className="text-sm text-muted-foreground mt-0.5">Consolidated team claim activity</p>
          </div>
          <Link href="/approvals">
            <button className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-primary/80 font-medium transition-colors mt-1">
              Review Queue
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </Link>
        </motion.div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Pending Review"
            value={data.pending_count.toString()}
            sub={data.pending_count === 1 ? "claim awaiting action" : "claims awaiting action"}
            icon={Clock}
            color={data.pending_count > 0 ? "bg-amber-500" : "bg-muted-foreground"}
          />
          <KpiCard
            label="Approved This Month"
            value={data.approved_this_month.toString()}
            sub={formatINR(data.approved_amount_this_month)}
            icon={CheckCircle2}
            color="bg-emerald-500"
          />
          <KpiCard
            label="Rejected Total"
            value={data.rejected_count.toString()}
            icon={XCircle}
            color="bg-red-500"
          />
          <KpiCard
            label="Total Processed"
            value={data.total_processed.toString()}
            sub="approved + rejected + paid"
            icon={LayoutList}
            color="bg-blue-500"
          />
        </div>

        {/* Team Breakdown */}
        <motion.div variants={itemVariants}>
          <Card className="border-border/40">
            <CardHeader className="pb-2 pt-5 px-5">
              <CardTitle className="text-sm font-semibold">Team Claim Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              {data.team_breakdown.length === 0 ? (
                <div className="flex flex-col items-center py-12 text-muted-foreground gap-2">
                  <LayoutList className="h-8 w-8 opacity-30" />
                  <p className="text-sm">No claim activity yet</p>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-border/50">
                        <th className="text-left text-xs text-muted-foreground font-medium pb-3 pr-3 w-8">#</th>
                        <th className="text-left text-xs text-muted-foreground font-medium pb-3 pr-4">Member</th>
                        <th className="text-center text-xs text-muted-foreground font-medium pb-3 pr-4">
                          <span className="text-amber-400/80">Pending</span>
                        </th>
                        <th className="text-center text-xs text-muted-foreground font-medium pb-3 pr-4">
                          <span className="text-emerald-400/80">Approved</span>
                        </th>
                        <th className="text-center text-xs text-muted-foreground font-medium pb-3 pr-4">
                          <span className="text-red-400/80">Rejected</span>
                        </th>
                        <th className="text-center text-xs text-muted-foreground font-medium pb-3 pr-4">
                          <span className="text-violet-400/80">Paid</span>
                        </th>
                        <th className="text-right text-xs text-muted-foreground font-medium pb-3 pr-4">Total Claimed</th>
                        <th className="text-right text-xs text-muted-foreground font-medium pb-3">Approval %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data.team_breakdown.map((member, i) => (
                        <TeamRow key={member.email} member={member} rank={i + 1} />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>

        {/* Summary footer */}
        <motion.div variants={itemVariants}>
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 px-1">
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <IndianRupee className="h-3.5 w-3.5" />
              <span>
                Total org claimed:{" "}
                <span className="font-medium text-foreground">
                  {formatINR(data.team_breakdown.reduce((s, m) => s + m.total_claimed, 0))}
                </span>
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <LayoutList className="h-3.5 w-3.5" />
              <span>
                {data.team_breakdown.length} active claimant{data.team_breakdown.length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}
