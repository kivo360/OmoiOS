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

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  ArrowLeft,
  Bot,
  AlertCircle,
  CheckCircle,
  Clock,
  Loader2,
  Target,
  ArrowUpRight,
  ArrowDownRight,
  GitBranch,
  ExternalLink,
  ZoomIn,
  LayoutGrid,
} from "lucide-react"

interface TicketGraphPageProps {
  params: Promise<{ projectId: string; ticketId: string }>
}

// Mock ticket data - focused view on a specific ticket's dependencies
const mockFocusTicket = {
  id: "TICKET-005",
  title: "Add password reset flow",
  status: "pending",
  priority: "low",
  assignee: null,
  description: "Implement a secure password reset flow with email verification",
}

// Tickets that block the focus ticket (upstream)
const mockBlockers = [
  {
    id: "TICKET-002",
    title: "Implement JWT token validation",
    status: "in_progress",
    priority: "high",
    assignee: "worker-1",
    depth: 1,
  },
  {
    id: "TICKET-003",
    title: "Add OAuth2 providers",
    status: "pending",
    priority: "medium",
    assignee: null,
    depth: 1,
  },
  {
    id: "TICKET-001",
    title: "Setup authentication flow",
    status: "in_progress",
    priority: "high",
    assignee: "worker-1",
    depth: 2,
  },
]

// Tickets blocked by the focus ticket (downstream)
const mockBlocked = [
  {
    id: "TICKET-010",
    title: "Integration tests",
    status: "blocked",
    priority: "high",
    assignee: null,
    depth: 1,
  },
  {
    id: "TICKET-012",
    title: "Security audit",
    status: "pending",
    priority: "high",
    assignee: null,
    depth: 2,
  },
]

// All related tickets including focus
const allTickets = [
  { ...mockFocusTicket, blockedBy: ["TICKET-002", "TICKET-003"] },
  { ...mockBlockers[0], blockedBy: ["TICKET-001"] },
  { ...mockBlockers[1], blockedBy: ["TICKET-001"] },
  { ...mockBlockers[2], blockedBy: [] },
  { ...mockBlocked[0], blockedBy: ["TICKET-005", "TICKET-007"] },
  { ...mockBlocked[1], blockedBy: ["TICKET-010"] },
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

interface TicketNodeData {
  id: string
  title: string
  status: string
  priority: string
  assignee: string | null
  blockedBy: string[]
  isFocus: boolean
  [key: string]: unknown
}

function TicketNode({ data, selected }: NodeProps) {
  const nodeData = data as TicketNodeData
  const status = statusConfig[nodeData.status as keyof typeof statusConfig]
  const StatusIcon = status.icon
  const priorityColor = priorityColors[nodeData.priority as keyof typeof priorityColors]
  const isFocus = nodeData.isFocus

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className={`group cursor-pointer rounded-lg border-2 bg-background p-3 shadow-sm transition-all hover:shadow-md ${
              isFocus
                ? "border-primary ring-2 ring-primary/30"
                : selected
                ? "border-primary ring-2 ring-primary/20"
                : "border-border"
            }`}
            style={{
              minWidth: isFocus ? 220 : 180,
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
                  <Badge
                    variant={isFocus ? "default" : "outline"}
                    className="font-mono text-[10px] px-1 py-0"
                  >
                    {nodeData.id}
                  </Badge>
                  {isFocus && (
                    <Badge variant="secondary" className="text-[10px] px-1 py-0">
                      <Target className="mr-0.5 h-2.5 w-2.5" />
                      Focus
                    </Badge>
                  )}
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
                <p
                  className={`text-xs font-medium leading-tight line-clamp-2 ${
                    isFocus ? "text-sm" : ""
                  }`}
                >
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
            {isFocus && (
              <p className="text-xs text-muted-foreground">This is the focus ticket</p>
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

function getLayoutedElements(nodes: Node[], edges: Edge[], direction: "TB" | "LR" = "TB") {
  const dagreGraph = new dagre.graphlib.Graph()
  dagreGraph.setDefaultEdgeLabel(() => ({}))

  const nodeWidth = 200
  const nodeHeight = 80

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 60,
    ranksep: 100,
    marginx: 40,
    marginy: 40,
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

function ticketsToFlowElements(tickets: typeof allTickets, focusId: string) {
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
      isFocus: ticket.id === focusId,
    },
  }))

  const edges: Edge[] = []
  tickets.forEach((ticket) => {
    ticket.blockedBy.forEach((blockerId) => {
      if (tickets.find((t) => t.id === blockerId)) {
        const isToFocus = ticket.id === focusId
        const isFromFocus = blockerId === focusId
        edges.push({
          id: `${blockerId}-${ticket.id}`,
          source: blockerId,
          target: ticket.id,
          type: "smoothstep",
          animated: ticket.status === "blocked" || isToFocus || isFromFocus,
          style: {
            stroke: isToFocus || isFromFocus ? "#3b82f6" : ticket.status === "blocked" ? "#ef4444" : "#9ca3af",
            strokeWidth: isToFocus || isFromFocus ? 3 : 2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: isToFocus || isFromFocus ? "#3b82f6" : ticket.status === "blocked" ? "#ef4444" : "#9ca3af",
          },
        })
      }
    })
  })

  return getLayoutedElements(nodes, edges, "TB")
}

export default function TicketGraphPage({ params }: TicketGraphPageProps) {
  const { projectId, ticketId } = use(params)
  const [direction, setDirection] = useState<"TB" | "LR">("TB")

  const { nodes: initialNodes, edges: initialEdges } = useMemo(
    () => ticketsToFlowElements(allTickets, ticketId),
    [ticketId]
  )

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

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

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (node.id !== ticketId) {
        window.location.href = `/board/${projectId}/${node.id}`
      }
    },
    [projectId, ticketId]
  )

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Sidebar */}
      <div className="w-80 border-r bg-background flex flex-col">
        <div className="p-4 border-b">
          <Link
            href={`/board/${projectId}/${ticketId}`}
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-3"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Ticket
          </Link>
          <h1 className="text-lg font-bold">Dependency Graph</h1>
          <p className="text-sm text-muted-foreground">
            Viewing dependencies for {ticketId}
          </p>
        </div>

        <ScrollArea className="flex-1 p-4">
          {/* Focus Ticket */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <Target className="h-4 w-4 text-primary" />
              <h2 className="text-sm font-medium">Focus Ticket</h2>
            </div>
            <Card className="border-primary/50">
              <CardContent className="p-3">
                <Badge variant="default" className="font-mono text-xs mb-2">
                  {mockFocusTicket.id}
                </Badge>
                <p className="text-sm font-medium">{mockFocusTicket.title}</p>
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <Badge variant="outline" className="text-xs">
                    {statusConfig[mockFocusTicket.status as keyof typeof statusConfig].label}
                  </Badge>
                  <span className="capitalize">{mockFocusTicket.priority}</span>
                </div>
              </CardContent>
            </Card>
          </div>

          <Separator className="mb-4" />

          {/* Blockers (Upstream) */}
          <div className="mb-6">
            <div className="flex items-center gap-2 mb-2">
              <ArrowDownRight className="h-4 w-4 text-orange-500" />
              <h2 className="text-sm font-medium">
                Blocked By ({mockBlockers.length})
              </h2>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              These tickets must be completed first
            </p>
            <div className="space-y-2">
              {mockBlockers.map((ticket) => {
                const status = statusConfig[ticket.status as keyof typeof statusConfig]
                const StatusIcon = status.icon
                return (
                  <Card
                    key={ticket.id}
                    className="cursor-pointer hover:border-primary/50 transition-colors"
                    onClick={() => (window.location.href = `/board/${projectId}/${ticket.id}`)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-1.5 mb-1">
                            <Badge variant="outline" className="font-mono text-[10px]">
                              {ticket.id}
                            </Badge>
                            <div
                              className="flex h-4 w-4 items-center justify-center rounded-full"
                              style={{ backgroundColor: status.bgColor }}
                            >
                              <StatusIcon
                                className={`h-2.5 w-2.5 ${
                                  ticket.status === "in_progress" ? "animate-spin" : ""
                                }`}
                                style={{ color: status.color }}
                              />
                            </div>
                            {ticket.depth > 1 && (
                              <span className="text-[10px] text-muted-foreground">
                                (depth {ticket.depth})
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-medium">{ticket.title}</p>
                        </div>
                        <ExternalLink className="h-3 w-3 text-muted-foreground" />
                      </div>
                      {ticket.assignee && (
                        <div className="flex items-center gap-1 mt-2 text-[10px] text-muted-foreground">
                          <Bot className="h-3 w-3" />
                          <span>{ticket.assignee}</span>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>

          <Separator className="mb-4" />

          {/* Blocked (Downstream) */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <ArrowUpRight className="h-4 w-4 text-red-500" />
              <h2 className="text-sm font-medium">
                Blocking ({mockBlocked.length})
              </h2>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              These tickets are waiting on this ticket
            </p>
            <div className="space-y-2">
              {mockBlocked.map((ticket) => {
                const status = statusConfig[ticket.status as keyof typeof statusConfig]
                const StatusIcon = status.icon
                return (
                  <Card
                    key={ticket.id}
                    className="cursor-pointer hover:border-primary/50 transition-colors"
                    onClick={() => (window.location.href = `/board/${projectId}/${ticket.id}`)}
                  >
                    <CardContent className="p-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="flex items-center gap-1.5 mb-1">
                            <Badge variant="outline" className="font-mono text-[10px]">
                              {ticket.id}
                            </Badge>
                            <div
                              className="flex h-4 w-4 items-center justify-center rounded-full"
                              style={{ backgroundColor: status.bgColor }}
                            >
                              <StatusIcon className="h-2.5 w-2.5" style={{ color: status.color }} />
                            </div>
                            {ticket.depth > 1 && (
                              <span className="text-[10px] text-muted-foreground">
                                (depth {ticket.depth})
                              </span>
                            )}
                          </div>
                          <p className="text-xs font-medium">{ticket.title}</p>
                        </div>
                        <ExternalLink className="h-3 w-3 text-muted-foreground" />
                      </div>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          </div>
        </ScrollArea>

        {/* Actions */}
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="flex-1" onClick={() => onLayout("TB")}>
              <LayoutGrid className="mr-2 h-4 w-4" />
              Vertical
            </Button>
            <Button variant="outline" size="sm" className="flex-1" onClick={() => onLayout("LR")}>
              <LayoutGrid className="mr-2 h-4 w-4 rotate-90" />
              Horizontal
            </Button>
          </div>
          <Button variant="default" className="w-full mt-2" asChild>
            <Link href={`/graph/${projectId}`}>
              <ZoomIn className="mr-2 h-4 w-4" />
              View Full Graph
            </Link>
          </Button>
        </div>
      </div>

      {/* Graph Area */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          minZoom={0.3}
          maxZoom={2}
        >
          <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
          <Controls showInteractive={false} />

          <Panel position="top-right" className="!m-4">
            <Card className="bg-background/95 backdrop-blur">
              <CardContent className="p-3">
                <p className="text-xs font-medium text-muted-foreground mb-2">Legend</p>
                <div className="space-y-1.5 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="h-0.5 w-6 bg-blue-500" />
                    <span>Direct dependency</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-0.5 w-6 bg-red-500" />
                    <span>Blocking (ticket blocked)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-0.5 w-6 bg-gray-400" />
                    <span>Other dependencies</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Panel>
        </ReactFlow>
      </div>
    </div>
  )
}
