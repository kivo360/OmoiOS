"use client"

import { use, useCallback, useEffect, useMemo, useState } from "react"
import Link from "next/link"
import {
  ReactFlow,
  Node,
  Edge,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
  Panel,
  MarkerType,
  Handle,
  Position,
  NodeProps,
} from "@xyflow/react"
import dagre from "dagre"
import "@xyflow/react/dist/style.css"

import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
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
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  ArrowLeft,
  Search,
  Filter,
  ZoomIn,
  ZoomOut,
  LayoutGrid,
  Bot,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
} from "lucide-react"

interface GraphPageProps {
  params: Promise<{ projectId: string }>
}

// Mock ticket data for the graph
const mockTickets = [
  {
    id: "TICKET-001",
    title: "Setup authentication flow",
    status: "in_progress",
    priority: "high",
    assignee: "worker-1",
    blockedBy: [],
  },
  {
    id: "TICKET-002",
    title: "Implement JWT token validation",
    status: "pending",
    priority: "high",
    assignee: null,
    blockedBy: ["TICKET-001"],
  },
  {
    id: "TICKET-003",
    title: "Add OAuth2 providers",
    status: "pending",
    priority: "medium",
    assignee: null,
    blockedBy: ["TICKET-001"],
  },
  {
    id: "TICKET-004",
    title: "Create user profile endpoint",
    status: "completed",
    priority: "medium",
    assignee: "worker-2",
    blockedBy: [],
  },
  {
    id: "TICKET-005",
    title: "Add password reset flow",
    status: "pending",
    priority: "low",
    assignee: null,
    blockedBy: ["TICKET-002", "TICKET-003"],
  },
  {
    id: "TICKET-006",
    title: "Rate limiting middleware",
    status: "completed",
    priority: "high",
    assignee: "worker-1",
    blockedBy: [],
  },
  {
    id: "TICKET-007",
    title: "Fix login redirect bug",
    status: "in_progress",
    priority: "critical",
    assignee: "worker-1",
    blockedBy: ["TICKET-001"],
  },
  {
    id: "TICKET-008",
    title: "Optimize database queries",
    status: "pending",
    priority: "low",
    assignee: null,
    blockedBy: ["TICKET-004"],
  },
  {
    id: "TICKET-009",
    title: "API documentation",
    status: "pending",
    priority: "low",
    assignee: null,
    blockedBy: ["TICKET-002", "TICKET-004"],
  },
  {
    id: "TICKET-010",
    title: "Integration tests",
    status: "blocked",
    priority: "high",
    assignee: null,
    blockedBy: ["TICKET-005", "TICKET-007"],
  },
]

const statusConfig = {
  pending: { label: "Pending", color: "#9ca3af", bgColor: "#f3f4f6", icon: Clock },
  in_progress: { label: "In Progress", color: "#3b82f6", bgColor: "#dbeafe", icon: Loader2 },
  completed: { label: "Completed", color: "#22c55e", bgColor: "#dcfce7", icon: CheckCircle },
  blocked: { label: "Blocked", color: "#ef4444", bgColor: "#fee2e2", icon: AlertCircle },
}

const priorityColors = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#ca8a04",
  low: "#6b7280",
}

const discoveryEvents = [
  {
    id: "disc-011",
    ticketId: "TICKET-002",
    branch: "auth-hardening",
    type: "discovery",
    summary: "JWT validation missing kid rotation handling; spawned hardening branch",
    impact: "Adds new sub-branch and tests",
  },
  {
    id: "disc-014",
    ticketId: "TICKET-007",
    branch: "login-hotfix",
    type: "bug",
    summary: "Login redirect loop reproduced; hotfix branch created",
    impact: "Blocks integration tests until merged",
  },
  {
    id: "disc-016",
    ticketId: "TICKET-005",
    branch: "reset-flow",
    type: "opportunity",
    summary: "Found shared email template module; reuse reduces effort",
    impact: "Threaded into reset-flow branch",
  },
]

const ticketThreads = [
  {
    ticketId: "TICKET-005",
    phases: ["Backlog", "Requirements", "Design", "Implementation"],
    current: "Implementation",
    thread: "reset-flow → integration-tests",
  },
  {
    ticketId: "TICKET-007",
    phases: ["Backlog", "Requirements", "Implementation"],
    current: "Implementation",
    thread: "login-hotfix → integration-tests",
  },
]

// Node data type
interface TicketNodeData {
  id: string
  title: string
  status: string
  priority: string
  assignee: string | null
  blockedBy: string[]
  [key: string]: unknown
}

// Custom node component
function TicketNode({ data, selected }: NodeProps) {
  const nodeData = data as TicketNodeData
  const status = statusConfig[nodeData.status as keyof typeof statusConfig]
  const StatusIcon = status.icon
  const priorityColor = priorityColors[nodeData.priority as keyof typeof priorityColors]

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={`group cursor-pointer rounded-lg border-2 bg-background p-3 shadow-sm transition-all hover:shadow-md ${
              selected ? "border-primary ring-2 ring-primary/20" : "border-border"
            }`}
            style={{
              minWidth: 180,
              borderLeftColor: priorityColor,
              borderLeftWidth: 4,
            }}
          >
            <Handle
              type="target"
              position={Position.Top}
              className="!h-2 !w-2 !border-2 !border-background !bg-muted-foreground"
            />

            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 mb-1">
                  <Badge variant="outline" className="font-mono text-[10px] px-1 py-0">
                    {nodeData.id}
                  </Badge>
                  <div
                    className="flex h-4 w-4 items-center justify-center rounded-full"
                    style={{ backgroundColor: status.bgColor }}
                  >
                    <StatusIcon
                      className={`h-2.5 w-2.5 ${
                        nodeData.status === "in_progress" ? "animate-spin" : ""
                      }`}
                      style={{ color: status.color }}
                    />
                  </div>
                </div>
                <p className="text-xs font-medium leading-tight line-clamp-2">
                  {nodeData.title}
                </p>
              </div>
            </div>

            {nodeData.assignee && (
              <div className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
                <Bot className="h-3 w-3" />
                <span>{nodeData.assignee}</span>
              </div>
            )}

            <Handle
              type="source"
              position={Position.Bottom}
              className="!h-2 !w-2 !border-2 !border-background !bg-muted-foreground"
            />
          </div>
        </TooltipTrigger>
        <TooltipContent side="right" className="max-w-xs">
          <div className="space-y-1">
            <p className="font-medium">{nodeData.title}</p>
            <div className="flex items-center gap-2 text-xs">
              <Badge variant="outline">{status.label}</Badge>
              <span className="capitalize">{nodeData.priority} priority</span>
            </div>
            {nodeData.blockedBy && nodeData.blockedBy.length > 0 && (
              <p className="text-xs text-muted-foreground">
                Blocked by: {nodeData.blockedBy.join(", ")}
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}

const nodeTypes = {
  ticket: TicketNode,
}

// Dagre layout function
function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: "TB" | "LR" = "TB"
) {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  const nodeWidth = 200
  const nodeHeight = 80

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 50,
    ranksep: 80,
    marginx: 20,
    marginy: 20,
  })

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight })
  })

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target)
  })

  dagre.layout(dagreGraph)

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id)
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    }
  })

  return { nodes: layoutedNodes, edges }
}

// Convert tickets to React Flow nodes and edges
function ticketsToFlowElements(tickets: typeof mockTickets) {
  const nodes: Node[] = tickets.map((ticket) => ({
    id: ticket.id,
    type: "ticket",
    position: { x: 0, y: 0 },
    data: {
      id: ticket.id,
      title: ticket.title,
      status: ticket.status,
      priority: ticket.priority,
      assignee: ticket.assignee,
      blockedBy: ticket.blockedBy,
    },
  }))

  const edges: Edge[] = []
  tickets.forEach((ticket) => {
    ticket.blockedBy.forEach((blockerId) => {
      edges.push({
        id: `${blockerId}-${ticket.id}`,
        source: blockerId,
        target: ticket.id,
        type: "smoothstep",
        animated: ticket.status === "blocked",
        style: {
          stroke: ticket.status === "blocked" ? "#ef4444" : "#9ca3af",
          strokeWidth: 2,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: ticket.status === "blocked" ? "#ef4444" : "#9ca3af",
        },
      })
    })
  })

  return getLayoutedElements(nodes, edges, "TB")
}

export default function DependencyGraphPage({ params }: GraphPageProps) {
  const { projectId } = use(params)
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [direction, setDirection] = useState<"TB" | "LR">("TB")
  const [showDiscoveries, setShowDiscoveries] = useState(true)

  // Filter tickets
  const filteredTickets = useMemo(() => {
    return mockTickets.filter((ticket) => {
      const matchesSearch =
        searchQuery === "" ||
        ticket.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        ticket.id.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesStatus =
        statusFilter === "all" || ticket.status === statusFilter
      return matchesSearch && matchesStatus
    })
  }, [searchQuery, statusFilter])

  // Generate initial layout
  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => ticketsToFlowElements(filteredTickets),
    [filteredTickets]
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Update nodes when filters change
  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = ticketsToFlowElements(filteredTickets)
    setNodes(newNodes)
    setEdges(newEdges)
  }, [filteredTickets, setNodes, setEdges])

  // Re-layout with new direction
  const onLayout = useCallback(
    (newDirection: "TB" | "LR") => {
      setDirection(newDirection)
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        nodes,
        edges,
        newDirection
      )
      setNodes([...layoutedNodes])
      setEdges([...layoutedEdges])
    },
    [nodes, edges, setNodes, setEdges]
  )

  // Handle node click
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      // Navigate to ticket detail
      window.location.href = `/board/${projectId}/${node.id}`
    },
    [projectId]
  )

  // Stats
  const stats = useMemo(() => {
    const total = filteredTickets.length
    const completed = filteredTickets.filter((t) => t.status === "completed").length
    const blocked = filteredTickets.filter((t) => t.status === "blocked").length
    const inProgress = filteredTickets.filter((t) => t.status === "in_progress").length
    return { total, completed, blocked, inProgress }
  }, [filteredTickets])

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b bg-background px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href={`/board/${projectId}`}
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Board
            </Link>
            <h1 className="text-xl font-bold">Dependency Graph</h1>
            <div className="flex items-center gap-2">
              <Badge variant="outline">{stats.total} tickets</Badge>
              <Badge variant="outline" className="text-green-600">
                {stats.completed} done
              </Badge>
              {stats.blocked > 0 && (
                <Badge variant="destructive">{stats.blocked} blocked</Badge>
              )}
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
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="blocked">Blocked</SelectItem>
              </SelectContent>
            </Select>

            {/* Layout Direction */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="icon">
                  <LayoutGrid className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onLayout("TB")}>
                  Vertical Layout (Top → Bottom)
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onLayout("LR")}>
                  Horizontal Layout (Left → Right)
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </div>

      {/* Graph + overlays */}
      <div className="flex-1 flex">
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.3}
          maxZoom={2}
          defaultEdgeOptions={{
            type: "smoothstep",
          }}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls showInteractive={false} />

          {/* Legend Panel */}
          <Panel position="bottom-left" className="!m-4">
            <Card className="bg-background/95 backdrop-blur">
              <CardContent className="p-3">
                <p className="text-xs font-medium text-muted-foreground mb-2">
                  Legend
                </p>
                <div className="space-y-1.5">
                  {Object.entries(statusConfig).map(([key, config]) => {
                    const Icon = config.icon
                    return (
                      <div key={key} className="flex items-center gap-2 text-xs">
                        <div
                          className="flex h-4 w-4 items-center justify-center rounded-full"
                          style={{ backgroundColor: config.bgColor }}
                        >
                          <Icon
                            className="h-2.5 w-2.5"
                            style={{ color: config.color }}
                          />
                        </div>
                        <span>{config.label}</span>
                      </div>
                    )
                  })}
                </div>
                <div className="mt-3 pt-2 border-t">
                  <p className="text-xs font-medium text-muted-foreground mb-2">
                    Priority (left border)
                  </p>
                  <div className="flex gap-2">
                    {Object.entries(priorityColors).map(([key, color]) => (
                      <div key={key} className="flex items-center gap-1 text-xs">
                        <div
                          className="h-3 w-1 rounded-full"
                          style={{ backgroundColor: color }}
                        />
                        <span className="capitalize">{key}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </Panel>

          {/* Info Panel */}
          <Panel position="top-right" className="!m-4">
            <Card className="bg-background/95 backdrop-blur">
              <CardContent className="p-3">
                <p className="text-xs font-medium text-muted-foreground mb-2">
                  Graph Info
                </p>
                <div className="space-y-1 text-xs">
                  <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Tickets</span>
                    <span className="font-medium">{stats.total}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Dependencies</span>
                    <span className="font-medium">{edges.length}</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">In Progress</span>
                    <span className="font-medium text-blue-600">
                      {stats.inProgress}
                    </span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-muted-foreground">Blocked</span>
                    <span className="font-medium text-red-600">{stats.blocked}</span>
                  </div>
                </div>
                <p className="text-[10px] text-muted-foreground mt-2 pt-2 border-t">
                  Click a ticket to view details
                </p>
              </CardContent>
            </Card>
          </Panel>
        </ReactFlow>
        </div>

        {/* Discovery + threading side panel */}
        <div className="w-96 border-l bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 overflow-y-auto">
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Discovery overlays</h3>
                <p className="text-xs text-muted-foreground">Branching reasons & impact</p>
              </div>
              <Button size="sm" variant="outline" onClick={() => setShowDiscoveries((v) => !v)}>
                {showDiscoveries ? "Hide" : "Show"}
              </Button>
            </div>

            {showDiscoveries && (
              <div className="space-y-3">
                {discoveryEvents.map((d) => (
                  <Card key={d.id}>
                    <CardContent className="p-3 space-y-2">
                      <div className="flex items-center justify-between gap-2">
                        <Badge variant="secondary" className="font-mono text-[10px]">
                          {d.id}
                        </Badge>
                        <Badge>{d.branch}</Badge>
                      </div>
                      <p className="text-sm font-medium">{d.summary}</p>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>Ticket {d.ticketId}</span>
                        <span className="capitalize">{d.type}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">Impact: {d.impact}</p>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            <Separator />

            <div className="space-y-3">
              <div>
                <h3 className="text-sm font-semibold">Ticket threading</h3>
                <p className="text-xs text-muted-foreground">Phase path & linked branches</p>
              </div>
              {ticketThreads.map((t) => (
                <Card key={t.ticketId}>
                  <CardContent className="p-3 space-y-2">
                    <div className="flex items-center justify-between">
                      <Badge variant="outline" className="font-mono text-[11px]">
                        {t.ticketId}
                      </Badge>
                      <Badge variant="secondary">{t.current}</Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">Thread: {t.thread}</p>
                    <div className="flex flex-wrap gap-1">
                      {t.phases.map((p) => (
                        <Badge
                          key={p}
                          variant="outline"
                          className={p === t.current ? "border-primary text-primary" : ""}
                        >
                          {p}
                        </Badge>
                      ))}
                    </div>
                    <Button variant="link" size="sm" className="px-0 text-xs" asChild>
                      <Link href={`/board/${projectId}/${t.ticketId}`}>Open ticket</Link>
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
