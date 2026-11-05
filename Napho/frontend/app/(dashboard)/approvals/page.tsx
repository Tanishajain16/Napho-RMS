"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { ClipboardCheck, Clock, ArrowRight, CheckCircle2, XCircle, Loader2 } from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { ApproveModal } from "@/components/approvals/ApproveModal"
import { RejectModal } from "@/components/approvals/RejectModal"
import { useApprovalQueue } from "@/hooks/use-approvals"
import { formatINR, formatDate, daysSince } from "@/lib/utils"
import type { Claim } from "@/lib/types"

function DaysWaitingBadge({ submittedAt }: { submittedAt?: string }) {
  if (!submittedAt) return null
  const days = daysSince(submittedAt)
  const cls =
    days >= 7
      ? "bg-red-500/10 text-red-400 border-red-500/30"
      : days >= 3
      ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
      : "bg-muted text-muted-foreground border-border"
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${cls}`}>
      <Clock className="h-2.5 w-2.5" />
      {days}d waiting
    </span>
  )
}

function MyDecisionBadge({ claim }: { claim: Claim }) {
  if (!claim.my_decision) return null
  if (claim.my_decision === "rejected") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium bg-red-500/10 text-red-400 border-red-500/30">
        <XCircle className="h-2.5 w-2.5" />
        You rejected
      </span>
    )
  }
  const partial = claim.my_decision === "partially_approved"
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium ${
        partial
          ? "bg-amber-500/10 text-amber-400 border-amber-500/30"
          : "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
      }`}
    >
      <CheckCircle2 className="h-2.5 w-2.5" />
      {partial ? "You partially approved" : "You approved"}
    </span>
  )
}

function QueueRow({
  claim,
  onApprove,
  onReject,
  actionLoading,
}: {
  claim: Claim
  onApprove: (claim: Claim) => void
  onReject: (claim: Claim) => void
  actionLoading: string | null
}) {
  const router = useRouter()
  const decided = !!claim.my_decision
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
    >
      <Card className="border-border/40 hover:border-border transition-colors">
        <CardContent className="p-4">
          <div className="flex items-start gap-4">
            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <StatusBadge status={claim.status} />
                {decided ? (
                  <MyDecisionBadge claim={claim} />
                ) : (
                  <DaysWaitingBadge submittedAt={claim.submitted_at} />
                )}
                <span className="text-xs text-muted-foreground font-mono">{claim.claim_number}</span>
              </div>
              <h3 className="text-sm font-semibold text-foreground truncate">{claim.title}</h3>
              <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                <span>{claim.claimant.name}</span>
                <span>·</span>
                <span>{formatDate(claim.expense_date)}</span>
                {claim.category && (
                  <>
                    <span>·</span>
                    <span>{claim.category.name}</span>
                  </>
                )}
              </div>
            </div>

            {/* Amount + actions */}
            <div className="flex items-center gap-3 shrink-0">
              <div className="text-right">
                {decided && claim.my_approved_amount != null ? (
                  <>
                    <p className="text-sm font-bold tabular-nums text-emerald-400">
                      {formatINR(claim.my_approved_amount)}
                    </p>
                    {claim.my_approved_amount !== claim.claimed_amount && (
                      <p className="text-[11px] text-muted-foreground tabular-nums">
                        of {formatINR(claim.claimed_amount)}
                      </p>
                    )}
                  </>
                ) : (
                  <p className="text-sm font-bold tabular-nums">{formatINR(claim.claimed_amount)}</p>
                )}
              </div>

              {claim.can_act && (
                <div className="flex items-center gap-1.5">
                  <Button
                    size="sm"
                    className="h-7 px-2.5 text-xs bg-emerald-600 hover:bg-emerald-700 text-white"
                    onClick={() => onApprove(claim)}
                    disabled={!!actionLoading}
                  >
                    {actionLoading === `approve-${claim.id}` ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <><CheckCircle2 className="h-3 w-3 mr-1" />Approve</>
                    )}
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="h-7 px-2.5 text-xs"
                    onClick={() => onReject(claim)}
                    disabled={!!actionLoading}
                  >
                    {actionLoading === `reject-${claim.id}` ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <><XCircle className="h-3 w-3 mr-1" />Reject</>
                    )}
                  </Button>
                </div>
              )}

              <Button
                variant="ghost"
                size="sm"
                className="h-7 w-7 p-0 text-muted-foreground"
                onClick={() => router.push(`/claims/${claim.id}`)}
              >
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function QueueTab({ status }: { status: string }) {
  const [approvingClaim, setApprovingClaim] = useState<Claim | null>(null)
  const [rejectingClaim, setRejectingClaim] = useState<Claim | null>(null)
  const [actionLoading] = useState<string | null>(null)
  const { data, isLoading } = useApprovalQueue(status)
  const claims = data?.items ?? []

  if (isLoading) {
    return (
      <div className="space-y-3 mt-4">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
      </div>
    )
  }

  if (claims.length === 0) {
    const emptyText: Record<string, [string, string]> = {
      pending:  ["Queue is empty", "No claims are waiting for your review"],
      approved: ["Nothing approved yet", "Claims you approve (fully or partially) appear here"],
      rejected: ["Nothing rejected", "Claims you reject appear here"],
      all:      ["No claims yet", "Claims waiting for you and ones you've reviewed appear here"],
    }
    const [title, hint] = emptyText[status] ?? emptyText.all
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
          <ClipboardCheck className="h-5 w-5 opacity-40" />
        </div>
        <p className="text-sm font-medium">{title}</p>
        <p className="text-xs opacity-60 mt-1">{hint}</p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-2.5 mt-4">
        {claims.map((claim) => (
          <QueueRow
            key={claim.id}
            claim={claim}
            onApprove={setApprovingClaim}
            onReject={setRejectingClaim}
            actionLoading={actionLoading}
          />
        ))}
        {data?.total != null && data.total > claims.length && (
          <p className="text-xs text-center text-muted-foreground pt-1">
            Showing {claims.length} of {data.total}
          </p>
        )}
      </div>

      {approvingClaim && (
        <ApproveModal
          open
          onClose={() => setApprovingClaim(null)}
          claimId={approvingClaim.id}
          claimedAmount={approvingClaim.claimed_amount}
          claimTitle={approvingClaim.title}
        />
      )}
      {rejectingClaim && (
        <RejectModal
          open
          onClose={() => setRejectingClaim(null)}
          claimId={rejectingClaim.id}
          claimTitle={rejectingClaim.title}
        />
      )}
    </>
  )
}

function TabCount({ n }: { n?: number }) {
  if (!n) return null
  return <span className="ml-1.5 text-[10px] tabular-nums opacity-70">{n}</span>
}

export default function ApprovalsPage() {
  const { data: pendingData } = useApprovalQueue("pending")
  const { data: approvedData } = useApprovalQueue("approved")
  const { data: rejectedData } = useApprovalQueue("rejected")
  const pendingCount = pendingData?.total ?? 0

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-start justify-between mb-6"
      >
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-2xl font-bold text-foreground">Review Queue</h1>
            {pendingCount > 0 && (
              <Badge className="bg-primary/20 text-primary border-primary/30 tabular-nums">
                {pendingCount}
              </Badge>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Claims awaiting your review and approval
          </p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        <Tabs defaultValue="pending">
          <TabsList>
            <TabsTrigger value="pending">Pending<TabCount n={pendingCount} /></TabsTrigger>
            <TabsTrigger value="approved">Approved<TabCount n={approvedData?.total} /></TabsTrigger>
            <TabsTrigger value="rejected">Rejected<TabCount n={rejectedData?.total} /></TabsTrigger>
            <TabsTrigger value="all">All</TabsTrigger>
          </TabsList>
          <TabsContent value="pending"><QueueTab status="pending" /></TabsContent>
          <TabsContent value="approved"><QueueTab status="approved" /></TabsContent>
          <TabsContent value="rejected"><QueueTab status="rejected" /></TabsContent>
          <TabsContent value="all"><QueueTab status="all" /></TabsContent>
        </Tabs>
      </motion.div>
    </div>
  )
}
