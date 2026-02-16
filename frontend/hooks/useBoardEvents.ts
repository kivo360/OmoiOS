/**
 * Custom hook for handling WebSocket events on the board
 * Provides real-time updates for tickets, tasks, and sandboxes
 */

import { useEffect, useCallback, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { getAccessToken } from "@/lib/api/client"
import { boardKeys } from "./useBoard"
import { ticketKeys } from "./useTickets"

// Event types we care about for the board
export type BoardEventType =
  | "TICKET_CREATED"
  | "TICKET_UPDATED"
  | "TICKET_STATUS_CHANGED"
  | "TICKET_PHASE_ADVANCED"
  | "TASK_CREATED"
  | "TASK_ASSIGNED"
  | "TASK_STATUS_CHANGED"
  | "TASK_COMPLETED"
  | "SANDBOX_SPAWNED"
  | "SANDBOX_COMPLETED"
  | "agent.started"
  | "agent.completed"

export interface BoardEvent {
  event_type: BoardEventType
  entity_type: string
  entity_id: string
  payload: Record<string, unknown>
}

export interface UseBoardEventsOptions {
  projectId?: string
  onEvent?: (event: BoardEvent) => void
  enabled?: boolean
}

export interface RunningTaskInfo {
  taskId: string
  ticketId: string
  sandboxId?: string
  taskTitle?: string
}

export interface BoardEventState {
  isConnected: boolean
  lastEvent: BoardEvent | null
  runningTasks: Map<string, RunningTaskInfo>
}

export function useBoardEvents({
  projectId,
  onEvent,
  enabled = true,
}: UseBoardEventsOptions = {}) {
  const queryClient = useQueryClient()
  const [isConnected, setIsConnected] = useState(false)
  const [lastEvent, setLastEvent] = useState<BoardEvent | null>(null)
  const [runningTasks, setRunningTasks] = useState<Map<string, RunningTaskInfo>>(new Map())
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const reconnectAttemptsRef = useRef(0)

  const handleEvent = useCallback(
    (event: BoardEvent) => {
      setLastEvent(event)

      // Track running tasks - using state to trigger re-renders
      if (event.event_type === "TASK_ASSIGNED" || event.event_type === "agent.started" || event.event_type === "SANDBOX_SPAWNED") {
        const taskId = event.entity_id
        const ticketId = (event.payload.ticket_id as string) || ""
        const sandboxId = (event.payload.sandbox_id as string) || (event.entity_type === "sandbox" ? event.entity_id : undefined)
        const taskTitle = event.payload.task_title as string | undefined
        setRunningTasks((prev) => {
          const next = new Map(prev)
          next.set(taskId, { taskId, ticketId, sandboxId, taskTitle })
          return next
        })
      }

      if (event.event_type === "TASK_COMPLETED" || event.event_type === "agent.completed" || event.event_type === "SANDBOX_COMPLETED") {
        setRunningTasks((prev) => {
          const next = new Map(prev)
          next.delete(event.entity_id)
          return next
        })
      }

      // Invalidate appropriate queries based on event type
      switch (event.event_type) {
        case "TICKET_CREATED":
        case "TICKET_UPDATED":
        case "TICKET_STATUS_CHANGED":
        case "TICKET_PHASE_ADVANCED":
          queryClient.invalidateQueries({ queryKey: boardKeys.all })
          queryClient.invalidateQueries({ queryKey: ticketKeys.lists() })
          if (event.entity_id) {
            queryClient.invalidateQueries({ queryKey: ticketKeys.detail(event.entity_id) })
          }
          break

        case "TASK_CREATED":
        case "TASK_ASSIGNED":
        case "TASK_STATUS_CHANGED":
        case "TASK_COMPLETED":
          // Tasks affect the board view
          queryClient.invalidateQueries({ queryKey: boardKeys.all })
          // Also invalidate the parent ticket
          if (event.payload.ticket_id) {
            queryClient.invalidateQueries({
              queryKey: ticketKeys.detail(event.payload.ticket_id as string),
            })
          }
          break

        case "SANDBOX_SPAWNED":
        case "SANDBOX_COMPLETED":
        case "agent.started":
        case "agent.completed":
          // Sandbox events affect task display
          queryClient.invalidateQueries({ queryKey: boardKeys.all })
          break
      }

      // Call custom event handler if provided
      onEvent?.(event)
    },
    [queryClient, onEvent]
  )

  useEffect(() => {
    if (!enabled) {
      return
    }

    const connect = () => {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"
      const wsUrl =
        apiUrl.replace("http://", "ws://").replace("https://", "wss://") +
        "/api/v1/ws/events"

      // Build query params with auth token and optional project filter
      const params = new URLSearchParams()
      const token = getAccessToken()
      if (token) {
        params.set("token", token)
      }
      if (projectId) {
        params.set("entity_ids", projectId)
      }
      const query = params.toString()
      const url = query ? `${wsUrl}?${query}` : wsUrl

      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        reconnectAttemptsRef.current = 0
        console.log("[BoardEvents] WebSocket connected")

        // Subscribe to board-relevant events
        ws.send(
          JSON.stringify({
            type: "subscribe",
            event_types: [
              "TICKET_CREATED",
              "TICKET_UPDATED",
              "TICKET_STATUS_CHANGED",
              "TICKET_PHASE_ADVANCED",
              "TASK_CREATED",
              "TASK_ASSIGNED",
              "TASK_STATUS_CHANGED",
              "TASK_COMPLETED",
              "SANDBOX_SPAWNED",
              "SANDBOX_COMPLETED",
              "agent.started",
              "agent.completed",
            ],
          })
        )
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // Skip ping messages
          if (data.type === "ping") {
            return
          }

          // Handle subscription confirmation
          if (data.status === "subscribed") {
            console.log("[BoardEvents] Subscription confirmed:", data.filters)
            return
          }

          // Process event
          if (data.event_type) {
            handleEvent(data as BoardEvent)
          }
        } catch (error) {
          console.error("[BoardEvents] Failed to parse message:", error)
        }
      }

      ws.onclose = (event) => {
        setIsConnected(false)

        // Don't reconnect for auth errors
        if (event.code === 1008 || event.code === 1003 || event.code === 1000 || event.code === 4401) {
          console.log("[BoardEvents] WebSocket closed normally")
          return
        }

        // Exponential backoff for reconnection
        const maxAttempts = 5
        if (reconnectAttemptsRef.current < maxAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000)
          reconnectAttemptsRef.current++
          console.log(
            `[BoardEvents] Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current}/${maxAttempts})`
          )
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        }
      }

      ws.onerror = (error) => {
        console.error("[BoardEvents] WebSocket error:", error)
      }
    }

    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close(1000)
      }
    }
  }, [enabled, projectId, handleEvent])

  // Helper to get running tasks for a specific ticket
  const getRunningTasksForTicket = useCallback(
    (ticketId: string): RunningTaskInfo[] => {
      return Array.from(runningTasks.values()).filter((t) => t.ticketId === ticketId)
    },
    [runningTasks]
  )

  return {
    isConnected,
    lastEvent,
    runningTasks,
    getRunningTasksForTicket,
  }
}
