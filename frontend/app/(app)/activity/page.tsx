"use client"

import { useState, useMemo } from "react"
import Link from "next/link"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group"
import {
  Search,
  Filter,
  RefreshCw,
  Bot,
  User,
  GitCommit,
  GitBranch,
  GitPullRequest,
  MessageSquare,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Play,
  Pause,
  FileText,
  Code,
  Zap,
  Lightbulb,
  AlertTriangle,
  Brain,
  Plus,
  ArrowRight,
  ExternalLink,
} from "lucide-react"

// Mock activity events spanning different types
const mockActivities = [
  {
    id: "act-1",
    timestamp: new Date(Date.now() - 5 * 60 * 1000),
    type: "commit",
    title: "Pushed 3 commits",
    description: "worker-1 pushed commits to feature/oauth2-auth",
    actor: { type: "agent", name: "worker-1", avatar: "W1" },
    project: "senseii-games",
    metadata: {
      branch: "feature/oauth2-auth",
      commits: [
        { sha: "a1b2c3d", message: "Implement Google OAuth flow" },
        { sha: "e4f5g6h", message: "Add token refresh logic" },
        { sha: "i7j8k9l", message: "Fix edge case in auth middleware" },
      ],
      linesAdded: 456,
      linesRemoved: 23,
    },
    link: "/board/senseii-games/TICKET-042",
  },
  {
    id: "act-2",
    timestamp: new Date(Date.now() - 12 * 60 * 1000),
    type: "decision",
    title: "Implementation Decision",
    description: "Decided to use silent re-authentication for expired tokens",
    actor: { type: "agent", name: "worker-1", avatar: "W1" },
    project: "senseii-games",
    metadata: {
      confidence: 0.92,
      alternatives: ["Force logout", "Extend token validity"],
    },
    link: "/diagnostic/ticket/TICKET-042",
  },
  {
    id: "act-3",
    timestamp: new Date(Date.now() - 25 * 60 * 1000),
    type: "comment",
    title: "New Comment",
    description: "You commented on TICKET-042",
    actor: { type: "user", name: "You", avatar: "U" },
    project: "senseii-games",
    metadata: {
      ticket: "TICKET-042",
      preview: "Let's prioritize Google OAuth first, then GitHub.",
    },
    link: "/board/senseii-games/TICKET-042",
  },
  {
    id: "act-4",
    timestamp: new Date(Date.now() - 45 * 60 * 1000),
    type: "task_complete",
    title: "Task Completed",
    description: "TASK-002: Implement JWT Generator marked as complete",
    actor: { type: "agent", name: "worker-1", avatar: "W1" },
    project: "senseii-games",
    metadata: {
      task: "TASK-002",
      testsPass: 12,
      testsTotal: 12,
      coverage: 85,
    },
    link: "/board/senseii-games/TICKET-042",
  },
  {
    id: "act-5",
    timestamp: new Date(Date.now() - 1 * 60 * 60 * 1000),
    type: "error",
    title: "Error Encountered",
    description: "Token refresh failure in integration test",
    actor: { type: "agent", name: "worker-1", avatar: "W1" },
    project: "senseii-games",
    metadata: {
      errorType: "TokenRefreshError",
      file: "token.ts:142",
    },
    link: "/diagnostic/ticket/TICKET-042",
  },
  {
    id: "act-6",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    type: "pr_opened",
    title: "Pull Request Opened",
    description: "PR #42: feat: Add OAuth2 authentication",
    actor: { type: "agent", name: "worker-1", avatar: "W1" },
    project: "senseii-games",
    metadata: {
      prNumber: 42,
      branch: "feature/oauth2-auth",
      baseBranch: "main",
    },
    link: "#",
  },
  {
    id: "act-7",
    timestamp: new Date(Date.now() - 3 * 60 * 60 * 1000),
    type: "discovery",
    title: "Dependency Discovered",
    description: "Found database dependency - auth tables required first",
    actor: { type: "agent", name: "worker-1", avatar: "W1" },
    project: "senseii-games",
    metadata: {
      blocker: "TICKET-038",
      reason: "Database schema must be updated",
    },
    link: "/diagnostic/ticket/TICKET-042",
  },
  {
    id: "act-8",
    timestamp: new Date(Date.now() - 4 * 60 * 60 * 1000),
    type: "blocking_added",
    title: "Blocking Relationship",
    description: "TICKET-045 is now blocked by TICKET-042",
    actor: { type: "agent", name: "worker-1", avatar: "W1" },
    project: "senseii-games",
    metadata: {
      blocker: "TICKET-042",
      blocked: "TICKET-045",
    },
    link: "/graph/senseii-games",
  },
  {
    id: "act-9",
    timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000),
    type: "ticket_status",
    title: "Status Changed",
    description: "TICKET-042 moved to Implementation",
    actor: { type: "agent", name: "orchestrator", avatar: "O" },
    project: "senseii-games",
    metadata: {
      from: "Requirements",
      to: "Implementation",
    },
    link: "/board/senseii-games",
  },
  {
    id: "act-10",
    timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000),
    type: "agent_spawned",
    title: "Agent Spawned",
    description: "worker-3 spawned for code review tasks",
    actor: { type: "system", name: "System", avatar: "S" },
    project: null,
    metadata: {
      agentType: "worker",
      specialization: "code-review",
    },
    link: "/agents",
  },
  {
    id: "act-11",
    timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    type: "tasks_generated",
    title: "Tasks Generated",
    description: "5 tasks auto-generated from TICKET-042 requirements",
    actor: { type: "agent", name: "orchestrator", avatar: "O" },
    project: "senseii-games",
    metadata: {
      ticketId: "TICKET-042",
      taskCount: 5,
    },
    link: "/board/senseii-games/TICKET-042",
  },
  {
    id: "act-12",
    timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    type: "spec_approved",
    title: "Spec Approved",
    description: "User Authentication System spec approved",
    actor: { type: "user", name: "You", avatar: "U" },
    project: "senseii-games",
    metadata: {
      specId: "spec-001",
      specName: "User Authentication System",
    },
    link: "/projects/senseii-games/specs/spec-001",
  },
]

const activityTypeConfig: Record<string, { icon: typeof Plus; color: string; bg: string; label: string }> = {
  commit: { icon: GitCommit, color: "text-cyan-600", bg: "bg-cyan-100", label: "Commit" },
  decision: { icon: Brain, color: "text-green-600", bg: "bg-green-100", label: "Decision" },
  comment: { icon: MessageSquare, color: "text-blue-600", bg: "bg-blue-100", label: "Comment" },
  task_complete: { icon: CheckCircle, color: "text-emerald-600", bg: "bg-emerald-100", label: "Complete" },
  error: { icon: AlertCircle, color: "text-red-600", bg: "bg-red-100", label: "Error" },
  pr_opened: { icon: GitPullRequest, color: "text-purple-600", bg: "bg-purple-100", label: "PR Opened" },
  discovery: { icon: Lightbulb, color: "text-yellow-600", bg: "bg-yellow-100", label: "Discovery" },
  blocking_added: { icon: AlertTriangle, color: "text-orange-600", bg: "bg-orange-100", label: "Blocking" },
  ticket_status: { icon: ArrowRight, color: "text-indigo-600", bg: "bg-indigo-100", label: "Status" },
  agent_spawned: { icon: Zap, color: "text-pink-600", bg: "bg-pink-100", label: "Spawned" },
  tasks_generated: { icon: Zap, color: "text-violet-600", bg: "bg-violet-100", label: "Generated" },
  spec_approved: { icon: FileText, color: "text-teal-600", bg: "bg-teal-100", label: "Approved" },
}

export default function ActivityPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState<string>("all")
  const [actorFilter, setActorFilter] = useState<string>("all")
  const [projectFilter, setProjectFilter] = useState<string>("all")
  const [isLive, setIsLive] = useState(true)

  const filteredActivities = useMemo(() => {
    return mockActivities.filter((activity) => {
      const matchesSearch =
        searchQuery === "" ||
        activity.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        activity.description.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesType =
        typeFilter === "all" || activity.type === typeFilter
      const matchesActor =
        actorFilter === "all" || activity.actor.type === actorFilter
      const matchesProject =
        projectFilter === "all" || activity.project === projectFilter || (!activity.project && projectFilter === "system")
      return matchesSearch && matchesType && matchesActor && matchesProject
    })
  }, [searchQuery, typeFilter, actorFilter, projectFilter])

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

  // Group activities by date
  const groupedActivities = useMemo(() => {
    const groups: { label: string; activities: typeof mockActivities }[] = []
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    const todayActivities = filteredActivities.filter(
      (a) => a.timestamp.toDateString() === today.toDateString()
    )
    const yesterdayActivities = filteredActivities.filter(
      (a) => a.timestamp.toDateString() === yesterday.toDateString()
    )
    const olderActivities = filteredActivities.filter(
      (a) =>
        a.timestamp.toDateString() !== today.toDateString() &&
        a.timestamp.toDateString() !== yesterday.toDateString()
    )

    if (todayActivities.length) groups.push({ label: "Today", activities: todayActivities })
    if (yesterdayActivities.length) groups.push({ label: "Yesterday", activities: yesterdayActivities })
    if (olderActivities.length) groups.push({ label: "Earlier", activities: olderActivities })

    return groups
  }, [filteredActivities])

  // Unique projects for filter
  const projects = useMemo(() => {
    const set = new Set<string>()
    mockActivities.forEach((a) => {
      if (a.project) set.add(a.project)
    })
    return Array.from(set)
  }, [])

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b bg-background px-6 py-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <h1 className="text-xl font-semibold">Activity Timeline</h1>
            <p className="text-sm text-muted-foreground">
              Real-time feed of all system activity
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{filteredActivities.length} events</Badge>
            <Button
              variant={isLive ? "default" : "outline"}
              size="sm"
              onClick={() => setIsLive(!isLive)}
            >
              {isLive ? (
                <>
                  <span className="relative flex h-2 w-2 mr-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                  </span>
                  Live
                </>
              ) : (
                <>
                  <Pause className="mr-2 h-3 w-3" />
                  Paused
                </>
              )}
            </Button>
            <Button variant="outline" size="icon">
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex-shrink-0 border-b bg-muted/30 px-6 py-3">
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search activity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>

          {/* Type Filter */}
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-[150px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="commit">Commits</SelectItem>
              <SelectItem value="decision">Decisions</SelectItem>
              <SelectItem value="comment">Comments</SelectItem>
              <SelectItem value="task_complete">Completions</SelectItem>
              <SelectItem value="error">Errors</SelectItem>
              <SelectItem value="pr_opened">Pull Requests</SelectItem>
              <SelectItem value="discovery">Discoveries</SelectItem>
              <SelectItem value="blocking_added">Blocking</SelectItem>
              <SelectItem value="ticket_status">Status Changes</SelectItem>
            </SelectContent>
          </Select>

          {/* Actor Filter */}
          <ToggleGroup
            type="single"
            value={actorFilter}
            onValueChange={(v) => v && setActorFilter(v)}
            className="border rounded-md"
          >
            <ToggleGroupItem value="all" className="px-3">
              All
            </ToggleGroupItem>
            <ToggleGroupItem value="agent" className="px-3">
              <Bot className="mr-1 h-3 w-3" />
              Agents
            </ToggleGroupItem>
            <ToggleGroupItem value="user" className="px-3">
              <User className="mr-1 h-3 w-3" />
              You
            </ToggleGroupItem>
            <ToggleGroupItem value="system" className="px-3">
              <Zap className="mr-1 h-3 w-3" />
              System
            </ToggleGroupItem>
          </ToggleGroup>

          {/* Project Filter */}
          <Select value={projectFilter} onValueChange={setProjectFilter}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Project" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Projects</SelectItem>
              <SelectItem value="system">System Events</SelectItem>
              {projects.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Activity Feed */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="max-w-3xl mx-auto space-y-6">
          {groupedActivities.map((group) => (
            <div key={group.label}>
              <h2 className="text-sm font-medium text-muted-foreground mb-3 sticky top-0 bg-background py-1">
                {group.label}
              </h2>
              <div className="space-y-3">
                {group.activities.map((activity) => {
                  const config = activityTypeConfig[activity.type] || activityTypeConfig.commit
                  const ActivityIcon = config.icon

                  return (
                    <Card key={activity.id} className="group hover:border-primary/30 transition-colors">
                      <CardContent className="p-4">
                        <div className="flex items-start gap-4">
                          {/* Avatar */}
                          <Avatar className="h-9 w-9">
                            <AvatarFallback
                              className={
                                activity.actor.type === "user"
                                  ? "bg-primary text-primary-foreground"
                                  : activity.actor.type === "agent"
                                  ? "bg-muted"
                                  : "bg-muted"
                              }
                            >
                              {activity.actor.avatar}
                            </AvatarFallback>
                          </Avatar>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">{activity.actor.name}</span>
                                  {activity.actor.type === "agent" && (
                                    <Badge variant="outline" className="text-xs">
                                      <Bot className="mr-1 h-3 w-3" />
                                      Agent
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  {activity.description}
                                </p>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <div
                                  className={`flex h-6 w-6 items-center justify-center rounded-full ${config.bg}`}
                                >
                                  <ActivityIcon className={`h-3 w-3 ${config.color}`} />
                                </div>
                                <span className="text-xs text-muted-foreground">
                                  {formatTimeAgo(activity.timestamp)}
                                </span>
                              </div>
                            </div>

                            {/* Metadata */}
                            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                              <Badge variant="secondary" className={`${config.bg} ${config.color} border-0`}>
                                {config.label}
                              </Badge>
                              {activity.project && (
                                <Badge variant="outline">{activity.project}</Badge>
                              )}

                              {/* Type-specific metadata */}
                              {activity.type === "commit" && activity.metadata.commits && (
                                <span className="text-muted-foreground">
                                  {activity.metadata.commits.length} commits on{" "}
                                  <code className="font-mono">{activity.metadata.branch}</code>
                                </span>
                              )}
                              {activity.type === "commit" && (
                                <span className="font-mono">
                                  <span className="text-green-600">+{activity.metadata.linesAdded}</span>
                                  {" "}
                                  <span className="text-red-600">-{activity.metadata.linesRemoved}</span>
                                </span>
                              )}
                              {activity.type === "decision" && activity.metadata.confidence !== undefined && (
                                <span className="text-muted-foreground">
                                  Confidence: {Math.round(activity.metadata.confidence * 100)}%
                                </span>
                              )}
                              {activity.type === "task_complete" && activity.metadata.testsPass !== undefined && (
                                <span className="text-muted-foreground">
                                  {activity.metadata.testsPass}/{activity.metadata.testsTotal} tests,{" "}
                                  {activity.metadata.coverage}% coverage
                                </span>
                              )}
                              {activity.type === "error" && activity.metadata.errorType && (
                                <span className="text-red-600 font-mono">
                                  {activity.metadata.errorType}
                                </span>
                              )}
                              {activity.type === "pr_opened" && activity.metadata.prNumber !== undefined && (
                                <span className="text-muted-foreground">
                                  #{activity.metadata.prNumber} •{" "}
                                  <code className="font-mono">{activity.metadata.branch}</code> →{" "}
                                  <code className="font-mono">{activity.metadata.baseBranch}</code>
                                </span>
                              )}
                              {activity.type === "ticket_status" && activity.metadata.from && (
                                <span className="text-muted-foreground">
                                  {activity.metadata.from} → {activity.metadata.to}
                                </span>
                              )}
                              {activity.type === "tasks_generated" && activity.metadata.taskCount !== undefined && (
                                <span className="text-muted-foreground">
                                  {activity.metadata.taskCount} tasks
                                </span>
                              )}
                            </div>

                            {/* Comment preview */}
                            {activity.type === "comment" && activity.metadata.preview && (
                              <div className="mt-2 p-2 rounded bg-muted/50 text-sm italic">
                                "{activity.metadata.preview}"
                              </div>
                            )}

                            {/* Commit list */}
                            {activity.type === "commit" && activity.metadata.commits && (
                              <div className="mt-2 space-y-1">
                                {activity.metadata.commits.slice(0, 2).map((commit: { sha: string; message: string }) => (
                                  <div key={commit.sha} className="flex items-center gap-2 text-xs">
                                    <code className="font-mono text-muted-foreground">
                                      {commit.sha}
                                    </code>
                                    <span className="truncate">{commit.message}</span>
                                  </div>
                                ))}
                                {activity.metadata.commits.length > 2 && (
                                  <span className="text-xs text-muted-foreground">
                                    +{activity.metadata.commits.length - 2} more
                                  </span>
                                )}
                              </div>
                            )}
                          </div>

                          {/* Link */}
                          {activity.link && activity.link !== "#" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="opacity-0 group-hover:opacity-100 transition-opacity"
                              asChild
                            >
                              <Link href={activity.link}>
                                <ExternalLink className="h-4 w-4" />
                              </Link>
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            </div>
          ))}

          {filteredActivities.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              No activities match your filters
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
