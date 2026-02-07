/**
 * Spec-driven settings API functions
 *
 * Provides typed fetch wrappers for spec-driven development settings endpoints.
 * Settings control workflow behavior including phase progression, gate enforcement,
 * test coverage requirements, and guardian auto-steering.
 */

import { apiRequest } from "./client"

/**
 * Gate enforcement strictness levels for spec-driven workflows.
 *
 * - bypass: No gate enforcement, all transitions allowed
 * - lenient: Warnings on gate failures but transitions allowed
 * - strict: Gate failures block phase transitions
 */
export type GateEnforcementStrictness = "bypass" | "lenient" | "strict"

/**
 * Configuration options for spec-driven development workflows.
 */
export interface SpecDrivenOptions {
  /** Automatically progress to next phase when gate criteria are met */
  auto_phase_progression: boolean
  /** How strictly to enforce phase transition gates */
  gate_enforcement_strictness: GateEnforcementStrictness
  /** Minimum test coverage percentage required (0-100) */
  min_test_coverage: number
  /** Enable guardian auto-steering for trajectory analysis */
  guardian_auto_steering: boolean
}

/**
 * Partial update payload for spec-driven settings.
 * All fields are optional for PATCH requests.
 */
export type SpecDrivenOptionsUpdate = Partial<SpecDrivenOptions>

/**
 * Get spec-driven settings for a project.
 *
 * @param projectId - The project ID to get settings for
 * @returns The current spec-driven settings
 * @throws ApiError if the request fails
 */
export async function getSpecDrivenSettings(
  projectId: string
): Promise<SpecDrivenOptions> {
  return apiRequest<SpecDrivenOptions>(
    `/api/v1/projects/${projectId}/settings/spec-driven`
  )
}

/**
 * Update spec-driven settings for a project.
 *
 * Accepts partial updates - only provided fields will be changed.
 *
 * @param projectId - The project ID to update settings for
 * @param settings - Partial settings object with fields to update
 * @returns The updated spec-driven settings
 * @throws ApiError if the request fails
 */
export async function updateSpecDrivenSettings(
  projectId: string,
  settings: SpecDrivenOptionsUpdate
): Promise<SpecDrivenOptions> {
  return apiRequest<SpecDrivenOptions>(
    `/api/v1/projects/${projectId}/settings/spec-driven`,
    {
      method: "PATCH",
      body: settings,
    }
  )
}
