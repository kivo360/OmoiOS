/**
 * React hook for prototype session management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import {
  prototypeApi,
  type PrototypeSession,
  type PromptResponse,
  type ExportResponse,
} from "@/lib/api/prototype";
import { ApiError } from "@/lib/api/client";
import { useEvents, type SystemEvent } from "./useEvents";

// ============================================================================
// Query Keys
// ============================================================================

export const prototypeKeys = {
  all: ["prototype"] as const,
  session: (sessionId: string) =>
    [...prototypeKeys.all, "session", sessionId] as const,
};

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook for managing a prototype session lifecycle.
 *
 * Features:
 * - Start session with a framework template
 * - Apply prompts to generate/modify code
 * - Export to git repository
 * - End session and clean up resources
 * - WebSocket events for prompt/export updates
 */
export function usePrototype(sessionId: string | null) {
  const queryClient = useQueryClient();

  // Query session status
  const {
    data: session,
    isLoading,
    error,
  } = useQuery<PrototypeSession | null>({
    queryKey: prototypeKeys.session(sessionId || ""),
    queryFn: async () => {
      try {
        return await prototypeApi.getSession(sessionId!);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          return null;
        }
        throw err;
      }
    },
    enabled: !!sessionId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      if (
        data.status === "creating" ||
        data.status === "prompting" ||
        data.status === "exporting"
      )
        return 5_000;
      return false;
    },
  });

  // Listen for WebSocket events
  const handleEvent = useCallback(
    (event: SystemEvent) => {
      if (
        (event.event_type === "PROTOTYPE_PROMPT_APPLIED" ||
          event.event_type === "PROTOTYPE_EXPORTED") &&
        event.entity_id === sessionId
      ) {
        queryClient.invalidateQueries({
          queryKey: prototypeKeys.session(sessionId!),
        });
      }
    },
    [sessionId, queryClient],
  );

  useEvents({
    enabled: !!sessionId,
    filters: {
      event_types: ["PROTOTYPE_PROMPT_APPLIED", "PROTOTYPE_EXPORTED"],
    },
    onEvent: handleEvent,
  });

  // Start session mutation
  const startMutation = useMutation({
    mutationFn: (framework: string) => prototypeApi.startSession(framework),
  });

  // Apply prompt mutation
  const promptMutation = useMutation({
    mutationFn: (prompt: string) =>
      prototypeApi.applyPrompt(sessionId!, prompt),
    onSuccess: () => {
      if (sessionId) {
        queryClient.invalidateQueries({
          queryKey: prototypeKeys.session(sessionId),
        });
      }
    },
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: ({
      repoUrl,
      branch,
      commitMessage,
    }: {
      repoUrl: string;
      branch?: string;
      commitMessage?: string;
    }) => prototypeApi.exportToRepo(sessionId!, repoUrl, branch, commitMessage),
    onSuccess: () => {
      if (sessionId) {
        queryClient.invalidateQueries({
          queryKey: prototypeKeys.session(sessionId),
        });
      }
    },
  });

  // End session mutation
  const endMutation = useMutation({
    mutationFn: () => prototypeApi.endSession(sessionId!),
    onSuccess: () => {
      if (sessionId) {
        queryClient.invalidateQueries({
          queryKey: prototypeKeys.session(sessionId),
        });
      }
    },
  });

  return {
    session,
    isLoading,
    error,

    // Start
    startSession: startMutation.mutateAsync,
    isStarting: startMutation.isPending,

    // Prompt
    applyPrompt: promptMutation.mutateAsync,
    isPrompting: promptMutation.isPending,
    promptResult: promptMutation.data as PromptResponse | undefined,

    // Export
    exportToRepo: exportMutation.mutateAsync,
    isExporting: exportMutation.isPending,
    exportResult: exportMutation.data as ExportResponse | undefined,

    // End
    endSession: endMutation.mutate,
    isEnding: endMutation.isPending,
  };
}
