import { AgentStatus } from "@/components/custom";

export interface MockAgent {
  id: string;
  taskName: string;
  status: AgentStatus;
  timeAgo: string;
  additions?: number;
  deletions?: number;
  repoName?: string;
  createdAt: Date;
  projectId?: string;
}

export const mockAgents: MockAgent[] = [
  {
    id: "agent-001",
    taskName: "Improve senseii games performance",
    status: "running",
    timeAgo: "2h",
    additions: 1539,
    deletions: 209,
    repoName: "senseii-games",
    createdAt: new Date(),
    projectId: "proj-001",
  },
  {
    id: "agent-002",
    taskName: "Fix groq API integration",
    status: "completed",
    timeAgo: "1d",
    additions: 29,
    deletions: 10,
    repoName: "api-service",
    createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
    projectId: "proj-002",
  },
  {
    id: "agent-003",
    taskName: "Fix gaming backend authentication",
    status: "completed",
    timeAgo: "2d",
    additions: 87,
    deletions: 34,
    repoName: "gaming-service",
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
    projectId: "proj-001",
  },
  {
    id: "agent-004",
    taskName: "Fix foreign key constraint issue",
    status: "completed",
    timeAgo: "1w",
    additions: 12,
    deletions: 5,
    repoName: "database",
    createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    projectId: "proj-003",
  },
  {
    id: "agent-005",
    taskName: "Database migration for user roles",
    status: "failed",
    timeAgo: "3d",
    repoName: "backend",
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
    projectId: "proj-003",
  },
  {
    id: "agent-006",
    taskName: "Add OAuth2 support",
    status: "completed",
    timeAgo: "5d",
    additions: 256,
    deletions: 45,
    repoName: "auth-system",
    createdAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
    projectId: "proj-004",
  },
  {
    id: "agent-007",
    taskName: "Implement rate limiting",
    status: "blocked",
    timeAgo: "4d",
    additions: 89,
    deletions: 12,
    repoName: "api-service",
    createdAt: new Date(Date.now() - 4 * 24 * 60 * 60 * 1000),
    projectId: "proj-002",
  },
];

export function getAgentById(id: string): MockAgent | undefined {
  return mockAgents.find((agent) => agent.id === id);
}

export function getAgentsByStatus(status: AgentStatus): MockAgent[] {
  return mockAgents.filter((agent) => agent.status === status);
}

export function getAgentsByProject(projectId: string): MockAgent[] {
  return mockAgents.filter((agent) => agent.projectId === projectId);
}
