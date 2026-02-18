/**
 * React hooks for sandbox operations and real-time events
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useState, useMemo, useEffect } from "react";
import { sandboxApi } from "@/lib/api/sandbox";
import { useEvents, type SystemEvent } from "./useEvents";
import type {
  SandboxEvent,
  SandboxMessage,
  SandboxTask,
  TrajectorySummaryResponse,
  SandboxEventsListResponse,
} from "@/lib/api/types";

// ============================================================================
// Query Keys
// ============================================================================

export const sandboxKeys = {
  all: ["sandboxes"] as const,
  events: (sandboxId: string) =>
    [...sandboxKeys.all, "events", sandboxId] as const,
  trajectory: (sandboxId: string) =>
    [...sandboxKeys.all, "trajectory", sandboxId] as const,
  messages: (sandboxId: string) =>
    [...sandboxKeys.all, "messages", sandboxId] as const,
  task: (sandboxId: string) => [...sandboxKeys.all, "task", sandboxId] as const,
};

// ============================================================================
// Hooks for Sandbox Events (HTTP API)
// ============================================================================

/**
 * Fetch sandbox events from database
 */
export function useSandboxEvents(
  sandboxId: string | null,
  options: {
    limit?: number;
    offset?: number;
    event_type?: string;
    enabled?: boolean;
  } = {},
) {
  const { limit = 100, offset = 0, event_type, enabled = true } = options;

  return useQuery({
    queryKey: [
      ...sandboxKeys.events(sandboxId || ""),
      { limit, offset, event_type },
    ],
    queryFn: () =>
      sandboxApi.getEvents(sandboxId!, { limit, offset, event_type }),
    enabled: enabled && !!sandboxId,
  });
}

/**
 * Fetch task associated with a sandbox
 */
export function useSandboxTask(
  sandboxId: string | null,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options;

  return useQuery<SandboxTask>({
    queryKey: sandboxKeys.task(sandboxId || ""),
    queryFn: () => sandboxApi.getTask(sandboxId!),
    enabled: enabled && !!sandboxId,
  });
}

/**
 * Fetch sandbox trajectory (events without heartbeats, with summary)
 * Supports cursor-based pagination for infinite scroll
 */
export function useSandboxTrajectory(
  sandboxId: string | null,
  options: {
    limit?: number;
    cursor?: string | null;
    direction?: "older" | "newer";
    enabled?: boolean;
  } = {},
) {
  const { limit = 100, cursor, direction, enabled = true } = options;

  return useQuery({
    queryKey: [
      ...sandboxKeys.trajectory(sandboxId || ""),
      { limit, cursor, direction },
    ],
    queryFn: () =>
      sandboxApi.getTrajectory(sandboxId!, { limit, cursor, direction }),
    enabled: enabled && !!sandboxId,
  });
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
    enabled?: boolean;
    onEvent?: (event: SandboxEvent) => void;
  } = {},
) {
  const { enabled = true, onEvent } = options;
  const [events, setEvents] = useState<SandboxEvent[]>([]);

  // Transform WebSocket event to SandboxEvent
  const handleEvent = useCallback(
    (systemEvent: SystemEvent) => {
      const sandboxEvent: SandboxEvent = {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        sandbox_id: systemEvent.entity_id,
        event_type:
          (systemEvent.payload.original_event_type as string) ||
          systemEvent.event_type,
        event_data: systemEvent.payload,
        source:
          (systemEvent.payload.source as "agent" | "worker" | "system") ||
          "agent",
        created_at: new Date().toISOString(),
      };

      setEvents((prev) => [sandboxEvent, ...prev].slice(0, 500));
      onEvent?.(sandboxEvent);
    },
    [onEvent],
  );

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
  });

  const clear = useCallback(() => {
    setEvents([]);
    clearEvents();
  }, [clearEvents]);

  return {
    events,
    isConnected,
    isConnecting,
    error,
    clearEvents: clear,
  };
}

// ============================================================================
// Hooks for Sandbox Messages
// ============================================================================

/**
 * Send a message to a sandbox
 */
export function useSendSandboxMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      sandboxId,
      message,
    }: {
      sandboxId: string;
      message: SandboxMessage;
    }) => sandboxApi.sendMessage(sandboxId, message),
    onSuccess: (_, { sandboxId }) => {
      // Invalidate messages query
      queryClient.invalidateQueries({
        queryKey: sandboxKeys.messages(sandboxId),
      });
    },
  });
}

/**
 * Get pending messages for a sandbox
 */
export function useSandboxMessages(
  sandboxId: string | null,
  options: { enabled?: boolean } = {},
) {
  const { enabled = true } = options;

  return useQuery({
    queryKey: sandboxKeys.messages(sandboxId || ""),
    queryFn: () => sandboxApi.getMessages(sandboxId!),
    enabled: enabled && !!sandboxId,
  });
}

// ============================================================================
// Combined Hook for Sandbox Monitoring
// ============================================================================

/**
 * Combined hook for monitoring a sandbox with real-time events, message sending,
 * and cursor-based infinite scroll pagination.
 */
export function useSandboxMonitor(sandboxId: string | null) {
  const queryClient = useQueryClient();

  // State for infinite scroll pagination
  const [olderEvents, setOlderEvents] = useState<SandboxEvent[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  // Real-time events
  const {
    events: realtimeEvents,
    isConnected,
    isConnecting,
    error: connectionError,
    clearEvents,
  } = useSandboxRealtimeEvents(sandboxId, {
    enabled: !!sandboxId,
  });

  // Historical events (for initial load)
  // Request 100 events per page (events are returned newest-first from API)
  const {
    data: historicalData,
    isLoading: isLoadingHistory,
    error: historyError,
  } = useSandboxTrajectory(sandboxId, {
    limit: 100,
    enabled: !!sandboxId,
  });

  // Reset pagination state when sandbox changes
  useEffect(() => {
    setOlderEvents([]);
    setNextCursor(null);
    setHasMore(false);
  }, [sandboxId]);

  // Update cursor and hasMore when initial data loads
  useEffect(() => {
    if (historicalData) {
      setNextCursor(historicalData.next_cursor);
      setHasMore(historicalData.has_more);
    }
  }, [historicalData]);

  // Send message mutation
  const sendMessageMutation = useSendSandboxMessage();

  // Memoize historical events reference (initial page)
  // API returns events newest-first, so we reverse to get chronological order for display
  const initialEvents = useMemo(
    () => (historicalData?.events || []).slice().reverse(),
    [historicalData?.events],
  );

  // Load more older events (for infinite scroll)
  const loadMoreEvents = useCallback(async () => {
    if (!sandboxId || !nextCursor || isLoadingMore) return;

    setIsLoadingMore(true);
    try {
      const data = await sandboxApi.getTrajectory(sandboxId, {
        limit: 100,
        cursor: nextCursor,
        direction: "older",
      });

      // Reverse to get chronological order (oldest first within this batch)
      const newEvents = data.events.slice().reverse();
      // Prepend older events (they go before the initial events)
      setOlderEvents((prev) => [...newEvents, ...prev]);
      setNextCursor(data.next_cursor);
      setHasMore(data.has_more);
    } catch (error) {
      console.error("Failed to load more events:", error);
    } finally {
      setIsLoadingMore(false);
    }
  }, [sandboxId, nextCursor, isLoadingMore]);

  // Combine all events: older (loaded via infinite scroll) + initial + realtime
  // Order: oldest first (chronological)
  const uniqueEvents = useMemo(() => {
    // olderEvents are already chronological (oldest first)
    // initialEvents are already chronological (oldest first within initial page)
    // realtimeEvents are newest first, so we need to handle them carefully
    const allEvents = [...olderEvents, ...initialEvents, ...realtimeEvents];

    // Deduplicate by event ID (most reliable) or fallback to type+timestamp
    const seen = new Set<string>();
    return allEvents.filter((event) => {
      const key = event.id || `${event.event_type}-${event.created_at}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [olderEvents, initialEvents, realtimeEvents]);

  // Memoize sendMessage callback
  const sendMessage = useCallback(
    (content: string, messageType?: SandboxMessage["message_type"]) => {
      if (!sandboxId) return;
      return sendMessageMutation.mutateAsync({
        sandboxId,
        message: { content, message_type: messageType || "user_message" },
      });
    },
    [sandboxId, sendMessageMutation],
  );

  // Memoize refresh callback - also clears loaded older events
  const refresh = useCallback(() => {
    if (sandboxId) {
      setOlderEvents([]);
      setNextCursor(null);
      setHasMore(false);
      queryClient.invalidateQueries({
        queryKey: sandboxKeys.trajectory(sandboxId),
      });
    }
  }, [sandboxId, queryClient]);

  // Clear all events including loaded older events
  const clearAllEvents = useCallback(() => {
    setOlderEvents([]);
    clearEvents();
  }, [clearEvents]);

  return {
    // Events
    events: uniqueEvents,
    realtimeEvents,
    historicalEvents: [...olderEvents, ...initialEvents],
    heartbeatSummary: historicalData?.heartbeat_summary,
    totalEvents: historicalData?.total_events || 0,

    // Connection state
    isConnected,
    isConnecting,
    connectionError,
    isLoadingHistory,
    historyError,

    // Pagination
    hasMore,
    isLoadingMore,
    loadMoreEvents,

    // Actions
    sendMessage,
    isSendingMessage: sendMessageMutation.isPending,
    clearEvents: clearAllEvents,

    // Refresh
    refresh,
  };
}
