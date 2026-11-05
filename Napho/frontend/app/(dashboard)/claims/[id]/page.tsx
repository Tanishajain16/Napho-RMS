"use client"

import { useState } from "react"
import { useParams, useRouter } from "next/navigation"
import { motion } from "framer-motion"
import {
  ArrowLeft, Send, RotateCcw, XCircle, CheckCircle2,
  CreditCard, Paperclip, Clock, FileText, Loader2, AlertTriangle,
  Pencil, Trash2,
} from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { StatusBadge } from "@/components/ui/status-badge"
import { ApprovalTimeline } from "@/components/claims/ApprovalTimeline"
import { ApproveModal } from "@/components/approvals/ApproveModal"
import { RejectModal } from "@/components/approvals/RejectModal"
import { DeleteClaimDialog } from "@/components/claims/DeleteClaimDialog"
import {
  useClaimDetail,
  useSubmitClaim,
  useCancelClaim,
  useResubmitClaim,
} from "@/hooks/use-claims"

// ─── Multi-step Approval Progress Timeline ─────────────────────────────────────

function ApprovalProgressTimeline({ approvals }: { approvals: ApprovalStep[] }) {
  if (!approvals || approvals.length < 2) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.12, duration: 0.25 }}
    >
      <Card className="border-border/40">
        <CardHeader className="pb-2 pt-4 px-5">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
            Approval Progress
          </CardTitle>
        </CardHeader>
        <CardContent className="px-5 pb-5">
          <div className="relative">
            {/* Connector line */}
            <div className="absolute left-4 top-5 bottom-5 w-px bg-border" />

            <div className="space-y-5">
              {approvals.map((step, i) => {
                const isApproved  = step.status === "approved"
                const isRejected  = step.status === "rejected"
                const isCurrent   = step.status === "pending" && approvals.slice(0, i).every(s => s.status === "approved")
                const isFuture    = step.status === "pending" && !isCurrent

                const circleClass = isApproved
                  ? "bg-emerald-500 border-emerald-500 text-white"
                  : isRejected
                  ? "bg-red-500 border-red-500 text-white"
                  : isCurrent
                  ? "bg-primary border-primary text-primary-foreground"
                  : "bg-muted border-border text-muted-foreground"

                const labelClass = isApproved
                  ? "text-emerald-400"
                  : isRejected
                  ? "text-red-400"
                  : isCurrent
                  ? "text-foreground font-semibold"
                  : "text-muted-foreground"

                return (
                  <motion.div
                    key={step.id}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.07, duration: 0.22 }}
                    className="relative flex items-start gap-4"
                  >
                    {/* Step circle */}
                    <div className={`relative z-10 flex items-center justify-center w-8 h-8 rounded-full border-2 shrink-0 text-xs font-bold ${circleClass}`}>
                      {isApproved ? (
                        <CheckCircle2 className="h-3.5 w-3.5" />
                      ) : isRejected ? (
                        <XCircle className="h-3.5 w-3.5" />
                      ) : (
                        step.level
                      )}
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0 pb-1">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <p className={`text-sm leading-snug ${labelClass}`}>
                            {step.level} Approval
                            {isCurrent && <span className="ml-2 text-[10px] text-primary bg-primary/10 border border-primary/20 px-1.5 py-0.5 rounded-full font-medium">Current</span>}
                          </p>
                          {step.approver_name && (
                            <p className="text-xs text-muted-foreground mt-0.5">{step.approver_name}</p>
                          )}
                          {step.approved_amount != null && isApproved && (
                            <p className="text-xs text-emerald-400 mt-0.5 tabular-nums">
                              Approved {formatINR(step.approved_amount)}
                            </p>
                          )}
                          {step.comment && (
                            <p className="mt-1.5 text-xs text-muted-foreground bg-muted/50 rounded-md px-2.5 py-1.5 border border-border/50 italic">
                              &ldquo;{step.comment}&rdquo;
                            </p>
                          )}
                        </div>
                        {step.acted_at && (
                          <time className="text-[10px] text-muted-foreground/60 shrink-0 mt-0.5">
                            {formatDate(step.acted_at)}
                          </time>
                        )}
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}
import { useMarkPaid } from "@/hooks/use-approvals"
import { useAuthStore } from "@/lib/auth"
import { formatINR, formatDate } from "@/lib/utils"
import type { ApprovalStep } from "@/lib/types"

function DetailSkeleton() {
  return (
    <div className="p-6 max-w-4xl mx-auto space-y-5">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-32 w-full rounded-xl" />
      <Skeleton className="h-48 w-full rounded-xl" />
      <Skeleton className="h-64 w-full rounded-xl" />
    </div>
  )
}

export default function ClaimDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { user } = useAuthStore()
  const { data: claim, isLoading, error } = useClaimDetail(id)

  const submitClaim = useSubmitClaim()
  const cancelClaim = useCancelClaim()
  const resubmitClaim = useResubmitClaim()
  const markPaid = useMarkPaid()

  const [approveOpen, setApproveOpen] = useState(false)
  const [rejectOpen, setRejectOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  const isApprover = user?.roles.some((r) => ["approver", "admin"].includes(r))
  const isFinance = user?.roles.some((r) => ["finance", "admin"].includes(r))
  const isOwner = user?.id === claim?.claimant.id

  const handleAction = async (
    action: string,
    fn: () => Promise<unknown>,
    successMsg: string
  ) => {
    setActionLoading(action)
    try {
      await fn()
      toast.success(successMsg)
    } catch {
      toast.error(`Failed to ${action} claim`)
    } finally {
      setActionLoading(null)
    }
  }

  if (isLoading) return <DetailSkeleton />

  if (error || !claim) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-24 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">Claim not found</p>
        <Button variant="ghost" size="sm" className="mt-3" onClick={() => router.push("/claims")}>
          Back to claims
        </Button>
      </div>
    )
  }

  const canSubmit = isOwner && claim.status === "draft"
  const canEditDraft = isOwner && claim.status === "draft"
  // Drafts get "Delete"; Cancel is only offered once a claim has been submitted
  const canCancel = isOwner && claim.status === "submitted"
  const canResubmit = isOwner && claim.status === "rejected"
  // Backend decides whose turn it is (current chain level, one decision per person)
  const canApprove = claim.can_act ?? (isApprover && ["submitted", "under_review"].includes(claim.status))
  const canMarkPaid = isFinance && ["approved", "partially_approved"].includes(claim.status)

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Back + header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25 }}
        className="mb-5"
      >
        <Button
          variant="ghost"
          size="sm"
          className="mb-3 -ml-2 text-muted-foreground"
          onClick={() => router.back()}
        >
          <ArrowLeft className="h-4 w-4 mr-1.5" />
          Back
        </Button>

        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-2.5 mb-1.5">
              <StatusBadge status={claim.status} />
              <span className="text-xs text-muted-foreground font-mono">{claim.claim_number}</span>
            </div>
            <h1 className="text-xl font-bold text-foreground">{claim.title}</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              {claim.claimant.name} · {formatDate(claim.expense_date)}
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            {canEditDraft && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => router.push(`/claims/${claim.id}/edit`)}
                disabled={!!actionLoading}
              >
                <Pencil className="h-3.5 w-3.5 mr-1.5" />Edit
              </Button>
            )}
            {canSubmit && (
              <Button
                size="sm"
                onClick={() =>
                  handleAction("submit", () => submitClaim.mutateAsync(claim.id), "Claim submitted!")
                }
                disabled={!!actionLoading}
              >
                {actionLoading === "submit" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <><Send className="h-3.5 w-3.5 mr-1.5" />Submit</>
                )}
              </Button>
            )}
            {canResubmit && (
              <Button
                size="sm"
                variant="outline"
                onClick={() =>
                  handleAction("resubmit", () => resubmitClaim.mutateAsync(claim.id), "Claim resubmitted!")
                }
                disabled={!!actionLoading}
              >
                {actionLoading === "resubmit" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <><RotateCcw className="h-3.5 w-3.5 mr-1.5" />Resubmit</>
                )}
              </Button>
            )}
            {canApprove && (
              <>
                <Button
                  size="sm"
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                  onClick={() => setApproveOpen(true)}
                >
                  <CheckCircle2 className="h-3.5 w-3.5 mr-1.5" />Approve
                </Button>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => setRejectOpen(true)}
                >
                  <XCircle className="h-3.5 w-3.5 mr-1.5" />Reject
                </Button>
              </>
            )}
            {canMarkPaid && (
              <Button
                size="sm"
                className="bg-violet-600 hover:bg-violet-700 text-white"
                onClick={() =>
                  handleAction("mark-paid", () => markPaid.mutateAsync({ id: claim.id }), "Marked as paid!")
                }
                disabled={!!actionLoading}
              >
                {actionLoading === "mark-paid" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <><CreditCard className="h-3.5 w-3.5 mr-1.5" />Mark paid</>
                )}
              </Button>
            )}
            {canCancel && (
              <Button
                size="sm"
                variant="ghost"
                className="text-muted-foreground hover:text-destructive"
                onClick={() =>
                  handleAction("cancel", () => cancelClaim.mutateAsync(claim.id), "Claim cancelled")
                }
                disabled={!!actionLoading}
              >
                {actionLoading === "cancel" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <><XCircle className="h-3.5 w-3.5 mr-1.5" />Cancel</>
                )}
              </Button>
            )}
            {canEditDraft && (
              <Button
                size="sm"
                variant="ghost"
                className="text-muted-foreground hover:text-destructive"
                onClick={() => setDeleteOpen(true)}
                disabled={!!actionLoading}
              >
                <Trash2 className="h-3.5 w-3.5 mr-1.5" />Delete
              </Button>
            )}
          </div>
        </div>
      </motion.div>

      {/* Rejection banner */}
      {claim.status === "rejected" && claim.rejection_reason && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-5 flex items-start gap-3 px-4 py-3 rounded-xl bg-red-500/10 border border-red-500/30"
        >
          <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-red-400">Claim rejected</p>
            <p className="text-xs text-red-400/80 mt-0.5">{claim.rejection_reason}</p>
          </div>
        </motion.div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left column: amounts + items + attachments */}
        <div className="lg:col-span-2 space-y-5">
          {/* Amount summary */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05, duration: 0.25 }}
          >
            <Card className="border-border/40">
              <CardContent className="p-5">
                <div className="grid grid-cols-3 divide-x divide-border">
                  <div className="pr-4">
                    <p className="text-xs text-muted-foreground mb-1">Claimed</p>
                    <p className="text-xl font-bold tabular-nums">{formatINR(claim.claimed_amount)}</p>
                  </div>
                  {claim.approved_amount != null && (
                    <div className="px-4">
                      <p className="text-xs text-muted-foreground mb-1">Approved</p>
                      <p className="text-xl font-bold text-emerald-400 tabular-nums">
                        {formatINR(claim.approved_amount)}
                      </p>
                    </div>
                  )}
                  {claim.paid_amount != null && (
                    <div className="pl-4">
                      <p className="text-xs text-muted-foreground mb-1">Paid</p>
                      <p className="text-xl font-bold text-violet-400 tabular-nums">
                        {formatINR(claim.paid_amount)}
                      </p>
                    </div>
                  )}
                </div>
                {claim.category && (
                  <div className="mt-3 pt-3 border-t border-border">
                    <Badge variant="secondary" className="text-xs">
                      {claim.category.name}
                    </Badge>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Line items */}
          {claim.items && claim.items.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1, duration: 0.25 }}
            >
              <Card className="border-border/40">
                <CardHeader className="pb-2 pt-4 px-5">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <FileText className="h-4 w-4 text-muted-foreground" />
                    Line Items
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-4">
                  <div className="space-y-2">
                    {claim.items.map((item, i) => (
                      <div
                        key={item.id ?? i}
                        className="flex items-start justify-between gap-3 py-2 border-b border-border/50 last:border-0"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-foreground truncate">
                            {item.description}
                          </p>
                          {item.vendor_name && (
                            <p className="text-xs text-muted-foreground">{item.vendor_name}</p>
                          )}
                          {item.expense_date && (
                            <p className="text-xs text-muted-foreground">{formatDate(item.expense_date)}</p>
                          )}
                        </div>
                        <div className="text-right shrink-0">
                          <p className="text-sm font-semibold tabular-nums">{formatINR(item.amount)}</p>
                          {item.approved_amount != null && item.approved_amount !== item.amount && (
                            <p className="text-xs text-emerald-400 tabular-nums">
                              ✓ {formatINR(item.approved_amount)}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <Separator className="my-3" />
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-muted-foreground">Total</span>
                    <span className="text-base font-bold tabular-nums">
                      {formatINR(claim.claimed_amount)}
                    </span>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          )}

          {/* Attachments */}
          {claim.attachments && claim.attachments.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.25 }}
            >
              <Card className="border-border/40">
                <CardHeader className="pb-2 pt-4 px-5">
                  <CardTitle className="text-sm font-semibold flex items-center gap-2">
                    <Paperclip className="h-4 w-4 text-muted-foreground" />
                    Attachments
                  </CardTitle>
                </CardHeader>
                <CardContent className="px-5 pb-4 space-y-2">
                  {claim.attachments.map((att) => (
                    <a
                      key={att.id}
                      href={att.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-muted/50 border border-border/50 hover:bg-accent transition-colors"
                    >
                      <Paperclip className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm text-foreground flex-1 truncate">{att.file_name}</span>
                      {att.file_size && (
                        <span className="text-xs text-muted-foreground shrink-0">
                          {(att.file_size / 1024).toFixed(0)} KB
                        </span>
                      )}
                    </a>
                  ))}
                </CardContent>
              </Card>
            </motion.div>
          )}
        </div>

        {/* Right column: timeline */}
        <div className="space-y-5">
          {/* Multi-step approval progress */}
          {claim.approvals && claim.approvals.length >= 2 && (
            <ApprovalProgressTimeline approvals={claim.approvals} />
          )}

          {/* Key dates */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.25 }}
          >
            <Card className="border-border/40">
              <CardHeader className="pb-2 pt-4 px-5">
                <CardTitle className="text-sm font-semibold flex items-center gap-2">
                  <Clock className="h-4 w-4 text-muted-foreground" />
                  Dates
                </CardTitle>
              </CardHeader>
              <CardContent className="px-5 pb-4 space-y-2.5">
                <div className="flex justify-between text-xs">
                  <span className="text-muted-foreground">Created</span>
                  <span className="text-foreground font-medium">{formatDate(claim.created_at)}</span>
                </div>
                {claim.submitted_at && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Submitted</span>
                    <span className="text-blue-400 font-medium">{formatDate(claim.submitted_at)}</span>
                  </div>
                )}
                {claim.approved_at && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Approved</span>
                    <span className="text-emerald-400 font-medium">{formatDate(claim.approved_at)}</span>
                  </div>
                )}
                {claim.paid_at && (
                  <div className="flex justify-between text-xs">
                    <span className="text-muted-foreground">Paid</span>
                    <span className="text-violet-400 font-medium">{formatDate(claim.paid_at)}</span>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>

          {/* Activity timeline */}
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.25 }}
          >
            <Card className="border-border/40">
              <CardHeader className="pb-2 pt-4 px-5">
                <CardTitle className="text-sm font-semibold">Activity</CardTitle>
              </CardHeader>
              <CardContent className="px-5 pb-5">
                <ApprovalTimeline history={claim.history ?? []} />
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>

      {/* Modals */}
      <ApproveModal
        open={approveOpen}
        onClose={() => setApproveOpen(false)}
        claimId={claim.id}
        claimedAmount={claim.claimed_amount}
        claimTitle={claim.title}
      />
      <RejectModal
        open={rejectOpen}
        onClose={() => setRejectOpen(false)}
        claimId={claim.id}
        claimTitle={claim.title}
      />
      <DeleteClaimDialog
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        claimId={claim.id}
        claimTitle={claim.title}
        claimNumber={claim.claim_number}
        onDeleted={() => router.push("/claims")}
      />
    </div>
  )
}
