/**
 * React hooks for real-time WebSocket events
 */

import { useEffect, useState, useCallback, useRef } from "react"
import { getAccessToken } from "@/lib/api/client"

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
  const onEventRef = useRef(onEvent)
  const enabledRef = useRef(enabled)

  // Update refs when they change
  useEffect(() => {
    filtersRef.current = filters
  }, [filters])

  useEffect(() => {
    onEventRef.current = onEvent
  }, [onEvent])

  useEffect(() => {
    enabledRef.current = enabled
  }, [enabled])

  const buildWsUrl = useCallback(() => {
    // Get API base URL, default to localhost:18000
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"

    // Parse the URL to get host and determine protocol
    let wsUrl: string
    try {
      const url = new URL(apiUrl)
      const wsProtocol = url.protocol === "https:" ? "wss:" : "ws:"
      wsUrl = `${wsProtocol}//${url.host}/api/v1/ws/events`
    } catch {
      // Fallback for invalid URLs
      wsUrl = "ws://localhost:18000/api/v1/ws/events"
    }

    const params = new URLSearchParams()
    const token = getAccessToken()
    if (token) {
      params.set("token", token)
    }
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
    return query ? `${wsUrl}?${query}` : wsUrl
  }, [])

  // Use ref to track connecting state to avoid dependency issues
  const isConnectingRef = useRef(false)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (isConnectingRef.current) return

    isConnectingRef.current = true
    setIsConnecting(true)
    setError(null)

    try {
      const url = buildWsUrl()
      console.log("[WebSocket] Connecting to:", url)
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        isConnectingRef.current = false
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
          onEventRef.current?.(systemEvent)
        } catch (err) {
          console.error("[WebSocket] Failed to parse message:", err)
        }
      }

      ws.onclose = (event) => {
        console.log("[WebSocket] Connection closed - code:", event.code, "reason:", event.reason)
        isConnectingRef.current = false
        setIsConnected(false)
        setIsConnecting(false)
        wsRef.current = null

        // Only auto-reconnect on abnormal closures (not auth failures)
        if (event.code !== 1000 && event.code !== 1001 && event.code !== 4401) {
          console.log("[WebSocket] Will reconnect in 5s...")
          reconnectTimeoutRef.current = setTimeout(() => {
            connect()
          }, 5000)
        }
      }

      ws.onerror = () => {
        // WebSocket error events don't contain useful info in browsers
        // The error is usually followed by onclose with more details
        console.error("[WebSocket] Error occurred - url:", url)
        isConnectingRef.current = false
        setError("WebSocket connection error")
        setIsConnecting(false)
      }
    } catch (err) {
      isConnectingRef.current = false
      setError(err instanceof Error ? err.message : "Failed to connect")
      setIsConnecting(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [buildWsUrl, maxEvents])

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

  // Auto-connect when enabled changes
  useEffect(() => {
    if (enabled) {
      connect()
    } else {
      disconnect()
    }

    return () => {
      disconnect()
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled])

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
