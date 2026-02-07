/**
 * Prototype API client for rapid prototyping mode
 */

import { api } from "./client"

// ============================================================================
// Types
// ============================================================================

export interface PromptHistoryItem {
  prompt: string
  response_summary: string
  timestamp: string
}

export interface PrototypeSession {
  id: string
  user_id: string
  framework: string
  sandbox_id: string | null
  preview_id: string | null
  status: "creating" | "ready" | "prompting" | "exporting" | "stopped" | "failed"
  preview_url: string | null
  prompt_history: PromptHistoryItem[]
  error_message: string | null
  created_at: string
}

export interface PromptResponse {
  prompt: string
  response_summary: string
  timestamp: string
}

export interface ExportResponse {
  repo_url: string
  branch: string
  commit_message: string
  timestamp: string
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Start a new prototype session
 */
export async function startSession(framework: string): Promise<PrototypeSession> {
  return api.post<PrototypeSession>("/api/v1/prototype/session", { framework })
}

/**
 * Get prototype session status
 */
export async function getSession(sessionId: string): Promise<PrototypeSession> {
  return api.get<PrototypeSession>(`/api/v1/prototype/session/${sessionId}`)
}

/**
 * Apply a prompt to the prototype
 */
export async function applyPrompt(
  sessionId: string,
  prompt: string
): Promise<PromptResponse> {
  return api.post<PromptResponse>(
    `/api/v1/prototype/session/${sessionId}/prompt`,
    { prompt }
  )
}

/**
 * Export prototype to a git repository
 */
export async function exportToRepo(
  sessionId: string,
  repoUrl: string,
  branch: string = "prototype",
  commitMessage: string = "Export prototype"
): Promise<ExportResponse> {
  return api.post<ExportResponse>(
    `/api/v1/prototype/session/${sessionId}/export`,
    { repo_url: repoUrl, branch, commit_message: commitMessage }
  )
}

/**
 * End a prototype session
 */
export async function endSession(sessionId: string): Promise<void> {
  await api.delete(`/api/v1/prototype/session/${sessionId}`)
}

// ============================================================================
// API Object
// ============================================================================

export const prototypeApi = {
  startSession,
  getSession,
  applyPrompt,
  exportToRepo,
  endSession,
}

export default prototypeApi
