"use client"

import { useState, useRef, useEffect, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  X,
  Terminal,
  Loader2,
  AlertCircle,
  Bot,
  CheckCircle,
  Clock,
  PlayCircle,
  XCircle,
  Wifi,
  WifiOff,
  ExternalLink,
  Minimize2,
  Maximize2,
} from "lucide-react"
import { useSandboxMonitor } from "@/hooks/useSandbox"
import { EventRenderer } from "@/components/sandbox"

interface AgentPanelProps {
  sandboxId: string | null
  ticketTitle?: string
  taskTitle?: string
  onClose: () => void
  isExpanded?: boolean
  onToggleExpand?: () => void
}

// Status badge configuration
const statusConfig: Record<string, { icon: typeof Loader2; color: string; iconClass: string; label: string }> = {
  pending: { icon: Clock, color: "secondary", iconClass: "", label: "Pending" },
  in_progress: { icon: PlayCircle, color: "warning", iconClass: "", label: "Running" },
  running: { icon: Loader2, color: "warning", iconClass: "animate-spin", label: "Running" },
  completed: { icon: CheckCircle, color: "success", iconClass: "", label: "Completed" },
  failed: { icon: XCircle, color: "destructive", iconClass: "", label: "Failed" },
  cancelled: { icon: XCircle, color: "secondary", iconClass: "", label: "Cancelled" },
}

// Event types to filter out
const HIDDEN_EVENT_TYPES = [
  "agent.heartbeat",
  "SANDBOX_HEARTBEAT",
]

export function AgentPanel({
  sandboxId,
  ticketTitle,
  taskTitle,
  onClose,
  isExpanded = false,
  onToggleExpand,
}: AgentPanelProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)

  // Fetch sandbox events using SSE
  const {
    events,
    isConnected,
    connectionError,
    isLoadingHistory,
    refresh,
  } = useSandboxMonitor(sandboxId)

  // Filter and deduplicate events
  const filteredEvents = useMemo(() => {
    if (!events) return []

    // Filter hidden events
    const visible = events.filter(
      (e) => !HIDDEN_EVENT_TYPES.includes(e.event_type)
    )

    // Simple dedup by event ID
    const seen = new Set<string>()
    return visible.filter((e) => {
      if (seen.has(e.id)) return false
      seen.add(e.id)
      return true
    })
  }, [events])

  // Auto-scroll to bottom on new events
  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: "smooth",
      })
    }
  }, [filteredEvents, autoScroll])

  // Handle scroll to detect manual scroll up
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    const target = e.target as HTMLDivElement
    const isAtBottom =
      target.scrollHeight - target.scrollTop - target.clientHeight < 50
    setAutoScroll(isAtBottom)
  }

  // Determine status from events
  const currentStatus = useMemo(() => {
    if (!events || events.length === 0) return "pending"
    const lastEvent = events[events.length - 1]
    if (lastEvent?.event_type === "agent.completed") return "completed"
    if (lastEvent?.event_type === "agent.error" || lastEvent?.event_type === "agent.failed") return "failed"
    return "running"
  }, [events])

  const StatusIcon = statusConfig[currentStatus]?.icon || Clock
  const statusLabel = statusConfig[currentStatus]?.label || currentStatus
  const statusColor = statusConfig[currentStatus]?.color || "secondary"
  const iconClass = statusConfig[currentStatus]?.iconClass || ""

  // Empty state - no sandbox selected
  if (!sandboxId) {
    return (
      <div className="h-full flex flex-col bg-background border-l">
        <div className="flex items-center justify-between p-3 border-b">
          <div className="flex items-center gap-2">
            <Bot className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium text-sm">Agent Output</span>
          </div>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="flex-1 flex items-center justify-center p-8 text-center">
          <div className="space-y-2">
            <Bot className="h-12 w-12 mx-auto text-muted-foreground/50" />
            <p className="text-sm text-muted-foreground">
              Click a running task to see agent output
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col bg-background border-l">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b bg-muted/30">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          <StatusIcon className={`h-4 w-4 shrink-0 ${iconClass} text-${statusColor}`} />
          <div className="truncate">
            <p className="font-medium text-sm truncate">
              {taskTitle || ticketTitle || `Sandbox ${sandboxId.slice(0, 8)}`}
            </p>
            {ticketTitle && taskTitle && (
              <p className="text-xs text-muted-foreground truncate">{ticketTitle}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {/* Connection indicator */}
          <div className="flex items-center gap-1 mr-2">
            {isConnected ? (
              <Wifi className="h-3 w-3 text-green-500" />
            ) : (
              <WifiOff className="h-3 w-3 text-muted-foreground" />
            )}
          </div>

          {/* Expand/collapse */}
          {onToggleExpand && (
            <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onToggleExpand}>
              {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
            </Button>
          )}

          {/* Open in new tab */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            asChild
          >
            <a href={`/sandbox/${sandboxId}`} target="_blank" rel="noopener noreferrer">
              <ExternalLink className="h-4 w-4" />
            </a>
          </Button>

          {/* Close */}
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Status bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b text-xs">
        <Badge variant={statusColor as "default" | "secondary" | "destructive" | "outline"}>
          {statusLabel}
        </Badge>
        <span className="text-muted-foreground">
          {filteredEvents.length} events
        </span>
        {!autoScroll && (
          <Button
            variant="ghost"
            size="sm"
            className="h-5 text-xs ml-auto"
            onClick={() => {
              setAutoScroll(true)
              scrollRef.current?.scrollTo({
                top: scrollRef.current.scrollHeight,
                behavior: "smooth",
              })
            }}
          >
            Jump to bottom
          </Button>
        )}
      </div>

      {/* Error state */}
      {connectionError && (
        <div className="p-4 border-b bg-destructive/10">
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            <span>Failed to load events</span>
          </div>
        </div>
      )}

      {/* Events */}
      <ScrollArea
        ref={scrollRef}
        className="flex-1"
        onScroll={handleScroll}
      >
        <div className="p-3 space-y-2">
          {filteredEvents.length === 0 && !connectionError && (
            <div className="text-center py-8 text-sm text-muted-foreground">
              <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
              Waiting for agent events...
            </div>
          )}
          {filteredEvents.map((event) => (
            <EventRenderer key={event.id} event={event} />
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
