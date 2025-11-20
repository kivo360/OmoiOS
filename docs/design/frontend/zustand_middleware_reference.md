# Zustand Middleware Reference

**Created**: 2025-11-20
**Status**: Technical Reference
**Purpose**: Comprehensive guide to custom Zustand middleware implementations for OmoiOS frontend.

---

## Overview

This document provides complete implementations of custom Zustand middleware that integrate with:
- **WebSocket** real-time synchronization
- **React Query** cache management
- **SSR** compatibility
- **Persistence** with compression and encryption
- **Time-travel** debugging

---

## 1. WebSocket Sync Middleware

Synchronizes Zustand state with WebSocket events in real-time.

### Implementation

```typescript
// middleware/websocket-sync.ts
import { StateCreator, StoreMutatorIdentifier } from 'zustand'
import { produce } from 'immer'

type WebSocketSync = <
  T,
  Mps extends [StoreMutatorIdentifier, unknown][] = [],
  Mcs extends [StoreMutatorIdentifier, unknown][] = []
>(
  config: StateCreator<T, Mps, Mcs>,
  options: WebSocketSyncOptions<T>
) => StateCreator<T, Mps, Mcs>

interface WebSocketSyncOptions<T> {
  /** Function to get current WebSocket instance */
  getWebSocket: () => WebSocket | null
  
  /** Event types to listen for */
  eventTypes: string[]
  
  /** Transform incoming message to state update */
  onMessage: (message: any, currentState: T) => Partial<T> | ((state: T) => T)
  
  /** Optional: Send state changes back through WebSocket */
  syncToServer?: boolean
  
  /** Optional: Filter which state changes should be synced */
  shouldSync?: (prevState: T, nextState: T) => boolean
  
  /** Optional: Transform state before sending to server */
  serialize?: (state: T) => any
}

export const websocketSync: WebSocketSync = (config, options) => (set, get, api) => {
  let unsubscribe: (() => void) | null = null
  
  // Setup WebSocket message listener
  const setupWebSocketListener = () => {
    const ws = options.getWebSocket()
    if (!ws) return
    
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        
        // Check if message matches our event types
        if (options.eventTypes.includes(data.type || data.event_type)) {
          const update = options.onMessage(data, get())
          
          if (typeof update === 'function') {
            // Function-based update (immer-style)
            set(produce(update))
          } else {
            // Object merge update
            set(update as any)
          }
        }
      } catch (error) {
        console.error('WebSocket message parsing error:', error)
      }
    }
    
    ws.addEventListener('message', handleMessage)
    
    unsubscribe = () => {
      ws.removeEventListener('message', handleMessage)
    }
  }
  
  // Enhanced set function that optionally syncs to server
  const enhancedSet: typeof set = (partial, replace) => {
    const prevState = get()
    
    set(partial, replace)
    
    const nextState = get()
    
    // Optionally sync to server
    if (options.syncToServer) {
      const shouldSync = options.shouldSync?.(prevState, nextState) ?? true
      
      if (shouldSync) {
        const ws = options.getWebSocket()
        const payload = options.serialize?.(nextState) ?? nextState
        
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'STATE_UPDATE',
            payload,
          }))
        }
      }
    }
  }
  
  // Initialize WebSocket listener (client-side only)
  if (typeof window !== 'undefined') {
    setupWebSocketListener()
  }
  
  // Cleanup on store destruction
  ;(api as any).destroy = () => {
    unsubscribe?.()
  }
  
  return config(enhancedSet, get, api)
}
```

### Usage Example

```typescript
import { create } from 'zustand'
import { websocketSync } from '@/middleware/websocket-sync'

let wsInstance: WebSocket | null = null
export const setWebSocket = (ws: WebSocket | null) => {
  wsInstance = ws
}

export const useStore = create(
  websocketSync(
    (set) => ({
      items: [],
      addItem: (item) => set((state) => ({ items: [...state.items, item] })),
    }),
    {
      getWebSocket: () => wsInstance,
      eventTypes: ['ITEM_CREATED', 'ITEM_UPDATED'],
      onMessage: (message, state) => {
        if (message.type === 'ITEM_CREATED') {
          return { items: [...state.items, message.payload] }
        }
        return {}
      },
    }
  )
)
```

---

## 2. React Query Bridge Middleware

Bidirectional synchronization between Zustand and React Query.

### Implementation

```typescript
// middleware/react-query-bridge.ts
import { QueryClient, QueryKey } from '@tanstack/react-query'
import { StateCreator, StoreMutatorIdentifier } from 'zustand'

type ReactQueryBridge = <
  T,
  Mps extends [StoreMutatorIdentifier, unknown][] = [],
  Mcs extends [StoreMutatorIdentifier, unknown][] = []
>(
  config: StateCreator<T, Mps, Mcs>,
  options: ReactQueryBridgeOptions<T>
) => StateCreator<T, Mps, Mcs>

interface ReactQueryBridgeOptions<T> {
  /** React Query client instance */
  queryClient: QueryClient
  
  /** Rules for when to invalidate React Query cache */
  invalidationRules: Array<{
    /** Check if this state change should trigger invalidation */
    shouldInvalidate: (prevState: T, nextState: T) => boolean
    
    /** Query keys to invalidate (can be dynamic based on state) */
    queryKeys: QueryKey[] | ((state: T) => QueryKey[])
    
    /** Optional: Apply optimistic update to React Query cache */
    optimisticUpdate?: (state: T) => Array<{
      queryKey: QueryKey
      updater: (old: any) => any
    }>
  }>
  
  /** Optional: Sync React Query data to Zustand */
  syncRules?: Array<{
    /** Query key to watch */
    queryKey: QueryKey
    
    /** Transform query data to Zustand state */
    toState: (data: any) => Partial<T>
    
    /** Optional: Condition to sync */
    shouldSync?: (data: any) => boolean
  }>
}

export const reactQueryBridge: ReactQueryBridge = (config, options) => (set, get, api) => {
  const { queryClient, invalidationRules, syncRules } = options
  
  // Enhanced set that triggers React Query invalidations
  const enhancedSet: typeof set = (partial, replace) => {
    const prevState = get()
    
    set(partial, replace)
    
    const nextState = get()
    
    // Process invalidation rules
    invalidationRules.forEach((rule) => {
      if (rule.shouldInvalidate(prevState, nextState)) {
        const keys = typeof rule.queryKeys === 'function' 
          ? rule.queryKeys(nextState) 
          : rule.queryKeys
        
        // Apply optimistic updates
        if (rule.optimisticUpdate) {
          const updates = rule.optimisticUpdate(nextState)
          updates.forEach(({ queryKey, updater }) => {
            queryClient.setQueryData(queryKey, updater)
          })
        }
        
        // Invalidate queries
        keys.forEach((key) => {
          queryClient.invalidateQueries({ queryKey: key })
        })
      }
    })
  }
  
  // Setup React Query sync (client-side only)
  if (typeof window !== 'undefined' && syncRules) {
    syncRules.forEach(({ queryKey, toState, shouldSync }) => {
      // Subscribe to query changes
      const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
        if (event?.type !== 'updated') return
        
        const query = queryClient.getQueryCache().find({ queryKey })
        if (!query) return
        
        const data = query.state.data
        
        if (data && (!shouldSync || shouldSync(data))) {
          const stateUpdate = toState(data)
          set(stateUpdate as any)
        }
      })
      
      // Store unsubscribe for cleanup
      ;(api as any)._unsubscribers = (api as any)._unsubscribers || []
      ;(api as any)._unsubscribers.push(unsubscribe)
    })
  }
  
  return config(enhancedSet, get, api)
}
```

### Usage Example

```typescript
import { create } from 'zustand'
import { reactQueryBridge } from '@/middleware/react-query-bridge'
import { boardKeys } from '@/lib/query-keys'

export const useBoardStore = create(
  reactQueryBridge(
    (set) => ({
      tickets: {},
      updateTicket: (id, updates) => 
        set((state) => ({
          tickets: {
            ...state.tickets,
            [id]: { ...state.tickets[id], ...updates }
          }
        })),
    }),
    {
      queryClient, // Passed from provider
      invalidationRules: [
        {
          shouldInvalidate: (prev, next) => prev.tickets !== next.tickets,
          queryKeys: (state) => [boardKeys.detail('current')],
          optimisticUpdate: (state) => [{
            queryKey: boardKeys.detail('current'),
            updater: (old) => ({
              ...old,
              tickets: Object.values(state.tickets),
            }),
          }],
        },
      ],
      syncRules: [
        {
          queryKey: boardKeys.detail('current'),
          toState: (data) => ({
            tickets: data.tickets.reduce((acc, t) => {
              acc[t.id] = t
              return acc
            }, {}),
          }),
        },
      ],
    }
  )
)
```

---

## 3. Complete Store Template

Full-featured store with all middleware combined:

```typescript
// stores/exampleStore.ts
import { create } from 'zustand'
import { devtools, persist, subscribeWithSelector, createJSONStorage } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import { temporal } from 'zundo'
import { pub } from 'zustand-pub'
import { websocketSync } from '@/middleware/websocket-sync'
import { reactQueryBridge } from '@/middleware/react-query-bridge'
import { compressedStorage } from '@/lib/storage'

interface ExampleState {
  items: Record<string, Item>
  selectedIds: string[]
  filters: FilterState
  
  // Actions
  addItem: (item: Item) => void
  updateItem: (id: string, updates: Partial<Item>) => void
  deleteItem: (id: string) => void
  selectItem: (id: string) => void
  setFilters: (filters: FilterState) => void
}

// WebSocket instance manager
let wsInstance: WebSocket | null = null
export const setExampleWebSocket = (ws: WebSocket | null) => {
  wsInstance = ws
}

export const useExampleStore = create<ExampleState>()(
  // 1. DevTools (outermost - for debugging)
  devtools(
    // 2. Cross-tab sync (optional)
    pub(
      // 3. Persistence with compression
      persist(
        // 4. WebSocket sync
        websocketSync(
          // 5. React Query bridge
          reactQueryBridge(
            // 6. Time-travel (dev only)
            temporal(
              // 7. Selective subscriptions
              subscribeWithSelector(
                // 8. Immer (innermost - for mutations)
                immer((set, get) => ({
                  items: {},
                  selectedIds: [],
                  filters: {},
                  
                  addItem: (item) =>
                    set((state) => {
                      state.items[item.id] = item
                    }),
                  
                  updateItem: (id, updates) =>
                    set((state) => {
                      if (state.items[id]) {
                        state.items[id] = { ...state.items[id], ...updates }
                      }
                    }),
                  
                  deleteItem: (id) =>
                    set((state) => {
                      delete state.items[id]
                      state.selectedIds = state.selectedIds.filter((i) => i !== id)
                    }),
                  
                  selectItem: (id) =>
                    set((state) => {
                      if (!state.selectedIds.includes(id)) {
                        state.selectedIds.push(id)
                      }
                    }),
                  
                  setFilters: (filters) => set({ filters }),
                }))
              ),
              {
                limit: 20,
                enabled: process.env.NODE_ENV === 'development',
              }
            ),
            {
              queryClient: queryClient, // Injected by provider
              invalidationRules: [
                {
                  shouldInvalidate: (prev, next) => prev.items !== next.items,
                  queryKeys: ['items'],
                },
              ],
            }
          ),
          {
            getWebSocket: () => wsInstance,
            eventTypes: ['ITEM_CREATED', 'ITEM_UPDATED', 'ITEM_DELETED'],
            onMessage: (message, state) => {
              const { type, payload } = message
              
              return (draft) => {
                switch (type) {
                  case 'ITEM_CREATED':
                    draft.items[payload.id] = payload
                    break
                  case 'ITEM_UPDATED':
                    if (draft.items[payload.id]) {
                      draft.items[payload.id] = { ...draft.items[payload.id], ...payload }
                    }
                    break
                  case 'ITEM_DELETED':
                    delete draft.items[payload.id]
                    break
                }
              }
            },
          }
        ),
        {
          name: 'example-store',
          storage: compressedStorage,
          partialize: (state) => ({
            filters: state.filters,
            // Don't persist items (from server)
          }),
          version: 1,
        }
      ),
      { name: 'example-channel' }
    ),
    { name: 'ExampleStore' }
  )
)

// Type-safe selectors
export const selectSelectedItems = (state: ExampleState) =>
  state.selectedIds.map((id) => state.items[id]).filter(Boolean)

// Time-travel actions
export const { undo, redo, clear } = useExampleStore.temporal.getState()
```

---

## 4. Storage Adapters

### Compressed Storage

```typescript
// lib/storage.ts
import { StateStorage } from 'zustand/middleware'
import { compress, decompress } from 'lz-string'

export const compressedStorage: StateStorage = {
  getItem: (name) => {
    const str = localStorage.getItem(name)
    if (!str) return null
    
    try {
      return decompress(str) || str
    } catch {
      return str // Fallback to uncompressed
    }
  },
  
  setItem: (name, value) => {
    try {
      const compressed = compress(value)
      localStorage.setItem(name, compressed)
    } catch (error) {
      console.error('Compression error:', error)
      localStorage.setItem(name, value) // Fallback
    }
  },
  
  removeItem: (name) => {
    localStorage.removeItem(name)
  },
}
```

### Robust Storage with Fallbacks

```typescript
export const robustStorage: StateStorage = {
  getItem: (name) => {
    try {
      return localStorage.getItem(name) || sessionStorage.getItem(name)
    } catch {
      return null
    }
  },
  
  setItem: (name, value) => {
    try {
      localStorage.setItem(name, value)
    } catch {
      try {
        sessionStorage.setItem(name, value)
      } catch {
        // Storage unavailable, ignore
      }
    }
  },
  
  removeItem: (name) => {
    try {
      localStorage.removeItem(name)
      sessionStorage.removeItem(name)
    } catch {}
  },
}
```

---

## 5. Installation Guide

### Required Packages

```bash
# Core Zustand
npm install zustand immer

# Official middleware
# (devtools, persist, subscribeWithSelector are included in zustand)

# Third-party middleware
npm install zundo  # Undo/redo with time-travel
npm install zustand-pub  # Cross-tab synchronization

# Utilities
npm install lz-string  # Compression for storage
npm install zustand-querystring  # URL state sync (optional)

# React Query integration
npm install @tanstack/react-query @tanstack/react-query-devtools

# Animations (for components)
npm install framer-motion

# Date utilities
npm install date-fns
```

### TypeScript Configuration

Ensure `tsconfig.json` has:

```json
{
  "compilerOptions": {
    "strict": true,
    "skipLibCheck": true,
    "esModuleInterop": true
  }
}
```

---

## 6. Best Practices

### 1. Middleware Order Matters

Place middleware in this order (outermost to innermost):
1. **devtools** - Debug tooling
2. **pub** - Cross-tab sync
3. **persist** - Persistence
4. **websocketSync** - Real-time sync
5. **reactQueryBridge** - Cache integration
6. **temporal** - Time-travel
7. **subscribeWithSelector** - Performance
8. **immer** - Mutations

### 2. Selective Persistence

Only persist UI preferences, not server data:

```typescript
persist(
  (set) => ({ /* ... */ }),
  {
    partialize: (state) => ({
      theme: state.theme,
      sidebarCollapsed: state.sidebarCollapsed,
      // Don't persist: tickets, agents (from server)
    }),
  }
)
```

### 3. Optimized Selectors

Use shallow equality and selectors:

```typescript
import { shallow } from 'zustand/shallow'

// Good: Only re-render when selectedIds change
const selectedIds = useStore((state) => state.selectedIds)

// Better: Multiple values with shallow
const { selectedIds, filters } = useStore(
  (state) => ({
    selectedIds: state.selectedIds,
    filters: state.filters,
  }),
  shallow
)

// Best: Exported selector
export const selectSelectedIds = (state) => state.selectedIds
const selectedIds = useStore(selectSelectedIds)
```

### 4. SSR Hydration

Always use manual hydration for SSR:

```typescript
// providers/StoreProvider.tsx
export function StoreProvider({ children }) {
  const hasHydrated = useRef(false)
  
  useEffect(() => {
    if (!hasHydrated.current) {
      useKanbanStore.persist.rehydrate()
      useAgentStore.persist.rehydrate()
      hasHydrated.current = true
    }
  }, [])
  
  return <>{children}</>
}
```

### 5. WebSocket Connection Management

Centralize WebSocket instance management:

```typescript
// providers/WebSocketProvider.tsx
export function WebSocketProvider({ children }) {
  const [socket, setSocket] = useState<WebSocket | null>(null)
  
  useEffect(() => {
    const ws = new WebSocket(WS_URL)
    
    ws.onopen = () => {
      // Set socket in all stores
      setKanbanWebSocket(ws)
      setAgentWebSocket(ws)
      setSocket(ws)
    }
    
    return () => ws.close()
  }, [])
  
  return <>{children}</>
}
```

---

## 7. Performance Optimization

### Subscription Patterns

```typescript
// ❌ Bad: Subscribe to entire store
const store = useStore()

// ✅ Good: Subscribe to specific values
const items = useStore((state) => state.items)

// ✅ Better: Use selectors
const selectedItems = useStore(selectSelectedItems)

// ✅ Best: Selective subscription
useStore.subscribe(
  (state) => state.selectedIds,
  (selectedIds) => {
    console.log('Selection changed:', selectedIds)
  },
  { fireImmediately: false }
)
```

### Avoiding Re-renders

```typescript
// Use subscribeWithSelector middleware
import { subscribeWithSelector } from 'zustand/middleware'

export const useStore = create(
  subscribeWithSelector((set) => ({
    // ... store
  }))
)

// Now you can subscribe to specific slices
useEffect(() => {
  const unsub = useStore.subscribe(
    (state) => state.count,
    (count) => console.log('Count changed:', count)
  )
  return unsub
}, [])
```

---

This provides a complete reference for implementing and using custom Zustand middleware with WebSocket synchronization, React Query integration, SSR support, and performance optimization.

