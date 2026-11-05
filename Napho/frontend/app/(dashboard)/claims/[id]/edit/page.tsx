"use client"

import { useParams, useRouter } from "next/navigation"
import { AlertTriangle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ClaimForm } from "@/components/claims/ClaimForm"
import { useClaimDetail } from "@/hooks/use-claims"
import { useAuthStore } from "@/lib/auth"

export default function EditClaimPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { user } = useAuthStore()
  const { data: claim, isLoading, error } = useClaimDetail(id)

  if (isLoading) {
    return (
      <div className="p-6 max-w-3xl mx-auto space-y-5">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-40 w-full rounded-xl" />
      </div>
    )
  }

  const notEditable =
    !claim || error || claim.status !== "draft" || claim.claimant.id !== user?.id

  if (notEditable) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-24 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">
          {claim ? "Only your own draft claims can be edited" : "Claim not found"}
        </p>
        <Button
          variant="ghost"
          size="sm"
          className="mt-3"
          onClick={() => router.push(claim ? `/claims/${claim.id}` : "/claims")}
        >
          {claim ? "Back to claim" : "Back to claims"}
        </Button>
      </div>
    )
  }

  // key forces a fresh form if the user navigates between different drafts
  return <ClaimForm key={claim.id} claim={claim} />
}
