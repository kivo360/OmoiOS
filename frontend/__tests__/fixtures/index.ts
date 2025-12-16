/**
 * Test fixtures for consistent mock data across tests
 *
 * Import these fixtures in your tests instead of creating mock data inline.
 * This ensures consistency and makes tests easier to maintain.
 */

import type {
  User,
  Project,
  Ticket,
  Agent,
  Task,
  BoardViewResponse,
} from "@/lib/api/types"

// ============================================================================
// User Fixtures
// ============================================================================

export const users = {
  default: {
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
  } satisfies User,

  admin: {
    id: "user-admin",
    email: "admin@example.com",
    full_name: "Admin User",
    department: "Platform",
    is_active: true,
    is_verified: true,
    is_super_admin: true,
    avatar_url: "https://example.com/avatar.png",
    attributes: { role: "admin" },
    created_at: "2023-01-01T00:00:00Z",
    last_login_at: "2024-01-16T08:00:00Z",
  } satisfies User,

  unverified: {
    id: "user-unverified",
    email: "unverified@example.com",
    full_name: "Unverified User",
    department: null,
    is_active: true,
    is_verified: false,
    is_super_admin: false,
    avatar_url: null,
    attributes: null,
    created_at: "2024-01-10T00:00:00Z",
    last_login_at: null,
  } satisfies User,
}

// ============================================================================
// Project Fixtures
// ============================================================================

export const projects = {
  active: {
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
  } satisfies Project,

  paused: {
    id: "proj-2",
    name: "Paused Project",
    description: "A paused project",
    github_owner: null,
    github_repo: null,
    github_connected: false,
    default_phase_id: "phase-1",
    status: "paused",
    settings: null,
    created_at: "2024-01-05T00:00:00Z",
    updated_at: "2024-01-10T10:00:00Z",
  } satisfies Project,

  archived: {
    id: "proj-3",
    name: "Archived Project",
    description: "An archived project",
    github_owner: "kivo360",
    github_repo: "old-repo",
    github_connected: false,
    default_phase_id: "phase-1",
    status: "archived",
    settings: { archived_reason: "Completed" },
    created_at: "2023-06-01T00:00:00Z",
    updated_at: "2023-12-01T00:00:00Z",
  } satisfies Project,
}

// ============================================================================
// Ticket Fixtures
// ============================================================================

export const tickets = {
  inProgress: {
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
  } satisfies Ticket,

  todo: {
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
  } satisfies Ticket,

  done: {
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
  } satisfies Ticket,

  blocked: {
    id: "ticket-4",
    title: "Deploy to production",
    description: "Deploy the latest changes",
    status: "blocked",
    priority: "critical",
    phase_id: "phase-3",
    approval_status: "pending",
    created_at: "2024-01-15T00:00:00Z",
    updated_at: "2024-01-15T12:00:00Z",
    project_id: "proj-1",
  } satisfies Ticket,
}

// ============================================================================
// Agent Fixtures
// ============================================================================

export const agents = {
  active: {
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
  } satisfies Agent,

  idle: {
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
  } satisfies Agent,

  unhealthy: {
    agent_id: "agent-3",
    agent_type: "tester",
    phase_id: "phase-1",
    status: "active",
    capabilities: ["test", "e2e"],
    capacity: 2,
    health_status: "unhealthy",
    tags: ["testing"],
    last_heartbeat: new Date(Date.now() - 600000).toISOString(), // 10 min ago
    created_at: "2024-01-03T00:00:00Z",
    is_available: false,
  } satisfies Agent,
}

// ============================================================================
// Task Fixtures
// ============================================================================

export const tasks = {
  completed: {
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
  } satisfies Task,

  pending: {
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
  } satisfies Task,

  failed: {
    id: "task-3",
    ticket_id: "ticket-1",
    phase_id: "phase-1",
    task_type: "deployment",
    description: "Deploy to staging",
    priority: "medium",
    status: "failed",
    assigned_agent_id: "agent-1",
    conversation_id: null,
    result: null,
    error_message: "Connection timeout",
    dependencies: null,
    timeout_seconds: 600,
    retry_count: 3,
    max_retries: 3,
    created_at: "2024-01-11T00:00:00Z",
    started_at: "2024-01-11T01:00:00Z",
    completed_at: "2024-01-11T01:05:00Z",
  } satisfies Task,
}

// ============================================================================
// Board Fixtures
// ============================================================================

export const boardViews = {
  default: {
    columns: [
      {
        id: "col-backlog",
        name: "Backlog",
        phase_mappings: ["backlog"],
        wip_limit: null,
        order: 0,
        tickets: [tickets.todo],
      },
      {
        id: "col-inprogress",
        name: "In Progress",
        phase_mappings: ["in_progress"],
        wip_limit: 5,
        order: 1,
        tickets: [tickets.inProgress],
      },
      {
        id: "col-done",
        name: "Done",
        phase_mappings: ["done"],
        wip_limit: null,
        order: 2,
        tickets: [tickets.done],
      },
    ],
  } satisfies BoardViewResponse,

  empty: {
    columns: [
      {
        id: "col-backlog",
        name: "Backlog",
        phase_mappings: ["backlog"],
        wip_limit: null,
        order: 0,
        tickets: [],
      },
      {
        id: "col-inprogress",
        name: "In Progress",
        phase_mappings: ["in_progress"],
        wip_limit: 3,
        order: 1,
        tickets: [],
      },
      {
        id: "col-done",
        name: "Done",
        phase_mappings: ["done"],
        wip_limit: null,
        order: 2,
        tickets: [],
      },
    ],
  } satisfies BoardViewResponse,
}

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * Create a user with custom overrides
 */
export function createUser(overrides: Partial<User> = {}): User {
  return { ...users.default, ...overrides }
}

/**
 * Create a project with custom overrides
 */
export function createProject(overrides: Partial<Project> = {}): Project {
  return { ...projects.active, ...overrides }
}

/**
 * Create a ticket with custom overrides
 */
export function createTicket(overrides: Partial<Ticket> = {}): Ticket {
  return { ...tickets.inProgress, ...overrides }
}

/**
 * Create an agent with custom overrides
 */
export function createAgent(overrides: Partial<Agent> = {}): Agent {
  return { ...agents.active, ...overrides }
}

/**
 * Create a task with custom overrides
 */
export function createTask(overrides: Partial<Task> = {}): Task {
  return { ...tasks.pending, ...overrides }
}

/**
 * Generate a list of tickets
 */
export function createTicketList(count: number): Ticket[] {
  return Array.from({ length: count }, (_, i) =>
    createTicket({
      id: `ticket-gen-${i}`,
      title: `Generated Ticket ${i + 1}`,
    })
  )
}
