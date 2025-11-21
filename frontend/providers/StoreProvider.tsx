"use client"

import { useEffect, useRef } from 'react'
import { useWebSocket } from './WebSocketProvider'

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const { socket } = useWebSocket()
  const hasHydrated = useRef(false)
  
  // Setup WebSocket connections for stores
  useEffect(() => {
    if (socket) {
      // Store WebSocket references will be set when stores are created
      // setKanbanWebSocket(socket)
      // setAgentWebSocket(socket)
    }
    
    return () => {
      // Cleanup
      // setKanbanWebSocket(null)
      // setAgentWebSocket(null)
    }
  }, [socket])
  
  // Manual hydration for SSR compatibility
  useEffect(() => {
    if (!hasHydrated.current) {
      // Store hydration will be added when stores are created
      // useKanbanStore.persist?.rehydrate()
      // useAgentStore.persist?.rehydrate()
      // useUIStore.persist?.rehydrate()
      hasHydrated.current = true
    }
  }, [])
  
  return <>{children}</>
}

