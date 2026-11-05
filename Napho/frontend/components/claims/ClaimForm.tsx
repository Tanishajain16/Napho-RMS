"use client"

import { useState, useCallback } from "react"
import { useRouter } from "next/navigation"
import { useForm, useFieldArray } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { z } from "zod"
import { motion } from "framer-motion"
import { useDropzone } from "react-dropzone"
import { useQueryClient } from "@tanstack/react-query"
import {
  Plus, Trash2, Upload, FileText, Loader2, Send, Save,
  X, AlertCircle, Paperclip,
} from "lucide-react"
import { toast } from "sonner"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"
import { useCreateClaim, useSubmitClaim, useUpdateClaim } from "@/hooks/use-claims"
import { useCategories } from "@/hooks/use-categories"
import { formatINR } from "@/lib/utils"
import { api, getApiError } from "@/lib/api"
import type { Attachment, ClaimDetail } from "@/lib/types"

const lineItemSchema = z.object({
  description: z.string().min(1, "Required"),
  amount: z.string().min(1, "Required"),
  vendor_name: z.string().optional(),
  expense_date: z.string().optional(),
})

const schema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters"),
  category_id: z.string().min(1, "Select a category"),
  expense_date: z.string().min(1, "Select a date"),
  description: z.string().optional(),
  items: z.array(lineItemSchema).min(1, "Add at least one item"),
})

type Form = z.infer<typeof schema>

interface UploadedFile {
  name: string
  size: number
  file?: File
  id?: string
  uploading?: boolean
  error?: string
}

const emptyItem = { description: "", amount: "", vendor_name: "", expense_date: "" }

function toFormValues(claim?: ClaimDetail): Partial<Form> {
  if (!claim) return { items: [emptyItem] }
  return {
    title: claim.title,
    category_id: claim.category?.id ?? "",
    expense_date: claim.expense_date?.slice(0, 10) ?? "",
    description: claim.description ?? "",
    items: claim.items.length
      ? claim.items.map((it) => ({
          description: it.description ?? "",
          amount: String(it.amount ?? ""),
          vendor_name: it.vendor_name ?? "",
          expense_date: it.expense_date?.slice(0, 10) ?? "",
        }))
      : [emptyItem],
  }
}

/**
 * Claim form used for both creating a new claim and editing an existing draft.
 * Pass `claim` to switch to edit mode.
 */
export function ClaimForm({ claim }: { claim?: ClaimDetail }) {
  const isEdit = !!claim
  const router = useRouter()
  const qc = useQueryClient()
  const createClaim = useCreateClaim()
  const updateClaim = useUpdateClaim(claim?.id ?? "")
  const submitClaim = useSubmitClaim()
  const { data: categories = [] } = useCategories()
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [existingFiles, setExistingFiles] = useState<Attachment[]>(claim?.attachments ?? [])
  const [removingFileId, setRemovingFileId] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const {
    register,
    control,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<Form>({
    resolver: zodResolver(schema),
    defaultValues: toFormValues(claim),
  })

  const { fields, append, remove } = useFieldArray({ control, name: "items" })
  const items = watch("items")
  const total = items.reduce((sum, item) => sum + (Number(item.amount) || 0), 0)

  // File upload — files are queued locally; actual upload happens after the claim is saved
  const onDrop = useCallback((accepted: File[]) => {
    setFiles((prev) => [
      ...prev,
      ...accepted.map((f) => ({ name: f.name, size: f.size, file: f })),
    ])
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [], "application/pdf": [] },
    maxSize: 10 * 1024 * 1024,
  })

  const buildPayload = (data: Form) => ({
    title: data.title,
    category_id: data.category_id,
    expense_date: data.expense_date,
    description: data.description,
    items: data.items.map((item) => ({
      description: item.description,
      amount: Number(item.amount),
      vendor_name: item.vendor_name || undefined,
      expense_date: item.expense_date || undefined,
    })),
  })

  /** Create the claim (new) or update it (edit). Returns the claim id. */
  const persist = async (payload: unknown): Promise<string> => {
    if (isEdit) {
      await updateClaim.mutateAsync(payload)
      return claim.id
    }
    const created = await createClaim.mutateAsync(payload)
    return created.id
  }

  const uploadPendingFiles = async (claimId: string) => {
    const pending = files.filter((f) => f.file && !f.id)
    for (const entry of pending) {
      setFiles((prev) =>
        prev.map((f) => (f.name === entry.name ? { ...f, uploading: true } : f))
      )
      try {
        const formData = new FormData()
        formData.append("file", entry.file!)
        const { data } = await api.post(`/claims/${claimId}/attachments`, formData, {
          headers: { "Content-Type": "multipart/form-data" },
        })
        setFiles((prev) =>
          prev.map((f) => (f.name === entry.name ? { ...f, uploading: false, id: data.id } : f))
        )
      } catch {
        setFiles((prev) =>
          prev.map((f) =>
            f.name === entry.name ? { ...f, uploading: false, error: "Upload failed" } : f
          )
        )
        throw new Error(`Failed to upload ${entry.name}`)
      }
    }
    if (pending.length) qc.invalidateQueries({ queryKey: ["claims"] })
  }

  const removeExistingFile = async (att: Attachment) => {
    if (!claim) return
    setRemovingFileId(att.id)
    try {
      await api.delete(`/claims/${claim.id}/attachments/${att.id}`)
      setExistingFiles((prev) => prev.filter((f) => f.id !== att.id))
      qc.invalidateQueries({ queryKey: ["claims"] })
      toast.success("Attachment removed")
    } catch (err: unknown) {
      toast.error(getApiError(err, "Failed to remove attachment"))
    } finally {
      setRemovingFileId(null)
    }
  }

  const afterSaveUrl = (claimId: string) => (isEdit ? `/claims/${claimId}` : "/claims")

  const handleSave = async () => {
    const data = watch()
    // Minimal validation for draft — just need title + expense_date + at least one item with amount
    if (!data.title || data.title.trim().length < 1) {
      toast.error("Title is required to save a draft")
      return
    }
    if (!data.expense_date) {
      toast.error("Expense date is required to save a draft")
      return
    }
    const validItems = (data.items || []).filter(
      (it) => it.description?.trim() && Number(it.amount) > 0
    )
    if (validItems.length === 0) {
      toast.error("Add at least one item with a description and amount")
      return
    }
    setSaving(true)
    try {
      const payload = {
        title: data.title.trim(),
        category_id: data.category_id || undefined,
        expense_date: data.expense_date,
        description: data.description ?? undefined,
        items: validItems.map((item) => ({
          description: item.description,
          amount: Number(item.amount),
          vendor_name: item.vendor_name || undefined,
          expense_date: item.expense_date || undefined,
        })),
      }
      const claimId = await persist(payload)
      await uploadPendingFiles(claimId)
      toast.success(isEdit ? "Draft updated" : "Draft saved")
      router.push(afterSaveUrl(claimId))
    } catch (err: unknown) {
      toast.error(getApiError(err, isEdit ? "Failed to update draft" : "Failed to save draft"))
    } finally {
      setSaving(false)
    }
  }

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleSubmitClaim = handleSubmit(async (data: any) => {
    setSubmitting(true)
    try {
      const claimId = await persist(buildPayload(data as Form))
      await uploadPendingFiles(claimId)
      await submitClaim.mutateAsync(claimId)
      toast.success("Claim submitted for review!")
      router.push(afterSaveUrl(claimId))
    } catch (err: unknown) {
      toast.error(getApiError(err, "Failed to submit claim"))
    } finally {
      setSubmitting(false)
    }
  })

  return (
    <div className="p-6 max-w-3xl mx-auto pb-28">
      <motion.div
        initial={{ opacity: 0, y: -8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mb-6"
      >
        <h1 className="text-2xl font-bold text-foreground">
          {isEdit ? "Edit Draft Claim" : "New Claim"}
        </h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          {isEdit ? (
            <>Update the details of <span className="font-mono">{claim.claim_number}</span>, then save or submit</>
          ) : (
            "Fill in the details below and submit for approval"
          )}
        </p>
      </motion.div>

      <div className="space-y-5">
        {/* Basic details */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.05, duration: 0.3 }}
        >
          <Card className="border-border/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Claim Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="title">Title *</Label>
                <Input
                  id="title"
                  placeholder="e.g. Client dinner at Taj Hotel"
                  {...register("title")}
                  className={errors.title ? "border-destructive" : ""}
                />
                {errors.title && (
                  <p className="text-xs text-destructive flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />{errors.title.message}
                  </p>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Category *</Label>
                  <Select
                    defaultValue={claim?.category?.id}
                    onValueChange={(v) => setValue("category_id", v, { shouldValidate: true })}
                  >
                    <SelectTrigger className={errors.category_id ? "border-destructive" : ""}>
                      <SelectValue placeholder="Select category" />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.map((cat) => (
                        <SelectItem key={cat.id} value={cat.id}>
                          {cat.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors.category_id && (
                    <p className="text-xs text-destructive">{errors.category_id.message}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="expense_date">Expense Date *</Label>
                  <Input
                    id="expense_date"
                    type="date"
                    {...register("expense_date")}
                    className={errors.expense_date ? "border-destructive" : ""}
                  />
                  {errors.expense_date && (
                    <p className="text-xs text-destructive">{errors.expense_date.message}</p>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Additional context or notes…"
                  rows={3}
                  {...register("description")}
                  className="resize-none"
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* Line items */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.3 }}
        >
          <Card className="border-border/40">
            <CardHeader className="pb-3 flex flex-row items-center justify-between">
              <CardTitle className="text-sm font-semibold">Line Items</CardTitle>
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-7 text-xs gap-1"
                onClick={() => append(emptyItem)}
              >
                <Plus className="h-3.5 w-3.5" />
                Add item
              </Button>
            </CardHeader>
            <CardContent className="space-y-3">
              {errors.items?.root && (
                <p className="text-xs text-destructive">{errors.items.root.message}</p>
              )}

              {fields.map((field, index) => (
                <motion.div
                  key={field.id}
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  className="grid grid-cols-12 gap-2 items-start"
                >
                  {/* Description */}
                  <div className="col-span-5 space-y-1">
                    {index === 0 && <Label className="text-xs text-muted-foreground">Description</Label>}
                    <Input
                      placeholder="Item description"
                      {...register(`items.${index}.description`)}
                      className={`text-sm h-9 ${errors.items?.[index]?.description ? "border-destructive" : ""}`}
                    />
                  </div>

                  {/* Vendor */}
                  <div className="col-span-3 space-y-1">
                    {index === 0 && <Label className="text-xs text-muted-foreground">Vendor</Label>}
                    <Input
                      placeholder="Vendor name"
                      {...register(`items.${index}.vendor_name`)}
                      className="text-sm h-9"
                    />
                  </div>

                  {/* Amount */}
                  <div className="col-span-3 space-y-1">
                    {index === 0 && <Label className="text-xs text-muted-foreground">Amount (₹)</Label>}
                    <Input
                      type="number"
                      min={0}
                      step={1}
                      placeholder="0"
                      {...register(`items.${index}.amount`)}
                      className={`text-sm h-9 tabular-nums ${errors.items?.[index]?.amount ? "border-destructive" : ""}`}
                    />
                  </div>

                  {/* Remove */}
                  <div className="col-span-1 space-y-1">
                    {index === 0 && <Label className="text-xs opacity-0">Del</Label>}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="h-9 w-9 p-0 text-muted-foreground hover:text-destructive"
                      onClick={() => fields.length > 1 && remove(index)}
                      disabled={fields.length === 1}
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                </motion.div>
              ))}

              <Separator />

              <div className="flex items-center justify-end gap-3">
                <span className="text-sm text-muted-foreground">Total</span>
                <span className="text-lg font-bold text-foreground tabular-nums">
                  {formatINR(total)}
                </span>
              </div>
            </CardContent>
          </Card>
        </motion.div>

        {/* File upload */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.3 }}
        >
          <Card className="border-border/40">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-semibold">Attachments</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Already-uploaded attachments (edit mode) */}
              {existingFiles.length > 0 && (
                <div className="space-y-2">
                  {existingFiles.map((att) => (
                    <div
                      key={att.id}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg bg-muted/50 border border-border/50"
                    >
                      <Paperclip className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm text-foreground flex-1 truncate">{att.file_name}</span>
                      <span className="text-xs text-emerald-400">Uploaded</span>
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                        onClick={() => removeExistingFile(att)}
                        disabled={removingFileId === att.id}
                        aria-label={`Remove ${att.file_name}`}
                      >
                        {removingFileId === att.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <X className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                  ))}
                </div>
              )}

              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? "border-primary bg-primary/5"
                    : "border-border hover:border-border/80 hover:bg-accent/30"
                }`}
              >
                <input {...getInputProps()} />
                <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground opacity-50" />
                <p className="text-sm text-muted-foreground">
                  {isDragActive
                    ? "Drop files here…"
                    : "Drag & drop receipts, or click to browse"}
                </p>
                <p className="text-xs text-muted-foreground/60 mt-1">
                  PDF, PNG, JPG up to 10 MB
                </p>
              </div>

              {files.length > 0 && (
                <div className="space-y-2">
                  {files.map((file, i) => (
                    <div
                      key={i}
                      className="flex items-center gap-3 px-3 py-2 rounded-lg bg-muted/50 border border-border/50"
                    >
                      <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                      <span className="text-sm text-foreground flex-1 truncate">{file.name}</span>
                      {file.uploading && (
                        <Loader2 className="h-3.5 w-3.5 text-muted-foreground animate-spin" />
                      )}
                      {file.error && (
                        <span className="text-xs text-destructive">{file.error}</span>
                      )}
                      {!file.uploading && !file.error && file.id && (
                        <span className="text-xs text-emerald-400">Uploaded</span>
                      )}
                      {!file.uploading && !file.error && !file.id && (
                        <span className="text-xs text-muted-foreground">Ready</span>
                      )}
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 text-muted-foreground hover:text-destructive"
                        onClick={() => setFiles((prev) => prev.filter((_, j) => j !== i))}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Sticky bottom action bar */}
      <div className="fixed bottom-0 left-0 right-0 z-20 bg-background/95 backdrop-blur-sm border-t border-border px-6 py-3">
        <div className="max-w-3xl mx-auto flex items-center justify-between gap-3">
          <div className="text-sm text-muted-foreground">
            Total:{" "}
            <span className="text-foreground font-semibold tabular-nums">{formatINR(total)}</span>
          </div>
          <div className="flex items-center gap-2">
            {isEdit && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => router.push(`/claims/${claim.id}`)}
                disabled={saving || submitting}
              >
                Cancel
              </Button>
            )}
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleSave}
              disabled={saving || submitting}
            >
              {saving ? (
                <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />Saving…</>
              ) : (
                <><Save className="mr-2 h-3.5 w-3.5" />{isEdit ? "Save changes" : "Save draft"}</>
              )}
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleSubmitClaim}
              disabled={saving || submitting}
            >
              {submitting ? (
                <><Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />Submitting…</>
              ) : (
                <><Send className="mr-2 h-3.5 w-3.5" />Submit for approval</>
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
