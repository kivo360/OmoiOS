/**
 * Spec-Driven Settings API functions
 */

import { apiRequest } from "./client"
import type { SpecDrivenOptions, SpecDrivenSettingsUpdate } from "./types"

/**
 * Get spec-driven settings for a project
 */
export async function getSpecDrivenSettings(
  projectId: string
): Promise<SpecDrivenOptions> {
  return apiRequest<SpecDrivenOptions>(
    `/api/v1/projects/${projectId}/spec-driven-settings`
  )
}

/**
 * Update spec-driven settings for a project
 */
export async function updateSpecDrivenSettings(
  projectId: string,
  settings: SpecDrivenSettingsUpdate
): Promise<SpecDrivenOptions> {
  return apiRequest<SpecDrivenOptions>(
    `/api/v1/projects/${projectId}/spec-driven-settings`,
    {
      method: "PUT",
      body: settings,
    }
  )
}
