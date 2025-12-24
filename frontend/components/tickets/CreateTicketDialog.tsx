"use client"

import { useState } from "react"
import { useCreateTicket, useCheckDuplicates } from "@/hooks/useTickets"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { AlertCircle, Loader2 } from "lucide-react"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface CreateTicketDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  projectId: string
  defaultPhase?: string
}

const PRIORITIES = [
  { value: "low", label: "Low" },
  { value: "medium", label: "Medium" },
  { value: "high", label: "High" },
  { value: "critical", label: "Critical" },
]

const PHASES = [
  { value: "PHASE_BACKLOG", label: "Backlog" },
  { value: "PHASE_REQUIREMENTS", label: "Requirements" },
  { value: "PHASE_DESIGN", label: "Design" },
  { value: "PHASE_IMPLEMENTATION", label: "Implementation" },
  { value: "PHASE_TESTING", label: "Testing" },
  { value: "PHASE_DEPLOYMENT", label: "Deployment" },
]

export function CreateTicketDialog({
  open,
  onOpenChange,
  projectId,
  defaultPhase = "PHASE_BACKLOG",
}: CreateTicketDialogProps) {
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [priority, setPriority] = useState("medium")
  const [phase, setPhase] = useState(defaultPhase)
  const [duplicateWarning, setDuplicateWarning] = useState<string | null>(null)
  const [forceCreate, setForceCreate] = useState(false)

  const createTicket = useCreateTicket()
  const checkDuplicates = useCheckDuplicates()

  const resetForm = () => {
    setTitle("")
    setDescription("")
    setPriority("medium")
    setPhase(defaultPhase)
    setDuplicateWarning(null)
    setForceCreate(false)
  }

  const handleClose = () => {
    resetForm()
    onOpenChange(false)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim()) return

    // Check for duplicates first (unless force creating)
    if (!forceCreate && !duplicateWarning) {
      try {
        const result = await checkDuplicates.mutateAsync({
          title: title.trim(),
          description: description.trim() || undefined,
          similarityThreshold: 0.7,
        })

        if (result.is_duplicate && result.candidates.length > 0) {
          const topMatch = result.candidates[0]
          setDuplicateWarning(
            `Similar ticket found: "${topMatch.title}" (${Math.round(topMatch.similarity_score * 100)}% match)`
          )
          return
        }
      } catch {
        // If duplicate check fails, proceed with creation
      }
    }

    // Create the ticket
    try {
      await createTicket.mutateAsync({
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
        phase_id: phase,
        project_id: projectId,
        force_create: forceCreate,
      })

      handleClose()
    } catch {
      // Error is handled by mutation
    }
  }

  const handleForceCreate = () => {
    setForceCreate(true)
    setDuplicateWarning(null)
  }

  const isLoading = createTicket.isPending || checkDuplicates.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[500px]">
        <form onSubmit={handleSubmit}>
          <DialogHeader>
            <DialogTitle>Create New Ticket</DialogTitle>
            <DialogDescription>
              Add a new ticket to track work. Fill in the details below.
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Title */}
            <div className="grid gap-2">
              <Label htmlFor="title">Title *</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => {
                  setTitle(e.target.value)
                  setDuplicateWarning(null)
                  setForceCreate(false)
                }}
                placeholder="Brief summary of the work"
                disabled={isLoading}
                autoFocus
              />
            </div>

            {/* Description */}
            <div className="grid gap-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Detailed description of what needs to be done..."
                rows={3}
                disabled={isLoading}
              />
            </div>

            {/* Priority and Phase row */}
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="priority">Priority</Label>
                <Select value={priority} onValueChange={setPriority} disabled={isLoading}>
                  <SelectTrigger id="priority">
                    <SelectValue placeholder="Select priority" />
                  </SelectTrigger>
                  <SelectContent>
                    {PRIORITIES.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="phase">Phase</Label>
                <Select value={phase} onValueChange={setPhase} disabled={isLoading}>
                  <SelectTrigger id="phase">
                    <SelectValue placeholder="Select phase" />
                  </SelectTrigger>
                  <SelectContent>
                    {PHASES.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Duplicate Warning */}
            {duplicateWarning && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="flex items-center justify-between">
                  <span>{duplicateWarning}</span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={handleForceCreate}
                  >
                    Create Anyway
                  </Button>
                </AlertDescription>
              </Alert>
            )}

            {/* Error Display */}
            {createTicket.isError && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  {createTicket.error instanceof Error
                    ? createTicket.error.message
                    : "Failed to create ticket"}
                </AlertDescription>
              </Alert>
            )}
          </div>

          <DialogFooter>
            <Button type="button" variant="outline" onClick={handleClose} disabled={isLoading}>
              Cancel
            </Button>
            <Button type="submit" disabled={isLoading || !title.trim()}>
              {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Create Ticket
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
