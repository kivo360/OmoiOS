/**
 * Preview API client for live preview session management
 */

import { api } from "./client"
import type { PreviewSession } from "./types"

// ============================================================================
// Preview API
// ============================================================================

/**
 * Get preview session by sandbox ID
 */
export async function getPreviewBySandbox(
  sandboxId: string
): Promise<PreviewSession> {
  return api.get<PreviewSession>(`/api/v1/preview/sandbox/${sandboxId}`)
}

/**
 * Get preview session by preview ID
 */
export async function getPreview(previewId: string): Promise<PreviewSession> {
  return api.get<PreviewSession>(`/api/v1/preview/${previewId}`)
}

/**
 * Stop a preview session
 */
export async function stopPreview(previewId: string): Promise<PreviewSession> {
  return api.delete<PreviewSession>(`/api/v1/preview/${previewId}`)
}

// ============================================================================
// Preview API Object (for convenience)
// ============================================================================

export const previewApi = {
  getBySandbox: getPreviewBySandbox,
  get: getPreview,
  stop: stopPreview,
}

export default previewApi
