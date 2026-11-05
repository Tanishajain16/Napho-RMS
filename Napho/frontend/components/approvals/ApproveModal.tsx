"use client"

import { useState, useEffect } from "react"
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useApproveClaim } from "@/hooks/use-approvals"
import { getApiError } from "@/lib/api"
import { formatINR } from "@/lib/utils"
import { cn } from "@/lib/utils"

interface ApprovalStepSummary {
  level: string
  approver_name?: string
  status: "pending" | "approved" | "rejected" | "skipped"
}

interface Props {
  open: boolean
  onClose: () => void
  claimId: string
  claimedAmount: number
  claimTitle: string
  approvalSteps?: ApprovalStepSummary[]
}

export function ApproveModal({ open, onClose, claimId, claimedAmount, claimTitle, approvalSteps }: Props) {
  const [approvedAmount, setApprovedAmount] = useState(claimedAmount)
  const [comment, setComment] = useState("")
  const approve = useApproveClaim()

  // Reset when dialog opens
  useEffect(() => {
    if (open) {
      setApprovedAmount(claimedAmount)
      setComment("")
    }
  }, [open, claimedAmount])

  const isPartial = approvedAmount < claimedAmount
  const isValid = approvedAmount > 0 && approvedAmount <= claimedAmount

  const handleSubmit = async () => {
    if (!isValid) return
    try {
      await approve.mutateAsync({ id: claimId, approved_amount: approvedAmount, comment: comment || undefined })
      toast.success(isPartial ? "Claim partially approved" : "Claim approved", {
        description: "Moved to the Approved tab in your Review Queue",
      })
      onClose()
    } catch (err: unknown) {
      toast.error(getApiError(err, "Failed to approve claim"))
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md border-border/60 bg-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-emerald-400" />
            Approve Claim
          </DialogTitle>
          <DialogDescription className="line-clamp-1">{claimTitle}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Claimed amount reference */}
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-muted/50 border border-border/50">
            <span className="text-sm text-muted-foreground">Claimed amount</span>
            <span className="text-sm font-semibold tabular-nums">{formatINR(claimedAmount)}</span>
          </div>

          {/* Approval steps indicator */}
          {approvalSteps && approvalSteps.length > 0 && (
            <div className="flex items-center gap-1.5 flex-wrap">
              {approvalSteps.map((step, i) => {
                const isApproved = step.status === "approved"
                const isRejected = step.status === "rejected"
                const isPending  = step.status === "pending"
                return (
                  <div key={i} className="flex items-center gap-1.5">
                    <div className={cn(
                      "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border",
                      isApproved ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                        : isRejected ? "bg-red-500/10 text-red-400 border-red-500/30"
                        : isPending ? "bg-primary/10 text-primary border-primary/30"
                        : "bg-muted/50 text-muted-foreground border-border/40"
                    )}>
                      <span>{step.level}</span>
                      {step.approver_name && (
                        <span className="opacity-70">· {step.approver_name}</span>
                      )}
                    </div>
                    {i < approvalSteps.length - 1 && (
                      <span className="text-muted-foreground/40 text-xs">→</span>
                    )}
                  </div>
                )
              })}
            </div>
          )}

          {/* Approved amount */}
          <div className="space-y-2">
            <Label htmlFor="approved-amount">Approved amount</Label>
            <div className="relative">
              <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-sm font-medium">
                ₹
              </span>
              <Input
                id="approved-amount"
                type="number"
                min={1}
                max={claimedAmount}
                step={1}
                value={approvedAmount}
                onChange={(e) => setApprovedAmount(Number(e.target.value))}
                className="pl-7 tabular-nums"
              />
            </div>
            {approvedAmount > claimedAmount && (
              <p className="text-xs text-destructive flex items-center gap-1">
                <AlertCircle className="h-3 w-3" />
                Cannot exceed claimed amount
              </p>
            )}
          </div>

          {/* Partial approval banner */}
          {isPartial && isValid && (
            <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-amber-500/10 border border-amber-500/30">
              <AlertCircle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-medium text-amber-400">Partial approval</p>
                <p className="text-xs text-amber-400/70 mt-0.5">
                  You are approving {formatINR(approvedAmount)} of {formatINR(claimedAmount)} (
                  {Math.round((approvedAmount / claimedAmount) * 100)}%)
                </p>
              </div>
            </div>
          )}

          {/* Comment */}
          <div className="space-y-2">
            <Label htmlFor="comment">
              Comment{" "}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <Textarea
              id="comment"
              placeholder="Add a note for the claimant…"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              rows={3}
              className="resize-none"
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={onClose} disabled={approve.isPending}>
            Cancel
          </Button>
          <Button
            onClick={handleSubmit}
            disabled={!isValid || approve.isPending}
            className={cn(isPartial ? "bg-amber-500 hover:bg-amber-600 text-white" : "")}
          >
            {approve.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Approving…
              </>
            ) : isPartial ? (
              `Partially approve · ${formatINR(approvedAmount)}`
            ) : (
              `Approve · ${formatINR(approvedAmount)}`
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
