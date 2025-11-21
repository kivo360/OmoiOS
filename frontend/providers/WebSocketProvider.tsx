"use client"

import { createContext, useContext, useEffect, useRef, useState } from "react"
import { useQueryClient } from "@tanstack/react-query"

interface WebSocketContextValue {
  socket: WebSocket | null
  isConnected: boolean
  send: (type: string, payload: any) => void
}

const WebSocketContext = createContext<WebSocketContextValue>({
  socket: null,
  isConnected: false,
  send: () => {},
})

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>()
  const queryClient = useQueryClient()
  
  useEffect(() => {
    const connect = () => {
      const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:18000/ws'
      const ws = new WebSocket(wsUrl)
      
      ws.onopen = () => {
        setIsConnected(true)
        console.log('WebSocket connected')
      }
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type && data.payload) {
            // Invalidate React Query cache on relevant events
            if (data.type === 'ticket_updated' || data.type === 'ticket_created') {
              queryClient.invalidateQueries({ queryKey: ['tickets'] })
            }
            if (data.type === 'agent_updated' || data.type === 'agent_created') {
              queryClient.invalidateQueries({ queryKey: ['agents'] })
            }
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
        }
      }
      
      ws.onclose = () => {
        setIsConnected(false)
        console.log('WebSocket disconnected, reconnecting...')
        reconnectTimeoutRef.current = setTimeout(connect, 3000)
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
      
      setSocket(ws)
    }
    
    connect()
    
    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      socket?.close()
    }
  }, [queryClient])
  
  const send = (type: string, payload: any) => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type, payload }))
    }
  }

  return (
    <WebSocketContext.Provider value={{ socket, isConnected, send }}>
      {children}
    </WebSocketContext.Provider>
  )
}

export const useWebSocket = () => useContext(WebSocketContext)

