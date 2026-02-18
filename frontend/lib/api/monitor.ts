/**
 * Monitor/Metrics API functions
 */

import { apiRequest } from "./client";
import type {
  MetricSample,
  Anomaly,
  DashboardSummary,
  MonitoringStatus,
  SystemHealth,
} from "./types";

/**
 * Get current system metrics
 */
export async function getMetrics(phaseId?: string): Promise<MetricSample[]> {
  const url = phaseId
    ? `/api/v1/monitor/metrics?phase_id=${phaseId}`
    : "/api/v1/monitor/metrics";
  return apiRequest<MetricSample[]>(url);
}

/**
 * Get recent anomalies
 */
export async function getAnomalies(params?: {
  hours?: number;
  severity?: string;
}): Promise<Anomaly[]> {
  const searchParams = new URLSearchParams();
  if (params?.hours) searchParams.set("hours", String(params.hours));
  if (params?.severity) searchParams.set("severity", params.severity);

  const query = searchParams.toString();
  const url = query
    ? `/api/v1/monitor/anomalies?${query}`
    : "/api/v1/monitor/anomalies";

  return apiRequest<Anomaly[]>(url);
}

/**
 * Acknowledge an anomaly
 */
export async function acknowledgeAnomaly(
  anomalyId: string,
): Promise<{ success: boolean; anomaly_id: string }> {
  return apiRequest<{ success: boolean; anomaly_id: string }>(
    `/api/v1/monitor/anomalies/${anomalyId}/acknowledge`,
    { method: "POST" },
  );
}

/**
 * Get dashboard summary statistics
 */
export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiRequest<DashboardSummary>("/api/v1/monitor/dashboard");
}

/**
 * Get intelligent monitoring loop status
 */
export async function getMonitoringStatus(): Promise<MonitoringStatus> {
  return apiRequest<MonitoringStatus>("/api/v1/monitor/intelligent/status");
}

/**
 * Get system health from intelligent monitoring
 */
export async function getSystemHealth(): Promise<SystemHealth> {
  return apiRequest<SystemHealth>("/api/v1/monitor/intelligent/health");
}

/**
 * Analyze agent trajectory
 */
export async function analyzeAgentTrajectory(
  agentId: string,
  force = false,
): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>(
    `/api/v1/monitor/intelligent/analyze/${agentId}?force=${force}`,
    { method: "POST" },
  );
}

/**
 * Trigger emergency analysis for specific agents
 */
export async function triggerEmergencyAnalysis(
  agentIds: string[],
): Promise<Record<string, unknown>> {
  return apiRequest<Record<string, unknown>>(
    "/api/v1/monitor/intelligent/emergency",
    {
      method: "POST",
      body: agentIds,
    },
  );
}
