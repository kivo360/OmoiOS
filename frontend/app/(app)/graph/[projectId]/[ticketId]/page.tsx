"use client";

import { use, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
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
} from "@xyflow/react";
import dagre from "dagre";
import "@xyflow/react/dist/style.css";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
  Lightbulb,
} from "lucide-react";
import { useTicketDependencyGraph } from "@/hooks/useGraph";
import { useTicket } from "@/hooks/useTickets";
import type { GraphNode, GraphEdge } from "@/lib/api/types";

interface TicketGraphPageProps {
  params: Promise<{ projectId: string; ticketId: string }>;
}

// Display node type
interface DisplayNode {
  id: string;
  title: string;
  status: string;
  priority: string;
  type: "task" | "discovery" | "ticket";
  assignee: string | null;
  blockedBy: string[];
  isFocus?: boolean;
}

const statusConfig = {
  pending: {
    label: "Pending",
    color: "#9ca3af",
    bgColor: "#f3f4f6",
    icon: Clock,
  },
  in_progress: {
    label: "In Progress",
    color: "#3b82f6",
    bgColor: "#dbeafe",
    icon: Loader2,
  },
  completed: {
    label: "Completed",
    color: "#22c55e",
    bgColor: "#dcfce7",
    icon: CheckCircle,
  },
  blocked: {
    label: "Blocked",
    color: "#ef4444",
    bgColor: "#fee2e2",
    icon: AlertCircle,
  },
};

const priorityColors = {
  critical: "#dc2626",
  high: "#ea580c",
  medium: "#ca8a04",
  low: "#6b7280",
};

interface TicketNodeData {
  id: string;
  title: string;
  status: string;
  priority: string;
  assignee: string | null;
  blockedBy: string[];
  isFocus: boolean;
  [key: string]: unknown;
}

function TicketNode({ data, selected }: NodeProps) {
  const nodeData = data as TicketNodeData;
  const status = statusConfig[nodeData.status as keyof typeof statusConfig];
  const StatusIcon = status.icon;
  const priorityColor =
    priorityColors[nodeData.priority as keyof typeof priorityColors];
  const isFocus = nodeData.isFocus;

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
                    <Badge
                      variant="secondary"
                      className="text-[10px] px-1 py-0"
                    >
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
              <p className="text-xs text-muted-foreground">
                This is the focus ticket
              </p>
            )}
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

const nodeTypes = {
  ticket: TicketNode,
};

function getLayoutedElements(
  nodes: Node[],
  edges: Edge[],
  direction: "TB" | "LR" = "TB",
) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));

  const nodeWidth = 200;
  const nodeHeight = 80;

  dagreGraph.setGraph({
    rankdir: direction,
    nodesep: 60,
    ranksep: 100,
    marginx: 40,
    marginy: 40,
  });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

interface FlowTicket {
  id: string;
  title: string;
  status: string;
  priority: string;
  assignee: string | null;
  blockedBy: string[];
}

function ticketsToFlowElements(tickets: FlowTicket[], focusId: string) {
  const nodes: Node[] = tickets.map((ticket: FlowTicket) => ({
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
  }));

  const edges: Edge[] = [];
  tickets.forEach((ticket: FlowTicket) => {
    ticket.blockedBy.forEach((blockerId: string) => {
      if (tickets.find((t: FlowTicket) => t.id === blockerId)) {
        const isToFocus = ticket.id === focusId;
        const isFromFocus = blockerId === focusId;
        edges.push({
          id: `${blockerId}-${ticket.id}`,
          source: blockerId,
          target: ticket.id,
          type: "smoothstep",
          animated: ticket.status === "blocked" || isToFocus || isFromFocus,
          style: {
            stroke:
              isToFocus || isFromFocus
                ? "#3b82f6"
                : ticket.status === "blocked"
                  ? "#ef4444"
                  : "#9ca3af",
            strokeWidth: isToFocus || isFromFocus ? 3 : 2,
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color:
              isToFocus || isFromFocus
                ? "#3b82f6"
                : ticket.status === "blocked"
                  ? "#ef4444"
                  : "#9ca3af",
          },
        });
      }
    });
  });

  return getLayoutedElements(nodes, edges, "TB");
}

export default function TicketGraphPage({ params }: TicketGraphPageProps) {
  const { projectId, ticketId } = use(params);
  const [direction, setDirection] = useState<"TB" | "LR">("TB");
  const [showDiscoveries, setShowDiscoveries] = useState(true);

  // Fetch real data
  const { data: ticket, isLoading: ticketLoading } = useTicket(ticketId);
  const { data: graphData, isLoading: graphLoading } = useTicketDependencyGraph(
    ticketId,
    {
      includeResolved: true,
      includeDiscoveries: showDiscoveries,
    },
  );

  const isLoading = ticketLoading || graphLoading;

  // Transform API data to display format
  const displayNodes: DisplayNode[] = useMemo(() => {
    if (!graphData?.nodes) return [];
    return graphData.nodes.map((node) => ({
      id: node.id,
      title: node.label || node.description || node.id,
      status: node.status || "pending",
      priority: node.priority || "medium",
      type: node.type,
      assignee: null,
      blockedBy: graphData.edges
        .filter((e) => e.target === node.id)
        .map((e) => e.source),
      isFocus: node.id === ticketId,
    }));
  }, [graphData, ticketId]);

  // Build flow elements from API data
  const { nodes: initialNodes, edges: initialEdges } = useMemo(() => {
    if (displayNodes.length === 0) {
      return { nodes: [], edges: [] };
    }

    // Convert to the format expected by ticketsToFlowElements
    const tickets = displayNodes.map((n) => ({
      id: n.id,
      title: n.title,
      status: n.status,
      priority: n.priority,
      assignee: n.assignee,
      blockedBy: n.blockedBy,
    }));

    return ticketsToFlowElements(tickets, ticketId);
  }, [displayNodes, ticketId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  // Update when data changes
  useEffect(() => {
    if (displayNodes.length > 0) {
      const tickets = displayNodes.map((n) => ({
        id: n.id,
        title: n.title,
        status: n.status,
        priority: n.priority,
        assignee: n.assignee,
        blockedBy: n.blockedBy,
      }));
      const { nodes: newNodes, edges: newEdges } = ticketsToFlowElements(
        tickets,
        ticketId,
      );
      setNodes(newNodes);
      setEdges(newEdges);
    }
  }, [displayNodes, ticketId, setNodes, setEdges]);

  const onLayout = useCallback(
    (newDirection: "TB" | "LR") => {
      setDirection(newDirection);
      const { nodes: layoutedNodes, edges: layoutedEdges } =
        getLayoutedElements(nodes, edges, newDirection);
      setNodes([...layoutedNodes]);
      setEdges([...layoutedEdges]);
    },
    [nodes, edges, setNodes, setEdges],
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      if (node.id !== ticketId) {
        window.location.href = `/board/${projectId}/${node.id}`;
      }
    },
    [projectId, ticketId],
  );

  // Get focus ticket and related nodes
  const focusNode = displayNodes.find((n) => n.id === ticketId);
  const blockerNodes = displayNodes.filter(
    (n) =>
      n.blockedBy.length === 0 &&
      n.id !== ticketId &&
      displayNodes.some((other) => other.blockedBy.includes(n.id)),
  );
  const blockedNodes = displayNodes.filter((n) =>
    n.blockedBy.includes(ticketId),
  );
  const discoveryNodes = displayNodes.filter((n) => n.type === "discovery");

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)]">
        <div className="w-80 border-r bg-background p-4 space-y-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
        <div className="flex-1 flex items-center justify-center">
          <Skeleton className="h-96 w-full max-w-4xl" />
        </div>
      </div>
    );
  }

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
                  {ticket?.id || ticketId}
                </Badge>
                <p className="text-sm font-medium">
                  {ticket?.title || focusNode?.title || ticketId}
                </p>
                <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                  <Badge variant="outline" className="text-xs">
                    {statusConfig[
                      (ticket?.status ||
                        focusNode?.status ||
                        "pending") as keyof typeof statusConfig
                    ]?.label || "Unknown"}
                  </Badge>
                  <span className="capitalize">
                    {ticket?.priority || focusNode?.priority || "medium"}
                  </span>
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
                Blocked By ({focusNode?.blockedBy.length || 0})
              </h2>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              These tasks must be completed first
            </p>
            {focusNode?.blockedBy.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                No blocking dependencies
              </p>
            ) : (
              <div className="space-y-2">
                {displayNodes
                  .filter((n) => focusNode?.blockedBy.includes(n.id))
                  .map((node) => {
                    const status =
                      statusConfig[node.status as keyof typeof statusConfig] ||
                      statusConfig.pending;
                    const StatusIcon = status.icon;
                    return (
                      <Card
                        key={node.id}
                        className="cursor-pointer hover:border-primary/50 transition-colors"
                        onClick={() =>
                          (window.location.href = `/board/${projectId}/${node.id}`)
                        }
                      >
                        <CardContent className="p-3">
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-1.5 mb-1">
                                <Badge
                                  variant="outline"
                                  className="font-mono text-[10px]"
                                >
                                  {node.id.slice(0, 12)}
                                </Badge>
                                <div
                                  className="flex h-4 w-4 items-center justify-center rounded-full"
                                  style={{ backgroundColor: status.bgColor }}
                                >
                                  <StatusIcon
                                    className={`h-2.5 w-2.5 ${
                                      node.status === "in_progress"
                                        ? "animate-spin"
                                        : ""
                                    }`}
                                    style={{ color: status.color }}
                                  />
                                </div>
                                {node.type === "discovery" && (
                                  <Lightbulb className="h-3 w-3 text-yellow-500" />
                                )}
                              </div>
                              <p className="text-xs font-medium">
                                {node.title}
                              </p>
                            </div>
                            <ExternalLink className="h-3 w-3 text-muted-foreground" />
                          </div>
                          {node.assignee && (
                            <div className="flex items-center gap-1 mt-2 text-[10px] text-muted-foreground">
                              <Bot className="h-3 w-3" />
                              <span>{node.assignee}</span>
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    );
                  })}
              </div>
            )}
          </div>

          <Separator className="mb-4" />

          {/* Blocked (Downstream) */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <ArrowUpRight className="h-4 w-4 text-red-500" />
              <h2 className="text-sm font-medium">
                Blocking ({blockedNodes.length})
              </h2>
            </div>
            <p className="text-xs text-muted-foreground mb-3">
              These tasks are waiting on this ticket
            </p>
            {blockedNodes.length === 0 ? (
              <p className="text-xs text-muted-foreground italic">
                No tasks blocked by this ticket
              </p>
            ) : (
              <div className="space-y-2">
                {blockedNodes.map((node) => {
                  const status =
                    statusConfig[node.status as keyof typeof statusConfig] ||
                    statusConfig.pending;
                  const StatusIcon = status.icon;
                  return (
                    <Card
                      key={node.id}
                      className="cursor-pointer hover:border-primary/50 transition-colors"
                      onClick={() =>
                        (window.location.href = `/board/${projectId}/${node.id}`)
                      }
                    >
                      <CardContent className="p-3">
                        <div className="flex items-start justify-between">
                          <div>
                            <div className="flex items-center gap-1.5 mb-1">
                              <Badge
                                variant="outline"
                                className="font-mono text-[10px]"
                              >
                                {node.id.slice(0, 12)}
                              </Badge>
                              <div
                                className="flex h-4 w-4 items-center justify-center rounded-full"
                                style={{ backgroundColor: status.bgColor }}
                              >
                                <StatusIcon
                                  className="h-2.5 w-2.5"
                                  style={{ color: status.color }}
                                />
                              </div>
                              {node.type === "discovery" && (
                                <Lightbulb className="h-3 w-3 text-yellow-500" />
                              )}
                            </div>
                            <p className="text-xs font-medium">{node.title}</p>
                          </div>
                          <ExternalLink className="h-3 w-3 text-muted-foreground" />
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            )}
          </div>
        </ScrollArea>

        {/* Actions */}
        <div className="p-4 border-t">
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => onLayout("TB")}
            >
              <LayoutGrid className="mr-2 h-4 w-4" />
              Vertical
            </Button>
            <Button
              variant="outline"
              size="sm"
              className="flex-1"
              onClick={() => onLayout("LR")}
            >
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

      {/* Graph Area + overlays */}
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
            fitViewOptions={{ padding: 0.3 }}
            minZoom={0.3}
            maxZoom={2}
          >
            <Background variant={BackgroundVariant.Dots} gap={16} size={1} />
            <Controls showInteractive={false} />

            <Panel position="top-right" className="!m-4">
              <Card className="bg-background/95 backdrop-blur">
                <CardContent className="p-3">
                  <p className="text-xs font-medium text-muted-foreground mb-2">
                    Legend
                  </p>
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

        {/* Discovery + threading panel */}
        <div className="w-96 border-l bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80 overflow-y-auto">
          <div className="p-4 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold">Discovery overlays</h3>
                <p className="text-xs text-muted-foreground">
                  Related discoveries
                </p>
              </div>
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowDiscoveries((v) => !v)}
              >
                {showDiscoveries ? "Hide" : "Show"}
              </Button>
            </div>

            {showDiscoveries && (
              <div className="space-y-3">
                {discoveryNodes.length === 0 ? (
                  <p className="text-xs text-muted-foreground italic">
                    No discoveries found
                  </p>
                ) : (
                  discoveryNodes.map((d) => (
                    <Card key={d.id}>
                      <CardContent className="p-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <Badge
                            variant="secondary"
                            className="font-mono text-[10px]"
                          >
                            {d.id.slice(0, 12)}
                          </Badge>
                          <Lightbulb className="h-4 w-4 text-yellow-500" />
                        </div>
                        <p className="text-sm font-medium">{d.title}</p>
                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <span className="capitalize">{d.status}</span>
                          <span className="capitalize">{d.priority}</span>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            )}

            <Separator />

            <div className="space-y-3">
              <div>
                <h3 className="text-sm font-semibold">Graph Summary</h3>
                <p className="text-xs text-muted-foreground">
                  Dependency statistics
                </p>
              </div>
              <Card>
                <CardContent className="p-3 space-y-2">
                  <div className="flex items-center justify-between">
                    <Badge variant="outline" className="font-mono text-[11px]">
                      {ticket?.id || ticketId}
                    </Badge>
                    <Badge variant="secondary">
                      {ticket?.status || focusNode?.status || "pending"}
                    </Badge>
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <p>Total nodes: {displayNodes.length}</p>
                    <p>Blocked by: {focusNode?.blockedBy.length || 0}</p>
                    <p>Blocking: {blockedNodes.length}</p>
                    <p>Discoveries: {discoveryNodes.length}</p>
                  </div>
                  <Button
                    variant="link"
                    size="sm"
                    className="px-0 text-xs"
                    asChild
                  >
                    <Link href={`/board/${projectId}/${ticketId}`}>
                      Open ticket
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
