import { cn } from "@/lib/utils"
import type { ClaimStatus } from "@/lib/types"

const STATUS_CONFIG: Record<ClaimStatus, { label: string; className: string }> = {
  draft: {
    label: "Draft",
    className: "bg-muted text-muted-foreground border-border",
  },
  submitted: {
    label: "Submitted",
    className: "bg-blue-500/10 text-blue-400 border-blue-500/30",
  },
  under_review: {
    label: "Under Review",
    className: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  },
  approved: {
    label: "Approved",
    className: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  },
  partially_approved: {
    label: "Partial",
    className: "bg-teal-500/10 text-teal-400 border-teal-500/30",
  },
  rejected: {
    label: "Rejected",
    className: "bg-red-500/10 text-red-400 border-red-500/30",
  },
  paid: {
    label: "Paid",
    className: "bg-violet-500/10 text-violet-400 border-violet-500/30",
  },
  cancelled: {
    label: "Cancelled",
    className: "bg-muted text-muted-foreground/50 border-border",
  },
}

export function StatusBadge({ status }: { status: ClaimStatus }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium",
        config.className
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {config.label}
    </span>
  )
}
