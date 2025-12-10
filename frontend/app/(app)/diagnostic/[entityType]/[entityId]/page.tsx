"use client"

import { use, useState, useMemo } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
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
  Bot,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  ExternalLink,
  Code,
  Loader2,
} from "lucide-react"
import { useReasoningChain } from "@/hooks/useReasoning"
import type { Evidence, Alternative } from "@/lib/api/reasoning"

interface DiagnosticPageProps {
  params: Promise<{ entityType: string; entityId: string }>
}

// Event types removed - now fetched from API

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
  const [expandedEvents, setExpandedEvents] = useState<string[]>([])

  // Fetch reasoning chain from API
  const { data: chainData, isLoading, error } = useReasoningChain(
    entityType,
    entityId,
    { event_type: typeFilter !== "all" ? typeFilter : undefined }
  )

  const events = chainData?.events || []
  const stats = chainData?.stats || { total: 0, decisions: 0, discoveries: 0, errors: 0 }

  const toggleEvent = (eventId: string) => {
    setExpandedEvents((prev) =>
      prev.includes(eventId) ? prev.filter((id) => id !== eventId) : [...prev, eventId]
    )
  }

  const expandAll = () => {
    setExpandedEvents(events.map((e) => e.id))
  }

  const collapseAll = () => {
    setExpandedEvents([])
  }

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const matchesSearch =
        searchQuery === "" ||
        event.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        event.description.toLowerCase().includes(searchQuery.toLowerCase())
      return matchesSearch
    })
  }, [events, searchQuery])

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / (1000 * 60))
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    })
  }

  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] flex-col">
        <div className="flex-shrink-0 border-b bg-background px-6 py-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96 mt-2" />
        </div>
        <div className="flex-1 px-6 py-4">
          <div className="max-w-4xl mx-auto space-y-4">
            {[1, 2, 3, 4].map((i) => (
              <Skeleton key={i} className="h-24 w-full" />
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
          <h2 className="text-lg font-semibold">Failed to load reasoning chain</h2>
          <p className="text-muted-foreground">{(error as Error).message}</p>
        </div>
      </div>
    )
  }

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
                                      {event.details.alternatives.map((alt: Alternative, i: number) => (
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
                                {event.details.lines_added !== undefined && (
                                  <div className="flex items-center gap-4">
                                    <span className="font-mono">
                                      <span className="text-green-600">+{event.details.lines_added}</span>
                                      {" / "}
                                      <span className="text-red-600">-{event.details.lines_removed}</span>
                                    </span>
                                    <span>{event.details.files_changed} files</span>
                                    <span>
                                      {event.details.tests_passing}/{event.details.tests_total} tests
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
