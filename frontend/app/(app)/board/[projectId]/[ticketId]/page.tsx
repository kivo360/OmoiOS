"use client"

import { use, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
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
  Circle,
  ChevronRight,
  Lightbulb,
  AlertTriangle,
  Zap,
} from "lucide-react"

interface TicketDetailPageProps {
  params: Promise<{ projectId: string; ticketId: string }>
}

// Mock ticket data
const mockTicket = {
  id: "TICKET-042",
  title: "Add OAuth2 Authentication",
  description: `Implement OAuth2 authentication with support for Google and GitHub providers.

## Requirements
- Support Google OAuth2 flow
- Support GitHub OAuth2 flow  
- Token refresh mechanism
- Secure token storage in HTTP-only cookies

## Technical Notes
- Use PKCE flow for added security
- Implement CSRF protection
- Add rate limiting for auth endpoints`,
  status: "in_progress",
  phase: "IMPLEMENTATION",
  priority: "HIGH",
  type: "feature",
  createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
  updatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
  linkedSpec: { id: "spec-001", name: "User Authentication System" },
  assignedAgent: "worker-1",
  linesChanged: { added: 2255, removed: 12 },
}

// Mock comments
const mockComments = [
  {
    id: "comment-1",
    author: { name: "You", avatar: "U", isUser: true },
    content: "Let's prioritize Google OAuth first, then GitHub.",
    timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    mentions: [],
  },
  {
    id: "comment-2",
    author: { name: "worker-1", avatar: "W1", isUser: false },
    content: "Understood. I've started with Google OAuth. Found an edge case with token refresh that needs handling. @guardian can you review the approach?",
    timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    mentions: ["guardian"],
  },
  {
    id: "comment-3",
    author: { name: "guardian", avatar: "G", isUser: false },
    content: "The token refresh approach looks good. Make sure to handle the case where the refresh token itself has expired.",
    timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000),
    mentions: [],
  },
]

// Mock tasks
const mockTasks = [
  {
    id: "task-001",
    title: "Setup OAuth2 Configuration",
    status: "completed",
    agent: "worker-1",
    completedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
  },
  {
    id: "task-002",
    title: "Implement Google OAuth Flow",
    status: "completed",
    agent: "worker-1",
    completedAt: new Date(Date.now() - 12 * 60 * 60 * 1000),
  },
  {
    id: "task-003",
    title: "Implement GitHub OAuth Flow",
    status: "in_progress",
    agent: "worker-1",
    completedAt: null,
  },
  {
    id: "task-004",
    title: "Token Refresh Mechanism",
    status: "pending",
    agent: null,
    completedAt: null,
  },
  {
    id: "task-005",
    title: "Write Integration Tests",
    status: "pending",
    agent: null,
    completedAt: null,
  },
]

// Mock commits
const mockCommits = [
  {
    sha: "02979f61095b7d",
    message: "Implement OAuth2 handler with Google provider",
    author: "worker-1",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    changes: { added: 2255, removed: 0, files: 17 },
    pr: { number: 42, status: "open" },
  },
  {
    sha: "a1b2c3d4e5f6",
    message: "Add OAuth2 configuration",
    author: "worker-1",
    timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000),
    changes: { added: 450, removed: 12, files: 3 },
    pr: null,
  },
  {
    sha: "b2c3d4e5f6g7",
    message: "Setup authentication middleware",
    author: "worker-1",
    timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    changes: { added: 180, removed: 0, files: 2 },
    pr: null,
  },
]

// Mock blocking relationships
const mockBlocking = {
  blockedBy: [
    {
      id: "TICKET-038",
      title: "Setup Database Migrations",
      status: "completed",
      reason: "Auth tables need to be created first",
    },
  ],
  blocking: [
    {
      id: "TICKET-045",
      title: "User Profile Management",
      status: "pending",
      reason: "Requires user authentication to be in place",
    },
    {
      id: "TICKET-048",
      title: "API Rate Limiting",
      status: "pending",
      reason: "Rate limiting depends on authenticated user context",
    },
  ],
}

// Mock reasoning/diagnostic events
const mockReasoning = [
  {
    id: "event-1",
    type: "ticket_created",
    timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
    title: "Ticket Created",
    description: "Created from spec requirement REQ-001: OAuth2 Support",
    details: {
      sourceSpec: "spec-001",
      sourceRequirement: "REQ-001",
      createdBy: "system",
    },
  },
  {
    id: "event-2",
    type: "discovery",
    timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    title: "Discovery: Database Dependency",
    description: "Agent discovered that auth tables must exist before implementing OAuth",
    details: {
      discoveryType: "dependency",
      agent: "worker-1",
      evidence: "Failed to create OAuth provider record - table 'oauth_providers' does not exist",
      action: "Linked to TICKET-038 as blocker",
    },
  },
  {
    id: "event-3",
    type: "task_spawned",
    timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    title: "Tasks Auto-Generated",
    description: "5 implementation tasks created from ticket requirements",
    details: {
      tasksCreated: 5,
      agent: "system",
      reasoning: "Analyzed ticket description and spec requirements to decompose into actionable tasks",
    },
  },
  {
    id: "event-4",
    type: "blocking_added",
    timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    title: "Blocking Relationship Added",
    description: "TICKET-045 now blocked by this ticket",
    details: {
      blockedTicket: "TICKET-045",
      reason: "User Profile Management requires authentication to be complete",
      agent: "worker-1",
      reasoning: "Profile endpoints need authenticated user context which depends on OAuth implementation",
    },
  },
  {
    id: "event-5",
    type: "agent_decision",
    timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000),
    title: "Agent Decision: Implementation Order",
    description: "Decided to implement Google OAuth before GitHub",
    details: {
      agent: "worker-1",
      reasoning: "Google OAuth has more comprehensive documentation and larger user base. Starting with Google allows establishing patterns that GitHub implementation can follow.",
      alternatives: ["Implement both in parallel", "Start with GitHub"],
    },
  },
]

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

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / (1000 * 60))
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  const StatusIcon = statusConfig[mockTicket.status as keyof typeof statusConfig].icon

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
                  {mockTicket.id}
                </Badge>
                <h1 className="text-xl font-semibold">{mockTicket.title}</h1>
              </div>
              <div className="flex items-center gap-3 text-sm">
                <Badge variant={statusConfig[mockTicket.status as keyof typeof statusConfig].color as any}>
                  <StatusIcon
                    className={`mr-1 h-3 w-3 ${
                      mockTicket.status === "in_progress" ? "animate-spin" : ""
                    }`}
                  />
                  {statusConfig[mockTicket.status as keyof typeof statusConfig].label}
                </Badge>
                <Badge variant="outline">{mockTicket.phase}</Badge>
                <Badge variant={priorityConfig[mockTicket.priority as keyof typeof priorityConfig].color as any}>
                  {priorityConfig[mockTicket.priority as keyof typeof priorityConfig].label}
                </Badge>
                <span className="text-muted-foreground">
                  Updated {formatTimeAgo(mockTicket.updatedAt)}
                </span>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Select defaultValue={mockTicket.phase}>
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
                Comments ({mockComments.length})
              </TabsTrigger>
              <TabsTrigger
                value="tasks"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <ListTodo className="mr-2 h-4 w-4" />
                Tasks ({mockTasks.length})
              </TabsTrigger>
              <TabsTrigger
                value="commits"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <GitCommit className="mr-2 h-4 w-4" />
                Commits ({mockCommits.length})
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
                      <div className="prose prose-sm max-w-none dark:prose-invert">
                        <pre className="whitespace-pre-wrap font-sans text-sm">
                          {mockTicket.description}
                        </pre>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Linked Spec */}
                {mockTicket.linkedSpec && (
                  <div>
                    <h2 className="text-lg font-semibold mb-3">Linked Specification</h2>
                    <Card>
                      <CardContent className="p-4">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <FileText className="h-5 w-5 text-muted-foreground" />
                            <div>
                              <p className="font-medium">{mockTicket.linkedSpec.name}</p>
                              <p className="text-sm text-muted-foreground">
                                {mockTicket.linkedSpec.id}
                              </p>
                            </div>
                          </div>
                          <Button variant="outline" size="sm" asChild>
                            <Link href={`/projects/${projectId}/specs/${mockTicket.linkedSpec.id}`}>
                              View Spec
                            </Link>
                          </Button>
                        </div>
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
                          <dt className="text-muted-foreground">Type</dt>
                          <dd className="font-medium capitalize">{mockTicket.type}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Priority</dt>
                          <dd>
                            <Badge variant={priorityConfig[mockTicket.priority as keyof typeof priorityConfig].color as any}>
                              {mockTicket.priority}
                            </Badge>
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Assigned Agent</dt>
                          <dd className="flex items-center gap-2">
                            <Bot className="h-4 w-4" />
                            <span className="font-medium">{mockTicket.assignedAgent || "Unassigned"}</span>
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Lines Changed</dt>
                          <dd className="font-mono">
                            <span className="text-green-600">+{mockTicket.linesChanged.added}</span>
                            {" / "}
                            <span className="text-red-600">-{mockTicket.linesChanged.removed}</span>
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Created</dt>
                          <dd>{formatDate(mockTicket.createdAt)}</dd>
                        </div>
                        <div>
                          <dt className="text-muted-foreground">Updated</dt>
                          <dd>{formatDate(mockTicket.updatedAt)}</dd>
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
                {/* Comment Thread */}
                <div className="space-y-4">
                  {mockComments.map((comment) => (
                    <div key={comment.id} className="flex gap-4">
                      <Avatar className="h-8 w-8">
                        <AvatarFallback
                          className={
                            comment.author.isUser
                              ? "bg-primary text-primary-foreground"
                              : "bg-muted"
                          }
                        >
                          {comment.author.avatar}
                        </AvatarFallback>
                      </Avatar>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className="font-medium">{comment.author.name}</span>
                          {!comment.author.isUser && (
                            <Badge variant="outline" className="text-xs">
                              <Bot className="mr-1 h-3 w-3" />
                              Agent
                            </Badge>
                          )}
                          <span className="text-sm text-muted-foreground">
                            {formatTimeAgo(comment.timestamp)}
                          </span>
                        </div>
                        <Card className="mt-2">
                          <CardContent className="p-3 text-sm">
                            {comment.content}
                          </CardContent>
                        </Card>
                      </div>
                    </div>
                  ))}
                </div>

                {/* New Comment */}
                <div className="flex gap-4">
                  <Avatar className="h-8 w-8">
                    <AvatarFallback className="bg-primary text-primary-foreground">
                      U
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 space-y-2">
                    <Textarea
                      placeholder="Add a comment... Use @mention to notify agents"
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      className="min-h-[100px]"
                    />
                    <div className="flex justify-end">
                      <Button disabled={!newComment.trim()}>
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
                    {mockTasks.filter((t) => t.status === "completed").length} of {mockTasks.length} tasks completed
                  </p>
                  <Button size="sm">
                    <Plus className="mr-2 h-4 w-4" />
                    Add Task
                  </Button>
                </div>

                <div className="space-y-2">
                  {mockTasks.map((task) => {
                    const config = statusConfig[task.status as keyof typeof statusConfig]
                    const TaskIcon = config.icon

                    return (
                      <Card key={task.id}>
                        <CardContent className="p-4">
                          <div className="flex items-center gap-4">
                            <div
                              className={`flex h-6 w-6 items-center justify-center rounded-full ${
                                task.status === "completed"
                                  ? "bg-primary text-primary-foreground"
                                  : task.status === "in_progress"
                                  ? "bg-blue-100 text-blue-600"
                                  : "border-2"
                              }`}
                            >
                              <TaskIcon
                                className={`h-3 w-3 ${
                                  task.status === "in_progress" ? "animate-spin" : ""
                                }`}
                              />
                            </div>
                            <div className="flex-1">
                              <p
                                className={
                                  task.status === "completed"
                                    ? "text-muted-foreground line-through"
                                    : "font-medium"
                                }
                              >
                                {task.title}
                              </p>
                              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                                <span className="font-mono">{task.id}</span>
                                {task.agent && (
                                  <>
                                    <span>•</span>
                                    <span className="flex items-center gap-1">
                                      <Bot className="h-3 w-3" />
                                      {task.agent}
                                    </span>
                                  </>
                                )}
                                {task.completedAt && (
                                  <>
                                    <span>•</span>
                                    <span>{formatTimeAgo(task.completedAt)}</span>
                                  </>
                                )}
                              </div>
                            </div>
                            <Badge variant={config.color as any}>{config.label}</Badge>
                          </div>
                        </CardContent>
                      </Card>
                    )
                  })}
                </div>
              </div>
            </TabsContent>

            {/* Commits Tab */}
            <TabsContent value="commits" className="m-0 p-6">
              <div className="max-w-3xl space-y-4">
                <div className="flex items-center justify-between text-sm">
                  <p className="text-muted-foreground">
                    {mockCommits.length} commits •{" "}
                    <span className="font-mono text-green-600">
                      +{mockCommits.reduce((sum, c) => sum + c.changes.added, 0)}
                    </span>
                    {" / "}
                    <span className="font-mono text-red-600">
                      -{mockCommits.reduce((sum, c) => sum + c.changes.removed, 0)}
                    </span>
                  </p>
                </div>

                <div className="space-y-3">
                  {mockCommits.map((commit) => (
                    <Card key={commit.sha}>
                      <CardContent className="p-4">
                        <div className="flex items-start gap-4">
                          <GitBranch className="mt-1 h-5 w-5 text-muted-foreground" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-4">
                              <div>
                                <p className="font-medium">{commit.message}</p>
                                <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                                  <code className="font-mono">{commit.sha}</code>
                                  <span className="flex items-center gap-1">
                                    <Bot className="h-3 w-3" />
                                    {commit.author}
                                  </span>
                                  <span>{formatTimeAgo(commit.timestamp)}</span>
                                </div>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <span className="font-mono text-xs">
                                  <span className="text-green-600">+{commit.changes.added}</span>
                                  {" "}
                                  <span className="text-red-600">-{commit.changes.removed}</span>
                                </span>
                                <span className="text-xs text-muted-foreground">
                                  {commit.changes.files} files
                                </span>
                              </div>
                            </div>
                            {commit.pr && (
                              <div className="mt-2">
                                <Badge variant="outline" className="text-xs">
                                  <GitBranch className="mr-1 h-3 w-3" />
                                  PR #{commit.pr.number} • {commit.pr.status}
                                </Badge>
                              </div>
                            )}
                          </div>
                          <Button variant="outline" size="sm">
                            View Diff
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            </TabsContent>

            {/* Blocking Tab */}
            <TabsContent value="blocking" className="m-0 p-6">
              <div className="max-w-3xl space-y-6">
                {/* Blocked By */}
                <div>
                  <h2 className="text-lg font-semibold mb-3">Blocked By</h2>
                  {mockBlocking.blockedBy.length > 0 ? (
                    <div className="space-y-2">
                      {mockBlocking.blockedBy.map((ticket) => (
                        <Card key={ticket.id}>
                          <CardContent className="p-4">
                            <div className="flex items-center gap-4">
                              <div
                                className={`flex h-8 w-8 items-center justify-center rounded-full ${
                                  ticket.status === "completed"
                                    ? "bg-green-100 text-green-600"
                                    : "bg-red-100 text-red-600"
                                }`}
                              >
                                {ticket.status === "completed" ? (
                                  <CheckCircle className="h-4 w-4" />
                                ) : (
                                  <AlertCircle className="h-4 w-4" />
                                )}
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className="font-mono">
                                    {ticket.id}
                                  </Badge>
                                  <span className="font-medium">{ticket.title}</span>
                                </div>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  {ticket.reason}
                                </p>
                              </div>
                              <Badge
                                variant={ticket.status === "completed" ? "outline" : "destructive"}
                              >
                                {ticket.status === "completed" ? "Resolved" : "Blocking"}
                              </Badge>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <Card>
                      <CardContent className="p-6 text-center text-muted-foreground">
                        No blockers - this ticket is ready to work on
                      </CardContent>
                    </Card>
                  )}
                </div>

                {/* Blocking Others */}
                <div>
                  <h2 className="text-lg font-semibold mb-3">Blocking</h2>
                  {mockBlocking.blocking.length > 0 ? (
                    <div className="space-y-2">
                      {mockBlocking.blocking.map((ticket) => (
                        <Card key={ticket.id}>
                          <CardContent className="p-4">
                            <div className="flex items-center gap-4">
                              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-orange-100 text-orange-600">
                                <ArrowRight className="h-4 w-4" />
                              </div>
                              <div className="flex-1">
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className="font-mono">
                                    {ticket.id}
                                  </Badge>
                                  <span className="font-medium">{ticket.title}</span>
                                </div>
                                <p className="mt-1 text-sm text-muted-foreground">
                                  {ticket.reason}
                                </p>
                              </div>
                              <Button variant="outline" size="sm">
                                View
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  ) : (
                    <Card>
                      <CardContent className="p-6 text-center text-muted-foreground">
                        This ticket is not blocking any other tickets
                      </CardContent>
                    </Card>
                  )}
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

                {/* Timeline */}
                <div className="relative space-y-0">
                  {mockReasoning.map((event, idx) => {
                    const config = eventTypeConfig[event.type as keyof typeof eventTypeConfig]
                    const EventIcon = config.icon

                    return (
                      <div key={event.id} className="relative pl-8 pb-8">
                        {/* Timeline line */}
                        {idx < mockReasoning.length - 1 && (
                          <div className="absolute left-[15px] top-8 h-full w-px bg-border" />
                        )}

                        {/* Event icon */}
                        <div
                          className={`absolute left-0 flex h-8 w-8 items-center justify-center rounded-full ${config.bg}`}
                        >
                          <EventIcon className={`h-4 w-4 ${config.color}`} />
                        </div>

                        {/* Event content */}
                        <Card>
                          <CardHeader className="pb-2">
                            <div className="flex items-start justify-between">
                              <div>
                                <CardTitle className="text-base">{event.title}</CardTitle>
                                <CardDescription>{event.description}</CardDescription>
                              </div>
                              <span className="text-xs text-muted-foreground">
                                {formatTimeAgo(event.timestamp)}
                              </span>
                            </div>
                          </CardHeader>
                          <CardContent className="pt-0">
                            <div className="rounded-md bg-muted/50 p-3 text-sm">
                              {event.type === "discovery" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">Agent:</span>
                                    <span className="font-medium">{event.details.agent}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Evidence:</span>
                                    <code className="ml-2 text-xs bg-background px-2 py-1 rounded">
                                      {event.details.evidence}
                                    </code>
                                  </div>
                                  <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">Action:</span>
                                    <span>{event.details.action}</span>
                                  </div>
                                </div>
                              )}
                              {event.type === "agent_decision" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">Agent:</span>
                                    <span className="font-medium">{event.details.agent}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Reasoning:</span>
                                    <p className="mt-1">{event.details.reasoning}</p>
                                  </div>
                                  {event.details.alternatives && (
                                    <div>
                                      <span className="text-muted-foreground">Alternatives considered:</span>
                                      <ul className="mt-1 list-disc list-inside text-muted-foreground">
                                        {event.details.alternatives.map((alt: string, i: number) => (
                                          <li key={i}>{alt}</li>
                                        ))}
                                      </ul>
                                    </div>
                                  )}
                                </div>
                              )}
                              {event.type === "blocking_added" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">Blocked Ticket:</span>
                                    <Badge variant="outline" className="font-mono">
                                      {event.details.blockedTicket}
                                    </Badge>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Reason:</span>
                                    <p className="mt-1">{event.details.reason}</p>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Agent reasoning:</span>
                                    <p className="mt-1 italic">{event.details.reasoning}</p>
                                  </div>
                                </div>
                              )}
                              {event.type === "task_spawned" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">Tasks created:</span>
                                    <span className="font-medium">{event.details.tasksCreated}</span>
                                  </div>
                                  <div>
                                    <span className="text-muted-foreground">Reasoning:</span>
                                    <p className="mt-1">{event.details.reasoning}</p>
                                  </div>
                                </div>
                              )}
                              {event.type === "ticket_created" && (
                                <div className="space-y-2">
                                  <div className="flex items-center gap-2">
                                    <span className="text-muted-foreground">Source:</span>
                                    <Badge variant="outline" className="font-mono">
                                      {event.details.sourceSpec} / {event.details.sourceRequirement}
                                    </Badge>
                                  </div>
                                </div>
                              )}
                            </div>
                          </CardContent>
                        </Card>
                      </div>
                    )
                  })}
                </div>
              </div>
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </div>

      {/* Right Sidebar - Quick Info */}
      <div className="hidden w-72 flex-shrink-0 border-l bg-muted/30 xl:block">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-6">
            {/* Assigned Agent */}
            <div>
              <h3 className="text-sm font-medium mb-3">Assigned Agent</h3>
              <Card>
                <CardContent className="p-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                      <Bot className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <p className="font-medium">{mockTicket.assignedAgent}</p>
                      <p className="text-xs text-muted-foreground">Active • 85% aligned</p>
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
                      {mockTasks.filter((t) => t.status === "completed").length}/{mockTasks.length}
                    </span>
                  </div>
                  <Progress
                    value={
                      (mockTasks.filter((t) => t.status === "completed").length /
                        mockTasks.length) *
                      100
                    }
                    className="h-2"
                  />
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Commits</span>
                  <span>{mockCommits.length}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Comments</span>
                  <span>{mockComments.length}</span>
                </div>
              </div>
            </div>

            <Separator />

            {/* Code Changes */}
            <div>
              <h3 className="text-sm font-medium mb-3">Code Changes</h3>
              <div className="text-center">
                <p className="text-2xl font-bold font-mono">
                  <span className="text-green-600">+{mockTicket.linesChanged.added}</span>
                </p>
                <p className="text-2xl font-bold font-mono">
                  <span className="text-red-600">-{mockTicket.linesChanged.removed}</span>
                </p>
              </div>
            </div>

            <Separator />

            {/* Related */}
            <div>
              <h3 className="text-sm font-medium mb-3">Related Tickets</h3>
              <div className="space-y-2">
                {mockBlocking.blocking.slice(0, 3).map((ticket) => (
                  <div key={ticket.id} className="text-sm">
                    <Badge variant="outline" className="font-mono text-xs">
                      {ticket.id}
                    </Badge>
                    <p className="mt-1 text-muted-foreground truncate">{ticket.title}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
