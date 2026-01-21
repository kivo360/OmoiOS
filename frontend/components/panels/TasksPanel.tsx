"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { Search, Filter, ArrowUpDown, Plus, AlertCircle, Check } from "lucide-react"
import { TaskCard, type TaskStatus } from "@/components/custom/TaskCard"
import { TimeGroupHeader } from "@/components/custom"
import { useSandboxTasks, useFailTask } from "@/hooks/useTasks"

type SortOption = "status" | "newest" | "oldest" | "name"

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)
  
  if (diffMins < 60) return `${diffMins}m`
  if (diffHours < 24) return `${diffHours}h`
  if (diffDays < 7) return `${diffDays}d`
  return `${Math.floor(diffDays / 7)}w`
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

interface TasksPanelProps {
  pathname?: string
}

export function TasksPanel({ pathname }: TasksPanelProps) {
  const [searchQuery, setSearchQuery] = useState("")
  const [sortOption, setSortOption] = useState<SortOption>("status")
  const { data: tasks, isLoading, error } = useSandboxTasks({ limit: 50 })
  const failTaskMutation = useFailTask()

  const handleMarkFailed = (taskId: string) => {
    failTaskMutation.mutate(
      { taskId, reason: "marked_failed_by_user" },
      {
        onSuccess: () => {
          toast.success("Task marked as failed")
        },
        onError: (error) => {
          toast.error(error instanceof Error ? error.message : "Failed to mark task as failed")
        },
      }
    )
  }

  // Extract sandboxId from pathname like /sandbox/[sandboxId]
  const selectedSandboxId = useMemo(() => {
    if (!pathname) return null
    const match = pathname.match(/^\/sandbox\/([^/]+)/)
    return match ? match[1] : null
  }, [pathname])

  const filteredTasks = useMemo(() => {
    if (!tasks) return []

    // First filter by search query
    let filtered = tasks.filter((task) => {
      const searchLower = searchQuery.toLowerCase()
      return (
        (task.title?.toLowerCase().includes(searchLower) ?? false) ||
        task.task_type.toLowerCase().includes(searchLower) ||
        task.id.toLowerCase().includes(searchLower)
      )
    })

    // Then sort based on sortOption (only for non-status sorting)
    if (sortOption !== "status") {
      filtered = [...filtered].sort((a, b) => {
        switch (sortOption) {
          case "newest":
            return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          case "oldest":
            return new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          case "name":
            return (a.title || "").localeCompare(b.title || "")
          default:
            return 0
        }
      })
    }

    return filtered
  }, [tasks, searchQuery, sortOption])

  // Group tasks by status
  const runningTasks = filteredTasks.filter((t) => {
    const status = normalizeStatus(t.status)
    return status === "running" || status === "assigned"
  })
  
  const completedTasks = filteredTasks.filter((t) => 
    normalizeStatus(t.status) === "completed"
  )
  
  const failedTasks = filteredTasks.filter((t) => 
    normalizeStatus(t.status) === "failed"
  )
  
  const pendingTasks = filteredTasks.filter((t) =>
    normalizeStatus(t.status) === "pending"
  )

  const pendingValidationTasks = filteredTasks.filter((t) =>
    normalizeStatus(t.status) === "pending_validation"
  )

  const validatingTasks = filteredTasks.filter((t) =>
    normalizeStatus(t.status) === "validating"
  )

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-3 space-y-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search tasks..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-9 pl-8 text-sm"
            />
          </div>
          <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0">
            <Filter className="h-4 w-4" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant={sortOption !== "status" ? "secondary" : "ghost"}
                size="icon"
                className="h-9 w-9 shrink-0"
              >
                <ArrowUpDown className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-40">
              <DropdownMenuRadioGroup value={sortOption} onValueChange={(v) => setSortOption(v as SortOption)}>
                <DropdownMenuRadioItem value="status">By Status</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="newest">Newest First</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="oldest">Oldest First</DropdownMenuRadioItem>
                <DropdownMenuRadioItem value="name">By Name</DropdownMenuRadioItem>
              </DropdownMenuRadioGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <Button className="w-full" size="sm" asChild>
          <Link href="/command">
            <Plus className="mr-2 h-4 w-4" /> New Task
          </Link>
        </Button>
      </div>

      {/* Task List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          ) : error ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              Failed to load tasks
            </div>
          ) : filteredTasks.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No tasks found
            </div>
          ) : sortOption === "status" ? (
            // Grouped by status view
            <>
              {runningTasks.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Running</TimeGroupHeader>
                  {runningTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      id={task.id}
                      sandboxId={task.sandbox_id}
                      title={task.title}
                      taskType={task.task_type}
                      status={normalizeStatus(task.status)}
                      timeAgo={task.started_at ? formatTimeAgo(task.started_at) : formatTimeAgo(task.created_at)}
                      isSelected={task.sandbox_id === selectedSandboxId}
                      onMarkFailed={handleMarkFailed}
                    />
                  ))}
                </div>
              )}

              {validatingTasks.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Validating</TimeGroupHeader>
                  {validatingTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      id={task.id}
                      sandboxId={task.sandbox_id}
                      title={task.title}
                      taskType={task.task_type}
                      status={normalizeStatus(task.status)}
                      timeAgo={task.started_at ? formatTimeAgo(task.started_at) : formatTimeAgo(task.created_at)}
                      isSelected={task.sandbox_id === selectedSandboxId}
                    />
                  ))}
                </div>
              )}

              {pendingValidationTasks.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Pending Validation</TimeGroupHeader>
                  {pendingValidationTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      id={task.id}
                      sandboxId={task.sandbox_id}
                      title={task.title}
                      taskType={task.task_type}
                      status={normalizeStatus(task.status)}
                      timeAgo={task.started_at ? formatTimeAgo(task.started_at) : formatTimeAgo(task.created_at)}
                      isSelected={task.sandbox_id === selectedSandboxId}
                    />
                  ))}
                </div>
              )}

              {pendingTasks.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Pending</TimeGroupHeader>
                  {pendingTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      id={task.id}
                      sandboxId={task.sandbox_id}
                      title={task.title}
                      taskType={task.task_type}
                      status={normalizeStatus(task.status)}
                      timeAgo={formatTimeAgo(task.created_at)}
                      isSelected={task.sandbox_id === selectedSandboxId}
                      onMarkFailed={handleMarkFailed}
                    />
                  ))}
                </div>
              )}

              {completedTasks.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Completed</TimeGroupHeader>
                  {completedTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      id={task.id}
                      sandboxId={task.sandbox_id}
                      title={task.title}
                      taskType={task.task_type}
                      status={normalizeStatus(task.status)}
                      timeAgo={task.started_at ? formatTimeAgo(task.started_at) : formatTimeAgo(task.created_at)}
                      isSelected={task.sandbox_id === selectedSandboxId}
                    />
                  ))}
                </div>
              )}

              {failedTasks.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Failed</TimeGroupHeader>
                  {failedTasks.map((task) => (
                    <TaskCard
                      key={task.id}
                      id={task.id}
                      sandboxId={task.sandbox_id}
                      title={task.title}
                      taskType={task.task_type}
                      status={normalizeStatus(task.status)}
                      timeAgo={task.started_at ? formatTimeAgo(task.started_at) : formatTimeAgo(task.created_at)}
                      isSelected={task.sandbox_id === selectedSandboxId}
                    />
                  ))}
                </div>
              )}
            </>
          ) : (
            // Flat sorted list view - stacked cards with full text
            <div className="space-y-2">
              {filteredTasks.map((task) => (
                <TaskCard
                  key={task.id}
                  id={task.id}
                  sandboxId={task.sandbox_id}
                  title={task.title}
                  taskType={task.task_type}
                  status={normalizeStatus(task.status)}
                  timeAgo={task.started_at ? formatTimeAgo(task.started_at) : formatTimeAgo(task.created_at)}
                  isSelected={task.sandbox_id === selectedSandboxId}
                  onMarkFailed={normalizeStatus(task.status) === "running" || normalizeStatus(task.status) === "pending" ? handleMarkFailed : undefined}
                  compact={false}
                />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
