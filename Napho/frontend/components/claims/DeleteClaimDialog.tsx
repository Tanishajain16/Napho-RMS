"use client"

import { Loader2, Trash2 } from "lucide-react"
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
import { useDeleteClaim } from "@/hooks/use-claims"
import { getApiError } from "@/lib/api"

interface Props {
  open: boolean
  onClose: () => void
  claimId: string
  claimTitle: string
  claimNumber?: string
  /** Called after a successful delete (e.g. to navigate away). */
  onDeleted?: () => void
}

export function DeleteClaimDialog({ open, onClose, claimId, claimTitle, claimNumber, onDeleted }: Props) {
  const del = useDeleteClaim()

  const handleDelete = async () => {
    try {
      await del.mutateAsync(claimId)
      toast.success("Draft claim deleted")
      onClose()
      onDeleted?.()
    } catch (err: unknown) {
      toast.error(getApiError(err, "Failed to delete claim"))
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && !del.isPending && onClose()}>
      <DialogContent className="sm:max-w-md border-border/60 bg-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Trash2 className="h-5 w-5 text-red-400" />
            Delete draft claim?
          </DialogTitle>
          <DialogDescription>
            <span className="font-medium text-foreground">{claimTitle}</span>
            {claimNumber && <span className="font-mono"> · {claimNumber}</span>}
            <br />
            This draft and its line items will be removed. This can&apos;t be undone.
          </DialogDescription>
        </DialogHeader>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={onClose} disabled={del.isPending}>
            Keep draft
          </Button>
          <Button variant="destructive" onClick={handleDelete} disabled={del.isPending}>
            {del.isPending ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Deleting…</>
            ) : (
              <><Trash2 className="mr-2 h-4 w-4" />Delete</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
