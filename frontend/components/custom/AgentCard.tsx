"use client"

import Link from "next/link"
import { cn } from "@/lib/utils"
import { LineChanges } from "./LineChanges"
import { Loader2, Check, X, AlertCircle } from "lucide-react"

export type AgentStatus = "running" | "completed" | "failed" | "blocked"

interface AgentCardProps {
  id: string
  taskName: string
  status: AgentStatus
  timeAgo: string
  additions?: number
  deletions?: number
  repoName?: string
  className?: string
}

const statusConfig = {
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
  blocked: {
    icon: AlertCircle,
    iconClass: "text-warning",
    label: "Blocked",
  },
}

export function AgentCard({
  id,
  taskName,
  status,
  timeAgo,
  additions = 0,
  deletions = 0,
  repoName,
  className,
}: AgentCardProps) {
  const { icon: StatusIcon, iconClass } = statusConfig[status]
  const hasChanges = additions > 0 || deletions > 0

  return (
    <Link
      href={`/agents/${id}`}
      className={cn(
        "block rounded-md p-2 transition-colors duration-150 hover:bg-accent",
        className
      )}
    >
      {/* Row 1: Status + Task Name + Time */}
      <div className="flex items-start gap-2">
        <StatusIcon className={cn("mt-0.5 h-4 w-4 shrink-0", iconClass)} />
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-foreground">
            {taskName}
          </p>
        </div>
        <span className="shrink-0 text-xs text-muted-foreground">{timeAgo}</span>
      </div>

      {/* Row 2: Line Changes + Repo */}
      {(hasChanges || repoName) && (
        <div className="mt-1 flex items-center gap-2 pl-6 text-xs text-muted-foreground">
          {hasChanges && (
            <LineChanges additions={additions} deletions={deletions} />
          )}
          {hasChanges && repoName && (
            <span className="text-muted-foreground/50">•</span>
          )}
          {repoName && (
            <span className="truncate">{repoName}</span>
          )}
        </div>
      )}
    </Link>
  )
}
