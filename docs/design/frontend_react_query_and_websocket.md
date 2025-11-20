# Frontend Data Architecture: React Query & WebSockets

**Created**: 2025-05-19
**Status**: Design Document
**Purpose**: Defines the data fetching strategy, cache management, and real-time synchronization via WebSockets for the Project Management Dashboard.

---

## 1. Query Key Factory

To ensure consistency and effective cache invalidation, we use a Query Key Factory pattern.

```typescript
// lib/query-keys.ts

export const projectKeys = {
  all: ['projects'] as const,
  lists: () => [...projectKeys.all, 'list'] as const,
  detail: (id: string) => [...projectKeys.all, 'detail', id] as const,
  stats: (id: string) => [...projectKeys.all, 'stats', id] as const,
}

export const boardKeys = {
  all: ['board'] as const,
  detail: (projectId: string) => [...boardKeys.all, 'detail', projectId] as const,
}

export const ticketKeys = {
  all: ['tickets'] as const,
  lists: (filters?: Record<string, any>) => [...ticketKeys.all, 'list', { ...filters }] as const,
  detail: (id: string) => [...ticketKeys.all, 'detail', id] as const,
  history: (id: string) => [...ticketKeys.all, 'history', id] as const,
  comments: (id: string) => [...ticketKeys.all, 'comments', id] as const,
}

export const agentKeys = {
  all: ['agents'] as const,
  lists: () => [...agentKeys.all, 'list'] as const,
  detail: (id: string) => [...agentKeys.all, 'detail', id] as const,
  trajectory: (id: string) => [...agentKeys.all, 'trajectory', id] as const,
}

export const graphKeys = {
  all: ['graph'] as const,
  detail: (projectId: string) => [...graphKeys.all, 'detail', projectId] as const,
}
```

---

## 2. Custom Hooks & Data Fetching

### Project Hooks

```typescript
// hooks/useProjects.ts
export function useProjects() {
  return useQuery({
    queryKey: projectKeys.lists(),
    queryFn: api.getProjects,
  })
}

export function useProject(id: string) {
  return useQuery({
    queryKey: projectKeys.detail(id),
    queryFn: () => api.getProject(id),
    enabled: !!id,
  })
}

export function useCreateProject() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: api.createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() })
    }
  })
}
```

### Board Hooks (Kanban)

**Key Feature**: Optimistic Updates for drag-and-drop performance.

```typescript
// hooks/useBoard.ts
export function useBoard(projectId: string) {
  return useQuery({
    queryKey: boardKeys.detail(projectId),
    queryFn: () => api.getBoardView(projectId),
  })
}

export function useMoveTicket() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: api.moveTicket, // { ticketId, columnId, projectId }
    onMutate: async ({ ticketId, columnId, projectId }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: boardKeys.detail(projectId) })

      // Snapshot previous value
      const previousBoard = queryClient.getQueryData(boardKeys.detail(projectId))

      // Optimistically update
      queryClient.setQueryData(boardKeys.detail(projectId), (old: any) => {
        // Logic to remove ticket from old column and add to new column
        return moveTicketInLocalState(old, ticketId, columnId)
      })

      return { previousBoard }
    },
    onError: (err, newTodo, context) => {
      // Rollback on error
      queryClient.setQueryData(boardKeys.detail(newTodo.projectId), context?.previousBoard)
    },
    onSettled: (data, error, variables) => {
      // Refetch to ensure sync
      queryClient.invalidateQueries({ queryKey: boardKeys.detail(variables.projectId) })
    },
  })
}
```

### Ticket Hooks

```typescript
// hooks/useTicket.ts
export function useTicket(ticketId: string) {
  return useQuery({
    queryKey: ticketKeys.detail(ticketId),
    queryFn: () => api.getTicket(ticketId),
  })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: api.createTicket,
    onSuccess: (newTicket, variables) => {
      // Invalidate board to show new ticket
      // Note: In a real app we might need projectId here to invalidate specific board
      queryClient.invalidateQueries({ queryKey: boardKeys.all }) 
    }
  })
}
```

---

## 3. WebSocket Event Handling

This section maps backend WebSocket events to frontend React Query actions (Invalidation or Direct Updates).

**Strategy**:
1.  **Invalidate**: Safest. Marks data as stale, triggers refetch. Use for complex state changes.
2.  **Update**: Fastest. Directly modifies the cache. Use for simple appends or status changes.

### Event Mapping Table

| Event Type | Affected Cache Keys | Action | Notes |
| :--- | :--- | :--- | :--- |
| `TICKET_CREATED` | `boardKeys.detail(projectId)` | **Update** | Append ticket to "Backlog" column in cache. |
| `TICKET_UPDATED` | `ticketKeys.detail(id)` | **Update** | Merge changes into specific ticket cache. |
| | `boardKeys.detail(projectId)` | **Update** | If phase/status changed, move ticket in board cache. |
| `TICKET_BLOCKED` | `ticketKeys.detail(id)` | **Invalidate** | Refetch to get block reason details. |
| | `boardKeys.detail(projectId)` | **Update** | Set blocked flag on ticket card. |
| `TASK_CREATED` | `ticketKeys.detail(id)` | **Invalidate** | Refetch ticket to show new task count. |
| | `graphKeys.detail(projectId)` | **Update** | Add node to graph. |
| `TASK_COMPLETED` | `graphKeys.detail(projectId)` | **Update** | Turn node green/completed. |
| | `boardKeys.detail(projectId)` | **Update** | Update progress bar on ticket card. |
| `AGENT_REGISTERED` | `agentKeys.lists()` | **Update** | Add new agent to list. |
| `AGENT_STATUS_CHANGED` | `agentKeys.detail(id)` | **Update** | Update status (idle/working). |
| `MONITORING_UPDATE` | `agentKeys.all` | **Update** | Bulk update agent statuses/trajectory. |
| `GUARDIAN_INTERVENTION` | `agentKeys.trajectory(id)` | **Invalidate** | Refetch trajectory to show intervention. |
| `DISCOVERY_MADE` | `ticketKeys.detail(id)` | **Invalidate** | Discovery might spawn new tasks/links. |

### WebSocket Hook Implementation

```typescript
// hooks/useWebSocketEvents.ts

export function useWebSocketEvents() {
  const queryClient = useQueryClient()
  const { lastMessage } = useWebSocket() // Base hook

  useEffect(() => {
    if (!lastMessage) return

    const { type, payload } = lastMessage

    switch (type) {
      case 'TICKET_CREATED':
        // Optimistically add to board
        queryClient.setQueryData(boardKeys.detail(payload.projectId), (old: any) => {
           // Add payload.ticket to columns[0]
           return addTicketToBoard(old, payload.ticket)
        })
        break

      case 'TICKET_UPDATED':
        // Update ticket details everywhere
        queryClient.setQueryData(ticketKeys.detail(payload.id), (old: any) => ({ ...old, ...payload }))
        // Invalidate board to ensure columns are correct if status changed
        queryClient.invalidateQueries({ queryKey: boardKeys.detail(payload.projectId) })
        break
        
      case 'MONITORING_UPDATE':
         // Payload contains array of agent statuses
         payload.agents.forEach((agent: any) => {
            queryClient.setQueryData(agentKeys.detail(agent.id), (old: any) => ({
               ...old, 
               status: agent.status,
               currentTask: agent.currentTask 
            }))
         })
         break

      case 'TASK_COMPLETED':
         queryClient.invalidateQueries({ queryKey: graphKeys.detail(payload.projectId) })
         break
    }
  }, [lastMessage, queryClient])
}
```

---

## 4. Data Fetching Patterns by Page

### **Dashboard Overview**
- **Queries**:
  - `useProjects()` (List active projects)
  - `useAgents()` (Active agents summary)
- **Real-time**: High frequency `MONITORING_UPDATE` events.

### **Kanban Board** (`/projects/[id]/board`)
- **Queries**:
  - `useBoard(id)` (Columns, Tickets)
  - `useProject(id)` (Project metadata)
- **Mutations**:
  - `useMoveTicket()` (Optimistic drag-and-drop)
  - `useCreateTicket()`
- **Real-time**: `TICKET_MOVED`, `TICKET_CREATED`, `TICKET_UPDATED`.

### **Dependency Graph** (`/projects/[id]/graph`)
- **Queries**:
  - `useGraph(id)` (Nodes, Edges)
- **Real-time**: `TASK_CREATED`, `TASK_COMPLETED` (Nodes changing color/shape).

### **Agent Detail** (`/agents/[id]`)
- **Queries**:
  - `useAgent(id)`
  - `useAgentTrajectory(id)` (History of alignment)
- **Real-time**: `AGENT_LOG`, `STEERING_ISSUED`.

### **Ticket Detail** (Modal/Page)
- **Queries**:
  - `useTicket(id)`
  - `useTicketHistory(id)`
  - `useTicketComments(id)`
- **Mutations**:
  - `useUpdateTicket()`
  - `useAddComment()`
- **Real-time**: `COMMENT_ADDED`, `COMMIT_LINKED`.

---

## 5. Agent State Management

### 5.1 Zustand Store for Agent UI State with Full Middleware Stack

Client-side state for agent selection, filters, and UI preferences with WebSocket sync and React Query bridge.

```typescript
// stores/agentStore.ts
import { create } from 'zustand'
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import { websocketSync } from '@/middleware/websocket-sync'
import { reactQueryBridge } from '@/middleware/react-query-bridge'
import { agentKeys } from '@/lib/query-keys'

interface AgentHealth {
  lastHeartbeat: string
  isStale: boolean
  currentTaskId?: string
}

interface AgentStore {
  // Selection
  selectedAgentIds: string[]
  setSelectedAgentIds: (ids: string[]) => void
  toggleAgentSelection: (id: string) => void
  
  // Filters
  agentTypeFilter: string[]
  phaseFilter: string[]
  statusFilter: string[]
  setAgentTypeFilter: (types: string[]) => void
  setPhaseFilter: (phases: string[]) => void
  setStatusFilter: (statuses: string[]) => void
  
  // UI State
  viewMode: 'list' | 'grid' | 'timeline'
  setViewMode: (mode: 'list' | 'grid' | 'timeline') => void
  showTrajectory: boolean
  setShowTrajectory: (show: boolean) => void
  showInterventions: boolean
  setShowInterventions: (show: boolean) => void
  
  // Real-time state
  agentHealthMap: Record<string, AgentHealth>
  updateAgentHealth: (agentId: string, health: AgentHealth) => void
  
  // Computed
  getFilteredAgentIds: () => string[]
}

// WebSocket instance (set by provider)
let wsInstance: WebSocket | null = null
export const setAgentWebSocket = (ws: WebSocket | null) => {
  wsInstance = ws
}

export const useAgentStore = create<AgentStore>()(
  devtools(
    persist(
      websocketSync(
        reactQueryBridge(
          subscribeWithSelector(
            immer((set, get) => ({
      // Selection
      selectedAgentIds: [],
      setSelectedAgentIds: (ids) => set({ selectedAgentIds: ids }),
      toggleAgentSelection: (id) =>
                set((state) => {
                  const index = state.selectedAgentIds.indexOf(id)
                  if (index > -1) {
                    state.selectedAgentIds.splice(index, 1)
                  } else {
                    state.selectedAgentIds.push(id)
                  }
                }),
      
      // Filters
      agentTypeFilter: [],
      phaseFilter: [],
      statusFilter: [],
      setAgentTypeFilter: (types) => set({ agentTypeFilter: types }),
      setPhaseFilter: (phases) => set({ phaseFilter: phases }),
      setStatusFilter: (statuses) => set({ statusFilter: statuses }),
      
      // UI State
      viewMode: 'list',
      setViewMode: (mode) => set({ viewMode: mode }),
      showTrajectory: true,
      setShowTrajectory: (show) => set({ showTrajectory: show }),
      showInterventions: true,
      setShowInterventions: (show) => set({ showInterventions: show }),
      
      // Real-time state
      agentHealthMap: {},
      updateAgentHealth: (agentId, health) =>
                set((state) => {
                  state.agentHealthMap[agentId] = health
                }),
              
              // Computed
              getFilteredAgentIds: () => {
                const state = get()
                // Filter logic based on active filters
                return Object.keys(state.agentHealthMap)
              },
            }))
          ),
          {
            queryClient: queryClient, // Injected by provider
            invalidationRules: [
              {
                shouldInvalidate: (prev, next) => 
                  prev.agentTypeFilter !== next.agentTypeFilter ||
                  prev.phaseFilter !== next.phaseFilter ||
                  prev.statusFilter !== next.statusFilter,
                queryKeys: [agentKeys.lists()],
              },
            ],
          }
        ),
        {
          getWebSocket: () => wsInstance,
          eventTypes: ['AGENT_HEARTBEAT', 'AGENT_STALE', 'AGENT_STATUS_CHANGED'],
          onMessage: (message, state) => {
            const { type, payload } = message
            
            switch (type) {
              case 'AGENT_HEARTBEAT':
                return (draft) => {
                  draft.updateAgentHealth(payload.agent_id, {
                    lastHeartbeat: payload.timestamp,
                    isStale: false,
                    currentTaskId: payload.current_task_id,
                  })
                }
              
              case 'AGENT_STALE':
                return (draft) => {
                  if (draft.agentHealthMap[payload.agent_id]) {
                    draft.agentHealthMap[payload.agent_id].isStale = true
                  }
                }
              
              default:
                return {}
            }
          },
        }
      ),
      {
        name: 'agent-store',
        partialize: (state) => ({
          viewMode: state.viewMode,
          showTrajectory: state.showTrajectory,
          showInterventions: state.showInterventions,
        }),
      }
    ),
    { name: 'AgentStore' }
  )
)

// Selectors for optimized subscriptions
export const selectSelectedAgents = (state: AgentStore) => state.selectedAgentIds
export const selectAgentFilters = (state: AgentStore) => ({
  type: state.agentTypeFilter,
  phase: state.phaseFilter,
  status: state.statusFilter,
})
```

### 5.2 Agent Query Keys

Extended query key factory for agent-related data.

```typescript
// lib/query-keys.ts (extended)

export const agentKeys = {
  all: ['agents'] as const,
  lists: (filters?: AgentFilters) => [...agentKeys.all, 'list', { ...filters }] as const,
  detail: (id: string) => [...agentKeys.all, 'detail', id] as const,
  trajectory: (id: string) => [...agentKeys.all, 'trajectory', id] as const,
  health: (id: string) => [...agentKeys.all, 'health', id] as const,
  interventions: (id: string) => [...agentKeys.all, 'interventions', id] as const,
  discoveries: (id: string) => [...agentKeys.all, 'discoveries', id] as const,
  tasks: (id: string) => [...agentKeys.all, 'tasks', id] as const,
  stats: (id: string) => [...agentKeys.all, 'stats', id] as const,
}

export const discoveryKeys = {
  all: ['discoveries'] as const,
  lists: (projectId?: string) => [...discoveryKeys.all, 'list', projectId] as const,
  detail: (id: string) => [...discoveryKeys.all, 'detail', id] as const,
}

export const interventionKeys = {
  all: ['interventions'] as const,
  lists: (agentId?: string) => [...interventionKeys.all, 'list', agentId] as const,
  detail: (id: string) => [...interventionKeys.all, 'detail', id] as const,
}
```

### 5.3 Agent Hooks

Comprehensive hooks for agent data fetching and mutations.

```typescript
// hooks/useAgents.ts

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { agentKeys } from '@/lib/query-keys'
import { useAgentStore } from '@/stores/agentStore'

// List agents with filters
export function useAgents() {
  const { agentTypeFilter, phaseFilter, statusFilter } = useAgentStore()
  
  return useQuery({
    queryKey: agentKeys.lists({
      agentType: agentTypeFilter,
      phase: phaseFilter,
      status: statusFilter,
    }),
    queryFn: () => api.getAgents({
      agentType: agentTypeFilter,
      phase: phaseFilter,
      status: statusFilter,
    }),
  })
}

// Agent detail
export function useAgent(id: string) {
  return useQuery({
    queryKey: agentKeys.detail(id),
    queryFn: () => api.getAgent(id),
    enabled: !!id,
  })
}

// Agent trajectory (alignment history)
export function useAgentTrajectory(id: string) {
  return useQuery({
    queryKey: agentKeys.trajectory(id),
    queryFn: () => api.getAgentTrajectory(id),
    enabled: !!id,
    refetchInterval: 60000, // Refetch every 60s (monitoring loop interval)
  })
}

// Agent health (heartbeat status)
export function useAgentHealth(id: string) {
  const { updateAgentHealth } = useAgentStore()
  
  return useQuery({
    queryKey: agentKeys.health(id),
    queryFn: () => api.getAgentHealth(id),
    enabled: !!id,
    refetchInterval: 10000, // Refetch every 10s (stale detection interval)
    onSuccess: (data) => {
      updateAgentHealth(id, {
        lastHeartbeat: data.last_heartbeat,
        isStale: data.is_stale,
        currentTaskId: data.current_task_id,
      })
    },
  })
}

// Agent interventions
export function useAgentInterventions(id: string) {
  return useQuery({
    queryKey: agentKeys.interventions(id),
    queryFn: () => api.getAgentInterventions(id),
    enabled: !!id,
  })
}

// Agent discoveries
export function useAgentDiscoveries(id: string) {
  return useQuery({
    queryKey: agentKeys.discoveries(id),
    queryFn: () => api.getAgentDiscoveries(id),
    enabled: !!id,
  })
}

// Agent tasks
export function useAgentTasks(id: string) {
  return useQuery({
    queryKey: agentKeys.tasks(id),
    queryFn: () => api.getAgentTasks(id),
    enabled: !!id,
  })
}

// Agent stats
export function useAgentStats(id: string) {
  return useQuery({
    queryKey: agentKeys.stats(id),
    queryFn: () => api.getAgentStats(id),
    enabled: !!id,
  })
}

// Spawn agent
export function useSpawnAgent() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: api.spawnAgent,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: agentKeys.lists() })
    },
  })
}

// Cancel agent task
export function useCancelAgentTask() {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn: ({ agentId, taskId }: { agentId: string; taskId: string }) =>
      api.cancelAgentTask(agentId, taskId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: agentKeys.detail(variables.agentId) })
      queryClient.invalidateQueries({ queryKey: agentKeys.tasks(variables.agentId) })
    },
  })
}
```

### 5.4 Agent WebSocket Event Handling

Extended WebSocket hook for agent-specific events.

```typescript
// hooks/useWebSocketEvents.ts (extended)

export function useWebSocketEvents() {
  const queryClient = useQueryClient()
  const { updateAgentHealth } = useAgentStore()
  const { lastMessage } = useWebSocket()

  useEffect(() => {
    if (!lastMessage) return

    const { type, payload } = lastMessage

    switch (type) {
      // ... existing cases ...

      case 'AGENT_REGISTERED':
        // Add new agent to list
        queryClient.setQueryData(agentKeys.lists(), (old: any) => {
          return old ? [...old, payload.agent] : [payload.agent]
        })
        // Set initial health
        updateAgentHealth(payload.agent.id, {
          lastHeartbeat: payload.agent.last_heartbeat,
          isStale: false,
        })
        break

      case 'AGENT_HEARTBEAT':
        // Update health in store and cache
        updateAgentHealth(payload.agent_id, {
          lastHeartbeat: payload.timestamp,
          isStale: false,
          currentTaskId: payload.current_task_id,
        })
        queryClient.setQueryData(agentKeys.health(payload.agent_id), (old: any) => ({
          ...old,
          last_heartbeat: payload.timestamp,
          is_stale: false,
          current_task_id: payload.current_task_id,
        }))
        break

      case 'AGENT_STALE':
        // Mark agent as stale
        updateAgentHealth(payload.agent_id, {
          lastHeartbeat: payload.last_heartbeat,
          isStale: true,
        })
        queryClient.setQueryData(agentKeys.health(payload.agent_id), (old: any) => ({
          ...old,
          is_stale: true,
        }))
        break

      case 'AGENT_STATUS_CHANGED':
        // Update agent status
        queryClient.setQueryData(agentKeys.detail(payload.agent_id), (old: any) => ({
          ...old,
          status: payload.status,
          current_task_id: payload.current_task_id,
        }))
        // Also update in list
        queryClient.setQueryData(agentKeys.lists(), (old: any) => {
          return old?.map((agent: any) =>
            agent.id === payload.agent_id
              ? { ...agent, status: payload.status, current_task_id: payload.current_task_id }
              : agent
          )
        })
        break

      case 'MONITORING_UPDATE':
        // Bulk update agent statuses and trajectories
        payload.agents.forEach((agent: any) => {
          // Update agent detail
          queryClient.setQueryData(agentKeys.detail(agent.id), (old: any) => ({
            ...old,
            alignment_score: agent.alignment_score,
            trajectory_summary: agent.trajectory_summary,
            needs_steering: agent.needs_steering,
            steering_type: agent.steering_type,
          }))
          
          // Update trajectory
          queryClient.setQueryData(agentKeys.trajectory(agent.id), (old: any) => {
            const newEntry = {
              timestamp: payload.timestamp,
              alignment_score: agent.alignment_score,
              trajectory_summary: agent.trajectory_summary,
              needs_steering: agent.needs_steering,
            }
            return old ? [...old, newEntry] : [newEntry]
          })
        })
        
        // Update system coherence (if needed for overview page)
        queryClient.setQueryData(['system', 'coherence'], {
          coherence_score: payload.systemCoherence,
          duplicates: payload.duplicates,
          timestamp: payload.timestamp,
        })
        break

      case 'GUARDIAN_INTERVENTION':
        // Add intervention to agent's intervention list
        queryClient.setQueryData(
          agentKeys.interventions(payload.target_entity),
          (old: any) => {
            const newIntervention = {
              id: payload.action_id,
              action_type: payload.action_type,
              reason: payload.reason,
              timestamp: payload.timestamp,
              delivered: !!payload.conversation_id,
              message: payload.intervention_message,
            }
            return old ? [newIntervention, ...old] : [newIntervention]
          }
        )
        
        // Invalidate trajectory to show intervention impact
        queryClient.invalidateQueries({
          queryKey: agentKeys.trajectory(payload.target_entity),
        })
        
        // Update agent detail if intervention affects status
        if (payload.action_type === 'cancel_task' || payload.action_type === 'reallocate') {
          queryClient.invalidateQueries({
            queryKey: agentKeys.detail(payload.target_entity),
          })
        }
        break

      case 'STEERING_ISSUED':
        // Update trajectory with steering event
        queryClient.setQueryData(agentKeys.trajectory(payload.agent_id), (old: any) => {
          const steeringEntry = {
            timestamp: payload.timestamp,
            type: 'steering',
            steering_type: payload.steering_type,
            message: payload.message,
          }
          return old ? [...old, steeringEntry] : [steeringEntry]
        })
        break

      case 'DISCOVERY_MADE':
        // Add discovery to agent's discovery list
        queryClient.setQueryData(agentKeys.discoveries(payload.agent_id), (old: any) => {
          const newDiscovery = {
            id: payload.discovery_id,
            discovery_type: payload.discovery_type,
            description: payload.description,
            discovered_at: payload.timestamp,
            spawned_tasks: payload.spawned_tasks || [],
            resolved: false,
          }
          return old ? [newDiscovery, ...old] : [newDiscovery]
        })
        
        // Invalidate agent tasks (new tasks may have been spawned)
        queryClient.invalidateQueries({
          queryKey: agentKeys.tasks(payload.agent_id),
        })
        
        // Update graph if discovery spawned tasks
        if (payload.spawned_tasks?.length > 0) {
          queryClient.invalidateQueries({
            queryKey: graphKeys.detail(payload.project_id),
          })
        }
        break

      case 'VALIDATION_STARTED':
        // Update task status in agent's task list
        queryClient.setQueryData(agentKeys.tasks(payload.agent_id), (old: any) => {
          return old?.map((task: any) =>
            task.id === payload.task_id
              ? { ...task, validation_status: 'validation_in_progress' }
              : task
          )
        })
        break

      case 'VALIDATION_REVIEW_SUBMITTED':
        // Update task with validation review
        queryClient.setQueryData(agentKeys.tasks(payload.agent_id), (old: any) => {
          return old?.map((task: any) =>
            task.id === payload.task_id
              ? {
                  ...task,
                  validation_status: payload.passed ? 'done' : 'needs_work',
                  validation_feedback: payload.feedback,
                }
              : task
          )
        })
        break
    }
  }, [lastMessage, queryClient, updateAgentHealth])
}
```

### 5.5 Agent State Synchronization Patterns

Best practices for keeping agent state in sync.

```typescript
// hooks/useAgentStateSync.ts

import { useMemo } from 'react'
import { useAgent, useAgentHealth, useAgentTrajectory } from './useAgents'
import { useAgentStore } from '@/stores/agentStore'

/**
 * Custom hook that synchronizes agent state across multiple sources:
 * - React Query cache (server state)
 * - Zustand store (client state)
 * - WebSocket events (real-time updates)
 */
export function useAgentStateSync(agentId: string) {
  const { data: agent } = useAgent(agentId)
  const { data: health } = useAgentHealth(agentId)
  const { data: trajectory } = useAgentTrajectory(agentId)
  const { agentHealthMap } = useAgentStore()
  
  // Derive combined state
  const agentState = useMemo(() => {
    const storeHealth = agentHealthMap[agentId]
    
    return {
      ...agent,
      health: storeHealth || health,
      trajectory: trajectory || [],
      isStale: storeHealth?.isStale || health?.is_stale || false,
      lastHeartbeat: storeHealth?.lastHeartbeat || health?.last_heartbeat,
    }
  }, [agent, health, trajectory, agentHealthMap, agentId])
  
  return agentState
}
```

### 5.6 Agent Monitoring Dashboard State

State management for the system overview dashboard.

```typescript
// stores/monitoringStore.ts

interface MonitoringStore {
  // System-wide metrics
  systemCoherence: number | null
  averageAlignment: number | null
  activeAgentCount: number
  runningTaskCount: number
  
  // Phase distribution
  phaseDistribution: Record<string, number>
  
  // Duplicate detection
  duplicates: Array<{
    agent1_id: string
    agent2_id: string
    similarity_score: number
  }>
  
  // Update methods
  updateSystemMetrics: (metrics: SystemMetrics) => void
  updatePhaseDistribution: (distribution: Record<string, number>) => void
  updateDuplicates: (duplicates: Duplicate[]) => void
}

export const useMonitoringStore = create<MonitoringStore>()(
  devtools(
    (set) => ({
      systemCoherence: null,
      averageAlignment: null,
      activeAgentCount: 0,
      runningTaskCount: 0,
      phaseDistribution: {},
      duplicates: [],
      
      updateSystemMetrics: (metrics) => set({
        systemCoherence: metrics.coherence_score,
        averageAlignment: metrics.average_alignment,
        activeAgentCount: metrics.active_agent_count,
        runningTaskCount: metrics.running_task_count,
      }),
      
      updatePhaseDistribution: (distribution) => set({ phaseDistribution: distribution }),
      updateDuplicates: (duplicates) => set({ duplicates }),
    }),
    { name: 'MonitoringStore' }
  )
)
```

---

## 6. Discovery & Intervention State Management

### 6.1 Discovery Hooks

```typescript
// hooks/useDiscoveries.ts

export function useDiscoveries(projectId?: string) {
  return useQuery({
    queryKey: discoveryKeys.lists(projectId),
    queryFn: () => api.getDiscoveries(projectId),
    enabled: !!projectId,
  })
}

export function useDiscovery(id: string) {
  return useQuery({
    queryKey: discoveryKeys.detail(id),
    queryFn: () => api.getDiscovery(id),
    enabled: !!id,
  })
}
```

### 6.2 Intervention Hooks

```typescript
// hooks/useInterventions.ts

export function useInterventions(agentId?: string) {
  return useQuery({
    queryKey: interventionKeys.lists(agentId),
    queryFn: () => api.getInterventions(agentId),
  })
}

export function useIntervention(id: string) {
  return useQuery({
    queryKey: interventionKeys.detail(id),
    queryFn: () => api.getIntervention(id),
    enabled: !!id,
  })
}
```

---

## 7. System-Wide Reusable Hooks

### 7.1 UI State Hooks

#### `useModal.ts` - Modal/Dialog State Management

```typescript
// hooks/ui/useModal.ts
import { useState, useCallback } from 'react'

export function useModal(initialOpen = false) {
  const [isOpen, setIsOpen] = useState(initialOpen)
  
  const open = useCallback(() => setIsOpen(true), [])
  const close = useCallback(() => setIsOpen(false), [])
  const toggle = useCallback(() => setIsOpen(prev => !prev), [])
  
  return { isOpen, open, close, toggle }
}
```

#### `useToast.ts` - Toast Notification Hook

```typescript
// hooks/ui/useToast.ts
import { useToast as useShadcnToast } from '@/hooks/use-toast'

export function useAppToast() {
  const { toast } = useShadcnToast()
  
  return {
    success: (message: string, title?: string) =>
      toast({ title: title || 'Success', description: message, variant: 'default' }),
    error: (message: string, title?: string) =>
      toast({ title: title || 'Error', description: message, variant: 'destructive' }),
    info: (message: string, title?: string) =>
      toast({ title: title || 'Info', description: message }),
    warning: (message: string, title?: string) =>
      toast({ title: title || 'Warning', description: message, variant: 'destructive' }),
  }
}
```

#### `useConfirmDialog.ts` - Confirmation Dialog Hook

```typescript
// hooks/ui/useConfirmDialog.ts
import { useState, useCallback } from 'react'

interface ConfirmOptions {
  title: string
  description: string
  confirmText?: string
  cancelText?: string
  variant?: 'default' | 'destructive'
}

export function useConfirmDialog() {
  const [isOpen, setIsOpen] = useState(false)
  const [options, setOptions] = useState<ConfirmOptions | null>(null)
  const [resolve, setResolve] = useState<((value: boolean) => void) | null>(null)
  
  const confirm = useCallback((opts: ConfirmOptions): Promise<boolean> => {
    return new Promise((res) => {
      setOptions(opts)
      setIsOpen(true)
      setResolve(() => res)
    })
  }, [])
  
  const handleConfirm = useCallback(() => {
    setIsOpen(false)
    resolve?.(true)
    setResolve(null)
  }, [resolve])
  
  const handleCancel = useCallback(() => {
    setIsOpen(false)
    resolve?.(false)
    setResolve(null)
  }, [resolve])
  
  return {
    isOpen,
    options,
    confirm,
    handleConfirm,
    handleCancel,
  }
}
```

### 7.2 Form Hooks

#### `useFormState.ts` - Form State Management

```typescript
// hooks/forms/useFormState.ts
import { useState, useCallback, useMemo } from 'react'

export function useFormState<T extends Record<string, any>>(initialValues: T) {
  const [values, setValues] = useState<T>(initialValues)
  const [errors, setErrors] = useState<Partial<Record<keyof T, string>>>({})
  const [touched, setTouched] = useState<Partial<Record<keyof T, boolean>>>({})
  
  const setValue = useCallback(<K extends keyof T>(key: K, value: T[K]) => {
    setValues(prev => ({ ...prev, [key]: value }))
    // Clear error when user types
    if (errors[key]) {
      setErrors(prev => {
        const next = { ...prev }
        delete next[key]
        return next
      })
    }
  }, [errors])
  
  const setError = useCallback(<K extends keyof T>(key: K, error: string) => {
    setErrors(prev => ({ ...prev, [key]: error }))
  }, [])
  
  const setFieldTouched = useCallback(<K extends keyof T>(key: K) => {
    setTouched(prev => ({ ...prev, [key]: true }))
  }, [])
  
  const reset = useCallback(() => {
    setValues(initialValues)
    setErrors({})
    setTouched({})
  }, [initialValues])
  
  const isValid = useMemo(() => Object.keys(errors).length === 0, [errors])
  
  return {
    values,
    errors,
    touched,
    setValue,
    setError,
    setFieldTouched,
    reset,
    isValid,
  }
}
```

#### `useDebouncedValue.ts` - Debounced Input Hook

```typescript
// hooks/forms/useDebouncedValue.ts
import { useState, useEffect } from 'react'

export function useDebouncedValue<T>(value: T, delay: number = 300): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)
  
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)
    
    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])
  
  return debouncedValue
}
```

### 7.3 Navigation & Routing Hooks

#### `useNavigation.ts` - Enhanced Navigation Hook

```typescript
// hooks/navigation/useNavigation.ts
import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { useCallback } from 'react'

export function useAppNavigation() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  
  const navigate = useCallback((path: string, options?: { replace?: boolean }) => {
    if (options?.replace) {
      router.replace(path)
    } else {
      router.push(path)
    }
  }, [router])
  
  const navigateWithQuery = useCallback((
    path: string,
    query: Record<string, string | number | boolean | null>,
    options?: { replace?: boolean }
  ) => {
    const params = new URLSearchParams()
    Object.entries(query).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        params.set(key, String(value))
      }
    })
    const queryString = params.toString()
    const fullPath = queryString ? `${path}?${queryString}` : path
    navigate(fullPath, options)
  }, [navigate])
  
  const updateQuery = useCallback((updates: Record<string, string | number | boolean | null>) => {
    const params = new URLSearchParams(searchParams.toString())
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === undefined) {
        params.delete(key)
      } else {
        params.set(key, String(value))
      }
    })
    router.replace(`${pathname}?${params.toString()}`)
  }, [router, pathname, searchParams])
  
  const getQueryParam = useCallback((key: string): string | null => {
    return searchParams.get(key)
  }, [searchParams])
  
  return {
    navigate,
    navigateWithQuery,
    updateQuery,
    getQueryParam,
    pathname,
    router,
  }
}
```

### 7.4 Permission & Auth Hooks

#### `usePermissions.ts` - Permission Checking Hook

```typescript
// hooks/auth/usePermissions.ts
import { useQuery } from '@tanstack/react-query'
import { useCallback } from 'react'

export function usePermissions() {
  const { data: user } = useQuery({
    queryKey: ['user', 'current'],
    queryFn: () => api.getCurrentUser(),
  })
  
  const hasPermission = useCallback((permission: string): boolean => {
    if (!user) return false
    return user.permissions?.includes(permission) || user.role === 'admin'
  }, [user])
  
  const hasAnyPermission = useCallback((permissions: string[]): boolean => {
    return permissions.some(p => hasPermission(p))
  }, [hasPermission])
  
  const hasAllPermissions = useCallback((permissions: string[]): boolean => {
    return permissions.every(p => hasPermission(p))
  }, [hasPermission])
  
  return {
    user,
    hasPermission,
    hasAnyPermission,
    hasAllPermissions,
    isAdmin: user?.role === 'admin',
  }
}
```

### 7.5 Optimistic Update Hooks

#### `useOptimisticMutation.ts` - Generic Optimistic Update Hook

```typescript
// hooks/mutations/useOptimisticMutation.ts
import { useMutation, useQueryClient, UseMutationOptions } from '@tanstack/react-query'

interface OptimisticMutationOptions<TData, TVariables> {
  queryKey: readonly unknown[]
  onMutate: (variables: TVariables) => TData | ((old: TData) => TData)
  onError?: (error: Error, variables: TVariables, context: TData) => void
  onSuccess?: (data: any, variables: TVariables, context: TData) => void
}

export function useOptimisticMutation<TData, TVariables, TError = Error>(
  mutationFn: (variables: TVariables) => Promise<any>,
  options: OptimisticMutationOptions<TData, TVariables>
) {
  const queryClient = useQueryClient()
  
  return useMutation({
    mutationFn,
    onMutate: async (variables) => {
      await queryClient.cancelQueries({ queryKey: options.queryKey })
      const previousData = queryClient.getQueryData<TData>(options.queryKey)
      
      const update = options.onMutate(variables)
      const newData = typeof update === 'function' 
        ? (update as (old: TData) => TData)(previousData as TData)
        : update
      
      queryClient.setQueryData(options.queryKey, newData)
      
      return previousData
    },
    onError: (error, variables, context) => {
      if (context) {
        queryClient.setQueryData(options.queryKey, context)
      }
      options.onError?.(error, variables, context as TData)
    },
    onSuccess: (data, variables, context) => {
      options.onSuccess?.(data, variables, context as TData)
      queryClient.invalidateQueries({ queryKey: options.queryKey })
    },
  })
}
```

### 7.6 Pagination Hooks

#### `usePagination.ts` - Pagination State Management

```typescript
// hooks/pagination/usePagination.ts
import { useState, useMemo, useCallback } from 'react'

interface UsePaginationOptions {
  initialPage?: number
  initialPageSize?: number
  totalItems?: number
}

export function usePagination(options: UsePaginationOptions = {}) {
  const { initialPage = 1, initialPageSize = 20, totalItems = 0 } = options
  
  const [page, setPage] = useState(initialPage)
  const [pageSize, setPageSize] = useState(initialPageSize)
  
  const totalPages = useMemo(
    () => Math.ceil(totalItems / pageSize),
    [totalItems, pageSize]
  )
  
  const hasNextPage = useMemo(() => page < totalPages, [page, totalPages])
  const hasPreviousPage = useMemo(() => page > 1, [page])
  
  const nextPage = useCallback(() => {
    if (hasNextPage) setPage(prev => prev + 1)
  }, [hasNextPage])
  
  const previousPage = useCallback(() => {
    if (hasPreviousPage) setPage(prev => prev - 1)
  }, [hasPreviousPage])
  
  const goToPage = useCallback((newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      setPage(newPage)
    }
  }, [totalPages])
  
  const reset = useCallback(() => {
    setPage(initialPage)
    setPageSize(initialPageSize)
  }, [initialPage, initialPageSize])
  
  return {
    page,
    pageSize,
    setPage,
    setPageSize,
    totalPages,
    hasNextPage,
    hasPreviousPage,
    nextPage,
    previousPage,
    goToPage,
    reset,
    offset: (page - 1) * pageSize,
  }
}
```

#### `useInfiniteScroll.ts` - Infinite Scroll Hook

```typescript
// hooks/pagination/useInfiniteScroll.ts
import { useEffect, useRef, useCallback } from 'react'
import { useInfiniteQuery } from '@tanstack/react-query'

interface UseInfiniteScrollOptions {
  queryKey: readonly unknown[]
  queryFn: ({ pageParam }: { pageParam: number }) => Promise<{
    data: any[]
    nextPage?: number
  }>
  enabled?: boolean
  threshold?: number // pixels from bottom to trigger load
}

export function useInfiniteScroll(options: UseInfiniteScrollOptions) {
  const { queryKey, queryFn, enabled = true, threshold = 200 } = options
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement | null>(null)
  
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam = 1 }) => queryFn({ pageParam }),
    getNextPageParam: (lastPage) => lastPage.nextPage,
    enabled,
  })
  
  const items = useMemo(
    () => data?.pages.flatMap(page => page.data) ?? [],
    [data]
  )
  
  useEffect(() => {
    if (!enabled || !hasNextPage || isFetchingNextPage) return
    
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          fetchNextPage()
        }
      },
      { rootMargin: `${threshold}px` }
    )
    
    if (loadMoreRef.current) {
      observer.observe(loadMoreRef.current)
    }
    
    observerRef.current = observer
    
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect()
      }
    }
  }, [enabled, hasNextPage, isFetchingNextPage, fetchNextPage, threshold])
  
  return {
    items,
    loadMoreRef,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    fetchNextPage,
  }
}
```

### 7.7 Search & Filter Hooks

#### `useSearch.ts` - Search Hook with Debouncing

```typescript
// hooks/search/useSearch.ts
import { useState, useMemo } from 'react'
import { useDebouncedValue } from './useDebouncedValue'

export function useSearch<T>(
  items: T[],
  searchFn: (item: T, query: string) => boolean,
  debounceMs: number = 300
) {
  const [query, setQuery] = useState('')
  const debouncedQuery = useDebouncedValue(query, debounceMs)
  
  const filteredItems = useMemo(() => {
    if (!debouncedQuery.trim()) return items
    return items.filter(item => searchFn(item, debouncedQuery))
  }, [items, debouncedQuery, searchFn])
  
  return {
    query,
    setQuery,
    debouncedQuery,
    filteredItems,
    resultCount: filteredItems.length,
  }
}
```

#### `useFilters.ts` - Multi-Filter Hook

```typescript
// hooks/filters/useFilters.ts
import { useState, useMemo, useCallback } from 'react'

type FilterValue = string | number | boolean | string[] | null

export function useFilters<T>(
  items: T[],
  filterFns: Record<string, (item: T, value: FilterValue) => boolean>
) {
  const [filters, setFilters] = useState<Record<string, FilterValue>>({})
  
  const setFilter = useCallback((key: string, value: FilterValue) => {
    setFilters(prev => {
      if (value === null || value === '' || (Array.isArray(value) && value.length === 0)) {
        const next = { ...prev }
        delete next[key]
        return next
      }
      return { ...prev, [key]: value }
    })
  }, [])
  
  const clearFilter = useCallback((key: string) => {
    setFilter(key, null)
  }, [setFilter])
  
  const clearAllFilters = useCallback(() => {
    setFilters({})
  }, [])
  
  const filteredItems = useMemo(() => {
    return items.filter(item => {
      return Object.entries(filters).every(([key, value]) => {
        const filterFn = filterFns[key]
        if (!filterFn) return true
        return filterFn(item, value)
      })
    })
  }, [items, filters, filterFns])
  
  const activeFilterCount = useMemo(
    () => Object.keys(filters).length,
    [filters]
  )
  
  return {
    filters,
    setFilter,
    clearFilter,
    clearAllFilters,
    filteredItems,
    activeFilterCount,
    hasActiveFilters: activeFilterCount > 0,
  }
}
```

### 7.8 Local Storage Hooks

#### `useLocalStorage.ts` - Local Storage Hook

```typescript
// hooks/storage/useLocalStorage.ts
import { useState, useEffect, useCallback } from 'react'

export function useLocalStorage<T>(key: string, initialValue: T) {
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') {
      return initialValue
    }
    try {
      const item = window.localStorage.getItem(key)
      return item ? JSON.parse(item) : initialValue
    } catch (error) {
      console.error(`Error reading localStorage key "${key}":`, error)
      return initialValue
    }
  })
  
  const setValue = useCallback(
    (value: T | ((val: T) => T)) => {
      try {
        const valueToStore = value instanceof Function ? value(storedValue) : value
        setStoredValue(valueToStore)
        if (typeof window !== 'undefined') {
          window.localStorage.setItem(key, JSON.stringify(valueToStore))
        }
      } catch (error) {
        console.error(`Error setting localStorage key "${key}":`, error)
      }
    },
    [key, storedValue]
  )
  
  const removeValue = useCallback(() => {
    try {
      setStoredValue(initialValue)
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(key)
      }
    } catch (error) {
      console.error(`Error removing localStorage key "${key}":`, error)
    }
  }, [key, initialValue])
  
  return [storedValue, setValue, removeValue] as const
}
```

### 7.9 WebSocket Connection Hooks

#### `useWebSocketConnection.ts` - WebSocket Connection State

```typescript
// hooks/websocket/useWebSocketConnection.ts
import { useState, useEffect, useCallback } from 'react'
import { useWebSocket } from '@/hooks/useWebSocket'

export function useWebSocketConnection() {
  const { lastMessage, sendMessage, readyState } = useWebSocket()
  const [isConnected, setIsConnected] = useState(false)
  const [reconnectAttempts, setReconnectAttempts] = useState(0)
  
  useEffect(() => {
    setIsConnected(readyState === WebSocket.OPEN)
  }, [readyState])
  
  const send = useCallback((type: string, payload: any) => {
    if (isConnected) {
      sendMessage(JSON.stringify({ type, payload }))
    }
  }, [isConnected, sendMessage])
  
  return {
    isConnected,
    readyState,
    reconnectAttempts,
    send,
    lastMessage,
  }
}
```

### 7.10 Keyboard Shortcuts Hook

#### `useKeyboardShortcut.ts` - Keyboard Shortcut Hook

```typescript
// hooks/keyboard/useKeyboardShortcut.ts
import { useEffect } from 'react'

export function useKeyboardShortcut(
  keys: string[], // e.g., ['ctrl', 'k'] or ['meta', 'k']
  callback: (event: KeyboardEvent) => void,
  options: { enabled?: boolean; preventDefault?: boolean } = {}
) {
  const { enabled = true, preventDefault = true } = options
  
  useEffect(() => {
    if (!enabled) return
    
    const handleKeyDown = (event: KeyboardEvent) => {
      const pressedKeys = []
      if (event.ctrlKey) pressedKeys.push('ctrl')
      if (event.metaKey) pressedKeys.push('meta')
      if (event.altKey) pressedKeys.push('alt')
      if (event.shiftKey) pressedKeys.push('shift')
      pressedKeys.push(event.key.toLowerCase())
      
      const matches = keys.length === pressedKeys.length &&
        keys.every((key, index) => key === pressedKeys[index])
      
      if (matches) {
        if (preventDefault) {
          event.preventDefault()
        }
        callback(event)
      }
    }
    
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [keys, callback, enabled, preventDefault])
}
```

### 7.11 Clipboard Hook

#### `useClipboard.ts` - Clipboard Operations

```typescript
// hooks/clipboard/useClipboard.ts
import { useState, useCallback } from 'react'

export function useClipboard() {
  const [copied, setCopied] = useState(false)
  
  const copy = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
      return true
    } catch (error) {
      console.error('Failed to copy:', error)
      return false
    }
  }, [])
  
  const paste = useCallback(async (): Promise<string | null> => {
    try {
      const text = await navigator.clipboard.readText()
      return text
    } catch (error) {
      console.error('Failed to paste:', error)
      return null
    }
  }, [])
  
  return { copy, paste, copied }
}
```

### 7.12 File Upload Hook

#### `useFileUpload.ts` - File Upload with Progress

```typescript
// hooks/files/useFileUpload.ts
import { useState, useCallback } from 'react'

interface UploadOptions {
  onProgress?: (progress: number) => void
  maxSize?: number
  accept?: string
}

export function useFileUpload(options: UploadOptions = {}) {
  const { onProgress, maxSize, accept } = options
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  
  const upload = useCallback(async (file: File, endpoint: string) => {
    if (maxSize && file.size > maxSize) {
      setError(`File size exceeds ${maxSize / 1024 / 1024}MB`)
      return null
    }
    
    if (accept && !file.type.match(accept)) {
      setError(`File type not allowed. Accepted: ${accept}`)
      return null
    }
    
    setUploading(true)
    setProgress(0)
    setError(null)
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      
      const xhr = new XMLHttpRequest()
      
      xhr.upload.addEventListener('progress', (e) => {
        if (e.lengthComputable) {
          const percentComplete = (e.loaded / e.total) * 100
          setProgress(percentComplete)
          onProgress?.(percentComplete)
        }
      })
      
      const result = await new Promise((resolve, reject) => {
        xhr.addEventListener('load', () => {
          if (xhr.status === 200) {
            resolve(JSON.parse(xhr.responseText))
          } else {
            reject(new Error(`Upload failed: ${xhr.statusText}`))
          }
        })
        
        xhr.addEventListener('error', () => {
          reject(new Error('Upload failed'))
        })
        
        xhr.open('POST', endpoint)
        xhr.send(formData)
      })
      
      setUploading(false)
      return result
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setUploading(false)
      return null
    }
  }, [maxSize, accept, onProgress])
  
  return { upload, uploading, progress, error }
}
```

### 7.13 Export/Import Hooks

#### `useExport.ts` - Data Export Hook

```typescript
// hooks/export/useExport.ts
import { useCallback } from 'react'

export function useExport() {
  const exportToCSV = useCallback((data: any[], filename: string) => {
    if (data.length === 0) return
    
    const headers = Object.keys(data[0])
    const csvContent = [
      headers.join(','),
      ...data.map(row => headers.map(header => {
        const value = row[header]
        return typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value
      }).join(','))
    ].join('\n')
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
  }, [])
  
  const exportToJSON = useCallback((data: any, filename: string) => {
    const jsonContent = JSON.stringify(data, null, 2)
    const blob = new Blob([jsonContent], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = filename
    link.click()
  }, [])
  
  return { exportToCSV, exportToJSON }
}
```

### 7.14 Theme Hook

#### `useTheme.ts` - Theme Management Hook

```typescript
// hooks/theme/useTheme.ts
import { useTheme as useNextTheme } from 'next-themes'
import { useLocalStorage } from './useLocalStorage'

export function useAppTheme() {
  const { theme, setTheme, systemTheme } = useNextTheme()
  const [customTheme, setCustomTheme] = useLocalStorage('custom-theme', {
    primaryColor: '#3b82f6',
    borderRadius: '0.5rem',
  })
  
  const currentTheme = theme === 'system' ? systemTheme : theme
  
  const updateCustomTheme = useCallback((updates: Partial<typeof customTheme>) => {
    setCustomTheme(prev => ({ ...prev, ...updates }))
  }, [setCustomTheme])
  
  return {
    theme: currentTheme,
    setTheme,
    isDark: currentTheme === 'dark',
    customTheme,
    updateCustomTheme,
  }
}
```

### 7.15 Real-time Subscription Hook

#### `useRealtimeSubscription.ts` - Subscribe to Entity Updates

```typescript
// hooks/realtime/useRealtimeSubscription.ts
import { useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useWebSocketConnection } from './useWebSocketConnection'

export function useRealtimeSubscription(
  entityType: 'ticket' | 'task' | 'agent' | 'project',
  entityId: string,
  queryKey: readonly unknown[]
) {
  const queryClient = useQueryClient()
  const { send, isConnected } = useWebSocketConnection()
  
  useEffect(() => {
    if (!isConnected) return
    
    // Subscribe to entity updates
    send('SUBSCRIBE', { entity_type: entityType, entity_id: entityId })
    
    return () => {
      // Unsubscribe on unmount
      send('UNSUBSCRIBE', { entity_type: entityType, entity_id: entityId })
    }
  }, [isConnected, entityType, entityId, send])
  
  // Invalidate query when entity updates
  useEffect(() => {
    const handleMessage = (event: MessageEvent) => {
      const message = JSON.parse(event.data)
      if (
        message.type === `${entityType.toUpperCase()}_UPDATED` &&
        message.payload.id === entityId
      ) {
        queryClient.invalidateQueries({ queryKey })
      }
    }
    
    // This would be handled by the global WebSocket hook
    // but included here for clarity
  }, [entityType, entityId, queryKey, queryClient])
}
```

### 7.16 Cache Management Hook

#### `useCacheManager.ts` - Manual Cache Operations

```typescript
// hooks/cache/useCacheManager.ts
import { useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

export function useCacheManager() {
  const queryClient = useQueryClient()
  
  const invalidate = useCallback((queryKey: readonly unknown[]) => {
    queryClient.invalidateQueries({ queryKey })
  }, [queryClient])
  
  const remove = useCallback((queryKey: readonly unknown[]) => {
    queryClient.removeQueries({ queryKey })
  }, [queryClient])
  
  const refetch = useCallback((queryKey: readonly unknown[]) => {
    queryClient.refetchQueries({ queryKey })
  }, [queryClient])
  
  const getCache = useCallback(<T>(queryKey: readonly unknown[]): T | undefined => {
    return queryClient.getQueryData<T>(queryKey)
  }, [queryClient])
  
  const setCache = useCallback(<T>(queryKey: readonly unknown[], data: T) => {
    queryClient.setQueryData(queryKey, data)
  }, [queryClient])
  
  const clearAll = useCallback(() => {
    queryClient.clear()
  }, [queryClient])
  
  return {
    invalidate,
    remove,
    refetch,
    getCache,
    setCache,
    clearAll,
  }
}
```

### 7.17 Terminal Streaming Hook (Xterm.js)

#### `useTerminalStream.ts` - Real-time Terminal Output Streaming for Xterm.js

```typescript
// hooks/terminal/useTerminalStream.ts
import { useState, useEffect, useCallback, useRef } from 'react'
import { useWebSocketConnection } from './useWebSocketConnection'

interface UseTerminalStreamOptions {
  taskId?: string
  agentId?: string
  projectId?: string
  onData?: (data: string) => void // Callback for Xterm.js write
}

export function useTerminalStream(options: UseTerminalStreamOptions = {}) {
  const { taskId, agentId, projectId, onData } = options
  const { send, isConnected, lastMessage } = useWebSocketConnection()
  const [isStreaming, setIsStreaming] = useState(false)
  const lastMessageTimeRef = useRef<number>(0)
  const streamingTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  
  // Subscribe to terminal stream
  useEffect(() => {
    if (!isConnected) return
    
    const subscription = {
      task_id: taskId,
      agent_id: agentId,
      project_id: projectId,
    }
    
    send('SUBSCRIBE_TERMINAL', subscription)
    
    return () => {
      send('UNSUBSCRIBE_TERMINAL', subscription)
    }
  }, [isConnected, taskId, agentId, projectId, send])
  
  // Handle terminal output messages
  useEffect(() => {
    if (!lastMessage) return
    
    try {
      const message = JSON.parse(lastMessage.data)
      
      if (message.type === 'TERMINAL_OUTPUT') {
        const { data, task_id, agent_id, timestamp } = message.payload
        
        // Filter by subscription if needed
        if (taskId && task_id !== taskId) return
        if (agentId && agent_id !== agentId) return
        
        // Write directly to Xterm.js via callback
        if (onData) {
          onData(data)
        }
        
        // Update streaming status
        setIsStreaming(true)
        lastMessageTimeRef.current = timestamp || Date.now()
        
        // Clear streaming status after 2 seconds of inactivity
        if (streamingTimeoutRef.current) {
          clearTimeout(streamingTimeoutRef.current)
        }
        streamingTimeoutRef.current = setTimeout(() => {
          setIsStreaming(false)
        }, 2000)
      }
    } catch (error) {
      console.error('Error parsing terminal message:', error)
    }
  }, [lastMessage, taskId, agentId, onData])
  
  const clear = useCallback(() => {
    // Clear is handled by Xterm.js terminal instance
    setIsStreaming(false)
  }, [])
  
  const write = useCallback((data: string) => {
    if (onData) {
      onData(data)
    }
  }, [onData])
  
  return {
    isStreaming,
    clear,
    write,
  }
}
```

#### `useTerminalCommand.ts` - Execute Commands and Stream Output

```typescript
// hooks/terminal/useTerminalCommand.ts
import { useState, useCallback } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useWebSocketConnection } from './useWebSocketConnection'

interface ExecuteCommandOptions {
  taskId?: string
  agentId?: string
  projectId?: string
  command: string
  workingDirectory?: string
  onOutput?: (data: string) => void // For Xterm.js
}

export function useTerminalCommand(onOutput?: (data: string) => void) {
  const { send, isConnected } = useWebSocketConnection()
  const [isExecuting, setIsExecuting] = useState(false)
  
  const execute = useMutation({
    mutationFn: async (options: ExecuteCommandOptions) => {
      setIsExecuting(true)
      
      // Send command via WebSocket for real-time streaming
      if (isConnected) {
        send('EXECUTE_COMMAND', {
          task_id: options.taskId,
          agent_id: options.agentId,
          project_id: options.projectId,
          command: options.command,
          working_directory: options.workingDirectory,
        })
      } else {
        // Fallback to HTTP API
        const res = await fetch('/api/v1/terminal/execute', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(options),
        })
        return res.json()
      }
    },
    onSettled: () => {
      setIsExecuting(false)
    },
  })
  
  return {
    execute: execute.mutate,
    isExecuting,
    error: execute.error,
  }
}
```

#### `useXterm.ts` - Xterm.js Terminal Instance Management

```typescript
// hooks/terminal/useXterm.ts
import { useEffect, useRef, useState } from 'react'
import { Terminal as XTerm } from 'xterm'
import { FitAddon } from 'xterm-addon-fit'
import { WebLinksAddon } from 'xterm-addon-web-links'
import { SearchAddon } from 'xterm-addon-search'
import { Unicode11Addon } from 'xterm-addon-unicode11'
import { SerializeAddon } from 'xterm-addon-serialize'
import { useTheme } from 'next-themes'

interface UseXtermOptions {
  containerRef: React.RefObject<HTMLDivElement>
  fontSize?: number
  fontFamily?: string
  cursorBlink?: boolean
  cursorStyle?: 'block' | 'underline' | 'bar'
  scrollback?: number
}

export function useXterm(options: UseXtermOptions) {
  const { containerRef, fontSize = 14, fontFamily, cursorBlink = true, cursorStyle = 'block', scrollback = 1000 } = options
  const { theme } = useTheme()
  const xtermRef = useRef<XTerm | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const [isReady, setIsReady] = useState(false)
  
  useEffect(() => {
    if (!containerRef.current) return
    
    const xterm = new XTerm({
      fontSize,
      fontFamily: fontFamily || "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace",
      cursorBlink,
      cursorStyle,
      scrollback,
      theme: {
        background: theme === 'dark' 
          ? 'hsl(var(--background))' 
          : '#ffffff',
        foreground: theme === 'dark'
          ? 'hsl(var(--foreground))'
          : '#000000',
        cursor: theme === 'dark'
          ? 'hsl(var(--foreground))'
          : '#000000',
        selection: 'hsl(var(--accent))',
        // ANSI colors
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5',
      },
      allowProposedApi: true,
    })
    
    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()
    const searchAddon = new SearchAddon()
    const unicode11Addon = new Unicode11Addon()
    const serializeAddon = new SerializeAddon()
    
    xterm.loadAddon(fitAddon)
    xterm.loadAddon(webLinksAddon)
    xterm.loadAddon(searchAddon)
    xterm.loadAddon(unicode11Addon)
    xterm.loadAddon(serializeAddon)
    
    xterm.open(containerRef.current)
    fitAddon.fit()
    
    xtermRef.current = xterm
    fitAddonRef.current = fitAddon
    setIsReady(true)
    
    // Handle resize
    const handleResize = () => {
      fitAddon.fit()
    }
    window.addEventListener('resize', handleResize)
    
    return () => {
      window.removeEventListener('resize', handleResize)
      xterm.dispose()
      setIsReady(false)
    }
  }, [containerRef, fontSize, fontFamily, cursorBlink, cursorStyle, scrollback, theme])
  
  const write = useCallback((data: string) => {
    xtermRef.current?.write(data)
  }, [])
  
  const clear = useCallback(() => {
    xtermRef.current?.clear()
  }, [])
  
  const fit = useCallback(() => {
    fitAddonRef.current?.fit()
  }, [])
  
  return {
    xterm: xtermRef.current,
    fitAddon: fitAddonRef.current,
    isReady,
    write,
    clear,
    fit,
  }
}
```

---

## 8. Code Highlighting Configuration

### 8.1 Syntax Highlighting Setup

**Recommended Library**: `react-syntax-highlighter` with Prism

**Installation**:
```bash
npm install react-syntax-highlighter @types/react-syntax-highlighter
```

**Theme Support**: 
- Dark mode: `vscDarkPlus`, `dracula`, `nightOwl`
- Light mode: `oneLight`, `prism`, `ghcolors`

**Language Detection**: Auto-detect from file extension or explicit `language` prop

**Performance Optimization**: Use dynamic imports for large language grammars:
```typescript
// lib/code-highlighting.ts
import dynamic from 'next/dynamic'

export const SyntaxHighlighter = dynamic(
  () => import('react-syntax-highlighter').then(mod => mod.Prism),
  { ssr: false }
)

export const CodeBlock = dynamic(
  () => import('@/components/shared/CodeBlock'),
  { ssr: false }
)
```

### 8.2 Language Detection Hook

```typescript
// hooks/code/useLanguageDetection.ts
import { useMemo } from 'react'

export function useLanguageDetection(filename?: string, explicitLanguage?: string) {
  return useMemo(() => {
    if (explicitLanguage) return explicitLanguage
    
    if (!filename) return 'text'
    
    const ext = filename.split('.').pop()?.toLowerCase()
    
    const languageMap: Record<string, string> = {
      'js': 'javascript',
      'jsx': 'javascript',
      'ts': 'typescript',
      'tsx': 'typescript',
      'py': 'python',
      'rb': 'ruby',
      'go': 'go',
      'rs': 'rust',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'php': 'php',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'sh': 'bash',
      'bash': 'bash',
      'zsh': 'bash',
      'yaml': 'yaml',
      'yml': 'yaml',
      'json': 'json',
      'xml': 'xml',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'sass': 'sass',
      'md': 'markdown',
      'sql': 'sql',
      'dockerfile': 'dockerfile',
      'makefile': 'makefile',
      'env': 'bash',
      'gitignore': 'text',
      'txt': 'text',
    }
    
    return languageMap[ext || ''] || 'text'
  }, [filename, explicitLanguage])
}
```

### 8.3 Diff Highlighting Hook

```typescript
// hooks/code/useDiffHighlighting.ts
import { useMemo } from 'react'
import { useLanguageDetection } from './useLanguageDetection'

interface DiffLine {
  type: 'added' | 'deleted' | 'unchanged' | 'context'
  content: string
  oldLine?: number
  newLine?: number
}

export function useDiffHighlighting(
  diff: string,
  filename?: string,
  language?: string
) {
  const detectedLanguage = useLanguageDetection(filename, language)
  
  const parsedDiff = useMemo(() => {
    const lines = diff.split('\n')
    const result: DiffLine[] = []
    
    lines.forEach((line, index) => {
      if (line.startsWith('+++') || line.startsWith('---')) {
        result.push({ type: 'context', content: line })
      } else if (line.startsWith('+')) {
        result.push({ type: 'added', content: line.slice(1) })
      } else if (line.startsWith('-')) {
        result.push({ type: 'deleted', content: line.slice(1) })
      } else if (line.startsWith('@@')) {
        result.push({ type: 'context', content: line })
      } else {
        result.push({ type: 'unchanged', content: line })
      }
    })
    
    return result
  }, [diff])
  
  return {
    lines: parsedDiff,
    language: detectedLanguage,
  }
}
```

---

## 9. Xterm.js Terminal Integration

### 9.1 Installation & Setup

**Installation**:
```bash
# Core package
npm install xterm

# Essential addons
npm install xterm-addon-fit xterm-addon-web-links xterm-addon-search xterm-addon-unicode11 xterm-addon-serialize

# Optional addons
npm install xterm-addon-image xterm-addon-ligatures xterm-addon-clipboard xterm-addon-attach
```

**CSS Import** (Required):
```typescript
// app/layout.tsx or app/globals.css
import "xterm/css/xterm.css"
```

**Dynamic Import** (Recommended for Next.js SSR):
```typescript
// components/terminal/TerminalViewer.tsx
import dynamic from 'next/dynamic'

export const TerminalViewer = dynamic(
  () => import('./TerminalViewer').then(mod => mod.TerminalViewer),
  { ssr: false }
)
```

### 9.2 WebSocket Event Format

**TERMINAL_OUTPUT Event**:
```typescript
{
  type: 'TERMINAL_OUTPUT',
  payload: {
    data: string,        // Raw terminal data (ANSI escape sequences supported)
    task_id?: string,
    agent_id?: string,
    project_id?: string,
    timestamp: number,
  }
}
```

**EXECUTE_COMMAND Event** (Client → Server):
```typescript
{
  type: 'EXECUTE_COMMAND',
  payload: {
    task_id?: string,
    agent_id?: string,
    project_id?: string,
    command: string,
    working_directory?: string,
  }
}
```

### 9.3 Terminal Features

**Supported Features**:
- ✅ ANSI color codes
- ✅ Cursor control
- ✅ Text selection and copy
- ✅ Paste support (Ctrl/Cmd+V)
- ✅ Web links (clickable URLs) - WebLinksAddon
- ✅ Search functionality - SearchAddon
- ✅ Auto-fit to container - FitAddon
- ✅ Scrollback buffer
- ✅ Fullscreen mode
- ✅ Theme support (dark/light)
- ✅ Unicode 11 support - Unicode11Addon
- ✅ Terminal serialization - SerializeAddon
- ✅ Image display - ImageAddon (optional)
- ✅ Font ligatures - LigaturesAddon (optional)
- ✅ Enhanced clipboard - ClipboardAddon (optional)

**Performance Optimizations**:
- Limit scrollback buffer size
- Use `fastScrollModifier` for large outputs
- Debounce resize events
- Virtual scrolling for very long outputs (if needed)
- Use WebGL renderer for very large outputs (100k+ lines)

### 9.4 AttachAddon Alternative (Direct WebSocket)

For simpler WebSocket integration, you can use `AttachAddon` instead of manual handling:

```typescript
// hooks/terminal/useTerminalAttach.ts
import { useEffect, useRef } from 'react'
import { Terminal as XTerm } from 'xterm'
import { AttachAddon } from 'xterm-addon-attach'
import { FitAddon } from 'xterm-addon-fit'

export function useTerminalAttach(
  xterm: XTerm | null,
  wsUrl: string,
  enabled: boolean = true
) {
  const attachAddonRef = useRef<AttachAddon | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  
  useEffect(() => {
    if (!xterm || !enabled) return
    
    const ws = new WebSocket(wsUrl)
    const attachAddon = new AttachAddon(ws)
    
    xterm.loadAddon(attachAddon)
    attachAddonRef.current = attachAddon
    wsRef.current = ws
    
    ws.onopen = () => {
      console.log('Terminal WebSocket connected')
    }
    
    ws.onerror = (error) => {
      console.error('Terminal WebSocket error:', error)
    }
    
    ws.onclose = () => {
      console.log('Terminal WebSocket closed')
    }
    
    return () => {
      attachAddon.dispose()
      ws.close()
      attachAddonRef.current = null
      wsRef.current = null
    }
  }, [xterm, wsUrl, enabled])
  
  return {
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    reconnect: () => {
      // Reconnection logic
    },
  }
}
```

**Note**: AttachAddon automatically handles bidirectional communication, but our manual approach gives more control over message formatting and filtering.

---

## 10. Advanced Zustand Middleware

### 10.1 WebSocket Sync Middleware

Synchronizes Zustand state with WebSocket events.

```typescript
// middleware/websocket-sync.ts
import { StateCreator, StoreMutatorIdentifier } from 'zustand'

type WebSocketSync = <T>(
  config: StateCreator<T>,
  options: {
    getWebSocket: () => WebSocket | null
    eventTypes: string[]
    onMessage: (message: any, state: T) => Partial<T> | ((state: T) => T)
    syncToServer?: boolean
  }
) => StateCreator<T>

export const websocketSync: WebSocketSync = (config, options) => (set, get, api) => {
  const setupListener = () => {
    const ws = options.getWebSocket()
    if (!ws) return
    
    const handleMessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data)
      
      if (options.eventTypes.includes(data.type || data.event_type)) {
        const update = options.onMessage(data, get())
        
        if (typeof update === 'function') {
          set(update as any)
        } else {
          set(update as any)
        }
      }
    }
    
    ws.addEventListener('message', handleMessage)
    return () => ws.removeEventListener('message', handleMessage)
  }
  
  if (typeof window !== 'undefined') {
    setupListener()
  }
  
  return config(set, get, api)
}
```

### 10.2 React Query Bridge Middleware

Bidirectional sync between Zustand and React Query.

```typescript
// middleware/react-query-bridge.ts
import { QueryClient, QueryKey } from '@tanstack/react-query'
import { StateCreator } from 'zustand'

type ReactQueryBridge = <T>(
  config: StateCreator<T>,
  options: {
    queryClient: QueryClient
    invalidationRules: Array<{
      shouldInvalidate: (prev: T, next: T) => boolean
      queryKeys: QueryKey[] | ((state: T) => QueryKey[])
      optimisticUpdate?: (state: T) => Array<{
        queryKey: QueryKey
        updater: (old: any) => any
      }>
    }>
    syncRules?: Array<{
      queryKey: QueryKey
      toState: (data: any) => Partial<T>
      shouldSync?: (data: any) => boolean
    }>
  }
) => StateCreator<T>

export const reactQueryBridge: ReactQueryBridge = (config, options) => (set, get, api) => {
  const enhancedSet: typeof set = (partial, replace) => {
    const prevState = get()
    set(partial, replace)
    const nextState = get()
    
    options.invalidationRules.forEach((rule) => {
      if (rule.shouldInvalidate(prevState, nextState)) {
        const keys = typeof rule.queryKeys === 'function' 
          ? rule.queryKeys(nextState) 
          : rule.queryKeys
        
        if (rule.optimisticUpdate) {
          const updates = rule.optimisticUpdate(nextState)
          updates.forEach(({ queryKey, updater }) => {
            options.queryClient.setQueryData(queryKey, updater)
          })
        }
        
        keys.forEach((key) => {
          options.queryClient.invalidateQueries({ queryKey: key })
        })
      }
    })
  }
  
  return config(enhancedSet, get, api)
}
```

### 10.3 SSR-Safe Store Creation

```typescript
// lib/create-ssr-store.ts
import { create, StateCreator } from 'zustand'
import { persist, PersistOptions } from 'zustand/middleware'

export function createSSRStore<T>(
  storeCreator: StateCreator<T>,
  persistOptions?: Partial<PersistOptions<T>>
) {
  if (typeof window === 'undefined') {
    return create<T>()(storeCreator)
  }
  
  return create<T>()(
    persist(storeCreator, {
      name: persistOptions?.name || 'store',
      skipHydration: true,
      ...persistOptions,
    })
  )
}

// Hook for hydration
export function useHydrateStore(useStore: any) {
  const [hydrated, setHydrated] = useState(false)
  
  useEffect(() => {
    const unsubHydrate = useStore.persist.onFinishHydration(() => {
      setHydrated(true)
    })
    
    useStore.persist.rehydrate()
    return unsubHydrate
  }, [])
  
  return hydrated
}
```

### 10.4 Complete Integration Example

Full Kanban store with all middleware.

```typescript
// stores/kanbanStore.ts
import { create } from 'zustand'
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import { websocketSync } from '@/middleware/websocket-sync'
import { reactQueryBridge } from '@/middleware/react-query-bridge'
import { temporal } from 'zundo'
import { compressedStorage } from '@/lib/storage'
import { boardKeys } from '@/lib/query-keys'

let wsInstance: WebSocket | null = null
export const setKanbanWebSocket = (ws: WebSocket | null) => {
  wsInstance = ws
}

export const useKanbanStore = create<KanbanState>()(
  devtools(
    persist(
      websocketSync(
        reactQueryBridge(
          temporal(
            subscribeWithSelector(
              immer((set, get) => ({
                // ... state implementation
              }))
            ),
            { limit: 20, enabled: process.env.NODE_ENV === 'development' }
          ),
          {
            queryClient: queryClient,
            invalidationRules: [
              {
                shouldInvalidate: (prev, next) => prev.tickets !== next.tickets,
                queryKeys: (state) => [boardKeys.detail(state.projectId!)],
                optimisticUpdate: (state) => [{
                  queryKey: boardKeys.detail(state.projectId!),
                  updater: (old: any) => ({
                    ...old,
                    tickets: Object.values(state.tickets),
                  }),
                }],
              },
            ],
          }
        ),
        {
          getWebSocket: () => wsInstance,
          eventTypes: ['TICKET_MOVED', 'TICKET_UPDATED'],
          onMessage: (message, state) => {
            // Transform WebSocket message to state update
            return (draft) => {
              // Immer draft mutations
            }
          },
        }
      ),
      {
        name: 'kanban-store',
        storage: compressedStorage,
      }
    ),
    { name: 'KanbanStore' }
  )
)

// Time-travel actions (from zundo)
const { undo, redo, clear } = useKanbanStore.temporal.getState()
```

### 10.5 Cross-Tab Synchronization

Using `zustand-pub` for multi-tab sync.

```typescript
// stores/uiStore.ts
import { pub } from 'zustand-pub'

export const useUIStore = create<UIState>()(
  pub(
    devtools(
      persist(
        (set) => ({
          // ... state
        }),
        { name: 'ui-store' }
      ),
      { name: 'UIStore' }
    ),
    {
      name: 'ui-channel', // Broadcast channel name
    }
  )
)

// Changes in one tab automatically sync to others
```

### 10.6 Store Provider with Hydration

```typescript
// providers/StoreProvider.tsx
"use client"

import { useEffect, useRef } from 'react'
import { useKanbanStore, setKanbanWebSocket } from '@/stores/kanbanStore'
import { useAgentStore, setAgentWebSocket } from '@/stores/agentStore'
import { useUIStore } from '@/stores/uiStore'
import { useWebSocket } from '@/hooks/useWebSocket'

export function StoreProvider({ children }: { children: React.ReactNode }) {
  const { socket } = useWebSocket()
  const hasHydrated = useRef(false)
  
  // Setup WebSocket connections
  useEffect(() => {
    if (socket) {
      setKanbanWebSocket(socket)
      setAgentWebSocket(socket)
    }
    
    return () => {
      setKanbanWebSocket(null)
      setAgentWebSocket(null)
    }
  }, [socket])
  
  // Manual hydration for SSR
  useEffect(() => {
    if (!hasHydrated.current) {
      useKanbanStore.persist.rehydrate()
      useAgentStore.persist.rehydrate()
      useUIStore.persist.rehydrate()
      hasHydrated.current = true
    }
  }, [])
  
  return <>{children}</>
}
```

---

## 11. Advanced Zustand Middleware Reference

### 11.1 Compressed Storage

Storage adapter with LZ-string compression for large state objects.

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
      return str
    }
  },
  
  setItem: (name, value) => {
    try {
      const compressed = compress(value)
      localStorage.setItem(name, compressed)
    } catch (error) {
      console.error('Compression error:', error)
      localStorage.setItem(name, value)
    }
  },
  
  removeItem: (name) => localStorage.removeItem(name),
}

// Robust storage with fallback
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
        // Storage unavailable
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

### 11.2 Time-Travel Debugging Middleware

```typescript
// middleware/time-travel.ts
import { StateCreator } from 'zustand'

export const timeTravel = <T>(
  config: StateCreator<T>,
  options: { maxHistory?: number; enabled?: boolean } = {}
) => (set: any, get: any, api: any) => {
  const { maxHistory = 50, enabled = process.env.NODE_ENV === 'development' } = options
  
  if (!enabled) {
    return config(set, get, api)
  }
  
  let history: T[] = []
  let historyIndex = -1
  
  const enhancedSet = (partial: any, replace?: boolean) => {
    if (historyIndex === history.length - 1) {
      history.push(get())
      if (history.length > maxHistory) {
        history.shift()
      } else {
        historyIndex++
      }
    } else {
      history = history.slice(0, historyIndex + 1)
      history.push(get())
      historyIndex = history.length - 1
    }
    
    set(partial, replace)
  }
  
  return {
    ...config(enhancedSet, get, api),
    undo: () => {
      if (historyIndex > 0) {
        historyIndex--
        set(history[historyIndex], true)
      }
    },
    redo: () => {
      if (historyIndex < history.length - 1) {
        historyIndex++
        set(history[historyIndex], true)
      }
    },
  }
}
```

### 11.3 Recommended Package Installations

```bash
# Core Zustand packages
npm install zustand immer

# Middleware extensions
npm install zundo  # Advanced undo/redo
npm install zustand-pub  # Cross-tab sync

# Utilities
npm install lz-string  # State compression
npm install zustand-querystring  # URL state sync (optional)

# React Query integration
npm install @tanstack/react-query @tanstack/react-query-devtools

# WebSocket client
npm install use-websocket  # Alternative to custom hook

# Animations
npm install framer-motion

# Terminal
npm install xterm xterm-addon-fit xterm-addon-web-links xterm-addon-search xterm-addon-unicode11 xterm-addon-serialize

# Code highlighting
npm install react-syntax-highlighter @types/react-syntax-highlighter

# Utilities
npm install date-fns
```

### 11.4 Store Architecture Summary

**Store Hierarchy**:
```
Root Providers
├── ThemeProvider (next-themes)
├── QueryProvider (React Query)
├── WebSocketProvider (Custom)
└── StoreProvider (Zustand hydration)
    ├── useUIStore (Global UI state)
    ├── useKanbanStore (Board state + WebSocket + RQ bridge)
    ├── useAgentStore (Agent state + WebSocket + RQ bridge)
    ├── useSearchStore (Search + history)
    ├── useTerminalStore (Multi-session terminals)
    └── useMonitoringStore (System metrics)
```

**Middleware Features**:
- ✅ SSR compatibility with manual hydration
- ✅ WebSocket real-time synchronization
- ✅ React Query automatic invalidation
- ✅ Persistent state with compression
- ✅ Time-travel debugging (dev only)
- ✅ Cross-tab synchronization (optional)
- ✅ Optimistic updates
- ✅ Type-safe selectors
- ✅ Redux DevTools integration

---

## 12. Practical Integration Examples

### 12.1 Complete Kanban Board Integration

Example showing Zustand + React Query + WebSocket working together:

```typescript
// components/kanban/KanbanBoard.tsx
"use client"

import { useEffect } from "react"
import { DndContext, DragEndEvent, DragStartEvent } from "@dnd-kit/core"
import { useKanbanStore } from "@/stores/kanbanStore"
import { useBoard } from "@/hooks/useBoard"
import { useMoveTicket } from "@/hooks/useBoard"
import { useUIStore } from "@/stores/uiStore"
import { shallow } from "zustand/shallow"

export function KanbanBoard({ projectId }: { projectId: string }) {
  const { data: boardData } = useBoard(projectId)
  const moveTicketMutation = useMoveTicket()
  const { addToast } = useUIStore()
  
  // Optimized Zustand selectors
  const {
    columns,
    tickets,
    draggedTicket,
    setColumns,
    setTickets,
    setDraggedTicket,
    moveTicket,
  } = useKanbanStore(
    (state) => ({
      columns: state.columns,
      tickets: state.tickets,
      draggedTicket: state.draggedTicket,
      setColumns: state.setColumns,
      setTickets: state.setTickets,
      setDraggedTicket: state.setDraggedTicket,
      moveTicket: state.moveTicket,
    }),
    shallow
  )

  // Sync React Query data → Zustand store
  useEffect(() => {
    if (boardData) {
      setColumns(boardData.columns)
      setTickets(
        boardData.tickets.reduce((acc, ticket) => {
          acc[ticket.id] = ticket
          return acc
        }, {})
      )
    }
  }, [boardData, setColumns, setTickets])

  const handleDragStart = (event: DragStartEvent) => {
    setDraggedTicket(event.active.id as string)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    
    if (over && active.id !== over.id) {
      const ticketId = active.id as string
      const ticket = tickets[ticketId]
      const newColumnId = over.id as string
      
      // 1. Optimistic update in Zustand (instant UI feedback)
      moveTicket(ticketId, ticket.status, newColumnId)
      
      // 2. React Query mutation (persist to server)
      // 3. React Query Bridge middleware will auto-invalidate cache
      // 4. WebSocket sync middleware will handle real-time updates from other clients
      moveTicketMutation.mutate(
        { ticketId, columnId: newColumnId, projectId },
        {
          onSuccess: () => {
            addToast({ type: 'success', message: 'Ticket moved' })
          },
          onError: () => {
            addToast({ type: 'error', message: 'Failed to move ticket' })
            // React Query will rollback optimistic update
          },
        }
      )
    }
    
    setDraggedTicket(null)
  }

  return (
    <DndContext onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
      {/* Board columns */}
    </DndContext>
  )
}
```

### 12.2 Real-Time Agent Health Monitoring

```typescript
// components/agents/AgentHealthMonitor.tsx
"use client"

import { useEffect } from "react"
import { useAgentStore } from "@/stores/agentStore"
import { useAgents } from "@/hooks/useAgents"
import { useWebSocketSubscription } from "@/hooks/useWebSocket"
import { Badge } from "@/components/ui/badge"
import { motion } from "framer-motion"

export function AgentHealthMonitor() {
  const { data: agents } = useAgents()
  const { agentHealthMap, updateAgentHealth } = useAgentStore()
  
  // WebSocket updates health map via middleware
  // No manual subscription needed - middleware handles it!
  
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {agents?.map((agent) => {
        const health = agentHealthMap[agent.id]
        
        return (
          <motion.div
            key={agent.id}
            layout
            className="p-4 border rounded-lg"
          >
            <div className="flex items-center justify-between">
              <span className="font-medium">{agent.name}</span>
              <Badge variant={health?.isStale ? "destructive" : "default"}>
                {health?.isStale ? "Stale" : "Active"}
              </Badge>
            </div>
            {health?.lastHeartbeat && (
              <span className="text-xs text-muted-foreground">
                Last heartbeat: {formatDistanceToNow(new Date(health.lastHeartbeat))}
              </span>
            )}
          </motion.div>
        )
      })}
    </div>
  )
}
```

### 12.3 Search with History and Type Filters

```typescript
// components/search/AdvancedSearch.tsx
"use client"

import { useSearchStore } from "@/stores/searchStore"
import { useSearchResults } from "@/hooks/useSearch"
import { useDebouncedValue } from "@/hooks/useDebouncedValue"
import { Command, CommandInput, CommandList, CommandGroup, CommandItem } from "@/components/ui/command"
import { Badge } from "@/components/ui/badge"

export function AdvancedSearch() {
  const {
    query,
    searchHistory,
    selectedTypes,
    setQuery,
    addToHistory,
    setSelectedTypes,
    getFilteredResults,
  } = useSearchStore()
  
  const debouncedQuery = useDebouncedValue(query, 300)
  const { data: results } = useSearchResults(debouncedQuery)
  
  // Store automatically persists searchHistory to localStorage
  // WebSocket sync middleware keeps results updated in real-time
  
  const handleSearch = (searchQuery: string) => {
    setQuery(searchQuery)
    if (searchQuery.trim()) {
      addToHistory(searchQuery) // Auto-persisted
    }
  }
  
  const toggleType = (type: string) => {
    setSelectedTypes(
      selectedTypes.includes(type)
        ? selectedTypes.filter((t) => t !== type)
        : [...selectedTypes, type]
    )
  }
  
  const filteredResults = getFilteredResults()
  
  return (
    <Command>
      <CommandInput value={query} onValueChange={handleSearch} />
      
      {/* Type filters */}
      <div className="flex gap-2 p-2">
        {['ticket', 'agent', 'commit'].map((type) => (
          <Badge
            key={type}
            variant={selectedTypes.includes(type) ? "default" : "outline"}
            onClick={() => toggleType(type)}
            className="cursor-pointer"
          >
            {type}
          </Badge>
        ))}
      </div>
      
      <CommandList>
        {!query && searchHistory.length > 0 && (
          <CommandGroup heading="Recent">
            {searchHistory.slice(0, 5).map((item) => (
              <CommandItem key={item} onSelect={() => handleSearch(item)}>
                {item}
              </CommandItem>
            ))}
          </CommandGroup>
        )}
        
        {filteredResults.map((result) => (
          <CommandItem key={result.id}>{result.title}</CommandItem>
        ))}
      </CommandList>
    </Command>
  )
}
```

### 12.4 Undo/Redo Implementation with Zundo

```typescript
// components/kanban/KanbanToolbar.tsx
import { useKanbanStore } from "@/stores/kanbanStore"
import { Button } from "@/components/ui/button"
import { Undo, Redo } from "lucide-react"

export function KanbanToolbar() {
  const { undo, redo, futureStates, pastStates } = useKanbanStore.temporal.getState()
  
  const canUndo = pastStates.length > 0
  const canRedo = futureStates.length > 0
  
  return (
    <div className="flex gap-2">
      <Button
        variant="outline"
        size="sm"
        onClick={undo}
        disabled={!canUndo}
        title={`Undo (${pastStates.length} available)`}
      >
        <Undo className="h-4 w-4" />
      </Button>
      <Button
        variant="outline"
        size="sm"
        onClick={redo}
        disabled={!canRedo}
        title={`Redo (${futureStates.length} available)`}
      >
        <Redo className="h-4 w-4" />
      </Button>
    </div>
  )
}
```

---

This completes the comprehensive system-wide reusable hooks documentation covering UI state, forms, navigation, permissions, optimistic updates, pagination, search/filters, storage, WebSocket, keyboard shortcuts, clipboard, file upload, export/import, theme, real-time subscriptions, cache management, terminal streaming with Xterm.js, code highlighting, advanced Zustand middleware integration, complete provider architecture, and practical integration examples.

