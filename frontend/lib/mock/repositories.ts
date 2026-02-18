export interface MockRepository {
  id: string;
  fullName: string;
  name: string;
  owner: string;
  description?: string;
  isPrivate: boolean;
  defaultBranch: string;
  updatedAt: Date;
  language?: string;
  isConnected: boolean;
  connectedProjectId?: string;
}

export const mockRepositories: MockRepository[] = [
  {
    id: "repo-001",
    fullName: "kivo360/senseii-games",
    name: "senseii-games",
    owner: "kivo360",
    description: "Gaming platform for interactive experiences",
    isPrivate: false,
    defaultBranch: "main",
    updatedAt: new Date(),
    language: "TypeScript",
    isConnected: true,
    connectedProjectId: "proj-001",
  },
  {
    id: "repo-002",
    fullName: "kivo360/api-service",
    name: "api-service",
    owner: "kivo360",
    description: "Core API microservice",
    isPrivate: true,
    defaultBranch: "main",
    updatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
    language: "Python",
    isConnected: true,
    connectedProjectId: "proj-002",
  },
  {
    id: "repo-003",
    fullName: "kivo360/database",
    name: "database",
    owner: "kivo360",
    description: "Database schemas and migrations",
    isPrivate: true,
    defaultBranch: "main",
    updatedAt: new Date(Date.now() - 24 * 60 * 60 * 1000),
    language: "SQL",
    isConnected: true,
    connectedProjectId: "proj-003",
  },
  {
    id: "repo-004",
    fullName: "kivo360/auth-system",
    name: "auth-system",
    owner: "kivo360",
    description: "Authentication service",
    isPrivate: true,
    defaultBranch: "main",
    updatedAt: new Date(Date.now() - 5 * 24 * 60 * 60 * 1000),
    language: "TypeScript",
    isConnected: true,
    connectedProjectId: "proj-004",
  },
  {
    id: "repo-005",
    fullName: "kivo360/payment-gateway",
    name: "payment-gateway",
    owner: "kivo360",
    description: "Payment processing",
    isPrivate: true,
    defaultBranch: "main",
    updatedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
    language: "Go",
    isConnected: true,
    connectedProjectId: "proj-005",
  },
  // Unconnected repositories
  {
    id: "repo-006",
    fullName: "kivo360/frontend-app",
    name: "frontend-app",
    owner: "kivo360",
    description: "Next.js frontend application",
    isPrivate: false,
    defaultBranch: "main",
    updatedAt: new Date(Date.now() - 10 * 24 * 60 * 60 * 1000),
    language: "TypeScript",
    isConnected: false,
  },
  {
    id: "repo-007",
    fullName: "kivo360/mobile-app",
    name: "mobile-app",
    owner: "kivo360",
    description: "React Native mobile application",
    isPrivate: true,
    defaultBranch: "develop",
    updatedAt: new Date(Date.now() - 15 * 24 * 60 * 60 * 1000),
    language: "TypeScript",
    isConnected: false,
  },
  {
    id: "repo-008",
    fullName: "kivo360/ml-pipeline",
    name: "ml-pipeline",
    owner: "kivo360",
    description: "Machine learning data pipeline",
    isPrivate: true,
    defaultBranch: "main",
    updatedAt: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000),
    language: "Python",
    isConnected: false,
  },
];

export function getRepositoryById(id: string): MockRepository | undefined {
  return mockRepositories.find((repo) => repo.id === id);
}

export function getRepositoryByFullName(
  fullName: string,
): MockRepository | undefined {
  return mockRepositories.find((repo) => repo.fullName === fullName);
}

export function getConnectedRepositories(): MockRepository[] {
  return mockRepositories.filter((repo) => repo.isConnected);
}

export function getUnconnectedRepositories(): MockRepository[] {
  return mockRepositories.filter((repo) => !repo.isConnected);
}

export function getRepositoriesByOwner(owner: string): MockRepository[] {
  return mockRepositories.filter((repo) => repo.owner === owner);
}
