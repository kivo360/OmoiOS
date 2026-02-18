/**
 * React Query hooks for Projects API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  listProjects,
  getProject,
  createProject,
  updateProject,
  deleteProject,
  getProjectStats,
} from "@/lib/api/projects";
import type {
  Project,
  ProjectCreate,
  ProjectUpdate,
  ProjectListResponse,
  ProjectStats,
} from "@/lib/api/types";

// Query keys
export const projectKeys = {
  all: ["projects"] as const,
  lists: () => [...projectKeys.all, "list"] as const,
  list: (filters: { status?: string; limit?: number; offset?: number }) =>
    [...projectKeys.lists(), filters] as const,
  details: () => [...projectKeys.all, "detail"] as const,
  detail: (id: string) => [...projectKeys.details(), id] as const,
  stats: (id: string) => [...projectKeys.detail(id), "stats"] as const,
};

/**
 * Hook to fetch list of projects
 */
export function useProjects(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}) {
  return useQuery<ProjectListResponse>({
    queryKey: projectKeys.list(params ?? {}),
    queryFn: () => listProjects(params),
  });
}

/**
 * Hook to fetch a single project
 */
export function useProject(projectId: string | undefined) {
  return useQuery<Project>({
    queryKey: projectKeys.detail(projectId!),
    queryFn: () => getProject(projectId!),
    enabled: !!projectId,
  });
}

/**
 * Hook to fetch project statistics
 */
export function useProjectStats(projectId: string | undefined) {
  return useQuery<ProjectStats>({
    queryKey: projectKeys.stats(projectId!),
    queryFn: () => getProjectStats(projectId!),
    enabled: !!projectId,
  });
}

/**
 * Hook to create a new project
 */
export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: ProjectCreate) => createProject(data),
    onSuccess: () => {
      // Invalidate project list queries to refetch
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

/**
 * Hook to update a project
 */
export function useUpdateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      projectId,
      data,
    }: {
      projectId: string;
      data: ProjectUpdate;
    }) => updateProject(projectId, data),
    onSuccess: (updatedProject) => {
      // Update the cache for this specific project
      queryClient.setQueryData(
        projectKeys.detail(updatedProject.id),
        updatedProject,
      );
      // Invalidate project list queries
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}

/**
 * Hook to delete (archive) a project
 */
export function useDeleteProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (projectId: string) => deleteProject(projectId),
    onSuccess: (_, projectId) => {
      // Remove from cache
      queryClient.removeQueries({ queryKey: projectKeys.detail(projectId) });
      // Invalidate project list queries
      queryClient.invalidateQueries({ queryKey: projectKeys.lists() });
    },
  });
}
