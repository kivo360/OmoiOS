"use client"

import { use, useState, useMemo } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Textarea } from "@/components/ui/textarea"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
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
  ArrowLeft,
  FileText,
  MessageSquare,
  ListTodo,
  GitCommit,
  Network,
  Brain,
  MoreHorizontal,
  Edit,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Bot,
  GitBranch,
  ExternalLink,
  Loader2,
  Send,
  Plus,
  Link as LinkIcon,
  ArrowRight,
  Lightbulb,
  AlertTriangle,
  Zap,
} from "lucide-react"
import { Markdown } from "@/components/ui/markdown"
import { useTicket, useTicketContext, useTransitionTicket } from "@/hooks/useTickets"
import { useTicketCommits } from "@/hooks/useCommits"
import { useTasks } from "@/hooks/useTasks"

interface TicketDetailPageProps {
  params: Promise<{ projectId: string; ticketId: string }>
}

// Config for status badges and icons

const statusConfig = {
  pending: { label: "Pending", color: "secondary", icon: Clock },
  in_progress: { label: "In Progress", color: "default", icon: Loader2 },
  completed: { label: "Completed", color: "outline", icon: CheckCircle },
  blocked: { label: "Blocked", color: "destructive", icon: AlertCircle },
}

const priorityConfig = {
  CRITICAL: { label: "Critical", color: "destructive" },
  HIGH: { label: "High", color: "destructive" },
  MEDIUM: { label: "Medium", color: "secondary" },
  LOW: { label: "Low", color: "secondary" },
}

const phaseConfig = {
  BACKLOG: "Backlog",
  REQUIREMENTS: "Requirements",
  IMPLEMENTATION: "Implementation",
  INTEGRATION: "Integration",
  DONE: "Done",
}

const eventTypeConfig = {
  ticket_created: { icon: Plus, color: "text-blue-500", bg: "bg-blue-100" },
  discovery: { icon: Lightbulb, color: "text-yellow-500", bg: "bg-yellow-100" },
  task_spawned: { icon: Zap, color: "text-purple-500", bg: "bg-purple-100" },
  blocking_added: { icon: AlertTriangle, color: "text-orange-500", bg: "bg-orange-100" },
  agent_decision: { icon: Brain, color: "text-green-500", bg: "bg-green-100" },
}

export default function TicketDetailPage({ params }: TicketDetailPageProps) {
  const { projectId, ticketId } = use(params)
  const [activeTab, setActiveTab] = useState("details")
  const [newComment, setNewComment] = useState("")

  // Fetch ticket data
  const { data: ticket, isLoading: ticketLoading, error: ticketError } = useTicket(ticketId)
  const { data: ticketContext } = useTicketContext(ticketId)
  const { data: commitsData } = useTicketCommits(ticketId)
  const { data: allTasks } = useTasks()

  // Filter tasks for this ticket
  const ticketTasks = useMemo(() => {
    if (!allTasks) return []
    return allTasks.filter((task) => task.ticket_id === ticketId)
  }, [allTasks, ticketId])

  const commits = commitsData?.commits ?? []

  const formatTimeAgo = (dateStr: string | Date | null | undefined) => {
    if (!dateStr) return "N/A"
    const date = typeof dateStr === "string" ? new Date(dateStr) : dateStr
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / (1000 * 60))
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  const formatDate = (dateStr: string | Date | null | undefined) => {
    if (!dateStr) return "N/A"
    const date = typeof dateStr === "string" ? new Date(dateStr) : dateStr
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  // Loading state
  if (ticketLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
        <div className="flex flex-1 flex-col p-6 space-y-4">
          <Skeleton className="h-8 w-1/3" />
          <Skeleton className="h-4 w-1/4" />
          <Skeleton className="h-64 w-full" />
        </div>
      </div>
    )
  }

  // Error state
  if (ticketError || !ticket) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
          <h2 className="text-xl font-semibold mb-2">Ticket Not Found</h2>
          <p className="text-muted-foreground mb-4">
            The ticket you&apos;re looking for doesn&apos;t exist or you don&apos;t have access to it.
          </p>
          <Button asChild>
            <Link href={`/board/${projectId}`}>Back to Board</Link>
          </Button>
        </div>
      </div>
    )
  }

  const ticketStatus = ticket.status?.toLowerCase() || "pending"
  const StatusIcon = statusConfig[ticketStatus as keyof typeof statusConfig]?.icon || Clock

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <div className="flex-shrink-0 border-b bg-background px-6 py-4">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <Link
                  href={`/board/${projectId}`}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <ArrowLeft className="h-5 w-5" />
                </Link>
                <Badge variant="outline" className="font-mono">
                  {ticket.id.slice(0, 8)}
                </Badge>
                <h1 className="text-xl font-semibold">{ticket.title}</h1>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Badge variant={statusConfig[ticketStatus as keyof typeof statusConfig]?.color as any || "secondary"}>
                  <StatusIcon
                    className={`mr-1 h-3 w-3 ${
                      ticketStatus === "in_progress" || ticketStatus === "building" ? "animate-spin" : ""
                    }`}
                  />
                  {statusConfig[ticketStatus as keyof typeof statusConfig]?.label || ticket.status}
                </Badge>
                <Badge variant="outline">{ticket.phase_id}</Badge>
                <Badge variant={priorityConfig[ticket.priority as keyof typeof priorityConfig]?.color as any || "secondary"}>
                  {priorityConfig[ticket.priority as keyof typeof priorityConfig]?.label || ticket.priority}
                </Badge>
                <span className="text-muted-foreground">
                  Created {formatTimeAgo(ticket.created_at)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Select defaultValue={ticket.phase_id}>
                <SelectTrigger className="w-40">
                  <SelectValue placeholder="Move to..." />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(phaseConfig).map(([key, label]) => (
                    <SelectItem key={key} value={key}>
                      {label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem>
                    <Edit className="mr-2 h-4 w-4" />
                    Edit
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <LinkIcon className="mr-2 h-4 w-4" />
                    Link Spec
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <Network className="mr-2 h-4 w-4" />
                    Add Blocker
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-destructive">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-shrink-0 border-b bg-background px-6">
            <TabsList className="h-12 w-full justify-start rounded-none border-0 bg-transparent p-0">
              <TabsTrigger
                value="details"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <FileText className="mr-2 h-4 w-4" />
                Details
              </TabsTrigger>
              <TabsTrigger
                value="comments"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <MessageSquare className="mr-2 h-4 w-4" />
                Comments
              </TabsTrigger>
              <TabsTrigger
                value="tasks"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <ListTodo className="mr-2 h-4 w-4" />
                Tasks ({ticketTasks.length})
              </TabsTrigger>
              <TabsTrigger
                value="commits"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <GitCommit className="mr-2 h-4 w-4" />
                Commits ({commits.length})
              </TabsTrigger>
              <TabsTrigger
                value="blocking"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <Network className="mr-2 h-4 w-4" />
                Blocking
              </TabsTrigger>
              <TabsTrigger
                value="reasoning"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <Brain className="mr-2 h-4 w-4" />
                Reasoning
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Tab Content */}
          <ScrollArea className="flex-1">
            {/* Details Tab */}
            <TabsContent value="details" className="m-0 p-6">
              <div className="max-w-3xl space-y-6">
                {/* Description */}
                <div>
                  <h2 className="text-lg font-semibold mb-3">Description</h2>
                  <Card>
                    <CardContent className="p-4">
                      {ticket.description ? (
                        <Markdown content={ticket.description} />
                      ) : (
                        <p className="text-muted-foreground">No description provided.</p>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* Context Summary (if available) */}
                {ticketContext?.summary && (
                  <div>
                    <h2 className="text-lg font-semibold mb-3">Context Summary</h2>
                    <Card>
                      <CardContent className="p-4">
                        <p className="text-sm">{ticketContext.summary}</p>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* Metadata */}
                <div>
                  <h2 className="text-lg font-semibold mb-3">Details</h2>
                  <Card>
                    <CardContent className="p-4">
                      <dl className="grid grid-cols-2 gap-4 text-sm">
                        <div>
                          <dt className="text-muted-foreground">Status</dt>
                          <dd className="font-medium capitalize">{ticket.status}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Priority</dt>
                          <dd>
                            <Badge variant={priorityConfig[ticket.priority as keyof typeof priorityConfig]?.color as any || "secondary"}>
                              {ticket.priority}
                            </Badge>
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Phase</dt>
                          <dd className="font-medium">{ticket.phase_id}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Approval Status</dt>
                          <dd className="font-medium capitalize">{ticket.approval_status || "N/A"}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Created</dt>
                          <dd>{formatDate(ticket.created_at)}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Commits</dt>
                          <dd>{commits.length}</dd>
                        </div>
                      </dl>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </TabsContent>

            {/* Comments Tab */}
            <TabsContent value="comments" className="m-0 p-6">
              <div className="max-w-3xl space-y-6">
                {/* Placeholder for future comments */}
                <Card>
                  <CardContent className="p-6 text-center text-muted-foreground">
                    <MessageSquare className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <p>Comments feature coming soon</p>
                    <p className="text-sm mt-2">Agent discussions and user feedback will appear here.</p>
                  </CardContent>
                </Card>

                {/* New Comment */}
                <div className="flex gap-4">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground">
                      U
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 space-y-2">
                    <Textarea
                      placeholder="Add a comment... (feature coming soon)"
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      className="min-h-[100px]"
                      disabled
                    />
                    <div className="flex justify-end">
                      <Button disabled>
                        <Send className="mr-2 h-4 w-4" />
                        Send
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            </TabsContent>

            {/* Tasks Tab */}
            <TabsContent value="tasks" className="m-0 p-6">
              <div className="max-w-3xl space-y-4">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-muted-foreground">
                    {ticketTasks.filter((t) => t.status === "completed").length} of {ticketTasks.length} tasks completed
                  </p>
                  <Button size="sm">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Task
                  </Button>
                </div>

                {ticketTasks.length === 0 ? (
                  <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                      <ListTodo className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No tasks yet</p>
                      <p className="text-sm mt-2">Tasks will be created as agents work on this ticket.</p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="space-y-2">
                    {ticketTasks.map((task) => {
                      const taskStatus = task.status?.toLowerCase() || "pending"
                      const config = statusConfig[taskStatus as keyof typeof statusConfig] || statusConfig.pending
                      const TaskIcon = config.icon
                      const hasSandbox = !!task.sandbox_id

                      const cardContent = (
                        <CardContent className="p-4">
                          <div className="flex items-center gap-4">
                            <div
                              className={`flex h-6 w-6 items-center justify-center rounded-full ${
                                taskStatus === "completed"
                                  ? "bg-primary text-primary-foreground"
                                  : taskStatus === "running" || taskStatus === "in_progress"
                                  ? "bg-blue-100 text-blue-600"
                                  : "border-2"
                              }`}
                            >
                              <TaskIcon
                                className={`h-3 w-3 ${
                                  taskStatus === "running" || taskStatus === "in_progress" ? "animate-spin" : ""
                                }`}
                              />
                            </div>
                            <div className="flex-1">
                              <p
                                className={
                                  taskStatus === "completed"
                                    ? "text-muted-foreground line-through"
                                    : "font-medium"
                                }
                              >
                                {task.description || task.task_type}
                              </p>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span className="font-mono">{task.id.slice(0, 8)}</span>
                                {task.assigned_agent_id && (
                                  <>
                                    <span>•</span>
                                    <span className="flex items-center gap-1">
                                      <Bot className="h-3 w-3" />
                                      {task.assigned_agent_id.slice(0, 8)}
                                    </span>
                                  </>
                                )}
                                <span>•</span>
                                <span>{task.task_type}</span>
                              </div>
                            </div>
                            <Badge variant={config.color as any}>{config.label}</Badge>
                            {hasSandbox && (
                              <ArrowRight className="h-4 w-4 text-muted-foreground" />
                            )}
                          </div>
                        </CardContent>
                      )

                      return hasSandbox ? (
                        <Link key={task.id} href={`/sandbox/${task.sandbox_id}`}>
                          <Card className="cursor-pointer transition-colors hover:bg-muted/50">
                            {cardContent}
                          </Card>
                        </Link>
                      ) : (
                        <Card key={task.id} className="opacity-75">
                          {cardContent}
                        </Card>
                      )
                    })}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Commits Tab */}
            <TabsContent value="commits" className="m-0 p-6">
              <div className="max-w-3xl space-y-4">
                <div className="flex items-center justify-between text-sm">
                  <p className="text-muted-foreground">
                    {commits.length} commits •{" "}
                    <span className="font-mono text-green-600">
                      +{commits.reduce((sum, c) => sum + (c.insertions || 0), 0)}
                    </span>
                    {" / "}
                    <span className="font-mono text-red-600">
                      -{commits.reduce((sum, c) => sum + (c.deletions || 0), 0)}
                    </span>
                  </p>
                </div>

                {commits.length === 0 ? (
                  <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                      <GitCommit className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No commits yet</p>
                      <p className="text-sm mt-2">Commits linked to this ticket will appear here.</p>
                    </CardContent>
                  </Card>
                ) : (
                  <div className="space-y-3">
                    {commits.map((commit) => (
                      <Card key={commit.commit_sha}>
                        <CardContent className="p-4">
                          <div className="flex items-start gap-4">
                            <GitBranch className="mt-1 h-5 w-5 text-muted-foreground" />
                            <div className="flex-1 min-w-0">
                              <div className="flex items-start justify-between gap-4">
                                <div>
                                  <p className="font-medium">{commit.commit_message}</p>
                                  <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                                    <code className="font-mono">{commit.commit_sha.slice(0, 12)}</code>
                                    {commit.agent_id && (
                                      <span className="flex items-center gap-1">
                                        <Bot className="h-3 w-3" />
                                        {commit.agent_id.slice(0, 8)}
                                      </span>
                                    )}
                                    <span>{formatTimeAgo(commit.commit_timestamp)}</span>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                  <span className="font-mono text-xs">
                                    <span className="text-green-600">+{commit.insertions || 0}</span>
                                    {" "}
                                    <span className="text-red-600">-{commit.deletions || 0}</span>
                                  </span>
                                  <span className="text-xs text-muted-foreground">
                                    {commit.files_changed || 0} files
                                  </span>
                                </div>
                              </div>
                            </div>
                            <Button variant="outline" size="sm" asChild>
                              <Link href={`/commits/${commit.commit_sha}`}>
                                View Diff
                              </Link>
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </TabsContent>

            {/* Blocking Tab */}
            <TabsContent value="blocking" className="m-0 p-6">
              <div className="max-w-3xl space-y-6">
                {/* Blocked By */}
                <div>
                  <h2 className="text-lg font-semibold mb-3">Blocked By</h2>
                  <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                      <CheckCircle className="h-8 w-8 mx-auto mb-2 text-green-500" />
                      No blockers - this ticket is ready to work on
                    </CardContent>
                  </Card>
                </div>

                {/* Blocking Others */}
                <div>
                  <h2 className="text-lg font-semibold mb-3">Blocking</h2>
                  <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                      This ticket is not blocking any other tickets
                    </CardContent>
                  </Card>
                </div>

                <Button variant="outline" asChild>
                  <Link href={`/graph/${projectId}`}>
                    <Network className="mr-2 h-4 w-4" />
                    View Dependency Graph
                  </Link>
                </Button>
              </div>
            </TabsContent>

            {/* Reasoning Tab */}
            <TabsContent value="reasoning" className="m-0 p-6">
              <div className="max-w-3xl space-y-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Diagnostic Reasoning</h2>
                    <p className="text-sm text-muted-foreground">
                      Timeline of agent decisions and discoveries
                    </p>
                  </div>
                  <Button variant="outline" asChild>
                    <Link href={`/diagnostic/ticket/${ticketId}`}>
                      <ExternalLink className="mr-2 h-4 w-4" />
                      Full View
                    </Link>
                  </Button>
                </div>

                {/* Context from ticket */}
                {ticketContext?.full_context && Object.keys(ticketContext.full_context).length > 0 ? (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Ticket Context</CardTitle>
                      <CardDescription>Aggregated context from agent work</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <pre className="text-xs bg-muted p-3 rounded-md overflow-auto">
                        {JSON.stringify(ticketContext.full_context, null, 2)}
                      </pre>
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                      <Brain className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No diagnostic events yet</p>
                      <p className="text-sm mt-2">
                        Agent decisions and discoveries will appear here as they work on this ticket.
                      </p>
                    </CardContent>
                  </Card>
                )}
              </div>
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </div>

      {/* Right Sidebar - Quick Info */}
      <div className="hidden w-72 flex-shrink-0 border-l bg-muted/30 xl:block">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-6">
            {/* Status */}
            <div>
              <h3 className="text-sm font-medium mb-3">Status</h3>
              <Card>
                <CardContent className="p-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <StatusIcon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium capitalize">{ticket.status}</p>
                      <p className="text-xs text-muted-foreground">{ticket.phase_id}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <Separator />

            {/* Progress */}
            <div>
              <h3 className="text-sm font-medium mb-3">Progress</h3>
              <div className="space-y-3">
                <div>
                  <div className="flex items-center justify-between text-sm mb-1">
                    <span className="text-muted-foreground">Tasks</span>
                    <span>
                      {ticketTasks.filter((t) => t.status === "completed").length}/{ticketTasks.length || 0}
                    </span>
                  </div>
                  <Progress
                    value={
                      ticketTasks.length > 0
                        ? (ticketTasks.filter((t) => t.status === "completed").length / ticketTasks.length) * 100
                        : 0
                    }
                    className="h-2"
                  />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Commits</span>
                  <span>{commits.length}</span>
                </div>
              </div>
            </div>

            <Separator />

            {/* Code Changes */}
            <div>
              <h3 className="text-sm font-medium mb-3">Code Changes</h3>
              <div className="text-center">
                <p className="text-2xl font-bold font-mono">
                  <span className="text-green-600">
                    +{commits.reduce((sum, c) => sum + (c.insertions || 0), 0)}
                  </span>
                </p>
                <p className="text-2xl font-bold font-mono">
                  <span className="text-red-600">
                    -{commits.reduce((sum, c) => sum + (c.deletions || 0), 0)}
                  </span>
                </p>
              </div>
            </div>

            <Separator />

            {/* Ticket Info */}
            <div>
              <h3 className="text-sm font-medium mb-3">Ticket Info</h3>
              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">ID</span>
                  <code className="font-mono text-xs">{ticket.id.slice(0, 8)}</code>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Priority</span>
                  <Badge variant="secondary" className="text-xs">{ticket.priority}</Badge>
                </div>
                {ticket.approval_status && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Approval</span>
                    <span className="capitalize">{ticket.approval_status}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
