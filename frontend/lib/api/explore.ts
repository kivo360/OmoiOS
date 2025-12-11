import { apiRequest } from "./client"

// Types

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: string
}

export interface Conversation {
  id: string
  project_id: string
  title: string
  last_message: string
  messages: Message[]
  created_at: string
  updated_at: string
}

export interface ConversationSummary {
  id: string
  title: string
  last_message: string
  timestamp: string
}

export interface ConversationListResponse {
  conversations: ConversationSummary[]
  total_count: number
}

export interface ConversationResponse {
  conversation: Conversation
}

export interface MessageResponse {
  user_message: Message
  assistant_message: Message
}

export interface ProjectFile {
  path: string
  type: "file" | "directory"
  lines?: number
  description?: string
}

export interface ProjectFilesResponse {
  project_id: string
  files: ProjectFile[]
  total_count: number
}

export interface SuggestionsResponse {
  suggestions: string[]
}

// API Functions

export async function listConversations(
  projectId: string,
  limit?: number
): Promise<ConversationListResponse> {
  const params = new URLSearchParams()
  if (limit) params.set("limit", String(limit))
  const query = params.toString()
  return apiRequest<ConversationListResponse>(
    `/api/v1/explore/project/${projectId}/conversations${query ? `?${query}` : ""}`
  )
}

export async function createConversation(
  projectId: string
): Promise<ConversationResponse> {
  return apiRequest<ConversationResponse>(
    `/api/v1/explore/project/${projectId}/conversations`,
    { method: "POST" }
  )
}

export async function getConversation(
  projectId: string,
  conversationId: string
): Promise<ConversationResponse> {
  return apiRequest<ConversationResponse>(
    `/api/v1/explore/project/${projectId}/conversations/${conversationId}`
  )
}

export async function sendMessage(
  projectId: string,
  conversationId: string,
  content: string
): Promise<MessageResponse> {
  return apiRequest<MessageResponse>(
    `/api/v1/explore/project/${projectId}/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: { content },
    }
  )
}

export async function deleteConversation(
  projectId: string,
  conversationId: string
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    `/api/v1/explore/project/${projectId}/conversations/${conversationId}`,
    { method: "DELETE" }
  )
}

export async function getProjectFiles(
  projectId: string
): Promise<ProjectFilesResponse> {
  return apiRequest<ProjectFilesResponse>(
    `/api/v1/explore/project/${projectId}/files`
  )
}

export async function getSuggestions(
  projectId: string,
  context?: string
): Promise<SuggestionsResponse> {
  const params = new URLSearchParams()
  if (context) params.set("context", context)
  const query = params.toString()
  return apiRequest<SuggestionsResponse>(
    `/api/v1/explore/project/${projectId}/suggestions${query ? `?${query}` : ""}`
  )
}
