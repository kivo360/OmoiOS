"use client"

import { use, useState, useMemo } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
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
  ArrowLeft,
  Search,
  Filter,
  ChevronDown,
  ChevronRight,
  Plus,
  Lightbulb,
  Zap,
  AlertTriangle,
  Brain,
  GitBranch,
  Clock,
  Bot,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  ArrowRight,
  ExternalLink,
  Code,
  MessageSquare,
  Play,
  Pause,
  RefreshCw,
} from "lucide-react"

interface DiagnosticPageProps {
  params: Promise<{ entityType: string; entityId: string }>
}

interface Evidence {
  type: string
  content: string
  link?: string
}

// Mock diagnostic events
const mockEvents = [
  {
    id: "event-1",
    timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
    type: "ticket_created",
    title: "Ticket Created",
    description: "Created from spec requirement REQ-001: OAuth2 Support",
    agent: null,
    details: {
      sourceSpec: "spec-001",
      sourceRequirement: "REQ-001",
      createdBy: "system",
      context: "During automated spec-to-ticket decomposition, the system identified OAuth2 authentication as a discrete implementation unit.",
    },
    evidence: [],
    decision: null,
  },
  {
    id: "event-2",
    timestamp: new Date(Date.now() - 2.5 * 24 * 60 * 60 * 1000),
    type: "task_spawned",
    title: "Tasks Auto-Generated",
    description: "5 implementation tasks created from ticket requirements",
    agent: "orchestrator",
    details: {
      tasksCreated: 5,
      reasoning: "Analyzed ticket description and spec requirements to decompose into actionable tasks. Each task represents an atomic unit of work that can be completed independently.",
      tasks: [
        "TASK-001: Setup OAuth2 Configuration",
        "TASK-002: Implement JWT Generator",
        "TASK-003: Build Token Validator",
        "TASK-004: Write Integration Tests",
        "TASK-005: API Documentation",
      ],
    },
    evidence: [
      { type: "requirement", content: "REQ-001: OAuth2 Support", link: "/projects/senseii-games/specs/spec-001" },
    ],
    decision: null,
  },
  {
    id: "event-3",
    timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    type: "discovery",
    title: "Discovery: Database Dependency",
    description: "Agent discovered that auth tables must exist before implementing OAuth",
    agent: "worker-1",
    details: {
      discoveryType: "dependency",
      context: "While attempting to implement OAuth provider storage, the agent encountered a database constraint error.",
      evidence: "Failed to create OAuth provider record - table 'oauth_providers' does not exist",
      action: "Linked to TICKET-038 as blocker",
      impact: "Blocked implementation until database migration is complete",
    },
    evidence: [
      { type: "error", content: "PostgresError: relation \"oauth_providers\" does not exist" },
      { type: "log", content: "SELECT * FROM oauth_providers WHERE user_id = $1" },
    ],
    decision: {
      type: "block",
      action: "Added TICKET-038 as blocker",
      reasoning: "Cannot proceed with OAuth implementation until database schema is updated",
    },
  },
  {
    id: "event-4",
    timestamp: new Date(Date.now() - 1.5 * 24 * 60 * 60 * 1000),
    type: "agent_decision",
    title: "Implementation Order Decision",
    description: "Decided to implement Google OAuth before GitHub",
    agent: "worker-1",
    details: {
      context: "Evaluating which OAuth provider to implement first",
      reasoning: "Google OAuth has more comprehensive documentation and larger user base. Starting with Google allows establishing patterns that GitHub implementation can follow. The Google OAuth library is also more mature and has better TypeScript support.",
      alternatives: [
        { option: "Implement both in parallel", rejected: "Would require context switching and duplicate testing setup" },
        { option: "Start with GitHub", rejected: "GitHub's OAuth documentation is less detailed" },
      ],
      confidence: 0.85,
    },
    evidence: [
      { type: "doc", content: "Google OAuth2 documentation: 47 pages with examples" },
      { type: "doc", content: "GitHub OAuth documentation: 12 pages, fewer examples" },
      { type: "stats", content: "Google: 92% of users, GitHub: 8% of users (from analytics)" },
    ],
    decision: {
      type: "proceed",
      action: "Implement Google OAuth first, then GitHub",
      reasoning: "Higher user impact, better documentation, establishes reusable patterns",
    },
  },
  {
    id: "event-5",
    timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    type: "blocking_added",
    title: "Blocking Relationship Added",
    description: "TICKET-045 now blocked by this ticket",
    agent: "worker-1",
    details: {
      blockedTicket: "TICKET-045",
      blockedTitle: "User Profile Management",
      reason: "User Profile Management requires authentication to be complete",
      context: "During code review, identified that profile endpoints depend on authenticated user context.",
    },
    evidence: [
      { type: "code", content: "const user = req.auth?.user // undefined without OAuth" },
      { type: "requirement", content: "Profile API must return authenticated user data" },
    ],
    decision: {
      type: "block",
      action: "Added blocking relationship",
      reasoning: "Profile endpoints cannot function without user authentication context",
    },
  },
  {
    id: "event-6",
    timestamp: new Date(Date.now() - 12 * 60 * 60 * 1000),
    type: "code_change",
    title: "Implementation: JWT Generator",
    description: "Completed JWT token generation service",
    agent: "worker-1",
    details: {
      task: "TASK-002",
      linesAdded: 450,
      linesRemoved: 12,
      filesChanged: 5,
      testsPassing: 12,
      testsTotal: 12,
      commit: "a1b2c3d",
    },
    evidence: [
      { type: "test", content: "12/12 tests passing" },
      { type: "coverage", content: "85% code coverage" },
    ],
    decision: {
      type: "complete",
      action: "Marked TASK-002 as complete",
      reasoning: "All tests passing, code review approved, coverage threshold met",
    },
  },
  {
    id: "event-7",
    timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000),
    type: "error",
    title: "Error: Token Refresh Failure",
    description: "Encountered edge case in token refresh flow",
    agent: "worker-1",
    details: {
      errorType: "TokenRefreshError",
      context: "During integration testing, token refresh failed for users with expired refresh tokens",
      stackTrace: "at TokenService.refresh (token.ts:142)\nat AuthMiddleware.handle (auth.ts:58)",
      impact: "Users with expired refresh tokens cannot re-authenticate",
    },
    evidence: [
      { type: "error", content: "TokenRefreshError: Refresh token expired" },
      { type: "log", content: "Token expiry: 2024-01-15T00:00:00Z, Current: 2024-01-20T12:00:00Z" },
    ],
    decision: {
      type: "investigate",
      action: "Created investigation task",
      reasoning: "Need to implement graceful fallback for expired refresh tokens",
    },
  },
  {
    id: "event-8",
    timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000),
    type: "agent_decision",
    title: "Error Resolution Strategy",
    description: "Decided to implement re-authentication flow for expired tokens",
    agent: "worker-1",
    details: {
      context: "Evaluating approaches to handle expired refresh tokens",
      reasoning: "Silent re-authentication provides better UX than forcing logout. Users with valid sessions can obtain new tokens without interruption.",
      alternatives: [
        { option: "Force logout", rejected: "Poor UX, users lose context" },
        { option: "Extend token validity", rejected: "Security concern, tokens should expire" },
      ],
      confidence: 0.92,
    },
    evidence: [
      { type: "doc", content: "OAuth2 best practices: silent re-auth for session continuity" },
      { type: "code", content: "if (isRefreshExpired) { await silentReauth(); }" },
    ],
    decision: {
      type: "implement",
      action: "Implementing silent re-authentication",
      reasoning: "Best balance of security and user experience",
    },
  },
]

const eventTypeConfig: Record<string, { icon: typeof Plus; color: string; bg: string }> = {
  ticket_created: { icon: Plus, color: "text-blue-600", bg: "bg-blue-100" },
  task_spawned: { icon: Zap, color: "text-purple-600", bg: "bg-purple-100" },
  discovery: { icon: Lightbulb, color: "text-yellow-600", bg: "bg-yellow-100" },
  agent_decision: { icon: Brain, color: "text-green-600", bg: "bg-green-100" },
  blocking_added: { icon: AlertTriangle, color: "text-orange-600", bg: "bg-orange-100" },
  code_change: { icon: GitBranch, color: "text-cyan-600", bg: "bg-cyan-100" },
  error: { icon: AlertCircle, color: "text-red-600", bg: "bg-red-100" },
}

const evidenceTypeConfig: Record<string, { icon: typeof Code; label: string }> = {
  error: { icon: AlertCircle, label: "Error" },
  log: { icon: FileText, label: "Log" },
  code: { icon: Code, label: "Code" },
  doc: { icon: FileText, label: "Documentation" },
  requirement: { icon: FileText, label: "Requirement" },
  test: { icon: CheckCircle, label: "Test" },
  coverage: { icon: CheckCircle, label: "Coverage" },
  stats: { icon: FileText, label: "Statistics" },
}

export default function DiagnosticPage({ params }: DiagnosticPageProps) {
  const { entityType, entityId } = use(params)
  const [searchQuery, setSearchQuery] = useState("")
  const [typeFilter, setTypeFilter] = useState<string>("all")
  const [expandedEvents, setExpandedEvents] = useState<string[]>(["event-3", "event-4"])

  const toggleEvent = (eventId: string) => {
    setExpandedEvents((prev) =>
      prev.includes(eventId) ? prev.filter((id) => id !== eventId) : [...prev, eventId]
    )
  }

  const expandAll = () => {
    setExpandedEvents(mockEvents.map((e) => e.id))
  }

  const collapseAll = () => {
    setExpandedEvents([])
  }

  const filteredEvents = useMemo(() => {
    return mockEvents.filter((event) => {
      const matchesSearch =
        searchQuery === "" ||
        event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        event.description.toLowerCase().includes(searchQuery.toLowerCase())
      const matchesType = typeFilter === "all" || event.type === typeFilter
      return matchesSearch && matchesType
    })
  }, [searchQuery, typeFilter])

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
      hour: "numeric",
      minute: "2-digit",
    })
  }

  // Stats
  const stats = useMemo(() => {
    const byType: Record<string, number> = {}
    mockEvents.forEach((event) => {
      byType[event.type] = (byType[event.type] || 0) + 1
    })
    return {
      total: mockEvents.length,
      decisions: mockEvents.filter((e) => e.decision).length,
      discoveries: byType.discovery || 0,
      errors: byType.error || 0,
    }
  }, [])

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b bg-background px-6 py-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-3">
              <Link
                href={entityType === "ticket" ? `/board/project/${entityId}` : `/projects/project/specs/${entityId}`}
                className="text-muted-foreground hover:text-foreground"
              >
                <ArrowLeft className="h-5 w-5" />
              </Link>
              <h1 className="text-xl font-semibold">Diagnostic Reasoning</h1>
              <Badge variant="outline" className="font-mono">
                {entityType.toUpperCase()}-{entityId}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Complete timeline of agent decisions, discoveries, and reasoning
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline">{stats.total} events</Badge>
            <Badge variant="outline" className="text-green-600">
              {stats.decisions} decisions
            </Badge>
            {stats.errors > 0 && (
              <Badge variant="destructive">{stats.errors} errors</Badge>
            )}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex-shrink-0 border-b bg-muted/30 px-6 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search events..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-[250px] pl-8"
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[160px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder="Event type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Events</SelectItem>
                <SelectItem value="ticket_created">Ticket Created</SelectItem>
                <SelectItem value="task_spawned">Tasks Spawned</SelectItem>
                <SelectItem value="discovery">Discovery</SelectItem>
                <SelectItem value="agent_decision">Agent Decision</SelectItem>
                <SelectItem value="blocking_added">Blocking Added</SelectItem>
                <SelectItem value="code_change">Code Change</SelectItem>
                <SelectItem value="error">Error</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={expandAll}>
              Expand All
            </Button>
            <Button variant="outline" size="sm" onClick={collapseAll}>
              Collapse All
            </Button>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="max-w-4xl mx-auto">
          <div className="relative space-y-0">
            {filteredEvents.map((event, idx) => {
              const config = eventTypeConfig[event.type] || eventTypeConfig.ticket_created
              const EventIcon = config.icon
              const isExpanded = expandedEvents.includes(event.id)

              return (
                <div key={event.id} className="relative pl-10 pb-8">
                  {/* Timeline line */}
                  {idx < filteredEvents.length - 1 && (
                    <div className="absolute left-[18px] top-10 h-full w-px bg-border" />
                  )}

                  {/* Event icon */}
                  <div
                    className={`absolute left-0 flex h-9 w-9 items-center justify-center rounded-full border-2 border-background ${config.bg}`}
                  >
                    <EventIcon className={`h-4 w-4 ${config.color}`} />
                  </div>

                  {/* Event content */}
                  <Collapsible open={isExpanded} onOpenChange={() => toggleEvent(event.id)}>
                    <Card className={isExpanded ? "ring-1 ring-primary/20" : ""}>
                      <CollapsibleTrigger asChild>
                        <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors py-3">
                          <div className="flex items-start justify-between">
                            <div className="flex items-start gap-3">
                              <div className="mt-0.5">
                                {isExpanded ? (
                                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                ) : (
                                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                )}
                              </div>
                              <div>
                                <CardTitle className="text-base">{event.title}</CardTitle>
                                <CardDescription className="mt-0.5">
                                  {event.description}
                                </CardDescription>
                              </div>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-muted-foreground">
                              {event.agent && (
                                <Badge variant="outline" className="text-xs">
                                  <Bot className="mr-1 h-3 w-3" />
                                  {event.agent}
                                </Badge>
                              )}
                              <span title={formatDate(event.timestamp)}>
                                {formatTimeAgo(event.timestamp)}
                              </span>
                            </div>
                          </div>
                        </CardHeader>
                      </CollapsibleTrigger>
                      <CollapsibleContent>
                        <CardContent className="border-t pt-4 space-y-4">
                          {/* Context/Details */}
                          {event.details && (
                            <div>
                              <h4 className="text-sm font-medium mb-2">Details</h4>
                              <div className="rounded-lg bg-muted/50 p-3 space-y-2 text-sm">
                                {event.details.context && (
                                  <p>{event.details.context}</p>
                                )}
                                {event.details.reasoning && (
                                  <div>
                                    <span className="font-medium">Reasoning: </span>
                                    {event.details.reasoning}
                                  </div>
                                )}
                                {event.details.tasks && (
                                  <div>
                                    <span className="font-medium">Tasks created:</span>
                                    <ul className="mt-1 list-disc list-inside text-muted-foreground">
                                      {event.details.tasks.map((task: string, i: number) => (
                                        <li key={i}>{task}</li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {event.details.alternatives && (
                                  <div>
                                    <span className="font-medium">Alternatives considered:</span>
                                    <ul className="mt-1 space-y-1 text-muted-foreground">
                                      {event.details.alternatives.map((alt: { option: string; rejected: string }, i: number) => (
                                        <li key={i} className="flex items-start gap-2">
                                          <XCircle className="h-4 w-4 text-red-500 mt-0.5 flex-shrink-0" />
                                          <span>
                                            <strong>{alt.option}:</strong> {alt.rejected}
                                          </span>
                                        </li>
                                      ))}
                                    </ul>
                                  </div>
                                )}
                                {event.details.confidence !== undefined && (
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">Confidence:</span>
                                    <Badge variant="outline">
                                      {Math.round(event.details.confidence * 100)}%
                                    </Badge>
                                  </div>
                                )}
                                {event.details.linesAdded !== undefined && (
                                  <div className="flex items-center gap-4">
                                    <span className="font-mono">
                                      <span className="text-green-600">+{event.details.linesAdded}</span>
                                      {" / "}
                                      <span className="text-red-600">-{event.details.linesRemoved}</span>
                                    </span>
                                    <span>{event.details.filesChanged} files</span>
                                    <span>
                                      {event.details.testsPassing}/{event.details.testsTotal} tests
                                    </span>
                                  </div>
                                )}
                              </div>
                            </div>
                          )}

                          {/* Evidence */}
                          {event.evidence && event.evidence.length > 0 && (
                            <div>
                              <h4 className="text-sm font-medium mb-2">Evidence</h4>
                              <div className="space-y-2">
                                {event.evidence.map((ev, i) => {
                                  const evConfig = evidenceTypeConfig[ev.type] || evidenceTypeConfig.log
                                  const EvIcon = evConfig.icon
                                  return (
                                    <div
                                      key={i}
                                      className="flex items-start gap-3 rounded-md border p-3"
                                    >
                                      <div className="flex h-6 w-6 items-center justify-center rounded bg-muted">
                                        <EvIcon className="h-3 w-3" />
                                      </div>
                                      <div className="flex-1 min-w-0">
                                        <Badge variant="outline" className="text-xs mb-1">
                                          {evConfig.label}
                                        </Badge>
                                        <p className="text-sm font-mono break-all">
                                          {ev.content}
                                        </p>
                                      </div>
                                      {(ev as Evidence).link && (
                                        <Button variant="ghost" size="sm" asChild>
                                          <Link href={(ev as Evidence).link!}>
                                            <ExternalLink className="h-3 w-3" />
                                          </Link>
                                        </Button>
                                      )}
                                    </div>
                                  )
                                })}
                              </div>
                            </div>
                          )}

                          {/* Decision */}
                          {event.decision && (
                            <div>
                              <h4 className="text-sm font-medium mb-2">Decision</h4>
                              <div
                                className={`rounded-lg p-3 ${
                                  event.decision.type === "complete"
                                    ? "bg-green-50 border border-green-200"
                                    : event.decision.type === "block"
                                    ? "bg-orange-50 border border-orange-200"
                                    : event.decision.type === "implement"
                                    ? "bg-blue-50 border border-blue-200"
                                    : "bg-muted/50"
                                }`}
                              >
                                <div className="flex items-center gap-2 mb-1">
                                  <Badge
                                    variant={
                                      event.decision.type === "complete"
                                        ? "default"
                                        : event.decision.type === "block"
                                        ? "destructive"
                                        : "secondary"
                                    }
                                    className="text-xs"
                                  >
                                    {event.decision.type.toUpperCase()}
                                  </Badge>
                                  <span className="font-medium text-sm">
                                    {event.decision.action}
                                  </span>
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  {event.decision.reasoning}
                                </p>
                              </div>
                            </div>
                          )}
                        </CardContent>
                      </CollapsibleContent>
                    </Card>
                  </Collapsible>
                </div>
              )
            })}

            {filteredEvents.length === 0 && (
              <div className="text-center py-12 text-muted-foreground">
                No events match your search criteria
              </div>
            )}
          </div>
        </div>
      </ScrollArea>
    </div>
  )
}
