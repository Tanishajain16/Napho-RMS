"use client"

import { motion } from "framer-motion"
import { Check, Clock, X, Send, FileText, CreditCard, XCircle } from "lucide-react"
import { formatDate } from "@/lib/utils"
import { cn } from "@/lib/utils"
import type { ClaimHistory } from "@/lib/types"

const ACTION_CONFIG: Record<string, {
  icon: React.ElementType
  label: string
  color: string
  dotColor: string
}> = {
  created:       { icon: FileText,  label: "Claim created",       color: "text-muted-foreground", dotColor: "bg-muted-foreground" },
  submitted:     { icon: Send,      label: "Submitted for review", color: "text-blue-400",         dotColor: "bg-blue-500" },
  under_review:  { icon: Clock,     label: "Under review",         color: "text-amber-400",        dotColor: "bg-amber-500" },
  approved:      { icon: Check,     label: "Approved",             color: "text-emerald-400",      dotColor: "bg-emerald-500" },
  partially_approved: { icon: Check, label: "Partially approved", color: "text-teal-400",         dotColor: "bg-teal-500" },
  rejected:      { icon: X,         label: "Rejected",             color: "text-red-400",          dotColor: "bg-red-500" },
  paid:          { icon: CreditCard, label: "Payment processed",   color: "text-violet-400",       dotColor: "bg-violet-500" },
  cancelled:     { icon: XCircle,   label: "Cancelled",            color: "text-muted-foreground", dotColor: "bg-muted-foreground" },
  resubmitted:   { icon: Send,      label: "Resubmitted",          color: "text-blue-400",         dotColor: "bg-blue-500" },
}

function getConfig(action: string) {
  return ACTION_CONFIG[action] ?? ACTION_CONFIG.created
}

interface Props {
  history: ClaimHistory[]
}

export function ApprovalTimeline({ history }: Props) {
  if (!history || history.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-4 text-center">
        No activity yet
      </div>
    )
  }

  return (
    <div className="relative">
      {/* Vertical line */}
      <div className="absolute left-3.5 top-3 bottom-3 w-px bg-border" />

      <div className="space-y-5">
        {history.map((item, i) => {
          const cfg = getConfig(item.action)
          const Icon = cfg.icon
          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.06, duration: 0.25 }}
              className="relative flex gap-4"
            >
              {/* Dot / icon */}
              <div className={cn(
                "relative z-10 flex items-center justify-center w-7 h-7 rounded-full border-2 border-background shrink-0 mt-0.5",
                cfg.dotColor
              )}>
                <Icon className="h-3.5 w-3.5 text-white" />
              </div>

              {/* Content */}
              <div className="flex-1 pb-1">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className={cn("text-sm font-medium leading-snug", cfg.color)}>
                      {cfg.label}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      by{" "}
                      <span className="text-foreground font-medium">
                        {item.actor.name}
                      </span>
                    </p>
                    {item.comment && (
                      <p className="mt-1.5 text-xs text-muted-foreground bg-muted/50 rounded-md px-2.5 py-1.5 border border-border/50 italic">
                        &ldquo;{item.comment}&rdquo;
                      </p>
                    )}
                  </div>
                  <time className="text-[10px] text-muted-foreground/60 shrink-0 mt-0.5">
                    {formatDate(item.created_at)}
                  </time>
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
