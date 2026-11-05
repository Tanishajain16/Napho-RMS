"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { toast } from "sonner"
import {
  Loader2,
  Plus,
  Trash2,
  Settings,
  Zap,
  ArrowRight,
  AlertTriangle,
} from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useAuthStore } from "@/lib/auth"
import {
  useApprovalChains,
  useAdminUsers,
  useCreateChain,
  useUpdateChain,
  useDeleteChain,
  useAddStep,
  useDeleteStep,
} from "@/hooks/use-admin"
import type { ApprovalChain, AdminApprovalStep } from "@/lib/types"

// ─── animation variants ────────────────────────────────────────────────────

const containerVariants = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.07 } },
}

const itemVariants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
}

// ─── helpers ───────────────────────────────────────────────────────────────

function formatAmountRange(min: number, max?: number): string {
  if (min === 0 && !max) return "Any amount"
  const fmtMin = `₹${min.toLocaleString("en-IN")}`
  const fmtMax = max ? `₹${max.toLocaleString("en-IN")}` : "∞"
  return `${fmtMin} – ${fmtMax}`
}

function levelLabel(order: number): string {
  return `L${order}`
}

// ─── skeletons ─────────────────────────────────────────────────────────────

function PageSkeleton() {
  return (
    <div className="p-6 max-w-5xl mx-auto space-y-5">
      <div className="flex items-center justify-between">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-9 w-32" />
      </div>
      {[...Array(3)].map((_, i) => (
        <Skeleton key={i} className="h-44 rounded-xl" />
      ))}
    </div>
  )
}

// ─── Step pill ─────────────────────────────────────────────────────────────

function StepPill({
  step,
  chainId,
  onDelete,
  isDeleting,
}: {
  step: AdminApprovalStep
  chainId: string
  onDelete: (chainId: string, stepId: string) => void
  isDeleting: boolean
}) {
  const [hovered, setHovered] = useState(false)

  const label =
    step.approver_type === "user"
      ? (step.approver_name ?? "Unknown user")
      : step.approver_role
        ? step.approver_role.charAt(0).toUpperCase() + step.approver_role.slice(1)
        : "Role"

  return (
    <div
      className="relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-border/50 bg-muted/40 group cursor-default select-none"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <span className="inline-flex items-center px-1.5 py-0.5 rounded border bg-primary/15 text-primary border-primary/30 text-[11px] font-semibold leading-none shrink-0">
        {levelLabel(step.step_order)}
      </span>
      <span className="text-xs text-foreground font-medium">{label}</span>
      {step.approver_type === "user" && (
        <span className="text-[11px] text-muted-foreground">(Approver)</span>
      )}
      {step.approver_type === "role" && step.approver_role && (
        <span className="text-[11px] text-muted-foreground capitalize">
          ({step.approver_role})
        </span>
      )}
      {hovered && (
        <button
          onClick={() => onDelete(chainId, step.id)}
          disabled={isDeleting}
          className="ml-1 w-4 h-4 rounded flex items-center justify-center hover:bg-destructive/20 hover:text-destructive text-muted-foreground transition-colors disabled:opacity-50"
          aria-label="Remove step"
        >
          {isDeleting ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : (
            <span className="text-[11px] font-bold leading-none">×</span>
          )}
        </button>
      )}
    </div>
  )
}

// ─── Chain card ─────────────────────────────────────────────────────────────

function ChainCard({
  chain,
  onAddStep,
  onEdit,
  onToggleActive,
  onDelete,
  onDeleteStep,
  deletingStepId,
  togglingId,
  deletingId,
}: {
  chain: ApprovalChain
  onAddStep: (chain: ApprovalChain) => void
  onEdit: (chain: ApprovalChain) => void
  onToggleActive: (chain: ApprovalChain) => void
  onDelete: (chain: ApprovalChain) => void
  onDeleteStep: (chainId: string, stepId: string) => void
  deletingStepId: string | null
  togglingId: string | null
  deletingId: string | null
}) {
  const sortedSteps = [...chain.steps].sort((a, b) => a.step_order - b.step_order)

  return (
    <motion.div variants={itemVariants}>
      <Card className="border-border/40">
        <CardHeader className="pb-3 pt-5 px-5">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <CardTitle className="text-sm font-semibold text-foreground">
                  {chain.name}
                </CardTitle>
                {chain.is_active ? (
                  <Badge
                    variant="outline"
                    className="text-[11px] bg-emerald-500/15 text-emerald-400 border-emerald-500/20 px-2 py-0"
                  >
                    Active
                  </Badge>
                ) : (
                  <Badge
                    variant="outline"
                    className="text-[11px] bg-muted text-muted-foreground border-border/40 px-2 py-0"
                  >
                    Inactive
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                {formatAmountRange(chain.min_amount, chain.max_amount)}
                <span className="mx-1.5 opacity-40">·</span>
                Used in {chain.claim_count} claim{chain.claim_count !== 1 ? "s" : ""}
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="px-5 pb-5 space-y-4">
          {/* Steps flow */}
          <div className="flex items-center flex-wrap gap-2 min-h-[2.25rem]">
            {sortedSteps.length === 0 && (
              <span className="text-xs text-muted-foreground italic">No steps yet</span>
            )}
            {sortedSteps.map((step, idx) => (
              <div key={step.id} className="flex items-center gap-2">
                <StepPill
                  step={step}
                  chainId={chain.id}
                  onDelete={onDeleteStep}
                  isDeleting={deletingStepId === step.id}
                />
                {idx < sortedSteps.length - 1 && (
                  <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0" />
                )}
              </div>
            ))}
            {sortedSteps.length > 0 && (
              <ArrowRight className="h-3.5 w-3.5 text-muted-foreground/50 shrink-0" />
            )}
            <button
              onClick={() => onAddStep(chain)}
              className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-dashed border-border/60 hover:border-primary/50 hover:bg-primary/5 text-xs text-muted-foreground hover:text-primary transition-all"
            >
              <Plus className="h-3 w-3" />
              Add step
            </button>
          </div>

          {/* Footer actions */}
          <div className="flex items-center gap-2 pt-1 border-t border-border/30">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => onEdit(chain)}
            >
              <Settings className="h-3.5 w-3.5 mr-1.5" />
              Edit
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-muted-foreground hover:text-foreground"
              onClick={() => onToggleActive(chain)}
              disabled={togglingId === chain.id}
            >
              {togglingId === chain.id ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : null}
              {chain.is_active ? "Deactivate" : "Activate"}
            </Button>
            <div className="flex-1" />
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs text-muted-foreground hover:text-destructive disabled:opacity-30"
              onClick={() => onDelete(chain)}
              disabled={chain.claim_count > 0 || deletingId === chain.id}
              title={chain.claim_count > 0 ? "Cannot delete: used in claims" : undefined}
            >
              {deletingId === chain.id ? (
                <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
              ) : (
                <Trash2 className="h-3.5 w-3.5 mr-1.5" />
              )}
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// ─── New Chain dialog ───────────────────────────────────────────────────────

function NewChainDialog({
  open,
  onClose,
}: {
  open: boolean
  onClose: () => void
}) {
  const [name, setName] = useState("")
  const [minAmount, setMinAmount] = useState("0")
  const [maxAmount, setMaxAmount] = useState("")
  const createChain = useCreateChain()

  function reset() {
    setName("")
    setMinAmount("0")
    setMaxAmount("")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!name.trim()) {
      toast.error("Chain name is required")
      return
    }
    try {
      await createChain.mutateAsync({
        name: name.trim(),
        min_amount: Number(minAmount) || 0,
        max_amount: maxAmount !== "" ? Number(maxAmount) : undefined,
      })
      toast.success("Approval chain created")
      reset()
      onClose()
    } catch {
      toast.error("Failed to create approval chain")
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) { reset(); onClose() }
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>New Approval Chain</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-1">
          <div className="space-y-1.5">
            <Label htmlFor="chain-name" className="text-xs">
              Chain name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="chain-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Standard Expense Approval"
              className="h-9 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="min-amount" className="text-xs">
                Min amount (₹)
              </Label>
              <Input
                id="min-amount"
                type="number"
                min={0}
                value={minAmount}
                onChange={(e) => setMinAmount(e.target.value)}
                placeholder="0"
                className="h-9 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="max-amount" className="text-xs">
                Max amount (₹) <span className="text-muted-foreground font-normal">optional</span>
              </Label>
              <Input
                id="max-amount"
                type="number"
                min={0}
                value={maxAmount}
                onChange={(e) => setMaxAmount(e.target.value)}
                placeholder="Unlimited"
                className="h-9 text-sm"
              />
            </div>
          </div>
          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => { reset(); onClose() }}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={createChain.isPending}>
              {createChain.isPending && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
              Create chain
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── Edit Chain dialog ──────────────────────────────────────────────────────

function EditChainDialog({
  chain,
  onClose,
}: {
  chain: ApprovalChain | null
  onClose: () => void
}) {
  const [name, setName] = useState(chain?.name ?? "")
  const [minAmount, setMinAmount] = useState(String(chain?.min_amount ?? 0))
  const [maxAmount, setMaxAmount] = useState(chain?.max_amount != null ? String(chain.max_amount) : "")
  const updateChain = useUpdateChain()

  // sync when chain changes
  if (chain && name === "" && chain.name !== "") {
    setName(chain.name)
    setMinAmount(String(chain.min_amount))
    setMaxAmount(chain.max_amount != null ? String(chain.max_amount) : "")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!chain) return
    if (!name.trim()) {
      toast.error("Chain name is required")
      return
    }
    try {
      await updateChain.mutateAsync({
        id: chain.id,
        name: name.trim(),
        min_amount: Number(minAmount) || 0,
        max_amount: maxAmount !== "" ? Number(maxAmount) : undefined,
      })
      toast.success("Chain updated")
      onClose()
    } catch {
      toast.error("Failed to update chain")
    }
  }

  return (
    <Dialog
      open={chain !== null}
      onOpenChange={(v) => { if (!v) onClose() }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit Chain</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-1">
          <div className="space-y-1.5">
            <Label htmlFor="edit-chain-name" className="text-xs">
              Chain name <span className="text-destructive">*</span>
            </Label>
            <Input
              id="edit-chain-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-9 text-sm"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="edit-min-amount" className="text-xs">
                Min amount (₹)
              </Label>
              <Input
                id="edit-min-amount"
                type="number"
                min={0}
                value={minAmount}
                onChange={(e) => setMinAmount(e.target.value)}
                className="h-9 text-sm"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-max-amount" className="text-xs">
                Max amount (₹) <span className="text-muted-foreground font-normal">optional</span>
              </Label>
              <Input
                id="edit-max-amount"
                type="number"
                min={0}
                value={maxAmount}
                onChange={(e) => setMaxAmount(e.target.value)}
                placeholder="Unlimited"
                className="h-9 text-sm"
              />
            </div>
          </div>
          <DialogFooter className="pt-2">
            <Button type="button" variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={updateChain.isPending}>
              {updateChain.isPending && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
              Save changes
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── Add Step dialog ────────────────────────────────────────────────────────

const ROLE_OPTIONS = ["approver", "finance", "admin"]

function AddStepDialog({
  chain,
  onClose,
}: {
  chain: ApprovalChain | null
  onClose: () => void
}) {
  const nextOrder = chain ? chain.steps.length + 1 : 1
  const [approverType, setApproverType] = useState<"user" | "role">("user")
  const [userId, setUserId] = useState("")
  const [roleName, setRoleName] = useState("")
  const [timeoutHours, setTimeoutHours] = useState("48")
  const addStep = useAddStep()
  const { data: users = [] } = useAdminUsers()

  const eligibleUsers = users.filter(
    (u) => u.roles.includes("approver") || u.roles.includes("admin")
  )

  function reset() {
    setApproverType("user")
    setUserId("")
    setRoleName("")
    setTimeoutHours("48")
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!chain) return
    if (approverType === "user" && !userId) {
      toast.error("Please select a user")
      return
    }
    if (approverType === "role" && !roleName) {
      toast.error("Please select a role")
      return
    }
    try {
      await addStep.mutateAsync({
        chainId: chain.id,
        step_order: nextOrder,
        approver_type: approverType,
        approver_id: approverType === "user" ? userId : undefined,
        approver_role: approverType === "role" ? roleName : undefined,
        timeout_hours: Number(timeoutHours) || 48,
      })
      toast.success("Step added")
      reset()
      onClose()
    } catch {
      toast.error("Failed to add step")
    }
  }

  return (
    <Dialog
      open={chain !== null}
      onOpenChange={(v) => { if (!v) { reset(); onClose() } }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            Add Step — {chain?.name}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4 pt-1">
          {/* Step order (read-only) */}
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span className="inline-flex items-center px-2 py-1 rounded border bg-primary/15 text-primary border-primary/30 text-[11px] font-semibold">
              L{nextOrder}
            </span>
            <span>This will be step {nextOrder}</span>
          </div>

          {/* Approver type toggle */}
          <div className="space-y-1.5">
            <Label className="text-xs">Approver type</Label>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setApproverType("user")}
                className={`flex-1 h-9 rounded-md border text-xs font-medium transition-colors ${
                  approverType === "user"
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/50 bg-muted/30 text-muted-foreground hover:bg-muted/60"
                }`}
              >
                Specific User
              </button>
              <button
                type="button"
                onClick={() => setApproverType("role")}
                className={`flex-1 h-9 rounded-md border text-xs font-medium transition-colors ${
                  approverType === "role"
                    ? "border-primary bg-primary/10 text-primary"
                    : "border-border/50 bg-muted/30 text-muted-foreground hover:bg-muted/60"
                }`}
              >
                Any Approver Role
              </button>
            </div>
          </div>

          {/* User or role picker */}
          {approverType === "user" ? (
            <div className="space-y-1.5">
              <Label className="text-xs">Select user</Label>
              <Select value={userId} onValueChange={setUserId}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Choose an approver…" />
                </SelectTrigger>
                <SelectContent>
                  {eligibleUsers.length === 0 ? (
                    <SelectItem value="_none" disabled>
                      No approvers found
                    </SelectItem>
                  ) : (
                    eligibleUsers.map((u) => (
                      <SelectItem key={u.id} value={u.id}>
                        {u.name}
                        <span className="ml-1.5 text-muted-foreground text-xs">
                          ({u.email})
                        </span>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <div className="space-y-1.5">
              <Label className="text-xs">Select role</Label>
              <Select value={roleName} onValueChange={setRoleName}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue placeholder="Choose a role…" />
                </SelectTrigger>
                <SelectContent>
                  {ROLE_OPTIONS.map((r) => (
                    <SelectItem key={r} value={r} className="capitalize">
                      {r.charAt(0).toUpperCase() + r.slice(1)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Timeout */}
          <div className="space-y-1.5">
            <Label htmlFor="timeout-hours" className="text-xs">
              Timeout (hours)
            </Label>
            <Input
              id="timeout-hours"
              type="number"
              min={1}
              value={timeoutHours}
              onChange={(e) => setTimeoutHours(e.target.value)}
              className="h-9 text-sm"
            />
          </div>

          <DialogFooter className="pt-2">
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => { reset(); onClose() }}
            >
              Cancel
            </Button>
            <Button type="submit" size="sm" disabled={addStep.isPending}>
              {addStep.isPending && <Loader2 className="h-3.5 w-3.5 mr-2 animate-spin" />}
              Add step
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

// ─── Main page ──────────────────────────────────────────────────────────────

export default function ApprovalChainsPage() {
  const { user } = useAuthStore()
  const { data: chains = [], isLoading, error } = useApprovalChains()
  const updateChain = useUpdateChain()
  const deleteChain = useDeleteChain()
  const deleteStep = useDeleteStep()

  const [newChainOpen, setNewChainOpen] = useState(false)
  const [editingChain, setEditingChain] = useState<ApprovalChain | null>(null)
  const [addingStepChain, setAddingStepChain] = useState<ApprovalChain | null>(null)
  const [togglingId, setTogglingId] = useState<string | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [deletingStepId, setDeletingStepId] = useState<string | null>(null)

  // Access guard
  const isAdmin = user?.roles.includes("admin")
  if (!isAdmin) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-32 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">Access denied. Admins only.</p>
      </div>
    )
  }

  if (isLoading) return <PageSkeleton />

  if (error) {
    return (
      <div className="p-6 flex flex-col items-center justify-center py-32 text-muted-foreground">
        <AlertTriangle className="h-10 w-10 mb-3 opacity-40" />
        <p className="text-sm font-medium">Failed to load approval chains</p>
      </div>
    )
  }

  async function handleToggleActive(chain: ApprovalChain) {
    setTogglingId(chain.id)
    try {
      await updateChain.mutateAsync({ id: chain.id, is_active: !chain.is_active })
      toast.success(chain.is_active ? "Chain deactivated" : "Chain activated")
    } catch {
      toast.error("Failed to update chain status")
    } finally {
      setTogglingId(null)
    }
  }

  async function handleDeleteChain(chain: ApprovalChain) {
    if (chain.claim_count > 0) return
    setDeletingId(chain.id)
    try {
      await deleteChain.mutateAsync(chain.id)
      toast.success("Chain deleted")
    } catch {
      toast.error("Failed to delete chain")
    } finally {
      setDeletingId(null)
    }
  }

  async function handleDeleteStep(chainId: string, stepId: string) {
    setDeletingStepId(stepId)
    try {
      await deleteStep.mutateAsync({ chainId, stepId })
      toast.success("Step removed")
    } catch {
      toast.error("Failed to remove step")
    } finally {
      setDeletingStepId(null)
    }
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="space-y-5"
      >
        {/* Page header */}
        <motion.div
          variants={itemVariants}
          className="flex items-center justify-between"
        >
          <div>
            <h1 className="text-2xl font-bold text-foreground">Approval Chains</h1>
            <p className="text-sm text-muted-foreground mt-0.5">
              Configure multi-level approval workflows
            </p>
          </div>
          <Button size="sm" onClick={() => setNewChainOpen(true)}>
            <Plus className="h-3.5 w-3.5 mr-1.5" />
            New Chain
          </Button>
        </motion.div>

        {/* Empty state */}
        {chains.length === 0 && (
          <motion.div
            variants={itemVariants}
            className="flex flex-col items-center justify-center py-24 text-muted-foreground"
          >
            <Zap className="h-10 w-10 mb-3 opacity-30" />
            <p className="text-sm font-medium">No approval chains configured yet</p>
            <p className="text-xs mt-1 opacity-70">
              Create a chain to define your approval workflows
            </p>
          </motion.div>
        )}

        {/* Chain cards */}
        {chains.map((chain) => (
          <ChainCard
            key={chain.id}
            chain={chain}
            onAddStep={setAddingStepChain}
            onEdit={setEditingChain}
            onToggleActive={handleToggleActive}
            onDelete={handleDeleteChain}
            onDeleteStep={handleDeleteStep}
            deletingStepId={deletingStepId}
            togglingId={togglingId}
            deletingId={deletingId}
          />
        ))}
      </motion.div>

      {/* Dialogs */}
      <NewChainDialog open={newChainOpen} onClose={() => setNewChainOpen(false)} />
      <EditChainDialog chain={editingChain} onClose={() => setEditingChain(null)} />
      <AddStepDialog chain={addingStepChain} onClose={() => setAddingStepChain(null)} />
    </div>
  )
}
