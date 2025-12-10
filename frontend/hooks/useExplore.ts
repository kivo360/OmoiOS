import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  listConversations,
  createConversation,
  getConversation,
  sendMessage,
  deleteConversation,
  getProjectFiles,
  getSuggestions,
} from "@/lib/api/explore"
import type {
  ConversationListResponse,
  ConversationResponse,
  MessageResponse,
  ProjectFilesResponse,
  SuggestionsResponse,
} from "@/lib/api/explore"

export const exploreKeys = {
  all: ["explore"] as const,
  conversations: (projectId: string) =>
    [...exploreKeys.all, "conversations", projectId] as const,
  conversation: (projectId: string, conversationId: string) =>
    [...exploreKeys.all, "conversation", projectId, conversationId] as const,
  files: (projectId: string) =>
    [...exploreKeys.all, "files", projectId] as const,
  suggestions: (projectId: string) =>
    [...exploreKeys.all, "suggestions", projectId] as const,
}

/**
 * Hook to list conversations for a project
 */
export function useConversations(projectId: string | undefined, limit?: number) {
  return useQuery<ConversationListResponse>({
    queryKey: exploreKeys.conversations(projectId!),
    queryFn: () => listConversations(projectId!, limit),
    enabled: !!projectId,
  })
}

/**
 * Hook to get a specific conversation
 */
export function useConversation(
  projectId: string | undefined,
  conversationId: string | undefined
) {
  return useQuery<ConversationResponse>({
    queryKey: exploreKeys.conversation(projectId!, conversationId!),
    queryFn: () => getConversation(projectId!, conversationId!),
    enabled: !!projectId && !!conversationId,
  })
}

/**
 * Hook to create a new conversation
 */
export function useCreateConversation(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation<ConversationResponse, Error, void>({
    mutationFn: () => createConversation(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: exploreKeys.conversations(projectId),
      })
    },
  })
}

/**
 * Hook to send a message in a conversation
 */
export function useSendMessage(projectId: string, conversationId: string) {
  const queryClient = useQueryClient()

  return useMutation<MessageResponse, Error, string>({
    mutationFn: (content) => sendMessage(projectId, conversationId, content),
    onSuccess: () => {
      // Invalidate both the specific conversation and the list
      queryClient.invalidateQueries({
        queryKey: exploreKeys.conversation(projectId, conversationId),
      })
      queryClient.invalidateQueries({
        queryKey: exploreKeys.conversations(projectId),
      })
    },
  })
}

/**
 * Hook to delete a conversation
 */
export function useDeleteConversation(projectId: string) {
  const queryClient = useQueryClient()

  return useMutation<{ message: string }, Error, string>({
    mutationFn: (conversationId) => deleteConversation(projectId, conversationId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: exploreKeys.conversations(projectId),
      })
    },
  })
}

/**
 * Hook to get project files
 */
export function useProjectFiles(projectId: string | undefined) {
  return useQuery<ProjectFilesResponse>({
    queryKey: exploreKeys.files(projectId!),
    queryFn: () => getProjectFiles(projectId!),
    enabled: !!projectId,
  })
}

/**
 * Hook to get suggestions
 */
export function useSuggestions(projectId: string | undefined, context?: string) {
  return useQuery<SuggestionsResponse>({
    queryKey: [...exploreKeys.suggestions(projectId!), context],
    queryFn: () => getSuggestions(projectId!, context),
    enabled: !!projectId,
  })
}
