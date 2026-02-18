import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getReasoningChain,
  addReasoningEvent,
  getReasoningEvent,
  deleteReasoningEvent,
  getEventTypes,
} from "@/lib/api/reasoning";
import type {
  ReasoningChainResponse,
  ReasoningEvent,
  ReasoningEventCreate,
  EventTypesResponse,
} from "@/lib/api/reasoning";

export const reasoningKeys = {
  all: ["reasoning"] as const,
  chain: (entityType: string, entityId: string) =>
    [...reasoningKeys.all, "chain", entityType, entityId] as const,
  event: (entityType: string, entityId: string, eventId: string) =>
    [...reasoningKeys.all, "event", entityType, entityId, eventId] as const,
  types: () => [...reasoningKeys.all, "types"] as const,
};

/**
 * Hook to get reasoning chain for an entity
 */
export function useReasoningChain(
  entityType: string | undefined,
  entityId: string | undefined,
  params?: { event_type?: string; limit?: number },
) {
  return useQuery<ReasoningChainResponse>({
    queryKey: reasoningKeys.chain(entityType!, entityId!),
    queryFn: () => getReasoningChain(entityType!, entityId!, params),
    enabled: !!entityType && !!entityId,
  });
}

/**
 * Hook to get a specific reasoning event
 */
export function useReasoningEvent(
  entityType: string | undefined,
  entityId: string | undefined,
  eventId: string | undefined,
) {
  return useQuery<ReasoningEvent>({
    queryKey: reasoningKeys.event(entityType!, entityId!, eventId!),
    queryFn: () => getReasoningEvent(entityType!, entityId!, eventId!),
    enabled: !!entityType && !!entityId && !!eventId,
  });
}

/**
 * Hook to get event types configuration
 */
export function useEventTypes() {
  return useQuery<EventTypesResponse>({
    queryKey: reasoningKeys.types(),
    queryFn: getEventTypes,
    staleTime: 1000 * 60 * 60, // Cache for 1 hour
  });
}

/**
 * Hook to add a reasoning event
 */
export function useAddReasoningEvent(entityType: string, entityId: string) {
  const queryClient = useQueryClient();

  return useMutation<ReasoningEvent, Error, ReasoningEventCreate>({
    mutationFn: (event) => addReasoningEvent(entityType, entityId, event),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reasoningKeys.chain(entityType, entityId),
      });
    },
  });
}

/**
 * Hook to delete a reasoning event
 */
export function useDeleteReasoningEvent(entityType: string, entityId: string) {
  const queryClient = useQueryClient();

  return useMutation<{ message: string }, Error, string>({
    mutationFn: (eventId) =>
      deleteReasoningEvent(entityType, entityId, eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: reasoningKeys.chain(entityType, entityId),
      });
    },
  });
}
