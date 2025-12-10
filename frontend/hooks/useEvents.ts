/**
 * React hooks for real-time WebSocket events
 */

import { useEffect, useState, useCallback, useRef } from "react"

export interface SystemEvent {
  event_type: string
  entity_type: string
  entity_id: string
  payload: Record<string, unknown>
}

export interface EventFilters {
  event_types?: string[]
  entity_types?: string[]
  entity_ids?: string[]
}

interface UseEventsOptions {
  filters?: EventFilters
  onEvent?: (event: SystemEvent) => void
  enabled?: boolean
  maxEvents?: number // Maximum events to keep in buffer
}

interface UseEventsReturn {
  events: SystemEvent[]
  isConnected: boolean
  isConnecting: boolean
  error: string | null
  connect: () => void
  disconnect: () => void
  clearEvents: () => void
  updateFilters: (filters: EventFilters) => void
}

/**
 * Hook for subscribing to real-time WebSocket events
 */
export function useEvents(options: UseEventsOptions = {}): UseEventsReturn {
  const { filters, onEvent, enabled = true, maxEvents = 100 } = options

  const [events, setEvents] = useState<SystemEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const filtersRef = useRef(filters)

  // Update filters ref when they change
  useEffect(() => {
    filtersRef.current = filters
  }, [filters])

  const buildWsUrl = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const host = process.env.NEXT_PUBLIC_API_URL?.replace(/^https?:\/\//, "") || "localhost:18000"

    const params = new URLSearchParams()
    if (filtersRef.current?.event_types?.length) {
      params.set("event_types", filtersRef.current.event_types.join(","))
    }
    if (filtersRef.current?.entity_types?.length) {
      params.set("entity_types", filtersRef.current.entity_types.join(","))
    }
    if (filtersRef.current?.entity_ids?.length) {
      params.set("entity_ids", filtersRef.current.entity_ids.join(","))
    }

    const query = params.toString()
    return `${protocol}//${host}/api/v1/events/ws/events${query ? `?${query}` : ""}`
  }, [])

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (isConnecting) return

    setIsConnecting(true)
    setError(null)

    try {
      const ws = new WebSocket(buildWsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
        setIsConnecting(false)
        setError(null)
        console.log("[WebSocket] Connected to events stream")
      }

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)

          // Handle ping messages
          if (data.type === "ping") return

          // Handle subscription confirmations
          if (data.status === "subscribed") return

          // Handle error messages
          if (data.error) {
            setError(data.error)
            return
          }

          // Process event
          const systemEvent: SystemEvent = {
            event_type: data.event_type,
            entity_type: data.entity_type,
            entity_id: data.entity_id,
            payload: data.payload || {},
          }

          // Add to events buffer
          setEvents((prev) => {
            const next = [systemEvent, ...prev]
            return next.slice(0, maxEvents)
          })

          // Call callback if provided
          onEvent?.(systemEvent)
        } catch (err) {
          console.error("[WebSocket] Failed to parse message:", err)
        }
      }

      ws.onclose = (event) => {
        setIsConnected(false)
        setIsConnecting(false)
        wsRef.current = null

        if (event.code !== 1000 && event.code !== 1001) {
          console.log("[WebSocket] Connection closed, reconnecting in 5s...")
          // Auto-reconnect after 5 seconds
          reconnectTimeoutRef.current = setTimeout(() => {
            if (enabled) connect()
          }, 5000)
        }
      }

      ws.onerror = (event) => {
        console.error("[WebSocket] Error:", event)
        setError("WebSocket connection error")
        setIsConnecting(false)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect")
      setIsConnecting(false)
    }
  }, [buildWsUrl, enabled, maxEvents, onEvent, isConnecting])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    if (wsRef.current) {
      wsRef.current.close(1000)
      wsRef.current = null
    }

    setIsConnected(false)
    setIsConnecting(false)
  }, [])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  const updateFilters = useCallback((newFilters: EventFilters) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

    try {
      wsRef.current.send(JSON.stringify({
        type: "subscribe",
        ...newFilters,
      }))
    } catch (err) {
      console.error("[WebSocket] Failed to update filters:", err)
    }
  }, [])

  // Auto-connect when enabled
  useEffect(() => {
    if (enabled) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
  }, [enabled, connect, disconnect])

  return {
    events,
    isConnected,
    isConnecting,
    error,
    connect,
    disconnect,
    clearEvents,
    updateFilters,
  }
}

/**
 * Hook for subscribing to events for a specific entity
 */
export function useEntityEvents(
  entityType: string,
  entityId: string | undefined,
  options: Omit<UseEventsOptions, "filters"> = {}
) {
  return useEvents({
    ...options,
    filters: entityId ? { entity_types: [entityType], entity_ids: [entityId] } : undefined,
    enabled: options.enabled !== false && !!entityId,
  })
}

/**
 * Hook for subscribing to specific event types
 */
export function useEventTypes(
  eventTypes: string[],
  options: Omit<UseEventsOptions, "filters"> = {}
) {
  return useEvents({
    ...options,
    filters: { event_types: eventTypes },
    enabled: options.enabled !== false && eventTypes.length > 0,
  })
}
