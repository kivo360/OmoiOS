"use client"

import Link from "next/link"
import { cn } from "@/lib/utils"
import { Loader2, Check, X, AlertCircle, Clock, ShieldCheck } from "lucide-react"

export type TaskStatus = "pending" | "assigned" | "running" | "completed" | "failed" | "pending_validation" | "validating"

interface TaskCardProps {
  id: string
  sandboxId: string | null
  title: string | null
  taskType: string
  status: TaskStatus
  timeAgo: string
  isSelected?: boolean
  className?: string
}

const statusConfig = {
  pending: {
    icon: Clock,
    iconClass: "text-muted-foreground",
    label: "Pending",
  },
  assigned: {
    icon: Clock,
    iconClass: "text-blue-500",
    label: "Assigned",
  },
  running: {
    icon: Loader2,
    iconClass: "animate-spin text-warning",
    label: "Running",
  },
  completed: {
    icon: Check,
    iconClass: "text-success",
    label: "Completed",
  },
  failed: {
    icon: X,
    iconClass: "text-destructive",
    label: "Failed",
  },
  pending_validation: {
    icon: ShieldCheck,
    iconClass: "text-purple-500",
    label: "Awaiting Validation",
  },
  validating: {
    icon: Loader2,
    iconClass: "animate-spin text-purple-500",
    label: "Validating",
  },
}

export function TaskCard({
  id,
  sandboxId,
  title,
  taskType,
  status,
  timeAgo,
  isSelected,
  className,
}: TaskCardProps) {
  const normalizedStatus = normalizeStatus(status)
  const { icon: StatusIcon, iconClass } = statusConfig[normalizedStatus]

  // Display title if available, otherwise fall back to task type
  const displayName = title || taskType || "Untitled Task"

  // Link to sandbox if available, otherwise to task
  const href = sandboxId ? `/sandbox/${sandboxId}` : `/tasks/${id}`

  return (
    <Link
      href={href}
      className={cn(
        "block rounded-md p-2 transition-colors duration-150 hover:bg-accent",
        isSelected && "bg-accent border-l-2 border-l-primary",
        className
      )}
    >
      {/* Row 1: Status + Task Name + Time */}
      <div className="flex items-start gap-2">
        <StatusIcon className={cn("mt-0.5 h-4 w-4 shrink-0", iconClass)} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {displayName}
          </p>
        </div>
        <span className="shrink-0 text-xs text-muted-foreground">{timeAgo}</span>
      </div>
    </Link>
  )
}

function normalizeStatus(status: string): TaskStatus {
  const lower = status.toLowerCase()
  switch (lower) {
    case "pending":
      return "pending"
    case "assigned":
      return "assigned"
    case "running":
    case "active":
      return "running"
    case "completed":
    case "done":
    case "success":
      return "completed"
    case "failed":
    case "error":
    case "cancelled":
      return "failed"
    case "pending_validation":
      return "pending_validation"
    case "validating":
      return "validating"
    default:
      return "pending"
  }
}
