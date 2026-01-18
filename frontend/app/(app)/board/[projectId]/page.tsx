"use client"

import { use, useState, useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { CreateTicketDialog } from "@/components/tickets/CreateTicketDialog"
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent,
  DragOverEvent,
} from "@dnd-kit/core"
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable"
import { CSS } from "@dnd-kit/utilities"
import {
  ArrowLeft,
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  AlertCircle,
  Bot,
  GripVertical,
  BarChart3,
  ListFilter,
  X,
  FolderGit2,
  Play,
  Loader2,
  Radio,
  CircleDot,
  FileText,
  Zap,
} from "lucide-react"
import { toast } from "sonner"
import { useBoardView, useMoveTicket } from "@/hooks/useBoard"
import { useProject, useUpdateProject } from "@/hooks/useProjects"
import { useBatchSpawnPhaseTasks } from "@/hooks/useTickets"
import { useBoardEvents, type BoardEvent, type RunningTaskInfo } from "@/hooks/useBoardEvents"
import { AgentPanel } from "@/components/board"
import type { Ticket as ApiTicket, BoardColumn, TicketContext } from "@/lib/api/types"

interface BoardPageProps {
  params: Promise<{ projectId: string }>
}

// Local ticket type for board display (maps API ticket to board format)
interface BoardTicket {
  id: string
  title: string
  columnId: string
  priority: "critical" | "high" | "medium" | "low"
  status: string
  phase: string
  description: string | null
  approval_status: string | null
  context?: TicketContext | null
}

interface Column {
  id: string
  title: string
  wipLimit: number | null
  phase_mappings: string[]
}

const priorityConfig: Record<string, { label: string; color: string }> = {
  CRITICAL: { label: "Critical", color: "destructive" },
  HIGH: { label: "High", color: "destructive" },
  MEDIUM: { label: "Medium", color: "secondary" },
  LOW: { label: "Low", color: "outline" },
  critical: { label: "Critical", color: "destructive" },
  high: { label: "High", color: "destructive" },
  medium: { label: "Medium", color: "secondary" },
  low: { label: "Low", color: "outline" },
}

const statusConfig: Record<string, { label: string; color: string }> = {
  backlog: { label: "Backlog", color: "outline" },
  in_progress: { label: "In Progress", color: "default" },
  review: { label: "Review", color: "secondary" },
  done: { label: "Done", color: "default" },
  blocked: { label: "Blocked", color: "destructive" },
}

// Sortable Ticket Card Component
function SortableTicketCard({
  ticket,
  projectId,
  runningTasks,
  onViewAgent,
}: {
  ticket: BoardTicket
  projectId: string
  runningTasks?: RunningTaskInfo[]
  onViewAgent?: (taskInfo: RunningTaskInfo) => void
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: ticket.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <div ref={setNodeRef} style={style}>
      <TicketCard
        ticket={ticket}
        projectId={projectId}
        dragHandleProps={{ ...attributes, ...listeners }}
        runningTasks={runningTasks}
        onViewAgent={onViewAgent}
      />
    </div>
  )
}

// Ticket Card Component
function TicketCard({
  ticket,
  projectId,
  dragHandleProps,
  isOverlay = false,
  runningTasks = [],
  onViewAgent,
}: {
  ticket: BoardTicket
  projectId: string
  dragHandleProps?: Record<string, unknown>
  isOverlay?: boolean
  runningTasks?: RunningTaskInfo[]
  onViewAgent?: (taskInfo: RunningTaskInfo) => void
}) {
  const priorityCfg = priorityConfig[ticket.priority] || { label: ticket.priority, color: "outline" }
  const statusCfg = statusConfig[ticket.status] || { label: ticket.status, color: "outline" }
  const hasRunningTasks = runningTasks.length > 0

  const handleAgentClick = (e: React.MouseEvent, taskInfo: RunningTaskInfo) => {
    e.preventDefault()
    e.stopPropagation()
    onViewAgent?.(taskInfo)
  }

  const content = (
    <Card
      className={`cursor-pointer transition-all ${
        isOverlay
          ? "shadow-lg ring-2 ring-primary"
          : hasRunningTasks
            ? "ring-2 ring-green-500/50 shadow-green-500/20 shadow-md hover:shadow-lg"
            : "hover:border-primary/50 hover:shadow-sm"
      }`}
    >
      <CardContent className="p-3 space-y-2">
        {/* Header with drag handle */}
        <div className="flex items-start gap-2">
          <button
            {...dragHandleProps}
            className="mt-0.5 cursor-grab text-muted-foreground hover:text-foreground active:cursor-grabbing"
          >
            <GripVertical className="h-4 w-4" />
          </button>
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2">
              <div className="space-y-1">
                <Badge variant="outline" className="font-mono text-xs">
                  {ticket.id.slice(0, 8)}
                </Badge>
                <p className="text-sm font-medium leading-tight line-clamp-2">
                  {ticket.title}
                </p>
              </div>
              {/* Running task indicator */}
              {hasRunningTasks && (
                <button
                  onClick={(e) => handleAgentClick(e, runningTasks[0])}
                  className="shrink-0 flex items-center gap-1 px-2 py-1 rounded-md bg-green-500/10 hover:bg-green-500/20 text-green-600 transition-colors"
                  title="View agent output"
                >
                  <Bot className="h-3.5 w-3.5 animate-pulse" />
                  <span className="text-xs font-medium">{runningTasks.length}</span>
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Badges row */}
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Spec badge - show if ticket was created from a spec */}
          {ticket.context?.spec_id && (
            <Badge
              variant="outline"
              className="text-xs bg-purple-500/10 text-purple-600 border-purple-500/30 hover:bg-purple-500/20"
              title={ticket.context.spec_title || "From Spec"}
            >
              <FileText className="h-3 w-3 mr-1" />
              Spec
            </Badge>
          )}
          <Badge variant={priorityCfg.color as "default" | "destructive" | "secondary" | "outline"} className="text-xs">
            {priorityCfg.label}
          </Badge>
          <Badge variant={statusCfg.color as "default" | "destructive" | "secondary" | "outline"} className="text-xs">
            {statusCfg.label}
          </Badge>
          {ticket.approval_status && ticket.approval_status !== "approved" && (
            <Badge variant="secondary" className="text-xs">
              {ticket.approval_status}
            </Badge>
          )}
        </div>

        {/* Footer with phase */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t">
          <span className="capitalize">{ticket.phase.toLowerCase().replace(/_/g, " ")}</span>
          {ticket.status === "blocked" && (
            <span className="flex items-center gap-1 text-orange-500">
              <AlertCircle className="h-3 w-3" />
              Blocked
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )

  if (isOverlay) {
    return content
  }

  return (
    <Link href={`/board/${projectId}/${ticket.id}`}>
      {content}
    </Link>
  )
}

// Column Component
function KanbanColumn({
  column,
  tickets,
  projectId,
  isOver,
  getRunningTasksForTicket,
  onViewAgent,
}: {
  column: Column
  tickets: BoardTicket[]
  projectId: string
  isOver?: boolean
  getRunningTasksForTicket?: (ticketId: string) => RunningTaskInfo[]
  onViewAgent?: (taskInfo: RunningTaskInfo) => void
}) {
  const isOverWipLimit = column.wipLimit !== null && column.wipLimit > 0 && tickets.length > column.wipLimit

  return (
    <div
      className={`flex w-[320px] shrink-0 flex-col rounded-lg transition-colors ${
        isOver ? "bg-primary/5 ring-2 ring-primary/20" : "bg-muted/30"
      }`}
    >
      {/* Column Header */}
      <div className="flex items-center justify-between p-3 border-b border-border/50">
        <div className="flex items-center gap-2">
          <h2 className="font-semibold">{column.title}</h2>
          <Badge
            variant={isOverWipLimit ? "destructive" : "secondary"}
            className="rounded-full"
          >
            {tickets.length}
            {column.wipLimit !== null && column.wipLimit > 0 && `/${column.wipLimit}`}
          </Badge>
          {isOverWipLimit && (
            <span className="text-xs text-destructive">WIP exceeded</span>
          )}
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Edit Column</DropdownMenuItem>
            <DropdownMenuItem>Set WIP Limit</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem>Archive All</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Column Content */}
      <SortableContext
        items={tickets.map((t) => t.id)}
        strategy={verticalListSortingStrategy}
      >
        <ScrollArea className="flex-1 max-h-[calc(100vh-220px)]">
          <div className="space-y-2 p-2">
            {tickets.map((ticket) => (
              <SortableTicketCard
                key={ticket.id}
                ticket={ticket}
                projectId={projectId}
                runningTasks={getRunningTasksForTicket?.(ticket.id)}
                onViewAgent={onViewAgent}
              />
            ))}

            {tickets.length === 0 && (
              <div className="rounded-lg border-2 border-dashed border-muted-foreground/20 p-6 text-center text-sm text-muted-foreground">
                Drop tickets here
              </div>
            )}

            {/* Add ticket button */}
            <Button
              variant="ghost"
              className="w-full justify-start text-muted-foreground"
              size="sm"
            >
              <Plus className="mr-2 h-4 w-4" />
              Add ticket
            </Button>
          </div>
        </ScrollArea>
      </SortableContext>
    </div>
  )
}

export default function BoardPage({ params }: BoardPageProps) {
  const { projectId } = use(params)
  const router = useRouter()
  const [searchQuery, setSearchQuery] = useState("")
  const [filterStatus, setFilterStatus] = useState<string>("all")
  const [filterPriority, setFilterPriority] = useState<string>("all")
  const [hideSpecDriven, setHideSpecDriven] = useState(false)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [overId, setOverId] = useState<string | null>(null)
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)

  // Agent panel state
  const [selectedSandboxId, setSelectedSandboxId] = useState<string | null>(null)
  const [selectedTaskInfo, setSelectedTaskInfo] = useState<{ ticketTitle?: string; taskTitle?: string }>({})
  const [isAgentPanelExpanded, setIsAgentPanelExpanded] = useState(false)

  // Fetch project and board data from API
  const { data: project, refetch: refetchProject } = useProject(projectId === "all" ? undefined : projectId)
  const { data: boardData, isLoading, error } = useBoardView(projectId === "all" ? undefined : projectId)
  const moveTicket = useMoveTicket()
  const batchSpawn = useBatchSpawnPhaseTasks()
  const updateProject = useUpdateProject()

  // Handle WebSocket events for real-time updates
  const handleBoardEvent = useCallback((event: BoardEvent) => {
    // Show toast for significant events
    switch (event.event_type) {
      case "TICKET_CREATED":
        toast.success("New ticket created", {
          description: (event.payload.title as string) || event.entity_id.slice(0, 8),
        })
        break
      case "TASK_ASSIGNED":
        toast.info("Task started", {
          description: `Agent assigned to task ${event.entity_id.slice(0, 8)}`,
        })
        break
      case "TASK_COMPLETED":
        toast.success("Task completed", {
          description: `Task ${event.entity_id.slice(0, 8)} finished`,
        })
        break
      case "TICKET_PHASE_ADVANCED":
        toast.success("Phase advanced", {
          description: `Ticket moved to ${(event.payload.new_phase as string) || "next phase"}`,
        })
        break
      case "SANDBOX_SPAWNED":
        // Auto-select sandbox when it spawns
        const sandboxId = event.entity_id
        const taskTitle = event.payload.task_title as string | undefined
        const ticketTitle = event.payload.ticket_title as string | undefined
        setSelectedSandboxId(sandboxId)
        setSelectedTaskInfo({ ticketTitle, taskTitle })
        toast.info("Agent started", {
          description: taskTitle || `Sandbox ${sandboxId.slice(0, 8)}`,
          action: {
            label: "View Sandbox",
            onClick: () => router.push(`/sandbox/${sandboxId}`),
          },
          duration: 10000, // Keep visible longer so user can click
        })
        break
    }
  }, [router])

  const { isConnected: wsConnected, runningTasks, getRunningTasksForTicket } = useBoardEvents({
    projectId: projectId === "all" ? undefined : projectId,
    onEvent: handleBoardEvent,
    enabled: true, // Always enable WebSocket events, even for "all" projects view
  })

  // Handler for clicking on agent indicator
  const handleViewAgent = useCallback((taskInfo: RunningTaskInfo) => {
    if (taskInfo.sandboxId) {
      setSelectedSandboxId(taskInfo.sandboxId)
      setSelectedTaskInfo({ taskTitle: taskInfo.taskTitle })
    }
  }, [])

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  )

  // Transform API data to local format
  const columns: Column[] = useMemo(() => {
    if (!boardData?.columns) return []
    return boardData.columns.map((col) => ({
      id: col.id,
      title: col.name,
      wipLimit: col.wip_limit,
      phase_mappings: col.phase_mappings,
    }))
  }, [boardData])

  // Transform tickets from columns
  const allTickets: BoardTicket[] = useMemo(() => {
    if (!boardData?.columns) return []
    return boardData.columns.flatMap((col) =>
      col.tickets.map((t: ApiTicket) => ({
        id: t.id,
        title: t.title,
        columnId: col.id,
        priority: (t.priority?.toLowerCase() || "medium") as "critical" | "high" | "medium" | "low",
        status: t.status,
        phase: t.phase_id,
        description: t.description,
        approval_status: t.approval_status,
        context: t.context,
      }))
    )
  }, [boardData])

  // Filter tickets
  const filteredTickets = allTickets.filter((ticket) => {
    const matchesSearch =
      searchQuery === "" ||
      ticket.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.id.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = filterStatus === "all" || ticket.status === filterStatus
    const matchesPriority =
      filterPriority === "all" || ticket.priority === filterPriority.toLowerCase()
    // Hide spec-driven tickets if toggle is enabled
    const matchesSpecFilter = !hideSpecDriven || ticket.context?.workflow_mode !== "spec_driven"
    return matchesSearch && matchesStatus && matchesPriority && matchesSpecFilter
  })

  // Group tickets by column
  const ticketsByColumn = columns.reduce((acc, column) => {
    acc[column.id] = filteredTickets.filter((t) => t.columnId === column.id)
    return acc
  }, {} as Record<string, BoardTicket[]>)

  // Get active ticket for drag overlay
  const activeTicket = activeId
    ? allTickets.find((t) => t.id === activeId)
    : null

  // Find which column a ticket belongs to
  const findColumn = useCallback((id: string) => {
    const ticket = allTickets.find((t) => t.id === id)
    if (ticket) return ticket.columnId
    // Check if id is a column id
    if (columns.find((c) => c.id === id)) return id
    return null
  }, [allTickets, columns])

  const handleDragStart = useCallback((event: DragStartEvent) => {
    setActiveId(event.active.id as string)
  }, [])

  const handleDragOver = useCallback((event: DragOverEvent) => {
    const { over } = event
    setOverId(over?.id as string | null)
  }, [])

  const handleDragEnd = useCallback((event: DragEndEvent) => {
    const { active, over } = event

    setActiveId(null)
    setOverId(null)

    if (!over) return

    const draggedId = active.id as string
    const droppedId = over.id as string

    const activeColumn = findColumn(draggedId)
    let overColumn = findColumn(droppedId)

    // If dropping on a column directly
    if (columns.find((c) => c.id === droppedId)) {
      overColumn = droppedId
    }

    if (!activeColumn || !overColumn) return
    if (activeColumn === overColumn) return

    // Move ticket via API
    moveTicket.mutate({
      ticket_id: draggedId,
      target_column_id: overColumn,
    })
  }, [columns, findColumn, moveTicket])

  const clearFilters = () => {
    setSearchQuery("")
    setFilterStatus("all")
    setFilterPriority("all")
    setHideSpecDriven(false)
  }

  const hasFilters = searchQuery || filterStatus !== "all" || filterPriority !== "all" || hideSpecDriven

  // Get processable tickets (backlog/in_progress that aren't blocked)
  const processableTickets = allTickets.filter(
    (t) => t.status !== "done" && t.status !== "blocked"
  )

  // Start processing all eligible tickets
  const handleStartProcessing = async () => {
    if (processableTickets.length === 0) {
      toast.info("No tickets to process", {
        description: "All tickets are either done or blocked.",
      })
      return
    }

    const ticketIds = processableTickets.map((t) => t.id)

    try {
      const results = await batchSpawn.mutateAsync(ticketIds)

      // Count successes and failures
      const successes = results.filter((r) => r.tasks_spawned > 0)
      const failures = results.filter((r) => r.error)
      const totalTasks = successes.reduce((sum, r) => sum + r.tasks_spawned, 0)

      if (failures.length === 0) {
        toast.success(`Started processing ${successes.length} tickets`, {
          description: `Spawned ${totalTasks} tasks. They will be picked up by the orchestrator.`,
        })
      } else if (successes.length > 0) {
        toast.warning(`Partial success`, {
          description: `Spawned ${totalTasks} tasks for ${successes.length} tickets. ${failures.length} tickets failed.`,
        })
      } else {
        toast.error("Failed to start processing", {
          description: failures[0]?.error || "Unknown error occurred",
        })
      }
    } catch (error) {
      toast.error("Failed to start processing", {
        description: error instanceof Error ? error.message : "Unknown error",
      })
    }
  }

  // Toggle autonomous execution
  const handleToggleAutonomousExecution = async (enabled: boolean) => {
    if (projectId === "all") return

    try {
      await updateProject.mutateAsync({
        projectId,
        data: { autonomous_execution_enabled: enabled },
      })
      await refetchProject()
      toast.success(enabled ? "Autonomous execution enabled" : "Autonomous execution disabled", {
        description: enabled
          ? "Tasks will be automatically executed by agents."
          : "Tasks will require manual triggering.",
      })
    } catch (error) {
      toast.error("Failed to update project", {
        description: error instanceof Error ? error.message : "Unknown error",
      })
    }
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="flex-shrink-0 border-b bg-background px-4 py-3">
          <div className="flex items-center gap-4">
            <Skeleton className="h-6 w-20" />
            <Skeleton className="h-8 w-40" />
          </div>
        </div>
        <div className="flex gap-4 p-4">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="w-[320px] shrink-0 rounded-lg bg-muted/30 p-3">
              <Skeleton className="h-6 w-32 mb-4" />
              <div className="space-y-2">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-24 w-full" />
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h2 className="mt-4 text-lg font-semibold">Failed to load board</h2>
          <p className="text-muted-foreground">
            {error instanceof Error ? error.message : "An error occurred"}
          </p>
          <Button className="mt-4" asChild>
            <Link href={`/projects/${projectId}`}>Back to Project</Link>
          </Button>
        </div>
      </div>
    )
  }

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        {/* Header */}
        <div className="flex-shrink-0 border-b bg-background px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              {/* Project Context Breadcrumb */}
              <div className="flex items-center gap-2 text-sm">
                <Link
                  href={projectId === "all" ? "/projects" : `/projects/${projectId}`}
                  className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <FolderGit2 className="h-4 w-4" />
                  <span className="font-medium text-foreground">{project?.name || (projectId === "all" ? "All Projects" : "Project")}</span>
                </Link>
                <span className="text-muted-foreground">/</span>
                <span className="text-muted-foreground">Kanban Board</span>
              </div>
              <h1 className="text-xl font-bold">Kanban Board</h1>
              <Badge variant="outline">
                {filteredTickets.length} tickets
              </Badge>
              {/* WebSocket connection indicator */}
              <div className="flex items-center gap-1.5" title={wsConnected ? "Live updates connected" : "Connecting..."}>
                <CircleDot className={`h-3 w-3 ${wsConnected ? "text-green-500 animate-pulse" : "text-yellow-500"}`} />
                <span className="text-xs text-muted-foreground">
                  {wsConnected ? "Live" : "..."}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Search */}
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search tickets..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-[200px] pl-8"
                />
              </div>

              {/* Status Filter */}
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger className="w-[130px]">
                  <ListFilter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Statuses</SelectItem>
                  <SelectItem value="backlog">Backlog</SelectItem>
                  <SelectItem value="in_progress">In Progress</SelectItem>
                  <SelectItem value="review">Review</SelectItem>
                  <SelectItem value="done">Done</SelectItem>
                  <SelectItem value="blocked">Blocked</SelectItem>
                </SelectContent>
              </Select>

              {/* Priority Filter */}
              <Select value={filterPriority} onValueChange={setFilterPriority}>
                <SelectTrigger className="w-[130px]">
                  <Filter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Priorities</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="low">Low</SelectItem>
                </SelectContent>
              </Select>

              {/* Autonomous Execution Toggle */}
              {projectId !== "all" && project && (
                <div className="flex items-center gap-2 px-2 border-l border-border/50 ml-1">
                  <Switch
                    id="autonomous-execution"
                    checked={project.autonomous_execution_enabled}
                    onCheckedChange={handleToggleAutonomousExecution}
                    disabled={updateProject.isPending}
                    className={project.autonomous_execution_enabled ? "data-[state=checked]:bg-amber-500" : ""}
                  />
                  <Label
                    htmlFor="autonomous-execution"
                    className={`text-sm cursor-pointer flex items-center gap-1.5 ${
                      project.autonomous_execution_enabled ? "text-amber-600 font-medium" : "text-muted-foreground"
                    }`}
                  >
                    <Zap className={`h-3.5 w-3.5 ${project.autonomous_execution_enabled ? "fill-amber-500" : ""}`} />
                    Auto
                  </Label>
                </div>
              )}

              {/* Hide Spec-Driven Toggle */}
              <div className="flex items-center gap-2 px-2">
                <Switch
                  id="hide-spec-driven"
                  checked={hideSpecDriven}
                  onCheckedChange={setHideSpecDriven}
                />
                <Label htmlFor="hide-spec-driven" className="text-sm text-muted-foreground cursor-pointer">
                  Hide Spec-Driven
                </Label>
              </div>

              {/* Clear Filters */}
              {hasFilters && (
                <Button variant="ghost" size="sm" onClick={clearFilters}>
                  <X className="mr-1 h-4 w-4" />
                  Clear
                </Button>
              )}

              {/* View Graph */}
              <Button variant="outline" asChild>
                <Link href={`/graph/${projectId}`}>
                  <BarChart3 className="mr-2 h-4 w-4" />
                  Graph
                </Link>
              </Button>

              {/* Start Processing - spawns tasks for all eligible tickets */}
              <Button
                variant="default"
                onClick={handleStartProcessing}
                disabled={batchSpawn.isPending || processableTickets.length === 0}
                className="bg-green-600 hover:bg-green-700"
              >
                {batchSpawn.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play className="mr-2 h-4 w-4" />
                    Start Processing
                    {processableTickets.length > 0 && (
                      <Badge variant="secondary" className="ml-2 bg-green-800">
                        {processableTickets.length}
                      </Badge>
                    )}
                  </>
                )}
              </Button>

              {/* Create Ticket */}
              <Button onClick={() => setIsCreateDialogOpen(true)}>
                <Plus className="mr-2 h-4 w-4" />
                Create Ticket
              </Button>
            </div>
          </div>
        </div>

        {/* Main Content Area - Board + Agent Panel */}
        <div className="flex-1 flex overflow-hidden">
          {/* Board */}
          <div className={`flex-1 transition-all duration-300 ${selectedSandboxId && !isAgentPanelExpanded ? "mr-0" : ""}`}>
            <ScrollArea className="h-full">
              <div className="flex gap-4 p-4 pb-8">
                {columns.map((column) => (
                  <KanbanColumn
                    key={column.id}
                    column={column}
                    tickets={ticketsByColumn[column.id] || []}
                    projectId={projectId}
                    isOver={overId === column.id || ticketsByColumn[column.id]?.some(t => t.id === overId)}
                    getRunningTasksForTicket={getRunningTasksForTicket}
                    onViewAgent={handleViewAgent}
                  />
                ))}
              </div>
              <ScrollBar orientation="horizontal" />
            </ScrollArea>
          </div>

          {/* Agent Panel - Slide in from right */}
          {selectedSandboxId && (
            <div
              className={`shrink-0 transition-all duration-300 ${
                isAgentPanelExpanded ? "w-[60%]" : "w-[400px]"
              }`}
            >
              <AgentPanel
                sandboxId={selectedSandboxId}
                ticketTitle={selectedTaskInfo.ticketTitle}
                taskTitle={selectedTaskInfo.taskTitle}
                onClose={() => {
                  setSelectedSandboxId(null)
                  setSelectedTaskInfo({})
                }}
                isExpanded={isAgentPanelExpanded}
                onToggleExpand={() => setIsAgentPanelExpanded(!isAgentPanelExpanded)}
              />
            </div>
          )}
        </div>

        {/* Drag Overlay */}
        <DragOverlay>
          {activeTicket && (
            <TicketCard
              ticket={activeTicket}
              projectId={projectId}
              isOverlay
            />
          )}
        </DragOverlay>

        {/* Create Ticket Dialog */}
        <CreateTicketDialog
          open={isCreateDialogOpen}
          onOpenChange={setIsCreateDialogOpen}
          projectId={projectId}
        />
      </div>
    </DndContext>
  )
}
