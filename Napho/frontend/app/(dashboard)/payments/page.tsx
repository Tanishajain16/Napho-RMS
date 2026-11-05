"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { CreditCard, ArrowRight, Loader2, CheckCircle2 } from "lucide-react"
import { toast } from "sonner"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { StatusBadge } from "@/components/ui/status-badge"
import { usePayments, useMarkPaid } from "@/hooks/use-approvals"
import { getApiError } from "@/lib/api"
import { formatINR, formatDate } from "@/lib/utils"
import type { Claim } from "@/lib/types"

type PaymentsTabKey = "ready" | "paid" | "all"

const READY_STATUSES = ["approved", "partially_approved"]

function MarkPaidDialog({
  claim,
  onClose,
}: {
  claim: Claim
  onClose: () => void
}) {
  const [ref, setRef] = useState("")
  const markPaid = useMarkPaid()

  const handleSubmit = async () => {
    try {
      await markPaid.mutateAsync({ id: claim.id, payment_reference: ref || undefined })
      toast.success("Payment recorded", { description: "Moved to the Paid tab" })
      onClose()
    } catch (err: unknown) {
      toast.error(getApiError(err, "Failed to record payment"))
    }
  }

  return (
    <Dialog open onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-sm border-border/60 bg-card">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CreditCard className="h-5 w-5 text-violet-400" />
            Record Payment
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex items-center justify-between px-3 py-2 rounded-lg bg-muted/50 border border-border/50">
            <span className="text-sm text-muted-foreground truncate flex-1 mr-3">{claim.title}</span>
            <span className="text-sm font-bold tabular-nums shrink-0">
              {formatINR(claim.approved_amount ?? claim.claimed_amount)}
            </span>
          </div>

          <div className="space-y-2">
            <Label htmlFor="ref">
              Payment reference{" "}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </Label>
            <Input
              id="ref"
              placeholder="UTR / transaction ID"
              value={ref}
              onChange={(e) => setRef(e.target.value)}
            />
          </div>
        </div>

        <DialogFooter className="gap-2">
          <Button variant="ghost" onClick={onClose} disabled={markPaid.isPending}>
            Cancel
          </Button>
          <Button
            className="bg-violet-600 hover:bg-violet-700 text-white"
            onClick={handleSubmit}
            disabled={markPaid.isPending}
          >
            {markPaid.isPending ? (
              <><Loader2 className="mr-2 h-4 w-4 animate-spin" />Processing…</>
            ) : (
              <><CheckCircle2 className="mr-2 h-4 w-4" />Confirm payment</>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function PaymentRow({ claim, onMarkPaid }: { claim: Claim; onMarkPaid: (c: Claim) => void }) {
  const router = useRouter()
  const isPaid = claim.status === "paid"
  const canPay = READY_STATUSES.includes(claim.status)
  const isPartial = claim.approved_amount != null && claim.approved_amount < claim.claimed_amount
  return (
    <Card className="border-border/40 hover:border-border transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <StatusBadge status={claim.status} />
              <span className="text-xs text-muted-foreground font-mono">{claim.claim_number}</span>
            </div>
            <h3 className="text-sm font-semibold text-foreground truncate">{claim.title}</h3>
            <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
              <span>{claim.claimant.name}</span>
              <span>·</span>
              <span>{formatDate(claim.expense_date)}</span>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <div className="text-right">
              {isPaid ? (
                <>
                  <p className="text-xs text-muted-foreground mb-0.5">
                    Paid{claim.paid_at ? ` on ${formatDate(claim.paid_at)}` : ""}
                  </p>
                  <p className="text-sm font-bold text-emerald-400 tabular-nums">
                    {formatINR(claim.paid_amount ?? claim.approved_amount ?? claim.claimed_amount)}
                  </p>
                </>
              ) : (
                <>
                  <p className="text-xs text-muted-foreground mb-0.5">To pay</p>
                  <p className="text-sm font-bold text-violet-400 tabular-nums">
                    {formatINR(claim.approved_amount ?? claim.claimed_amount)}
                  </p>
                  {isPartial && (
                    <p className="text-[11px] text-muted-foreground tabular-nums">
                      of {formatINR(claim.claimed_amount)} claimed
                    </p>
                  )}
                </>
              )}
            </div>
            {canPay && (
              <Button
                size="sm"
                className="h-7 px-3 text-xs bg-violet-600 hover:bg-violet-700 text-white"
                onClick={() => onMarkPaid(claim)}
              >
                <CreditCard className="h-3 w-3 mr-1" />
                Pay
              </Button>
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
  )
}

const EMPTY_TEXT: Record<PaymentsTabKey, [string, string]> = {
  ready: ["Nothing to pay", "Approved claims waiting for payment appear here"],
  paid:  ["No payments yet", "Claims you've paid appear here"],
  all:   ["Nothing here", "Approved and paid claims appear here"],
}

function PaymentsTab({ tab }: { tab: PaymentsTabKey }) {
  const [payingClaim, setPayingClaim] = useState<Claim | null>(null)
  const { data, isLoading } = usePayments(tab)
  const claims = data?.items ?? []

  if (isLoading) {
    return (
      <div className="space-y-3 mt-4">
        {[1, 2, 3].map((i) => <Skeleton key={i} className="h-20 w-full rounded-xl" />)}
      </div>
    )
  }

  if (claims.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
          <CreditCard className="h-5 w-5 opacity-40" />
        </div>
        <p className="text-sm font-medium">{EMPTY_TEXT[tab][0]}</p>
        <p className="text-xs opacity-60 mt-1">{EMPTY_TEXT[tab][1]}</p>
      </div>
    )
  }

  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="space-y-2.5 mt-4"
      >
        {claims.map((claim, i) => (
          <motion.div
            key={claim.id}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.04 }}
          >
            <PaymentRow claim={claim} onMarkPaid={setPayingClaim} />
          </motion.div>
        ))}
        {data && data.total > claims.length && (
          <p className="text-xs text-center text-muted-foreground pt-1">
            Showing {claims.length} of {data.total}
          </p>
        )}
      </motion.div>

      {payingClaim && (
        <MarkPaidDialog claim={payingClaim} onClose={() => setPayingClaim(null)} />
      )}
    </>
  )
}

function TabCount({ n }: { n?: number }) {
  if (!n) return null
  return <span className="ml-1.5 text-[10px] tabular-nums opacity-70">{n}</span>
}

export default function PaymentsPage() {
  const { data: readyData } = usePayments("ready")
  const { data: paidData } = usePayments("paid")
  return (
    <div className="p-6 max-w-4xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mb-6"
      >
        <h1 className="text-2xl font-bold text-foreground">Payments</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Process approved claims and record disbursements
        </p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        <Tabs defaultValue="ready">
          <TabsList>
            <TabsTrigger value="ready">Ready to pay<TabCount n={readyData?.total} /></TabsTrigger>
            <TabsTrigger value="paid">Paid<TabCount n={paidData?.total} /></TabsTrigger>
            <TabsTrigger value="all">All</TabsTrigger>
          </TabsList>
          <TabsContent value="ready"><PaymentsTab tab="ready" /></TabsContent>
          <TabsContent value="paid"><PaymentsTab tab="paid" /></TabsContent>
          <TabsContent value="all"><PaymentsTab tab="all" /></TabsContent>
        </Tabs>
      </motion.div>
    </div>
  )
}
