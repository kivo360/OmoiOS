"use client"

import { use, useState, useCallback, useMemo } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea, ScrollBar } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
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
} from "lucide-react"
import { useBoardView, useMoveTicket } from "@/hooks/useBoard"
import type { Ticket as ApiTicket, BoardColumn } from "@/lib/api/types"

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
}: {
  ticket: BoardTicket
  projectId: string
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
}: {
  ticket: BoardTicket
  projectId: string
  dragHandleProps?: Record<string, unknown>
  isOverlay?: boolean
}) {
  const priorityCfg = priorityConfig[ticket.priority] || { label: ticket.priority, color: "outline" }
  const statusCfg = statusConfig[ticket.status] || { label: ticket.status, color: "outline" }

  const content = (
    <Card
      className={`cursor-pointer transition-all ${
        isOverlay
          ? "shadow-lg ring-2 ring-primary"
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
            </div>
          </div>
        </div>

        {/* Badges row */}
        <div className="flex items-center gap-1.5 flex-wrap">
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
}: {
  column: Column
  tickets: BoardTicket[]
  projectId: string
  isOver?: boolean
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
  const [searchQuery, setSearchQuery] = useState("")
  const [filterStatus, setFilterStatus] = useState<string>("all")
  const [filterPriority, setFilterPriority] = useState<string>("all")
  const [activeId, setActiveId] = useState<string | null>(null)
  const [overId, setOverId] = useState<string | null>(null)

  // Fetch board data from API
  const { data: boardData, isLoading, error } = useBoardView(projectId === "all" ? undefined : projectId)
  const moveTicket = useMoveTicket()

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
    return matchesSearch && matchesStatus && matchesPriority
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
  }

  const hasFilters = searchQuery || filterStatus !== "all" || filterPriority !== "all"

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
              <Link
                href={`/projects/${projectId}`}
                className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back
              </Link>
              <h1 className="text-xl font-bold">Kanban Board</h1>
              <Badge variant="outline">
                {filteredTickets.length} tickets
              </Badge>
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

              {/* Create Ticket */}
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                Create Ticket
              </Button>
            </div>
          </div>
        </div>

        {/* Board */}
        <ScrollArea className="flex-1">
          <div className="flex gap-4 p-4 pb-8">
            {columns.map((column) => (
              <KanbanColumn
                key={column.id}
                column={column}
                tickets={ticketsByColumn[column.id] || []}
                projectId={projectId}
                isOver={overId === column.id || ticketsByColumn[column.id]?.some(t => t.id === overId)}
              />
            ))}
          </div>
          <ScrollBar orientation="horizontal" />
        </ScrollArea>

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
      </div>
    </DndContext>
  )
}
