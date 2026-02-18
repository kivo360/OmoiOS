/**
 * Projects API functions
 */

import { apiRequest } from "./client";
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectListResponse,
  ProjectStats,
} from "./types";

/**
 * List all projects
 */
export async function listProjects(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ProjectListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));

  const query = searchParams.toString();
  const url = query ? `/api/v1/projects?${query}` : "/api/v1/projects";

  return apiRequest<ProjectListResponse>(url);
}

/**
 * Get a project by ID
 */
export async function getProject(projectId: string): Promise<Project> {
  return apiRequest<Project>(`/api/v1/projects/${projectId}`);
}

/**
 * Create a new project
 */
export async function createProject(data: ProjectCreate): Promise<Project> {
  return apiRequest<Project>("/api/v1/projects", {
    method: "POST",
    body: data,
  });
}

/**
 * Update a project
 */
export async function updateProject(
  projectId: string,
  data: ProjectUpdate,
): Promise<Project> {
  return apiRequest<Project>(`/api/v1/projects/${projectId}`, {
    method: "PATCH",
    body: data,
  });
}

/**
 * Delete (archive) a project
 */
export async function deleteProject(
  projectId: string,
): Promise<{ success: boolean; message: string }> {
  return apiRequest<{ success: boolean; message: string }>(
    `/api/v1/projects/${projectId}`,
    { method: "DELETE" },
  );
}

/**
 * Get project statistics
 */
export async function getProjectStats(
  projectId: string,
): Promise<ProjectStats> {
  return apiRequest<ProjectStats>(`/api/v1/projects/${projectId}/stats`);
}
