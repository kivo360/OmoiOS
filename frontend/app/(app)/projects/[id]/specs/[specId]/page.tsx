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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
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
  Palette,
  ListTodo,
  Play,
  MoreHorizontal,
  Download,
  History,
  Settings,
  ChevronDown,
  ChevronRight,
  Plus,
  Edit,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Bot,
  GitBranch,
  ExternalLink,
  Loader2,
  Check,
  X,
  Link as LinkIcon,
} from "lucide-react"

interface SpecPageProps {
  params: Promise<{ id: string; specId: string }>
}

// Mock spec data
const mockSpec = {
  id: "spec-001",
  title: "User Authentication System",
  description: "Implement secure user authentication with OAuth2 and JWT tokens",
  status: "executing",
  phase: "Implementation",
  progress: 75,
  testCoverage: 65,
  activeAgents: 2,
  updatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
  linkedTickets: 5,
}

// Mock requirements (EARS-style)
const mockRequirements = [
  {
    id: "REQ-001",
    title: "OAuth2 Support",
    condition: "User requests authentication via OAuth2 provider",
    action: "Provide OAuth2 authentication flow with Google and GitHub providers",
    criteria: [
      { id: "AC-001", text: "Support Google OAuth", completed: true },
      { id: "AC-002", text: "Support GitHub OAuth", completed: true },
      { id: "AC-003", text: "Token refresh mechanism", completed: false },
      { id: "AC-004", text: "Secure token storage", completed: false },
    ],
    linkedDesign: "DESIGN-001",
    status: "in_progress",
  },
  {
    id: "REQ-002",
    title: "JWT Token Management",
    condition: "User successfully authenticates",
    action: "Create JWT token and return to client with secure storage guidelines",
    criteria: [
      { id: "AC-005", text: "Token includes user ID", completed: true },
      { id: "AC-006", text: "Token expires after 24h", completed: true },
      { id: "AC-007", text: "Token signed with secret", completed: true },
    ],
    linkedDesign: "DESIGN-002",
    status: "completed",
  },
  {
    id: "REQ-003",
    title: "Session Management",
    condition: "User is authenticated",
    action: "Maintain active session with automatic refresh and secure logout",
    criteria: [
      { id: "AC-008", text: "Session persists across page reloads", completed: false },
      { id: "AC-009", text: "Logout invalidates all tokens", completed: false },
      { id: "AC-010", text: "Multi-device session support", completed: false },
    ],
    linkedDesign: null,
    status: "pending",
  },
]

// Mock design elements
const mockDesign = {
  architecture: `
┌─────────────────────────────────────────┐
│           Authentication Service         │
├─────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐          │
│  │  OAuth2   │  │    JWT    │          │
│  │  Handler  │  │ Generator │          │
│  └─────┬─────┘  └─────┬─────┘          │
│        │              │                 │
│        └──────┬───────┘                 │
│               │                         │
│        ┌──────▼──────┐                  │
│        │   Token     │                  │
│        │  Validator  │                  │
│        └─────────────┘                  │
└─────────────────────────────────────────┘
  `,
  dataModel: `
User {
  id: UUID
  email: string
  password_hash: string
  oauth_providers: OAuthProvider[]
  created_at: timestamp
  updated_at: timestamp
}

OAuthProvider {
  provider: "google" | "github"
  provider_user_id: string
  access_token: string
  refresh_token: string
}

Session {
  id: UUID
  user_id: UUID
  token: string
  expires_at: timestamp
  created_at: timestamp
}
  `,
  apiSpec: [
    { method: "POST", endpoint: "/auth/login", description: "Email/password login" },
    { method: "POST", endpoint: "/auth/register", description: "New user registration" },
    { method: "POST", endpoint: "/auth/oauth/:provider", description: "OAuth authentication" },
    { method: "POST", endpoint: "/auth/refresh", description: "Refresh JWT token" },
    { method: "POST", endpoint: "/auth/logout", description: "Logout and invalidate tokens" },
    { method: "GET", endpoint: "/auth/me", description: "Get current user" },
  ],
}

// Mock tasks
const mockTasks = [
  {
    id: "TASK-001",
    title: "Setup OAuth2 Configuration",
    description: "Configure OAuth2 providers (Google, GitHub) with client IDs and secrets",
    phase: "IMPLEMENTATION",
    priority: "HIGH",
    status: "completed",
    assignedAgent: "worker-1",
    dependencies: [],
    estimatedHours: 2,
    actualHours: 1.5,
  },
  {
    id: "TASK-002",
    title: "Implement JWT Generator",
    description: "Create JWT token generation service with proper signing",
    phase: "IMPLEMENTATION",
    priority: "HIGH",
    status: "completed",
    assignedAgent: "worker-1",
    dependencies: ["TASK-001"],
    estimatedHours: 4,
    actualHours: 3,
  },
  {
    id: "TASK-003",
    title: "Build Token Validator",
    description: "Implement token validation middleware",
    phase: "IMPLEMENTATION",
    priority: "HIGH",
    status: "in_progress",
    assignedAgent: "worker-2",
    dependencies: ["TASK-002"],
    estimatedHours: 3,
    actualHours: null,
  },
  {
    id: "TASK-004",
    title: "Write Integration Tests",
    description: "Create comprehensive tests for auth flows",
    phase: "INTEGRATION",
    priority: "MEDIUM",
    status: "pending",
    assignedAgent: null,
    dependencies: ["TASK-002", "TASK-003"],
    estimatedHours: 6,
    actualHours: null,
  },
  {
    id: "TASK-005",
    title: "API Documentation",
    description: "Document all authentication endpoints",
    phase: "DOCUMENTATION",
    priority: "LOW",
    status: "pending",
    assignedAgent: null,
    dependencies: ["TASK-003"],
    estimatedHours: 2,
    actualHours: null,
  },
]

// Mock execution data
const mockExecution = {
  overallProgress: 65,
  testCoverage: 78,
  testsTotal: 50,
  testsPassing: 32,
  activeAgents: 2,
  commits: 12,
  linesChanged: { added: 2450, removed: 120 },
  runningTasks: [
    {
      id: "TASK-003",
      title: "Build Token Validator",
      agent: "worker-2",
      progress: 60,
      startedAt: new Date(Date.now() - 45 * 60 * 1000),
    },
  ],
  recentCommits: [
    {
      sha: "a1b2c3d",
      message: "Implement JWT token generation",
      author: "worker-1",
      timestamp: new Date(Date.now() - 30 * 60 * 1000),
      changes: { added: 450, removed: 12 },
    },
    {
      sha: "e5f6g7h",
      message: "Add OAuth2 provider configuration",
      author: "worker-1",
      timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
      changes: { added: 280, removed: 0 },
    },
  ],
  pullRequests: [
    {
      number: 42,
      title: "feat: Add OAuth2 authentication",
      status: "open",
      author: "worker-1",
      reviewStatus: "pending",
    },
  ],
}

const statusConfig = {
  pending: { label: "Pending", color: "secondary", icon: Clock },
  in_progress: { label: "In Progress", color: "warning", icon: Loader2 },
  completed: { label: "Completed", color: "success", icon: CheckCircle },
}

const priorityConfig = {
  HIGH: { label: "High", color: "destructive" },
  MEDIUM: { label: "Medium", color: "warning" },
  LOW: { label: "Low", color: "secondary" },
}

export default function SpecWorkspacePage({ params }: SpecPageProps) {
  const { id, specId } = use(params)
  const [activeTab, setActiveTab] = useState("requirements")
  const [expandedRequirements, setExpandedRequirements] = useState<string[]>(["REQ-001"])

  const toggleRequirement = (reqId: string) => {
    setExpandedRequirements((prev) =>
      prev.includes(reqId) ? prev.filter((id) => id !== reqId) : [...prev, reqId]
    )
  }

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

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Left Sidebar - Spec Switcher */}
      <div className="hidden w-56 flex-shrink-0 border-r bg-muted/30 lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b p-4">
            <Select defaultValue={specId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select spec" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="spec-001">User Authentication</SelectItem>
                <SelectItem value="spec-002">Payment Processing</SelectItem>
                <SelectItem value="spec-003">API Rate Limiting</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                All Specs
              </p>
              {[
                { id: "spec-001", name: "User Authentication", status: "executing" },
                { id: "spec-002", name: "Payment Processing", status: "design" },
                { id: "spec-003", name: "API Rate Limiting", status: "requirements" },
              ].map((spec) => (
                <Link
                  key={spec.id}
                  href={`/projects/${id}/specs/${spec.id}`}
                  className={`block rounded-md px-3 py-2 text-sm transition-colors ${
                    spec.id === specId
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate">{spec.name}</span>
                    <div
                      className={`h-2 w-2 rounded-full ${
                        spec.status === "executing"
                          ? "bg-primary"
                          : spec.status === "design"
                          ? "bg-warning"
                          : "bg-muted-foreground"
                      }`}
                    />
                  </div>
                </Link>
              ))}
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <div className="flex-shrink-0 border-b bg-background px-6 py-4">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <div className="flex items-center gap-3">
                <Link
                  href={`/projects/${id}/specs`}
                  className="text-muted-foreground hover:text-foreground"
                >
                  <ArrowLeft className="h-5 w-5" />
                </Link>
                <h1 className="text-xl font-semibold">{mockSpec.title}</h1>
                <Badge
                  variant={
                    mockSpec.status === "executing"
                      ? "default"
                      : "secondary"
                  }
                >
                  {mockSpec.phase}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">{mockSpec.description}</p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm">
                <History className="mr-2 h-4 w-4" />
                History
              </Button>
              <Button variant="outline" size="sm">
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuItem>
                    <LinkIcon className="mr-2 h-4 w-4" />
                    Link Tickets
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-destructive">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Archive
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
                value="requirements"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <FileText className="mr-2 h-4 w-4" />
                Requirements
              </TabsTrigger>
              <TabsTrigger
                value="design"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <Palette className="mr-2 h-4 w-4" />
                Design
              </TabsTrigger>
              <TabsTrigger
                value="tasks"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <ListTodo className="mr-2 h-4 w-4" />
                Tasks
              </TabsTrigger>
              <TabsTrigger
                value="execution"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <Play className="mr-2 h-4 w-4" />
                Execution
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Tab Content */}
          <ScrollArea className="flex-1">
            {/* Requirements Tab */}
            <TabsContent value="requirements" className="m-0 p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Requirements</h2>
                    <p className="text-sm text-muted-foreground">
                      EARS-style structured requirements
                    </p>
                  </div>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Requirement
                  </Button>
                </div>

                <div className="space-y-4">
                  {mockRequirements.map((req) => {
                    const isExpanded = expandedRequirements.includes(req.id)
                    const completedCriteria = req.criteria.filter((c) => c.completed).length
                    const config = statusConfig[req.status as keyof typeof statusConfig]

                    return (
                      <Collapsible
                        key={req.id}
                        open={isExpanded}
                        onOpenChange={() => toggleRequirement(req.id)}
                      >
                        <Card className="overflow-hidden">
                          <CollapsibleTrigger asChild>
                            <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                              <div className="flex items-start gap-4">
                                <div className="mt-1">
                                  {isExpanded ? (
                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  ) : (
                                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                  )}
                                </div>
                                <div className="flex-1 space-y-1">
                                  <div className="flex items-center gap-2">
                                    <Badge variant="outline" className="font-mono text-xs">
                                      {req.id}
                                    </Badge>
                                    <CardTitle className="text-base">{req.title}</CardTitle>
                                    <Badge variant={config.color as any} className="ml-auto">
                                      {config.label}
                                    </Badge>
                                  </div>
                                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                    <span>
                                      {completedCriteria}/{req.criteria.length} criteria met
                                    </span>
                                    {req.linkedDesign && (
                                      <span className="flex items-center gap-1">
                                        <LinkIcon className="h-3 w-3" />
                                        {req.linkedDesign}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </CardHeader>
                          </CollapsibleTrigger>
                          <CollapsibleContent>
                            <CardContent className="border-t pt-4">
                              {/* EARS Format */}
                              <div className="space-y-4">
                                <div className="rounded-lg bg-muted/50 p-4 font-mono text-sm">
                                  <p>
                                    <span className="font-semibold text-primary">WHEN</span>{" "}
                                    {req.condition}
                                  </p>
                                  <p className="mt-2">
                                    <span className="font-semibold text-primary">THE SYSTEM SHALL</span>{" "}
                                    {req.action}
                                  </p>
                                </div>

                                {/* Acceptance Criteria */}
                                <div>
                                  <h4 className="text-sm font-medium mb-3">Acceptance Criteria</h4>
                                  <div className="space-y-2">
                                    {req.criteria.map((criterion) => (
                                      <div
                                        key={criterion.id}
                                        className="flex items-center gap-3 rounded-md border p-3"
                                      >
                                        <div
                                          className={`flex h-5 w-5 items-center justify-center rounded-full ${
                                            criterion.completed
                                              ? "bg-primary text-primary-foreground"
                                              : "border-2"
                                          }`}
                                        >
                                          {criterion.completed && <Check className="h-3 w-3" />}
                                        </div>
                                        <span
                                          className={
                                            criterion.completed ? "text-muted-foreground line-through" : ""
                                          }
                                        >
                                          {criterion.text}
                                        </span>
                                        <Badge variant="outline" className="ml-auto font-mono text-xs">
                                          {criterion.id}
                                        </Badge>
                                      </div>
                                    ))}
                                  </div>
                                </div>

                                {/* Actions */}
                                <div className="flex items-center gap-2 pt-2">
                                  <Button variant="outline" size="sm">
                                    <Edit className="mr-2 h-4 w-4" />
                                    Edit
                                  </Button>
                                  <Button variant="outline" size="sm">
                                    <Plus className="mr-2 h-4 w-4" />
                                    Add Criterion
                                  </Button>
                                  {!req.linkedDesign && (
                                    <Button variant="outline" size="sm">
                                      <LinkIcon className="mr-2 h-4 w-4" />
                                      Link Design
                                    </Button>
                                  )}
                                </div>
                              </div>
                            </CardContent>
                          </CollapsibleContent>
                        </Card>
                      </Collapsible>
                    )
                  })}
                </div>

                {/* Approval Actions */}
                <div className="flex items-center justify-end gap-2 pt-4 border-t">
                  <Button variant="outline">Request Changes</Button>
                  <Button>Approve Requirements</Button>
                </div>
              </div>
            </TabsContent>

            {/* Design Tab */}
            <TabsContent value="design" className="m-0 p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Design</h2>
                    <p className="text-sm text-muted-foreground">
                      Architecture diagrams and data models
                    </p>
                  </div>
                  <Button variant="outline">
                    <Edit className="mr-2 h-4 w-4" />
                    Edit Design
                  </Button>
                </div>

                <div className="grid gap-6 lg:grid-cols-2">
                  {/* Architecture Diagram */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Architecture Overview</CardTitle>
                      <CardDescription>Component diagram</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <pre className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-xs">
                        {mockDesign.architecture}
                      </pre>
                    </CardContent>
                  </Card>

                  {/* Data Model */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Data Model</CardTitle>
                      <CardDescription>Entity definitions</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <pre className="overflow-x-auto rounded-lg bg-muted p-4 font-mono text-xs whitespace-pre-wrap">
                        {mockDesign.dataModel}
                      </pre>
                    </CardContent>
                  </Card>
                </div>

                {/* API Specification */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">API Specification</CardTitle>
                    <CardDescription>Endpoint definitions</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {mockDesign.apiSpec.map((endpoint, idx) => (
                        <div
                          key={idx}
                          className="flex items-center gap-4 rounded-md border p-3"
                        >
                          <Badge
                            variant={
                              endpoint.method === "GET"
                                ? "secondary"
                                : endpoint.method === "POST"
                                ? "default"
                                : "outline"
                            }
                            className="w-16 justify-center font-mono"
                          >
                            {endpoint.method}
                          </Badge>
                          <code className="flex-1 font-mono text-sm">{endpoint.endpoint}</code>
                          <span className="text-sm text-muted-foreground">
                            {endpoint.description}
                          </span>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>

                {/* Approval Actions */}
                <div className="flex items-center justify-end gap-2 pt-4 border-t">
                  <Button variant="outline">Request Changes</Button>
                  <Button>Approve Design</Button>
                </div>
              </div>
            </TabsContent>

            {/* Tasks Tab */}
            <TabsContent value="tasks" className="m-0 p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Task Breakdown</h2>
                    <p className="text-sm text-muted-foreground">
                      Implementation tasks with dependencies
                    </p>
                  </div>
                  <Button>
                    <Plus className="mr-2 h-4 w-4" />
                    Add Task
                  </Button>
                </div>

                {/* Tasks Table */}
                <Card>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b bg-muted/50">
                          <th className="px-4 py-3 text-left text-sm font-medium">Task</th>
                          <th className="px-4 py-3 text-left text-sm font-medium">Phase</th>
                          <th className="px-4 py-3 text-left text-sm font-medium">Priority</th>
                          <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                          <th className="px-4 py-3 text-left text-sm font-medium">Agent</th>
                          <th className="px-4 py-3 text-left text-sm font-medium">Dependencies</th>
                          <th className="px-4 py-3 text-left text-sm font-medium">Est.</th>
                          <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {mockTasks.map((task) => {
                          const status = statusConfig[task.status as keyof typeof statusConfig]
                          const priority = priorityConfig[task.priority as keyof typeof priorityConfig]
                          const StatusIcon = status.icon

                          return (
                            <tr key={task.id} className="border-b last:border-0">
                              <td className="px-4 py-3">
                                <div>
                                  <Badge variant="outline" className="font-mono text-xs mb-1">
                                    {task.id}
                                  </Badge>
                                  <p className="font-medium">{task.title}</p>
                                  <p className="text-xs text-muted-foreground line-clamp-1">
                                    {task.description}
                                  </p>
                                </div>
                              </td>
                              <td className="px-4 py-3">
                                <Badge variant="outline">{task.phase}</Badge>
                              </td>
                              <td className="px-4 py-3">
                                <Badge variant={priority.color as any}>{priority.label}</Badge>
                              </td>
                              <td className="px-4 py-3">
                                <Badge variant={status.color as any} className="gap-1">
                                  <StatusIcon
                                    className={`h-3 w-3 ${
                                      task.status === "in_progress" ? "animate-spin" : ""
                                    }`}
                                  />
                                  {status.label}
                                </Badge>
                              </td>
                              <td className="px-4 py-3">
                                {task.assignedAgent ? (
                                  <div className="flex items-center gap-2">
                                    <Bot className="h-4 w-4 text-muted-foreground" />
                                    <span className="text-sm">{task.assignedAgent}</span>
                                  </div>
                                ) : (
                                  <span className="text-sm text-muted-foreground">Unassigned</span>
                                )}
                              </td>
                              <td className="px-4 py-3">
                                {task.dependencies.length > 0 ? (
                                  <div className="flex flex-wrap gap-1">
                                    {task.dependencies.map((dep) => (
                                      <Badge key={dep} variant="outline" className="font-mono text-xs">
                                        {dep}
                                      </Badge>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-sm text-muted-foreground">None</span>
                                )}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                {task.actualHours
                                  ? `${task.actualHours}h / ${task.estimatedHours}h`
                                  : `${task.estimatedHours}h`}
                              </td>
                              <td className="px-4 py-3 text-right">
                                <DropdownMenu>
                                  <DropdownMenuTrigger asChild>
                                    <Button variant="ghost" size="icon">
                                      <MoreHorizontal className="h-4 w-4" />
                                    </Button>
                                  </DropdownMenuTrigger>
                                  <DropdownMenuContent align="end">
                                    <DropdownMenuItem>View Details</DropdownMenuItem>
                                    <DropdownMenuItem>Edit Task</DropdownMenuItem>
                                    <DropdownMenuItem>Assign Agent</DropdownMenuItem>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuItem className="text-destructive">
                                      Delete
                                    </DropdownMenuItem>
                                  </DropdownMenuContent>
                                </DropdownMenu>
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </Card>

                {/* Approval Actions */}
                <div className="flex items-center justify-end gap-2 pt-4 border-t">
                  <Button variant="outline">Edit Tasks</Button>
                  <Button>Approve Plan</Button>
                </div>
              </div>
            </TabsContent>

            {/* Execution Tab */}
            <TabsContent value="execution" className="m-0 p-6">
              <div className="space-y-6">
                <div>
                  <h2 className="text-lg font-semibold">Execution Progress</h2>
                  <p className="text-sm text-muted-foreground">
                    Real-time execution status and metrics
                  </p>
                </div>

                {/* Progress Overview */}
                <div className="grid gap-4 md:grid-cols-4">
                  <Card>
                    <CardContent className="p-4">
                      <div className="space-y-2">
                        <p className="text-sm text-muted-foreground">Overall Progress</p>
                        <p className="text-2xl font-bold">{mockExecution.overallProgress}%</p>
                        <Progress value={mockExecution.overallProgress} />
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4">
                      <div className="space-y-2">
                        <p className="text-sm text-muted-foreground">Test Coverage</p>
                        <p className="text-2xl font-bold">{mockExecution.testCoverage}%</p>
                        <p className="text-xs text-muted-foreground">
                          {mockExecution.testsPassing}/{mockExecution.testsTotal} passing
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4">
                      <div className="space-y-2">
                        <p className="text-sm text-muted-foreground">Active Agents</p>
                        <p className="text-2xl font-bold">{mockExecution.activeAgents}</p>
                        <p className="text-xs text-muted-foreground">
                          {mockExecution.commits} commits
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="p-4">
                      <div className="space-y-2">
                        <p className="text-sm text-muted-foreground">Lines Changed</p>
                        <p className="text-2xl font-bold font-mono">
                          <span className="text-green-600">+{mockExecution.linesChanged.added}</span>
                          {" / "}
                          <span className="text-red-600">-{mockExecution.linesChanged.removed}</span>
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Running Tasks */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">Running Tasks</CardTitle>
                    <CardDescription>Currently executing tasks</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      {mockExecution.runningTasks.map((task) => (
                        <div key={task.id} className="rounded-lg border p-4">
                          <div className="flex items-start justify-between">
                            <div>
                              <div className="flex items-center gap-2">
                                <Badge variant="outline" className="font-mono text-xs">
                                  {task.id}
                                </Badge>
                                <span className="font-medium">{task.title}</span>
                              </div>
                              <div className="mt-1 flex items-center gap-4 text-sm text-muted-foreground">
                                <span className="flex items-center gap-1">
                                  <Bot className="h-3 w-3" />
                                  {task.agent}
                                </span>
                                <span className="flex items-center gap-1">
                                  <Clock className="h-3 w-3" />
                                  Started {formatTimeAgo(task.startedAt)}
                                </span>
                              </div>
                            </div>
                            <Button variant="outline" size="sm">
                              View Logs
                            </Button>
                          </div>
                          <div className="mt-3 space-y-1">
                            <div className="flex items-center justify-between text-sm">
                              <span className="text-muted-foreground">Progress</span>
                              <span>{task.progress}%</span>
                            </div>
                            <Progress value={task.progress} className="h-2" />
                          </div>
                        </div>
                      ))}
                      {mockExecution.runningTasks.length === 0 && (
                        <p className="text-center text-sm text-muted-foreground py-4">
                          No tasks currently running
                        </p>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Recent Commits & PRs */}
                <div className="grid gap-6 lg:grid-cols-2">
                  {/* Recent Commits */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Recent Commits</CardTitle>
                      <CardDescription>Latest code changes</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {mockExecution.recentCommits.map((commit) => (
                          <div
                            key={commit.sha}
                            className="flex items-start gap-3 rounded-md border p-3"
                          >
                            <GitBranch className="mt-0.5 h-4 w-4 text-muted-foreground" />
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{commit.message}</p>
                              <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                                <code className="font-mono">{commit.sha}</code>
                                <span>{commit.author}</span>
                                <span>{formatTimeAgo(commit.timestamp)}</span>
                              </div>
                            </div>
                            <span className="flex-shrink-0 font-mono text-xs">
                              <span className="text-green-600">+{commit.changes.added}</span>
                              {" "}
                              <span className="text-red-600">-{commit.changes.removed}</span>
                            </span>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  {/* Pull Requests */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Pull Requests</CardTitle>
                      <CardDescription>Open PRs from execution</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {mockExecution.pullRequests.map((pr) => (
                          <div
                            key={pr.number}
                            className="flex items-start gap-3 rounded-md border p-3"
                          >
                            <div
                              className={`mt-0.5 flex h-5 w-5 items-center justify-center rounded-full ${
                                pr.status === "open"
                                  ? "bg-green-100 text-green-600"
                                  : "bg-purple-100 text-purple-600"
                              }`}
                            >
                              <GitBranch className="h-3 w-3" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium">
                                #{pr.number} {pr.title}
                              </p>
                              <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                                <span>{pr.author}</span>
                                <Badge variant="outline" className="text-xs">
                                  {pr.reviewStatus}
                                </Badge>
                              </div>
                            </div>
                            <Button variant="outline" size="sm">
                              <ExternalLink className="mr-2 h-3 w-3" />
                              View
                            </Button>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Quick Actions */}
                <div className="flex items-center gap-2 pt-4 border-t">
                  <Button variant="outline" asChild>
                    <Link href={`/board/${id}`}>View Board</Link>
                  </Button>
                  <Button variant="outline" asChild>
                    <Link href={`/graph/${id}`}>View Graph</Link>
                  </Button>
                </div>
              </div>
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </div>

      {/* Right Sidebar - Metadata */}
      <div className="hidden w-64 flex-shrink-0 border-l bg-muted/30 xl:block">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-6">
            <div>
              <h3 className="text-sm font-medium mb-3">Spec Details</h3>
              <div className="space-y-3 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <Badge>{mockSpec.phase}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Progress</span>
                  <span className="font-medium">{mockSpec.progress}%</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Active Agents</span>
                  <span className="font-medium">{mockSpec.activeAgents}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Linked Tickets</span>
                  <span className="font-medium">{mockSpec.linkedTickets}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Updated</span>
                  <span className="text-muted-foreground">{formatTimeAgo(mockSpec.updatedAt)}</span>
                </div>
              </div>
            </div>

            <Separator />

            <div>
              <h3 className="text-sm font-medium mb-3">Test Coverage</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Coverage</span>
                  <span className="font-medium">{mockSpec.testCoverage}%</span>
                </div>
                <Progress value={mockSpec.testCoverage} className="h-2" />
              </div>
            </div>

            <Separator />

            <div>
              <h3 className="text-sm font-medium mb-3">Version History</h3>
              <div className="space-y-2">
                {[
                  { version: "v1.3", date: "2h ago", author: "AI" },
                  { version: "v1.2", date: "1d ago", author: "AI" },
                  { version: "v1.1", date: "2d ago", author: "You" },
                  { version: "v1.0", date: "3d ago", author: "You" },
                ].map((v, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between text-sm py-1"
                  >
                    <span className="font-mono">{v.version}</span>
                    <span className="text-muted-foreground">
                      {v.date} • {v.author}
                    </span>
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
