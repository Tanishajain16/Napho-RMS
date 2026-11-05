"use client"

import { useState, useEffect } from "react"
import { Loader2, XCircle, AlertTriangle } from "lucide-react"
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
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { useRejectClaim } from "@/hooks/use-approvals"
import { getApiError } from "@/lib/api"

interface Props {
  open: boolean
  onClose: () => void
  claimId: string
  claimTitle: string
}

export function RejectModal({ open, onClose, claimId, claimTitle }: Props) {
  const [reason, setReason] = useState("")
  const reject = useRejectClaim()

  useEffect(() => {
    if (open) setReason("")
  }, [open])

  const isValid = reason.trim().length >= 10

  const handleSubmit = async () => {
    if (!isValid) return
    try {
      await reject.mutateAsync({ id: claimId, reason: reason.trim() })
      toast.success("Claim rejected", { description: "Moved to the Rejected tab in your Review Queue" })
      onClose()
    } catch (err: unknown) {
      toast.error(getApiError(err, "Failed to reject claim"))
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md border-border/60 bg-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <XCircle className="h-5 w-5 text-red-400" />
            Reject Claim
          </DialogTitle>
          <DialogDescription className="line-clamp-1">{claimTitle}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Warning banner */}
          <div className="flex items-start gap-2 px-3 py-2.5 rounded-lg bg-red-500/10 border border-red-500/30">
            <AlertTriangle className="h-4 w-4 text-red-400 shrink-0 mt-0.5" />
            <p className="text-xs text-red-400">
              This action will notify the claimant and cannot be undone without resubmission.
            </p>
          </div>

          {/* Reason */}
          <div className="space-y-2">
            <Label htmlFor="reason">
              Reason for rejection{" "}
              <span className="text-destructive">*</span>
            </Label>
            <Textarea
              id="reason"
              placeholder="Explain why this claim is being rejected (min. 10 characters)…"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              rows={4}
              className="resize-none"
            />
            <div className="flex items-center justify-between">
              {!isValid && reason.length > 0 ? (
                <p className="text-xs text-destructive">
                  Please provide at least 10 characters
                </p>
              ) : (
                <span />
              )}
              <span className="text-xs text-muted-foreground ml-auto">
                {reason.length} chars
              </span>
            </div>
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={onClose} disabled={reject.isPending}>
            Cancel
          </Button>
          <Button
            variant="destructive"
            onClick={handleSubmit}
            disabled={!isValid || reject.isPending}
          >
            {reject.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Rejecting…
              </>
            ) : (
              "Reject claim"
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
