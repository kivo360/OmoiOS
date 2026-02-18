"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { getAccessToken } from "@/lib/api/client";

interface WebSocketContextValue {
  socket: WebSocket | null;
  isConnected: boolean;
  send: (type: string, payload: any) => void;
}

const WebSocketContext = createContext<WebSocketContextValue>({
  socket: null,
  isConnected: false,
  send: () => {},
});

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const queryClient = useQueryClient();

  useEffect(() => {
    let isMounted = true;
    let reconnectAttempts = 0;
    const MAX_RECONNECT_ATTEMPTS = 5;
    const RECONNECT_DELAY = 3000;

    const connect = () => {
      // Use the correct WebSocket endpoint
      const apiUrl =
        process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000";
      const baseWsUrl =
        apiUrl.replace("http://", "ws://").replace("https://", "wss://") +
        "/api/v1/ws/events";
      const token = getAccessToken();
      const wsUrl = token
        ? `${baseWsUrl}?token=${encodeURIComponent(token)}`
        : baseWsUrl;

      const ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        if (!isMounted) {
          ws.close();
          return;
        }
        setIsConnected(true);
        reconnectAttempts = 0; // Reset on successful connection
        console.log("WebSocket connected");
      };

      ws.onmessage = (event) => {
        if (!isMounted) return;
        try {
          const data = JSON.parse(event.data);
          if (data.type && data.payload) {
            // Invalidate React Query cache on relevant events
            if (
              data.type === "ticket_updated" ||
              data.type === "ticket_created"
            ) {
              queryClient.invalidateQueries({ queryKey: ["tickets"] });
            }
            if (
              data.type === "agent_updated" ||
              data.type === "agent_created"
            ) {
              queryClient.invalidateQueries({ queryKey: ["agents"] });
            }
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      ws.onclose = (event) => {
        if (!isMounted) return;

        setIsConnected(false);

        // Don't reconnect if:
        // 1. Close code is 1008 (policy violation) or 1003 (forbidden) - likely auth issue
        // 2. We've exceeded max reconnect attempts
        // 3. Close code is 1000 (normal closure)
        const shouldReconnect =
          event.code !== 1008 &&
          event.code !== 1003 &&
          event.code !== 1000 &&
          event.code !== 4401 &&
          reconnectAttempts < MAX_RECONNECT_ATTEMPTS;

        if (shouldReconnect) {
          reconnectAttempts++;
          console.log(
            `WebSocket disconnected (code: ${event.code}), reconnecting in ${RECONNECT_DELAY}ms... (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`,
          );
          reconnectTimeoutRef.current = setTimeout(connect, RECONNECT_DELAY);
        } else {
          if (
            event.code === 1008 ||
            event.code === 1003 ||
            event.code === 4401
          ) {
            console.warn(
              "WebSocket connection rejected (auth required). Code:",
              event.code,
            );
          } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            console.error(
              "WebSocket: Max reconnect attempts reached. Stopping reconnection.",
            );
          } else {
            console.log("WebSocket closed normally");
          }
        }
      };

      ws.onerror = (error) => {
        if (!isMounted) return;
        console.error("WebSocket error:", error);
      };

      setSocket(ws);
    };

    connect();

    return () => {
      isMounted = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      socket?.close();
    };
  }, [queryClient]);

  const send = (type: string, payload: any) => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type, payload }));
    }
  };

  return (
    <WebSocketContext.Provider value={{ socket, isConnected, send }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export const useWebSocket = () => useContext(WebSocketContext);
