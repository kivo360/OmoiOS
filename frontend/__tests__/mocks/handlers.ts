import { http, HttpResponse } from "msw"
import type {
  User,
  TokenResponse,
  Project,
  ProjectListResponse,
  ProjectStats,
  Ticket,
  TicketListResponse,
  Agent,
  BoardViewResponse,
  Task,
  DependencyGraphResponse,
} from "@/lib/api/types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"
const BASE_URL = `${API_URL}/api/v1`

// ============================================================================
// Mock Data Factories
// ============================================================================

export const mockUser: User = {
  id: "user-1",
  email: "test@example.com",
  full_name: "Test User",
  department: "Engineering",
  is_active: true,
  is_verified: true,
  is_super_admin: false,
  avatar_url: null,
  attributes: null,
  created_at: "2024-01-01T00:00:00Z",
  last_login_at: "2024-01-15T10:00:00Z",
}

export const mockTokens: TokenResponse = {
  access_token: "mock-access-token",
  refresh_token: "mock-refresh-token",
  token_type: "bearer",
  expires_in: 900,
}

export const mockProjects: Project[] = [
  {
    id: "proj-1",
    name: "OmoiOS",
    description: "Autonomous engineering platform",
    github_owner: "kivo360",
    github_repo: "OmoiOS",
    github_connected: true,
    default_phase_id: "phase-1",
    status: "active",
    settings: null,
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: "proj-2",
    name: "Test Project",
    description: "A test project for development",
    github_owner: null,
    github_repo: null,
    github_connected: false,
    default_phase_id: "phase-1",
    status: "active",
    settings: null,
    created_at: "2024-01-05T00:00:00Z",
    updated_at: "2024-01-10T10:00:00Z",
  },
]

export const mockProjectStats: ProjectStats = {
  project_id: "proj-1",
  total_tickets: 25,
  tickets_by_status: {
    backlog: 10,
    in_progress: 8,
    done: 7,
  },
  tickets_by_phase: {
    "phase-1": 15,
    "phase-2": 10,
  },
  active_agents: 3,
  total_commits: 45,
}

export const mockTickets: Ticket[] = [
  {
    id: "ticket-1",
    title: "Implement authentication",
    description: "Add JWT-based authentication",
    status: "in_progress",
    priority: "high",
    phase_id: "phase-1",
    approval_status: null,
    created_at: "2024-01-10T00:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
    project_id: "proj-1",
  },
  {
    id: "ticket-2",
    title: "Add testing infrastructure",
    description: "Set up Vitest, RTL, MSW, and Playwright",
    status: "todo",
    priority: "medium",
    phase_id: "phase-1",
    approval_status: null,
    created_at: "2024-01-12T00:00:00Z",
    updated_at: "2024-01-12T00:00:00Z",
    project_id: "proj-1",
  },
  {
    id: "ticket-3",
    title: "Refactor API client",
    description: "Improve error handling",
    status: "done",
    priority: "low",
    phase_id: "phase-2",
    approval_status: "approved",
    created_at: "2024-01-08T00:00:00Z",
    updated_at: "2024-01-14T10:00:00Z",
    project_id: "proj-1",
  },
]

export const mockAgents: Agent[] = [
  {
    agent_id: "agent-1",
    agent_type: "developer",
    phase_id: "phase-1",
    status: "active",
    capabilities: ["code", "test", "review"],
    capacity: 5,
    health_status: "healthy",
    tags: ["backend", "python"],
    last_heartbeat: new Date().toISOString(),
    created_at: "2024-01-01T00:00:00Z",
    is_available: true,
  },
  {
    agent_id: "agent-2",
    agent_type: "reviewer",
    phase_id: "phase-2",
    status: "idle",
    capabilities: ["review", "validate"],
    capacity: 3,
    health_status: "healthy",
    tags: ["review"],
    last_heartbeat: new Date().toISOString(),
    created_at: "2024-01-02T00:00:00Z",
    is_available: true,
  },
]

export const mockBoardView: BoardViewResponse = {
  columns: [
    {
      id: "col-backlog",
      name: "Backlog",
      phase_mappings: ["backlog"],
      wip_limit: null,
      order: 0,
      tickets: [mockTickets[1]],
    },
    {
      id: "col-inprogress",
      name: "In Progress",
      phase_mappings: ["in_progress"],
      wip_limit: 5,
      order: 1,
      tickets: [mockTickets[0]],
    },
    {
      id: "col-done",
      name: "Done",
      phase_mappings: ["done"],
      wip_limit: null,
      order: 2,
      tickets: [mockTickets[2]],
    },
  ],
}

export const mockTasks: Task[] = [
  {
    id: "task-1",
    ticket_id: "ticket-1",
    phase_id: "phase-1",
    task_type: "implementation",
    description: "Implement login endpoint",
    priority: "high",
    status: "completed",
    assigned_agent_id: "agent-1",
    conversation_id: null,
    result: { success: true },
    error_message: null,
    dependencies: null,
    timeout_seconds: 3600,
    retry_count: 0,
    max_retries: 3,
    created_at: "2024-01-10T00:00:00Z",
    started_at: "2024-01-10T01:00:00Z",
    completed_at: "2024-01-10T02:00:00Z",
  },
  {
    id: "task-2",
    ticket_id: "ticket-1",
    phase_id: "phase-1",
    task_type: "testing",
    description: "Write tests for login",
    priority: "high",
    status: "pending",
    assigned_agent_id: null,
    conversation_id: null,
    result: null,
    error_message: null,
    dependencies: { depends_on: ["task-1"] },
    timeout_seconds: 1800,
    retry_count: 0,
    max_retries: 3,
    created_at: "2024-01-10T00:00:00Z",
    started_at: null,
    completed_at: null,
  },
]

export const mockGraph: DependencyGraphResponse = {
  nodes: [
    { id: "task-1", type: "task", label: "Implement login", status: "completed" },
    { id: "task-2", type: "task", label: "Write tests", status: "pending" },
  ],
  edges: [{ source: "task-1", target: "task-2", type: "depends_on" }],
  metadata: { total_nodes: 2, total_edges: 1, ticket_id: "ticket-1" },
}

// ============================================================================
// Request Handlers
// ============================================================================

export const handlers = [
  // Auth handlers
  http.post(`${BASE_URL}/auth/login`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string }
    if (body.email === "test@example.com" && body.password === "password123") {
      return HttpResponse.json(mockTokens)
    }
    return HttpResponse.json(
      { detail: "Invalid credentials" },
      { status: 401 }
    )
  }),

  http.post(`${BASE_URL}/auth/register`, async ({ request }) => {
    const body = (await request.json()) as { email: string; password: string }
    if (body.email === "existing@example.com") {
      return HttpResponse.json(
        { detail: "Email already registered" },
        { status: 400 }
      )
    }
    return HttpResponse.json(mockTokens, { status: 201 })
  }),

  http.post(`${BASE_URL}/auth/refresh`, () => {
    return HttpResponse.json(mockTokens)
  }),

  http.get(`${BASE_URL}/auth/me`, () => {
    return HttpResponse.json(mockUser)
  }),

  http.post(`${BASE_URL}/auth/forgot-password`, () => {
    return HttpResponse.json({ message: "Password reset email sent" })
  }),

  http.post(`${BASE_URL}/auth/reset-password`, () => {
    return HttpResponse.json({ message: "Password reset successful" })
  }),

  // Projects handlers
  http.get(`${BASE_URL}/projects`, () => {
    const response: ProjectListResponse = {
      projects: mockProjects,
      total: mockProjects.length,
    }
    return HttpResponse.json(response)
  }),

  http.get(`${BASE_URL}/projects/:id`, ({ params }) => {
    const project = mockProjects.find((p) => p.id === params.id)
    if (!project) {
      return HttpResponse.json({ detail: "Project not found" }, { status: 404 })
    }
    return HttpResponse.json(project)
  }),

  http.get(`${BASE_URL}/projects/:id/stats`, ({ params }) => {
    if (params.id === "proj-1") {
      return HttpResponse.json(mockProjectStats)
    }
    return HttpResponse.json({ detail: "Project not found" }, { status: 404 })
  }),

  http.post(`${BASE_URL}/projects`, async ({ request }) => {
    const body = (await request.json()) as { name: string; description?: string }
    const newProject: Project = {
      id: `proj-${Date.now()}`,
      name: body.name,
      description: body.description || null,
      github_owner: null,
      github_repo: null,
      github_connected: false,
      default_phase_id: "phase-1",
      status: "active",
      settings: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    return HttpResponse.json(newProject, { status: 201 })
  }),

  // Tickets handlers
  http.get(`${BASE_URL}/tickets`, ({ request }) => {
    const url = new URL(request.url)
    const projectId = url.searchParams.get("project_id")
    let tickets = mockTickets
    if (projectId) {
      tickets = mockTickets.filter((t) => t.project_id === projectId)
    }
    const response: TicketListResponse = {
      tickets,
      total: tickets.length,
    }
    return HttpResponse.json(response)
  }),

  http.get(`${BASE_URL}/tickets/:id`, ({ params }) => {
    const ticket = mockTickets.find((t) => t.id === params.id)
    if (!ticket) {
      return HttpResponse.json({ detail: "Ticket not found" }, { status: 404 })
    }
    return HttpResponse.json(ticket)
  }),

  http.post(`${BASE_URL}/tickets`, async ({ request }) => {
    const body = (await request.json()) as { title: string; description?: string }
    const newTicket: Ticket = {
      id: `ticket-${Date.now()}`,
      title: body.title,
      description: body.description || null,
      status: "backlog",
      priority: "medium",
      phase_id: "phase-1",
      approval_status: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      project_id: "proj-1",
    }
    return HttpResponse.json(newTicket, { status: 201 })
  }),

  // Board handlers
  http.get(`${BASE_URL}/board/:projectId`, () => {
    return HttpResponse.json(mockBoardView)
  }),

  http.post(`${BASE_URL}/board/move`, async ({ request }) => {
    const body = (await request.json()) as {
      ticket_id: string
      target_column_id: string
    }
    return HttpResponse.json({
      success: true,
      ticket_id: body.ticket_id,
      new_column: body.target_column_id,
    })
  }),

  // Agents handlers
  http.get(`${BASE_URL}/agents`, () => {
    return HttpResponse.json(mockAgents)
  }),

  http.get(`${BASE_URL}/agents/:id`, ({ params }) => {
    const agent = mockAgents.find((a) => a.agent_id === params.id)
    if (!agent) {
      return HttpResponse.json({ detail: "Agent not found" }, { status: 404 })
    }
    return HttpResponse.json(agent)
  }),

  http.get(`${BASE_URL}/agents/:id/health`, ({ params }) => {
    const agent = mockAgents.find((a) => a.agent_id === params.id)
    if (!agent) {
      return HttpResponse.json({ detail: "Agent not found" }, { status: 404 })
    }
    return HttpResponse.json({
      agent_id: agent.agent_id,
      status: agent.status,
      health_status: agent.health_status,
      last_heartbeat: agent.last_heartbeat,
      seconds_since_heartbeat: 5,
      is_stale: false,
    })
  }),

  // Tasks handlers
  http.get(`${BASE_URL}/tasks`, ({ request }) => {
    const url = new URL(request.url)
    const ticketId = url.searchParams.get("ticket_id")
    let tasks = mockTasks
    if (ticketId) {
      tasks = mockTasks.filter((t) => t.ticket_id === ticketId)
    }
    return HttpResponse.json({ tasks, total: tasks.length })
  }),

  http.get(`${BASE_URL}/tasks/:id`, ({ params }) => {
    const task = mockTasks.find((t) => t.id === params.id)
    if (!task) {
      return HttpResponse.json({ detail: "Task not found" }, { status: 404 })
    }
    return HttpResponse.json(task)
  }),

  // Graph handlers
  http.get(`${BASE_URL}/graph/ticket/:ticketId`, () => {
    return HttpResponse.json(mockGraph)
  }),

  http.get(`${BASE_URL}/graph/project/:projectId`, () => {
    return HttpResponse.json(mockGraph)
  }),
]
