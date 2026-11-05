"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { useRouter } from "next/navigation"
import { Calendar, Tag, ArrowRight, Pencil, Trash2 } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/ui/status-badge"
import { DeleteClaimDialog } from "@/components/claims/DeleteClaimDialog"
import { useAuthStore } from "@/lib/auth"
import { formatINR, formatDate } from "@/lib/utils"
import type { Claim } from "@/lib/types"

export function ClaimCard({ claim }: { claim: Claim }) {
  const router = useRouter()
  const { user } = useAuthStore()
  const [deleteOpen, setDeleteOpen] = useState(false)

  const isEditableDraft = claim.status === "draft" && claim.claimant?.id === user?.id

  return (
    <>
      <motion.div whileHover={{ y: -2 }} transition={{ duration: 0.15 }}>
        <Card
          className="border-border/40 hover:border-border hover:shadow-lg hover:shadow-black/20 cursor-pointer transition-all duration-200 bg-card"
          onClick={() => router.push(`/claims/${claim.id}`)}
        >
          <CardContent className="p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5">
                  <StatusBadge status={claim.status} />
                  <span className="text-xs text-muted-foreground font-mono tracking-tight">
                    {claim.claim_number}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-foreground truncate leading-snug">
                  {claim.title}
                </h3>
                <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="h-3 w-3" />
                    {formatDate(claim.expense_date)}
                  </span>
                  {claim.category && (
                    <span className="flex items-center gap-1">
                      <Tag className="h-3 w-3" />
                      {claim.category.name}
                    </span>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <div className="text-right">
                  <p className="text-sm font-semibold text-foreground tabular-nums">
                    {formatINR(claim.claimed_amount)}
                  </p>
                  {claim.approved_amount != null &&
                    claim.approved_amount !== claim.claimed_amount && (
                      <p className="text-xs text-emerald-400 tabular-nums">
                        ✓ {formatINR(claim.approved_amount)}
                      </p>
                    )}
                </div>

                {isEditableDraft && (
                  <div className="flex items-center gap-0.5" onClick={(e) => e.stopPropagation()}>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-foreground"
                      onClick={() => router.push(`/claims/${claim.id}/edit`)}
                      aria-label="Edit draft"
                      title="Edit draft"
                    >
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => setDeleteOpen(true)}
                      aria-label="Delete draft"
                      title="Delete draft"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                )}

                <ArrowRight className="h-4 w-4 text-muted-foreground/50" />
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {isEditableDraft && (
        <DeleteClaimDialog
          open={deleteOpen}
          onClose={() => setDeleteOpen(false)}
          claimId={claim.id}
          claimTitle={claim.title}
          claimNumber={claim.claim_number}
        />
      )}
    </>
  )
}
