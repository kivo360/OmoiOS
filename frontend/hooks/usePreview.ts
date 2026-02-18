/**
 * React hook for live preview session management
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useEffect, useState } from "react";
import { previewApi } from "@/lib/api/preview";
import { ApiError } from "@/lib/api/client";
import { useEvents, type SystemEvent } from "./useEvents";
import type { PreviewSession } from "@/lib/api/types";

// ============================================================================
// Query Keys
// ============================================================================

export const previewKeys = {
  all: ["previews"] as const,
  bySandbox: (sandboxId: string) =>
    [...previewKeys.all, "sandbox", sandboxId] as const,
};

// ============================================================================
// Hook
// ============================================================================

/**
 * Hook for managing a live preview session for a sandbox.
 *
 * Features:
 * - Polls for preview status (10s while pending/starting, 30s when no preview)
 * - Listens for PREVIEW_READY WebSocket event to instantly update
 * - Tracks `justBecameReady` for parent to auto-switch to Preview tab
 * - Graceful 404 handling (returns null when no preview exists)
 */
export function usePreview(sandboxId: string | null) {
  const queryClient = useQueryClient();
  const [justBecameReady, setJustBecameReady] = useState(false);
  const prevStatusRef = useRef<string | null>(null);

  // Fetch preview by sandbox ID, gracefully handling 404
  const {
    data: preview,
    isLoading,
    error,
  } = useQuery<PreviewSession | null>({
    queryKey: previewKeys.bySandbox(sandboxId || ""),
    queryFn: async () => {
      try {
        return await previewApi.getBySandbox(sandboxId!);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          return null;
        }
        throw err;
      }
    },
    enabled: !!sandboxId,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 30_000; // No preview yet — poll slowly
      if (data.status === "pending" || data.status === "starting")
        return 10_000;
      // Terminal states: don't poll
      if (
        data.status === "ready" ||
        data.status === "stopped" ||
        data.status === "failed"
      )
        return false;
      return 30_000;
    },
  });

  // Track status transitions to detect when preview becomes ready
  useEffect(() => {
    const currentStatus = preview?.status ?? null;
    if (
      prevStatusRef.current !== null &&
      prevStatusRef.current !== "ready" &&
      currentStatus === "ready"
    ) {
      setJustBecameReady(true);
    }
    prevStatusRef.current = currentStatus;
  }, [preview?.status]);

  // Auto-clear justBecameReady after a short delay
  useEffect(() => {
    if (!justBecameReady) return;
    const timer = setTimeout(() => setJustBecameReady(false), 500);
    return () => clearTimeout(timer);
  }, [justBecameReady]);

  // Listen for PREVIEW_READY WebSocket event
  const handleEvent = useCallback(
    (event: SystemEvent) => {
      if (
        event.event_type === "PREVIEW_READY" &&
        event.payload.sandbox_id === sandboxId
      ) {
        queryClient.invalidateQueries({
          queryKey: previewKeys.bySandbox(sandboxId!),
        });
      }
    },
    [sandboxId, queryClient],
  );

  useEvents({
    enabled: !!sandboxId,
    filters: {
      event_types: ["PREVIEW_READY"],
    },
    onEvent: handleEvent,
  });

  // Stop mutation
  const stopMutation = useMutation({
    mutationFn: (previewId: string) => previewApi.stop(previewId),
    onSuccess: () => {
      if (sandboxId) {
        queryClient.invalidateQueries({
          queryKey: previewKeys.bySandbox(sandboxId),
        });
      }
    },
  });

  const stop = useCallback(() => {
    if (preview?.id) {
      stopMutation.mutate(preview.id);
    }
  }, [preview?.id, stopMutation]);

  const refresh = useCallback(() => {
    if (sandboxId) {
      queryClient.invalidateQueries({
        queryKey: previewKeys.bySandbox(sandboxId),
      });
    }
  }, [sandboxId, queryClient]);

  const hasPreview = preview !== null && preview !== undefined;
  const isReady = preview?.status === "ready";
  const isPending =
    preview?.status === "pending" || preview?.status === "starting";
  const isFailed = preview?.status === "failed";
  const isStopped = preview?.status === "stopped";

  return {
    preview: preview ?? null,
    hasPreview,
    isReady,
    isPending,
    isFailed,
    isStopped,
    isLoading,
    error,
    stop,
    isStopping: stopMutation.isPending,
    refresh,
    justBecameReady,
  };
}
