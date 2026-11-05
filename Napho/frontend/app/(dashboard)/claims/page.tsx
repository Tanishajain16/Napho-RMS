"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { motion } from "framer-motion"
import { Plus, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ClaimCard } from "@/components/claims/ClaimCard"
import { useClaimsList } from "@/hooks/use-claims"
// `status` may be a comma-separated list. "Submitted" covers claims waiting at any
// approval level (submitted = waiting for L1, under_review = passed L1, waiting for L2).
const TABS: { value: string; label: string; status?: string; empty?: string }[] = [
  { value: "all",       label: "All" },
  { value: "draft",     label: "Draft",     status: "draft" },
  { value: "submitted", label: "Submitted", status: "submitted,under_review", empty: "submitted" },
  { value: "approved",  label: "Approved",  status: "approved,partially_approved", empty: "approved" },
  { value: "paid",      label: "Paid",      status: "paid" },
  { value: "rejected",  label: "Rejected",  status: "rejected" },
]

function TabContent({ status, empty }: { status?: string; empty?: string }) {
  const { data, isLoading } = useClaimsList(status)
  const claims = data?.items ?? []

  if (isLoading) {
    return (
      <div className="space-y-3 mt-4">
        {[1, 2, 3, 4].map((i) => (
          <Skeleton key={i} className="h-[72px] w-full rounded-xl" />
        ))}
      </div>
    )
  }

  if (claims.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
        <div className="w-12 h-12 rounded-2xl bg-muted flex items-center justify-center mb-3">
          <FileText className="h-5 w-5 opacity-40" />
        </div>
        <p className="text-sm font-medium">No claims found</p>
        <p className="text-xs opacity-60 mt-1">
          {status ? `You have no ${empty ?? status} claims` : "Create your first claim to get started"}
        </p>
      </div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2 }}
      className="space-y-2.5 mt-4"
    >
      {claims.map((claim, i) => (
        <motion.div
          key={claim.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.04, duration: 0.2 }}
        >
          <ClaimCard claim={claim} />
        </motion.div>
      ))}
      {data?.has_more && (
        <p className="text-xs text-center text-muted-foreground pt-2">
          Showing {claims.length} of {data.total} claims
        </p>
      )}
    </motion.div>
  )
}

export default function ClaimsPage() {
  const router = useRouter()
  const [activeTab, setActiveTab] = useState("all")

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="flex items-center justify-between mb-6"
      >
        <div>
          <h1 className="text-2xl font-bold text-foreground">My Claims</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Track all your reimbursement requests
          </p>
        </div>
        <Button onClick={() => router.push("/claims/new")} size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          New claim
        </Button>
      </motion.div>

      {/* Tabs */}
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1, duration: 0.3 }}
      >
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="flex-wrap h-auto gap-1">
            {TABS.map((t) => (
              <TabsTrigger key={t.value} value={t.value}>
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>

          {TABS.map((t) => (
            <TabsContent key={t.value} value={t.value}>
              <TabContent status={t.status} empty={t.empty} />
            </TabsContent>
          ))}
        </Tabs>
      </motion.div>
    </div>
  )
}
