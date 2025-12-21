/**
 * React hooks for sandbox operations and real-time events
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { useCallback, useState, useMemo } from "react"
import { sandboxApi } from "@/lib/api/sandbox"
import { useEvents, type SystemEvent } from "./useEvents"
import type {
  SandboxEvent,
  SandboxMessage,
  SandboxTask,
  TrajectorySummaryResponse,
  SandboxEventsListResponse,
} from "@/lib/api/types"

// ============================================================================
// Query Keys
// ============================================================================

export const sandboxKeys = {
  all: ["sandboxes"] as const,
  events: (sandboxId: string) => [...sandboxKeys.all, "events", sandboxId] as const,
  trajectory: (sandboxId: string) => [...sandboxKeys.all, "trajectory", sandboxId] as const,
  messages: (sandboxId: string) => [...sandboxKeys.all, "messages", sandboxId] as const,
  task: (sandboxId: string) => [...sandboxKeys.all, "task", sandboxId] as const,
}

// ============================================================================
// Hooks for Sandbox Events (HTTP API)
// ============================================================================

/**
 * Fetch sandbox events from database
 */
export function useSandboxEvents(
  sandboxId: string | null,
  options: {
    limit?: number
    offset?: number
    event_type?: string
    enabled?: boolean
  } = {}
) {
  const { limit = 100, offset = 0, event_type, enabled = true } = options

  return useQuery({
    queryKey: [...sandboxKeys.events(sandboxId || ""), { limit, offset, event_type }],
    queryFn: () => sandboxApi.getEvents(sandboxId!, { limit, offset, event_type }),
    enabled: enabled && !!sandboxId,
  })
}

/**
 * Fetch task associated with a sandbox
 */
export function useSandboxTask(sandboxId: string | null, options: { enabled?: boolean } = {}) {
  const { enabled = true } = options

  return useQuery<SandboxTask>({
    queryKey: sandboxKeys.task(sandboxId || ""),
    queryFn: () => sandboxApi.getTask(sandboxId!),
    enabled: enabled && !!sandboxId,
  })
}

/**
 * Fetch sandbox trajectory (events without heartbeats, with summary)
 */
export function useSandboxTrajectory(
  sandboxId: string | null,
  options: {
    limit?: number
    offset?: number
    enabled?: boolean
  } = {}
) {
  const { limit = 100, offset = 0, enabled = true } = options

  return useQuery({
    queryKey: [...sandboxKeys.trajectory(sandboxId || ""), { limit, offset }],
    queryFn: () => sandboxApi.getTrajectory(sandboxId!, { limit, offset }),
    enabled: enabled && !!sandboxId,
  })
}

// ============================================================================
// Hooks for Real-time Sandbox Events (WebSocket)
// ============================================================================

/**
 * Subscribe to real-time sandbox events via WebSocket
 */
export function useSandboxRealtimeEvents(
  sandboxId: string | null,
  options: {
    enabled?: boolean
    onEvent?: (event: SandboxEvent) => void
  } = {}
) {
  const { enabled = true, onEvent } = options
  const [events, setEvents] = useState<SandboxEvent[]>([])

  // Transform WebSocket event to SandboxEvent
  const handleEvent = useCallback(
    (systemEvent: SystemEvent) => {
      const sandboxEvent: SandboxEvent = {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        sandbox_id: systemEvent.entity_id,
        event_type: (systemEvent.payload.original_event_type as string) || systemEvent.event_type,
        event_data: systemEvent.payload,
        source: (systemEvent.payload.source as "agent" | "worker" | "system") || "agent",
        created_at: new Date().toISOString(),
      }

      setEvents((prev) => [sandboxEvent, ...prev].slice(0, 500))
      onEvent?.(sandboxEvent)
    },
    [onEvent]
  )

  // Subscribe to sandbox events via WebSocket
  const { isConnected, isConnecting, error, clearEvents } = useEvents({
    enabled: enabled && !!sandboxId,
    filters: sandboxId
      ? {
          entity_types: ["sandbox"],
          entity_ids: [sandboxId],
        }
      : undefined,
    onEvent: handleEvent,
    maxEvents: 500,
  })

  const clear = useCallback(() => {
    setEvents([])
    clearEvents()
  }, [clearEvents])

  return {
    events,
    isConnected,
    isConnecting,
    error,
    clearEvents: clear,
  }
}

// ============================================================================
// Hooks for Sandbox Messages
// ============================================================================

/**
 * Send a message to a sandbox
 */
export function useSendSandboxMessage() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ sandboxId, message }: { sandboxId: string; message: SandboxMessage }) =>
      sandboxApi.sendMessage(sandboxId, message),
    onSuccess: (_, { sandboxId }) => {
      // Invalidate messages query
      queryClient.invalidateQueries({ queryKey: sandboxKeys.messages(sandboxId) })
    },
  })
}

/**
 * Get pending messages for a sandbox
 */
export function useSandboxMessages(sandboxId: string | null, options: { enabled?: boolean } = {}) {
  const { enabled = true } = options

  return useQuery({
    queryKey: sandboxKeys.messages(sandboxId || ""),
    queryFn: () => sandboxApi.getMessages(sandboxId!),
    enabled: enabled && !!sandboxId,
  })
}

// ============================================================================
// Combined Hook for Sandbox Monitoring
// ============================================================================

/**
 * Combined hook for monitoring a sandbox with real-time events and message sending
 */
export function useSandboxMonitor(sandboxId: string | null) {
  const queryClient = useQueryClient()

  // Real-time events
  const {
    events: realtimeEvents,
    isConnected,
    isConnecting,
    error: connectionError,
    clearEvents,
  } = useSandboxRealtimeEvents(sandboxId, {
    enabled: !!sandboxId,
  })

  // Historical events (for initial load)
  const {
    data: historicalData,
    isLoading: isLoadingHistory,
    error: historyError,
  } = useSandboxTrajectory(sandboxId, {
    limit: 100,
    enabled: !!sandboxId,
  })

  // Send message mutation
  const sendMessageMutation = useSendSandboxMessage()

  // Memoize historical events reference
  const historicalEvents = useMemo(
    () => historicalData?.events || [],
    [historicalData?.events]
  )

  // Combine historical and real-time events with memoization
  // Real-time events are newer, so they go first
  const uniqueEvents = useMemo(() => {
    const allEvents = [...realtimeEvents, ...historicalEvents]

    // Deduplicate by event type + created_at (rough dedup)
    return allEvents.reduce((acc, event) => {
      const key = `${event.event_type}-${event.created_at}`
      if (!acc.some((e) => `${e.event_type}-${e.created_at}` === key)) {
        acc.push(event)
      }
      return acc
    }, [] as SandboxEvent[])
  }, [realtimeEvents, historicalEvents])

  // Memoize sendMessage callback
  const sendMessage = useCallback(
    (content: string, messageType?: SandboxMessage["message_type"]) => {
      if (!sandboxId) return
      return sendMessageMutation.mutateAsync({
        sandboxId,
        message: { content, message_type: messageType || "user_message" },
      })
    },
    [sandboxId, sendMessageMutation]
  )

  // Memoize refresh callback
  const refresh = useCallback(() => {
    if (sandboxId) {
      queryClient.invalidateQueries({ queryKey: sandboxKeys.trajectory(sandboxId) })
    }
  }, [sandboxId, queryClient])

  return {
    // Events
    events: uniqueEvents,
    realtimeEvents,
    historicalEvents,
    heartbeatSummary: historicalData?.heartbeat_summary,
    totalEvents: historicalData?.total_events || 0,

    // Connection state
    isConnected,
    isConnecting,
    connectionError,
    isLoadingHistory,
    historyError,

    // Actions
    sendMessage,
    isSendingMessage: sendMessageMutation.isPending,
    clearEvents,

    // Refresh
    refresh,
  }
}
