"use client"

import { motion } from "framer-motion"
import { useRouter } from "next/navigation"
import {
  Clock,
  CheckCircle2,
  CreditCard,
  XCircle,
  TrendingUp,
  Plus,
  ArrowRight,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ClaimCard } from "@/components/claims/ClaimCard"
import { useClaimStats, useClaimsList } from "@/hooks/use-claims"
import { useAuthStore } from "@/lib/auth"
import { formatINR } from "@/lib/utils"

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.08 } },
}
const item = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

function StatCard({
  icon: Icon,
  label,
  count,
  amount,
  iconClass,
  loading,
}: {
  icon: React.ElementType
  label: string
  count: number
  amount: number
  iconClass: string
  loading: boolean
}) {
  return (
    <motion.div variants={item}>
      <Card className="border-border/40 bg-card">
        <CardContent className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-2">
                {label}
              </p>
              {loading ? (
                <>
                  <Skeleton className="h-7 w-24 mb-1" />
                  <Skeleton className="h-4 w-16" />
                </>
              ) : (
                <>
                  <p className="text-2xl font-bold text-foreground tabular-nums">
                    {formatINR(amount)}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {count} claim{count !== 1 ? "s" : ""}
                  </p>
                </>
              )}
            </div>
            <div
              className={`flex items-center justify-center w-9 h-9 rounded-xl ${iconClass}`}
            >
              <Icon className="h-4.5 w-4.5" />
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// status may be a comma-separated list (e.g. "submitted,under_review")
function ClaimsTab({ status }: { status?: string }) {
  const { data, isLoading } = useClaimsList(status)
  const claims = data?.items ?? []

  if (isLoading)
    return (
      <div className="space-y-3 mt-4">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-20 w-full rounded-xl" />
        ))}
      </div>
    )

  if (claims.length === 0)
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
          <TrendingUp className="h-5 w-5 opacity-40" />
        </div>
        <p className="text-sm font-medium">No claims here</p>
        <p className="text-xs opacity-60 mt-1">
          {status ? `No ${status.split(",")[0].replace("_", " ")} claims` : "Submit your first claim to get started"}
        </p>
      </div>
    )

  return (
    <div className="space-y-2.5 mt-4">
      {claims.map((claim) => (
        <ClaimCard key={claim.id} claim={claim} />
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const router = useRouter()
  const { user } = useAuthStore()

  const isApprover = user?.roles.some((r) => ["approver", "admin"].includes(r))
  // Only employees file claims: New claim button, personal stat cards and My Claims tabs
  const isEmployee = !!user?.roles.includes("employee")
  const isAdminOnly = !!user?.roles.includes("admin") && !isEmployee
  // Approvers / finance (who don't file claims) see organisation-wide figures instead
  const showOrgStats =
    !isEmployee && !isAdminOnly && !!user?.roles.some((r) => ["approver", "finance"].includes(r))
  const { data: stats, isLoading: statsLoading } = useClaimStats(
    showOrgStats ? "org" : "mine",
    !!user && !isAdminOnly,
  )

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-start justify-between mb-6"
      >
        <div>
          <h1 className="text-2xl font-bold text-foreground">
            Good day, {user?.name.split(" ")[0]}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {showOrgStats
              ? "Organization overview — claims across all employees"
              : "Here's your reimbursement overview"}
          </p>
        </div>
        {isEmployee && (
          <Button onClick={() => router.push("/claims/new")} size="sm" className="gap-1.5">
            <Plus className="h-4 w-4" />
            New claim
          </Button>
        )}
      </motion.div>

      {/* Stats grid (personal claim stats — not shown to admins, who don't file claims) */}
      {!isAdminOnly && (
      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 lg:grid-cols-4 gap-3 mb-6"
      >
        <StatCard
          icon={Clock}
          label="Pending"
          count={stats?.pending_count ?? 0}
          amount={stats?.pending_amount ?? 0}
          iconClass="bg-blue-500/10 text-blue-400"
          loading={statsLoading}
        />
        <StatCard
          icon={CheckCircle2}
          label="Approved"
          count={stats?.approved_count ?? 0}
          amount={stats?.approved_amount ?? 0}
          iconClass="bg-emerald-500/10 text-emerald-400"
          loading={statsLoading}
        />
        <StatCard
          icon={CreditCard}
          label="Paid"
          count={stats?.paid_count ?? 0}
          amount={stats?.paid_amount ?? 0}
          iconClass="bg-violet-500/10 text-violet-400"
          loading={statsLoading}
        />
        <StatCard
          icon={XCircle}
          label="Rejected"
          count={stats?.rejected_count ?? 0}
          amount={stats?.rejected_amount ?? 0}
          iconClass="bg-red-500/10 text-red-400"
          loading={statsLoading}
        />
      </motion.div>
      )}

      {/* Approver quick-action */}
      {isApprover && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.3 }}
          className="mb-6"
        >
          <Card className="border-primary/20 bg-primary/5 cursor-pointer hover:bg-primary/10 transition-colors"
            onClick={() => router.push("/approvals")}>
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center">
                  <CheckCircle2 className="h-4 w-4 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-foreground">Review Queue</p>
                  <p className="text-xs text-muted-foreground">Claims awaiting your approval</p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Claims tabs */}
      {isEmployee && (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.3 }}
        >
          <Card className="border-border/40">
            <CardHeader className="pb-0 pt-5 px-5">
              <CardTitle className="text-base">My Claims</CardTitle>
            </CardHeader>
            <CardContent className="px-5 pb-5">
              <Tabs defaultValue="all">
                <TabsList className="mt-3">
                  <TabsTrigger value="all">All</TabsTrigger>
                  <TabsTrigger value="draft">Draft</TabsTrigger>
                  <TabsTrigger value="submitted">Submitted</TabsTrigger>
                  <TabsTrigger value="approved">Approved</TabsTrigger>
                  <TabsTrigger value="paid">Paid</TabsTrigger>
                </TabsList>
                <TabsContent value="all">
                  <ClaimsTab />
                </TabsContent>
                <TabsContent value="draft">
                  <ClaimsTab status="draft" />
                </TabsContent>
                <TabsContent value="submitted">
                  <ClaimsTab status="submitted,under_review" />
                </TabsContent>
                <TabsContent value="approved">
                  <ClaimsTab status="approved,partially_approved" />
                </TabsContent>
                <TabsContent value="paid">
                  <ClaimsTab status="paid" />
                </TabsContent>
              </Tabs>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  )
}
