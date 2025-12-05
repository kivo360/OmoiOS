"use client"

import { use, useState, useCallback } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
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
  User,
  AlertCircle,
  Bot,
  GitBranch,
  GripVertical,
  BarChart3,
  ListFilter,
  X,
} from "lucide-react"

interface BoardPageProps {
  params: Promise<{ projectId: string }>
}

interface Ticket {
  id: string
  title: string
  columnId: string
  priority: "critical" | "high" | "medium" | "low"
  type: "feature" | "bug" | "task" | "optimization"
  phase: string
  assignee: string | null
  labels: string[]
  blockers: number
  linesAdded: number
  linesRemoved: number
  commitCount: number
}

interface Column {
  id: string
  title: string
  wipLimit: number
}

// Mock columns with WIP limits
const initialColumns: Column[] = [
  { id: "backlog", title: "Backlog", wipLimit: 0 },
  { id: "requirements", title: "Requirements", wipLimit: 5 },
  { id: "implementation", title: "Implementation", wipLimit: 3 },
  { id: "review", title: "Review", wipLimit: 3 },
  { id: "done", title: "Done", wipLimit: 0 },
]

// Mock tickets with more details
const initialTickets: Ticket[] = [
  {
    id: "TICKET-001",
    title: "Setup authentication flow",
    columnId: "implementation",
    priority: "high",
    type: "feature",
    phase: "IMPLEMENTATION",
    assignee: "worker-1",
    labels: ["auth"],
    blockers: 0,
    linesAdded: 1255,
    linesRemoved: 42,
    commitCount: 5,
  },
  {
    id: "TICKET-002",
    title: "Implement JWT token validation",
    columnId: "requirements",
    priority: "high",
    type: "feature",
    phase: "REQUIREMENTS",
    assignee: null,
    labels: ["auth", "security"],
    blockers: 1,
    linesAdded: 0,
    linesRemoved: 0,
    commitCount: 0,
  },
  {
    id: "TICKET-003",
    title: "Add OAuth2 providers (Google, GitHub)",
    columnId: "backlog",
    priority: "medium",
    type: "feature",
    phase: "BACKLOG",
    assignee: null,
    labels: ["auth", "oauth"],
    blockers: 0,
    linesAdded: 0,
    linesRemoved: 0,
    commitCount: 0,
  },
  {
    id: "TICKET-004",
    title: "Create user profile endpoint",
    columnId: "review",
    priority: "medium",
    type: "feature",
    phase: "REVIEW",
    assignee: "worker-2",
    labels: ["api", "user"],
    blockers: 0,
    linesAdded: 450,
    linesRemoved: 12,
    commitCount: 3,
  },
  {
    id: "TICKET-005",
    title: "Add password reset flow",
    columnId: "requirements",
    priority: "low",
    type: "feature",
    phase: "REQUIREMENTS",
    assignee: null,
    labels: ["auth"],
    blockers: 2,
    linesAdded: 0,
    linesRemoved: 0,
    commitCount: 0,
  },
  {
    id: "TICKET-006",
    title: "Rate limiting middleware",
    columnId: "done",
    priority: "high",
    type: "feature",
    phase: "DONE",
    assignee: "worker-1",
    labels: ["security", "middleware"],
    blockers: 0,
    linesAdded: 320,
    linesRemoved: 0,
    commitCount: 2,
  },
  {
    id: "TICKET-007",
    title: "Fix login redirect bug",
    columnId: "implementation",
    priority: "critical",
    type: "bug",
    phase: "IMPLEMENTATION",
    assignee: "worker-1",
    labels: ["bug", "auth"],
    blockers: 0,
    linesAdded: 45,
    linesRemoved: 23,
    commitCount: 1,
  },
  {
    id: "TICKET-008",
    title: "Optimize database queries",
    columnId: "backlog",
    priority: "low",
    type: "optimization",
    phase: "BACKLOG",
    assignee: null,
    labels: ["performance", "database"],
    blockers: 0,
    linesAdded: 0,
    linesRemoved: 0,
    commitCount: 0,
  },
]

const priorityConfig = {
  critical: { label: "Critical", color: "destructive" },
  high: { label: "High", color: "destructive" },
  medium: { label: "Medium", color: "secondary" },
  low: { label: "Low", color: "outline" },
}

const typeConfig = {
  feature: { label: "Feature", color: "default" },
  bug: { label: "Bug", color: "destructive" },
  task: { label: "Task", color: "secondary" },
  optimization: { label: "Optimization", color: "outline" },
}

// Sortable Ticket Card Component
function SortableTicketCard({
  ticket,
  projectId,
}: {
  ticket: Ticket
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
  ticket: Ticket
  projectId: string
  dragHandleProps?: any
  isOverlay?: boolean
}) {
  const priorityCfg = priorityConfig[ticket.priority]
  const typeCfg = typeConfig[ticket.type]

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
                  {ticket.id}
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
          <Badge variant={priorityCfg.color as any} className="text-xs">
            {priorityCfg.label}
          </Badge>
          <Badge variant={typeCfg.color as any} className="text-xs">
            {typeCfg.label}
          </Badge>
          {ticket.labels.slice(0, 2).map((label) => (
            <Badge key={label} variant="outline" className="text-xs">
              {label}
            </Badge>
          ))}
        </div>

        {/* Footer with assignee and stats */}
        <div className="flex items-center justify-between text-xs text-muted-foreground pt-1 border-t">
          <div className="flex items-center gap-2">
            {ticket.assignee ? (
              <span className="flex items-center gap-1">
                <Bot className="h-3 w-3" />
                {ticket.assignee}
              </span>
            ) : (
              <span className="text-muted-foreground/50">Unassigned</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {(ticket.linesAdded > 0 || ticket.linesRemoved > 0) && (
              <span className="font-mono">
                <span className="text-green-600">+{ticket.linesAdded}</span>
                {" "}
                <span className="text-red-600">-{ticket.linesRemoved}</span>
              </span>
            )}
            {ticket.blockers > 0 && (
              <span className="flex items-center gap-1 text-orange-500">
                <AlertCircle className="h-3 w-3" />
                {ticket.blockers}
              </span>
            )}
          </div>
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
  tickets: Ticket[]
  projectId: string
  isOver?: boolean
}) {
  const isOverWipLimit = column.wipLimit > 0 && tickets.length > column.wipLimit

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
            {column.wipLimit > 0 && `/${column.wipLimit}`}
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
  const [tickets, setTickets] = useState<Ticket[]>(initialTickets)
  const [columns] = useState<Column[]>(initialColumns)
  const [searchQuery, setSearchQuery] = useState("")
  const [filterType, setFilterType] = useState<string>("all")
  const [filterPriority, setFilterPriority] = useState<string>("all")
  const [activeId, setActiveId] = useState<string | null>(null)
  const [overId, setOverId] = useState<string | null>(null)

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

  // Filter tickets
  const filteredTickets = tickets.filter((ticket) => {
    const matchesSearch =
      searchQuery === "" ||
      ticket.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      ticket.id.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = filterType === "all" || ticket.type === filterType
    const matchesPriority =
      filterPriority === "all" || ticket.priority === filterPriority
    return matchesSearch && matchesType && matchesPriority
  })

  // Group tickets by column
  const ticketsByColumn = columns.reduce((acc, column) => {
    acc[column.id] = filteredTickets.filter((t) => t.columnId === column.id)
    return acc
  }, {} as Record<string, Ticket[]>)

  // Get active ticket for drag overlay
  const activeTicket = activeId
    ? tickets.find((t) => t.id === activeId)
    : null

  // Find which column a ticket belongs to
  const findColumn = (id: string) => {
    const ticket = tickets.find((t) => t.id === id)
    if (ticket) return ticket.columnId
    // Check if id is a column id
    if (columns.find((c) => c.id === id)) return id
    return null
  }

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

    const activeId = active.id as string
    const overId = over.id as string

    const activeColumn = findColumn(activeId)
    let overColumn = findColumn(overId)

    // If dropping on a column directly
    if (columns.find((c) => c.id === overId)) {
      overColumn = overId
    }

    if (!activeColumn || !overColumn) return
    if (activeColumn === overColumn) return

    // Move ticket to new column
    setTickets((prev) =>
      prev.map((ticket) =>
        ticket.id === activeId
          ? { ...ticket, columnId: overColumn!, phase: overColumn!.toUpperCase() }
          : ticket
      )
    )
  }, [columns])

  const clearFilters = () => {
    setSearchQuery("")
    setFilterType("all")
    setFilterPriority("all")
  }

  const hasFilters = searchQuery || filterType !== "all" || filterPriority !== "all"

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

              {/* Type Filter */}
              <Select value={filterType} onValueChange={setFilterType}>
                <SelectTrigger className="w-[130px]">
                  <ListFilter className="mr-2 h-4 w-4" />
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Types</SelectItem>
                  <SelectItem value="feature">Feature</SelectItem>
                  <SelectItem value="bug">Bug</SelectItem>
                  <SelectItem value="task">Task</SelectItem>
                  <SelectItem value="optimization">Optimization</SelectItem>
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
