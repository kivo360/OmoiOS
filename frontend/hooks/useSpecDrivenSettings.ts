/**
 * React Query hooks for Spec-Driven Settings API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  getSpecDrivenSettings,
  updateSpecDrivenSettings,
} from "@/lib/api/spec-driven-settings"
import type { SpecDrivenOptions, SpecDrivenSettingsUpdate } from "@/lib/api/types"

// Query keys
export const specDrivenSettingsKeys = {
  all: ["spec-driven-settings"] as const,
  detail: (projectId: string) =>
    [...specDrivenSettingsKeys.all, projectId] as const,
}

/**
 * Hook to fetch spec-driven settings for a project
 */
export function useSpecDrivenSettings(projectId: string | undefined) {
  return useQuery<SpecDrivenOptions>({
    queryKey: specDrivenSettingsKeys.detail(projectId!),
    queryFn: () => getSpecDrivenSettings(projectId!),
    enabled: !!projectId,
  })
}

/**
 * Hook to update spec-driven settings
 */
export function useUpdateSpecDrivenSettings() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      projectId,
      settings,
    }: {
      projectId: string
      settings: SpecDrivenSettingsUpdate
    }) => updateSpecDrivenSettings(projectId, settings),
    onSuccess: (updatedSettings, { projectId }) => {
      // Update the cache for this specific project
      queryClient.setQueryData(
        specDrivenSettingsKeys.detail(projectId),
        updatedSettings
      )
    },
  })
}
