/**
 * React Query hooks for Spec-Driven Settings API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { api } from "@/lib/api/client"

// ============================================================================
// Types
// ============================================================================

/**
 * Spec-driven settings options for a project
 */
export interface SpecDrivenOptions {
  /** Whether spec-driven mode is enabled */
  enabled: boolean
  /** Auto-generate specs from requirements */
  auto_generate_specs: boolean
  /** Require approval before execution */
  require_approval: boolean
  /** Maximum concurrent tasks */
  max_concurrent_tasks: number
  /** Default phase for new specs */
  default_phase: string
  /** Enable AI-powered suggestions */
  ai_suggestions_enabled: boolean
  /** Custom validation rules */
  validation_rules: Record<string, unknown>
}

/**
 * Response from the spec-driven settings API
 */
export interface SpecDrivenSettingsResponse {
  project_id: string
  settings: SpecDrivenOptions
  updated_at: string
}

// ============================================================================
// Query Keys
// ============================================================================

export const specDrivenSettingsKeys = {
  all: ["spec-driven-settings"] as const,
  detail: (projectId: string) => [...specDrivenSettingsKeys.all, projectId] as const,
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Get spec-driven settings for a project
 */
async function getSpecDrivenSettings(projectId: string): Promise<SpecDrivenSettingsResponse> {
  return api.get<SpecDrivenSettingsResponse>(`/api/v1/projects/${projectId}/spec-driven-settings`)
}

/**
 * Update spec-driven settings for a project
 */
async function updateSpecDrivenSettings(
  projectId: string,
  settings: Partial<SpecDrivenOptions>
): Promise<SpecDrivenSettingsResponse> {
  return api.patch<SpecDrivenSettingsResponse>(
    `/api/v1/projects/${projectId}/spec-driven-settings`,
    settings
  )
}

// ============================================================================
// Hooks
// ============================================================================

/**
 * Hook to fetch spec-driven settings for a project
 *
 * @param projectId - The project ID to fetch settings for
 * @returns Query result with settings data, loading state, and error state
 *
 * @example
 * ```tsx
 * function SettingsPanel({ projectId }: { projectId: string }) {
 *   const { data, isLoading, error } = useSpecDrivenSettings(projectId);
 *
 *   if (isLoading) return <Spinner />;
 *   if (error) return <ErrorMessage error={error} />;
 *
 *   return <SettingsForm settings={data.settings} />;
 * }
 * ```
 */
export function useSpecDrivenSettings(projectId: string | undefined) {
  return useQuery<SpecDrivenSettingsResponse>({
    queryKey: specDrivenSettingsKeys.detail(projectId!),
    queryFn: () => getSpecDrivenSettings(projectId!),
    enabled: !!projectId,
  })
}

/**
 * Hook to update spec-driven settings for a project
 *
 * @returns Mutation object with mutate function and mutation state
 *
 * @example
 * ```tsx
 * function SettingsForm({ projectId }: { projectId: string }) {
 *   const updateSettings = useUpdateSpecDrivenSettings();
 *
 *   const handleSave = (settings: Partial<SpecDrivenOptions>) => {
 *     updateSettings.mutate(
 *       { projectId, settings },
 *       {
 *         onSuccess: () => toast.success('Settings saved'),
 *         onError: (error) => toast.error(error.message),
 *       }
 *     );
 *   };
 *
 *   return (
 *     <form onSubmit={handleSubmit(handleSave)}>
 *       ...
 *       <button disabled={updateSettings.isPending}>
 *         {updateSettings.isPending ? 'Saving...' : 'Save'}
 *       </button>
 *     </form>
 *   );
 * }
 * ```
 */
export function useUpdateSpecDrivenSettings() {
  const queryClient = useQueryClient()

  return useMutation<
    SpecDrivenSettingsResponse,
    Error,
    { projectId: string; settings: Partial<SpecDrivenOptions> }
  >({
    mutationFn: ({ projectId, settings }) => updateSpecDrivenSettings(projectId, settings),
    onSuccess: (data, { projectId }) => {
      // Update cache with the new settings
      queryClient.setQueryData(specDrivenSettingsKeys.detail(projectId), data)
      // Invalidate to ensure fresh data
      queryClient.invalidateQueries({ queryKey: specDrivenSettingsKeys.detail(projectId) })
    },
  })
}
