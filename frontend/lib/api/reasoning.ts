import { apiRequest } from "./client";

// Types

export interface Evidence {
  type: string;
  content: string;
  link?: string;
}

export interface Alternative {
  option: string;
  rejected: string;
}

export interface Decision {
  type: string;
  action: string;
  reasoning: string;
}

export interface EventDetails {
  context?: string;
  reasoning?: string;
  source_spec?: string;
  source_requirement?: string;
  created_by?: string;
  tasks_created?: number;
  tasks?: string[];
  discovery_type?: string;
  evidence?: string;
  action?: string;
  impact?: string;
  alternatives?: Alternative[];
  confidence?: number;
  blocked_ticket?: string;
  blocked_title?: string;
  reason?: string;
  task?: string;
  lines_added?: number;
  lines_removed?: number;
  files_changed?: number;
  tests_passing?: number;
  tests_total?: number;
  commit?: string;
  error_type?: string;
  stack_trace?: string;
}

export interface ReasoningEvent {
  id: string;
  timestamp: string;
  type: string;
  title: string;
  description: string;
  agent: string | null;
  details: EventDetails | null;
  evidence: Evidence[];
  decision: Decision | null;
}

export interface ReasoningChainResponse {
  entity_type: string;
  entity_id: string;
  events: ReasoningEvent[];
  total_count: number;
  stats: {
    total: number;
    decisions: number;
    discoveries: number;
    errors: number;
    by_type: Record<string, number>;
  };
}

export interface ReasoningEventCreate {
  type: string;
  title: string;
  description: string;
  agent?: string;
  details?: EventDetails;
  evidence?: Evidence[];
  decision?: Decision;
}

export interface EventTypesResponse {
  event_types: Array<{ id: string; label: string; icon: string }>;
  evidence_types: Array<{ id: string; label: string }>;
  decision_types: Array<{ id: string; label: string }>;
}

// API Functions

export async function getReasoningChain(
  entityType: string,
  entityId: string,
  params?: { event_type?: string; limit?: number },
): Promise<ReasoningChainResponse> {
  const searchParams = new URLSearchParams();
  if (params?.event_type) {
    searchParams.set("event_type", params.event_type);
  }
  if (params?.limit) {
    searchParams.set("limit", String(params.limit));
  }
  const query = searchParams.toString();
  return apiRequest<ReasoningChainResponse>(
    `/api/v1/reasoning/${entityType}/${entityId}${query ? `?${query}` : ""}`,
  );
}

export async function addReasoningEvent(
  entityType: string,
  entityId: string,
  event: ReasoningEventCreate,
): Promise<ReasoningEvent> {
  return apiRequest<ReasoningEvent>(
    `/api/v1/reasoning/${entityType}/${entityId}/events`,
    {
      method: "POST",
      body: event,
    },
  );
}

export async function getReasoningEvent(
  entityType: string,
  entityId: string,
  eventId: string,
): Promise<ReasoningEvent> {
  return apiRequest<ReasoningEvent>(
    `/api/v1/reasoning/${entityType}/${entityId}/events/${eventId}`,
  );
}

export async function deleteReasoningEvent(
  entityType: string,
  entityId: string,
  eventId: string,
): Promise<{ message: string }> {
  return apiRequest<{ message: string }>(
    `/api/v1/reasoning/${entityType}/${entityId}/events/${eventId}`,
    { method: "DELETE" },
  );
}

export async function getEventTypes(): Promise<EventTypesResponse> {
  return apiRequest<EventTypesResponse>("/api/v1/reasoning/types");
}
