export interface MockProject {
  id: string;
  name: string;
  description?: string;
  repo: string;
  ticketCount: number;
  activeAgents: number;
  lastActivity: Date;
  status: "active" | "paused" | "archived";
  organizationId: string;
}

export const mockProjects: MockProject[] = [
  {
    id: "proj-001",
    name: "Senseii Games",
    description: "Gaming platform backend and frontend",
    repo: "kivo360/senseii-games",
    ticketCount: 24,
    activeAgents: 2,
    lastActivity: new Date(),
    status: "active",
    organizationId: "org-001",
  },
  {
    id: "proj-002",
    name: "API Service",
    description: "Core API microservice",
    repo: "kivo360/api-service",
    ticketCount: 15,
    activeAgents: 1,
    lastActivity: new Date(Date.now() - 2 * 60 * 60 * 1000),
    status: "active",
    organizationId: "org-001",
  },
  {
    id: "proj-003",
    name: "Database Infrastructure",
    description: "Database schemas and migrations",
    repo: "kivo360/database",
    ticketCount: 8,
    activeAgents: 0,
    lastActivity: new Date(Date.now() - 24 * 60 * 60 * 1000),
    status: "active",
    organizationId: "org-001",
  },
  {
    id: "proj-004",
    name: "Auth System",
    description: "Authentication and authorization service",
    repo: "kivo360/auth-system",
    ticketCount: 12,
    activeAgents: 0,
    lastActivity: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
    status: "active",
    organizationId: "org-001",
  },
  {
    id: "proj-005",
    name: "Payment Gateway",
    description: "Payment processing integration",
    repo: "kivo360/payment-gateway",
    ticketCount: 6,
    activeAgents: 0,
    lastActivity: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    status: "paused",
    organizationId: "org-001",
  },
];

export function getProjectById(id: string): MockProject | undefined {
  return mockProjects.find((project) => project.id === id);
}

export function getProjectByRepo(repo: string): MockProject | undefined {
  return mockProjects.find((project) => project.repo === repo);
}

export function getProjectsByOrganization(orgId: string): MockProject[] {
  return mockProjects.filter((project) => project.organizationId === orgId);
}

export function getActiveProjects(): MockProject[] {
  return mockProjects.filter((project) => project.status === "active");
}
