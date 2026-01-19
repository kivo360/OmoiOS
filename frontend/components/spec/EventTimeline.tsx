"use client"

import { useState, useEffect, useRef } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import {
  Play,
  CheckCircle,
  XCircle,
  AlertCircle,
  Clock,
  Bot,
  Zap,
  RefreshCw,
  Pause,
  ChevronDown,
  ChevronUp,
  Activity,
  ExternalLink,
  Terminal,
} from "lucide-react"
import Link from "next/link"
import { useSpecEvents } from "@/hooks/useSpecs"
import type { SpecEventItem } from "@/lib/api/specs"

interface EventTimelineProps {
  specId: string
  isExecuting?: boolean
  maxHeight?: string
  className?: string
}

// Map event types to display configuration
const eventConfig: Record<string, {
  icon: React.ComponentType<{ className?: string }>
  color: string
  label: string
}> = {
  // Spec lifecycle events
  "spec.execution_started": { icon: Play, color: "text-blue-500", label: "Execution Started" },
  "spec.phase_started": { icon: Activity, color: "text-blue-400", label: "Phase Started" },
  "spec.phase_completed": { icon: CheckCircle, color: "text-green-500", label: "Phase Completed" },
  "spec.phase_failed": { icon: XCircle, color: "text-red-500", label: "Phase Failed" },
  "spec.phase_retry": { icon: RefreshCw, color: "text-yellow-500", label: "Phase Retry" },
  "spec.execution_completed": { icon: CheckCircle, color: "text-green-600", label: "Execution Complete" },
  "spec.sync_started": { icon: RefreshCw, color: "text-blue-400", label: "Sync Started" },
  "spec.sync_completed": { icon: CheckCircle, color: "text-green-500", label: "Sync Completed" },
  "spec.tasks_queued": { icon: Zap, color: "text-purple-500", label: "Tasks Queued" },

  // Agent events
  "agent.started": { icon: Bot, color: "text-blue-500", label: "Agent Started" },
  "agent.completed": { icon: CheckCircle, color: "text-green-500", label: "Agent Completed" },
  "agent.failed": { icon: XCircle, color: "text-red-500", label: "Agent Failed" },
  "agent.error": { icon: AlertCircle, color: "text-red-400", label: "Agent Error" },
  "agent.tool_completed": { icon: Zap, color: "text-purple-400", label: "Tool Completed" },
  "agent.heartbeat": { icon: Activity, color: "text-gray-400", label: "Heartbeat" },

  // Default fallback
  default: { icon: Clock, color: "text-gray-500", label: "Event" },
}

function getEventConfig(eventType: string) {
  return eventConfig[eventType] || eventConfig.default
}

function formatTimestamp(timestamp: string) {
  const date = new Date(timestamp)
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
}

function formatEventMessage(event: SpecEventItem): string {
  const data = event.event_data

  // Try to extract meaningful message from event_data
  if (data.message) return String(data.message)
  if (data.phase) return `Phase: ${String(data.phase)}`
  if (data.task_count) return `${data.task_count} tasks`
  if (data.eval_score !== undefined) return `Score: ${data.eval_score}`
  if (data.error) return String(data.error).slice(0, 100)
  if (data.duration) return `Duration: ${data.duration}s`

  // Extract from nested structures
  if (data.result && typeof data.result === "object") {
    const result = data.result as Record<string, unknown>
    if (result.summary) return String(result.summary)
  }

  return ""
}

function EventItem({ event, isNew }: { event: SpecEventItem; isNew?: boolean }) {
  const config = getEventConfig(event.event_type)
  const Icon = config.icon
  const message = formatEventMessage(event)

  return (
    <div
      className={cn(
        "flex items-start gap-3 py-2 px-3 rounded-md transition-colors",
        isNew && "bg-primary/5 animate-pulse"
      )}
    >
      <div className={cn("mt-0.5 flex-shrink-0", config.color)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-foreground">
            {config.label}
          </span>
          <Badge variant="outline" className="text-[10px] px-1.5 py-0">
            {event.source}
          </Badge>
        </div>
        {message && (
          <p className="text-xs text-muted-foreground mt-0.5 truncate">
            {message}
          </p>
        )}
      </div>
      <span className="text-[10px] text-muted-foreground flex-shrink-0">
        {formatTimestamp(event.created_at)}
      </span>
    </div>
  )
}

export function EventTimeline({
  specId,
  isExecuting = false,
  maxHeight = "400px",
  className,
}: EventTimelineProps) {
  const [isPaused, setIsPaused] = useState(false)
  const [isExpanded, setIsExpanded] = useState(true)
  const [newEventIds, setNewEventIds] = useState<Set<string>>(new Set())
  const previousEventsRef = useRef<Set<string>>(new Set())
  const scrollRef = useRef<HTMLDivElement>(null)

  // Poll every 2s when executing and not paused
  const { data: eventsData, isLoading } = useSpecEvents(specId, {
    enabled: true,
    refetchInterval: isExecuting && !isPaused ? 2000 : false,
    limit: 100,
  })

  const events = eventsData?.events || []

  // Get the most recent sandbox_id from events (for linking to sandbox viewer)
  const activeSandboxId = events.length > 0 ? events[0].sandbox_id : null

  // Track new events for highlight animation
  useEffect(() => {
    if (!events.length) return

    const currentIds = new Set(events.map((e) => e.id))
    const newIds = new Set<string>()

    currentIds.forEach((id) => {
      if (!previousEventsRef.current.has(id)) {
        newIds.add(id)
      }
    })

    if (newIds.size > 0) {
      setNewEventIds(newIds)
      // Clear highlight after animation
      setTimeout(() => setNewEventIds(new Set()), 2000)
    }

    previousEventsRef.current = currentIds
  }, [events])

  // Auto-scroll to top when new events arrive (they're newest first)
  useEffect(() => {
    if (newEventIds.size > 0 && !isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = 0
    }
  }, [newEventIds, isPaused])

  if (!isExpanded) {
    return (
      <div className={cn("border rounded-lg", className)}>
        <button
          onClick={() => setIsExpanded(true)}
          className="w-full flex items-center justify-between p-3 hover:bg-muted/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Activity className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm font-medium">Event Timeline</span>
            {events.length > 0 && (
              <Badge variant="secondary" className="text-xs">
                {events.length}
              </Badge>
            )}
          </div>
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </button>
      </div>
    )
  }

  return (
    <div className={cn("border rounded-lg", className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium">Event Timeline</span>
          {events.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {events.length}
            </Badge>
          )}
          {isExecuting && !isPaused && (
            <span className="flex items-center gap-1 text-xs text-green-600">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
              </span>
              Live
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          {/* Sandbox link when executing */}
          {activeSandboxId && isExecuting && (
            <Button
              variant="outline"
              size="sm"
              asChild
              className="h-7 px-2 text-xs"
            >
              <Link href={`/sandbox/${activeSandboxId}`} target="_blank">
                <Terminal className="h-3 w-3 mr-1" />
                View Sandbox
                <ExternalLink className="h-3 w-3 ml-1" />
              </Link>
            </Button>
          )}
          {isExecuting && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsPaused(!isPaused)}
              className="h-7 px-2"
            >
              {isPaused ? (
                <>
                  <Play className="h-3 w-3 mr-1" />
                  Resume
                </>
              ) : (
                <>
                  <Pause className="h-3 w-3 mr-1" />
                  Pause
                </>
              )}
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsExpanded(false)}
            className="h-7 px-2"
          >
            <ChevronUp className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Event List */}
      <div className="overflow-auto" style={{ maxHeight }} ref={scrollRef}>
        <div className="p-2">
          {isLoading && events.length === 0 ? (
            <div className="flex items-center justify-center py-8 text-muted-foreground">
              <RefreshCw className="h-4 w-4 animate-spin mr-2" />
              Loading events...
            </div>
          ) : events.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Clock className="h-8 w-8 mb-2 opacity-50" />
              <p className="text-sm">No events yet</p>
              <p className="text-xs">Events will appear here during execution</p>
            </div>
          ) : (
            <div className="space-y-1">
              {events.map((event) => (
                <EventItem
                  key={event.id}
                  event={event}
                  isNew={newEventIds.has(event.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Footer with count */}
      {events.length > 0 && (
        <div className="px-3 py-2 border-t text-xs text-muted-foreground">
          Showing {events.length} of {eventsData?.total_count || events.length} events
          {eventsData?.has_more && " • Scroll for more"}
        </div>
      )}
    </div>
  )
}
