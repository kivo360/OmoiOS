/**
 * GitHub Integration API functions
 */

import { apiRequest } from "./client"
import type {
  ConnectRepositoryRequest,
  ConnectRepositoryResponse,
  RepositoryInfo,
  SyncRepositoryResponse,
} from "./types"

/**
 * Connect a GitHub repository to a project
 */
export async function connectRepository(
  projectId: string,
  data: ConnectRepositoryRequest
): Promise<ConnectRepositoryResponse> {
  return apiRequest<ConnectRepositoryResponse>(
    `/api/v1/github/connect?project_id=${projectId}`,
    {
      method: "POST",
      body: data,
    }
  )
}

/**
 * List all connected GitHub repositories
 */
export async function listConnectedRepositories(): Promise<RepositoryInfo[]> {
  return apiRequest<RepositoryInfo[]>("/api/v1/github/repos")
}

/**
 * Manually trigger sync with GitHub repository
 */
export async function syncRepository(
  projectId: string
): Promise<SyncRepositoryResponse> {
  return apiRequest<SyncRepositoryResponse>(
    `/api/v1/github/sync?project_id=${projectId}`,
    { method: "POST" }
  )
}
