"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardContent } from "@/components/ui/card"
import {
  Search,
  Plus,
  AlertCircle,
  Terminal,
  CheckCircle,
  XCircle,
  Clock,
  PlayCircle,
  Loader2,
  RefreshCw,
  Box,
} from "lucide-react"
import { useSandboxTasks } from "@/hooks/useTasks"
import { useQueryClient } from "@tanstack/react-query"
import { taskKeys } from "@/hooks/useTasks"

type TaskStatus = "pending" | "running" | "completed" | "failed" | "pending_validation" | "validating"

function normalizeStatus(status: string): TaskStatus {
  const lower = status.toLowerCase()
  switch (lower) {
    case "pending":
      return "pending"
    case "assigned":
    case "running":
    case "active":
    case "in_progress":
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

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return "just now"
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return `${Math.floor(diffDays / 7)}w ago`
}

const statusConfig: Record<TaskStatus, { icon: typeof Clock; color: string; bgColor: string; label: string }> = {
  pending: { icon: Clock, color: "text-muted-foreground", bgColor: "bg-muted", label: "Pending" },
  running: { icon: Loader2, color: "text-blue-500", bgColor: "bg-blue-500/10", label: "Running" },
  completed: { icon: CheckCircle, color: "text-green-500", bgColor: "bg-green-500/10", label: "Completed" },
  failed: { icon: XCircle, color: "text-red-500", bgColor: "bg-red-500/10", label: "Failed" },
  pending_validation: { icon: Clock, color: "text-purple-500", bgColor: "bg-purple-500/10", label: "Awaiting Validation" },
  validating: { icon: Loader2, color: "text-purple-500", bgColor: "bg-purple-500/10", label: "Validating" },
}

export default function SandboxesPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<TaskStatus | "all">("all")
  const queryClient = useQueryClient()
  
  const { data: tasks, isLoading, error, refetch, isFetching } = useSandboxTasks({ limit: 100 })

  const filteredTasks = useMemo(() => {
    if (!tasks) return []
    return tasks.filter((task) => {
      // Search filter
      const searchLower = searchQuery.toLowerCase()
      const matchesSearch =
        (task.title?.toLowerCase().includes(searchLower) ?? false) ||
        task.task_type.toLowerCase().includes(searchLower) ||
        task.id.toLowerCase().includes(searchLower) ||
        (task.sandbox_id?.toLowerCase().includes(searchLower) ?? false)

      // Status filter
      const status = normalizeStatus(task.status)
      const matchesStatus = statusFilter === "all" || status === statusFilter

      return matchesSearch && matchesStatus
    })
  }, [tasks, searchQuery, statusFilter])

  // Count by status
  const statusCounts = useMemo(() => {
    if (!tasks) return { pending: 0, running: 0, completed: 0, failed: 0, pending_validation: 0, validating: 0 }
    return tasks.reduce(
      (acc, task) => {
        const status = normalizeStatus(task.status)
        acc[status]++
        return acc
      },
      { pending: 0, running: 0, completed: 0, failed: 0, pending_validation: 0, validating: 0 }
    )
  }, [tasks])

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: taskKeys.sandboxList({}) })
    refetch()
  }

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <Box className="h-6 w-6" />
            <div>
              <h1 className="text-xl font-bold">Sandboxes</h1>
              <p className="text-sm text-muted-foreground">
                {tasks?.length ?? 0} sandboxes total
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={isFetching}>
              <RefreshCw className={`h-4 w-4 mr-2 ${isFetching ? "animate-spin" : ""}`} />
              Refresh
            </Button>
            <Button size="sm" asChild>
              <Link href="/command">
                <Plus className="h-4 w-4 mr-2" />
                New Sandbox
              </Link>
            </Button>
          </div>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search sandboxes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          
          {/* Status filter buttons */}
          <div className="flex items-center gap-1">
            <Button
              variant={statusFilter === "all" ? "default" : "ghost"}
              size="sm"
              onClick={() => setStatusFilter("all")}
            >
              All
            </Button>
            {(["running", "validating", "pending_validation", "pending", "completed", "failed"] as TaskStatus[]).map((status) => {
              const config = statusConfig[status]
              const count = statusCounts[status]
              return (
                <Button
                  key={status}
                  variant={statusFilter === status ? "default" : "ghost"}
                  size="sm"
                  onClick={() => setStatusFilter(status)}
                  className="gap-1.5"
                >
                  <config.icon className={`h-3.5 w-3.5 ${statusFilter !== status ? config.color : ""}`} />
                  {config.label}
                  {count > 0 && (
                    <Badge variant="secondary" className="ml-1 h-5 px-1.5 text-[10px]">
                      {count}
                    </Badge>
                  )}
                </Button>
              )
            })}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {isLoading ? (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <Skeleton key={i} className="h-32 rounded-lg" />
            ))}
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <AlertCircle className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">Failed to load sandboxes</p>
            <p className="text-sm">Please try again later</p>
            <Button variant="outline" className="mt-4" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Retry
            </Button>
          </div>
        ) : filteredTasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
            <Terminal className="h-12 w-12 mb-4 opacity-50" />
            <p className="text-lg font-medium">No sandboxes found</p>
            <p className="text-sm">
              {searchQuery || statusFilter !== "all"
                ? "Try adjusting your filters"
                : "Create a new sandbox to get started"}
            </p>
            {!searchQuery && statusFilter === "all" && (
              <Button className="mt-4" asChild>
                <Link href="/command">
                  <Plus className="h-4 w-4 mr-2" />
                  Create Sandbox
                </Link>
              </Button>
            )}
          </div>
        ) : (
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {filteredTasks.map((task) => {
              const status = normalizeStatus(task.status)
              const config = statusConfig[status]
              const StatusIcon = config.icon

              return (
                <Link
                  key={task.id}
                  href={task.sandbox_id ? `/sandbox/${task.sandbox_id}` : "#"}
                  className={!task.sandbox_id ? "pointer-events-none opacity-50" : ""}
                >
                  <Card className="hover:border-primary/50 hover:shadow-md transition-all cursor-pointer h-full">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className={`p-1.5 rounded ${config.bgColor}`}>
                            <StatusIcon
                              className={`h-4 w-4 ${config.color} ${status === "running" ? "animate-spin" : ""}`}
                            />
                          </div>
                          <Badge variant="outline" className="text-[10px]">
                            {task.task_type}
                          </Badge>
                        </div>
                        <span className="text-xs text-muted-foreground">
                          {formatTimeAgo(task.started_at || task.created_at)}
                        </span>
                      </div>

                      <h3 className="font-medium text-sm mb-1 line-clamp-2">
                        {task.title || `Task ${task.id.slice(0, 8)}`}
                      </h3>

                      {task.sandbox_id && (
                        <p className="text-[10px] text-muted-foreground font-mono truncate">
                          {task.sandbox_id}
                        </p>
                      )}

                      <div className="flex items-center gap-2 mt-3 pt-3 border-t">
                        <Badge variant={status === "completed" ? "default" : status === "failed" ? "destructive" : "secondary"} className="text-[10px]">
                          {config.label}
                        </Badge>
                        {!task.sandbox_id && (
                          <span className="text-[10px] text-muted-foreground">No sandbox</span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
