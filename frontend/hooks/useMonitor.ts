/**
 * React Query hooks for Monitor/Metrics API
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getMetrics,
  getAnomalies,
  acknowledgeAnomaly,
  getDashboardSummary,
  getMonitoringStatus,
  getSystemHealth,
  analyzeAgentTrajectory,
  triggerEmergencyAnalysis,
} from "@/lib/api/monitor";
import type {
  MetricSample,
  Anomaly,
  DashboardSummary,
  MonitoringStatus,
  SystemHealth,
} from "@/lib/api/types";

// Query keys
export const monitorKeys = {
  all: ["monitor"] as const,
  metrics: (phaseId?: string) =>
    [...monitorKeys.all, "metrics", phaseId] as const,
  anomalies: (params?: { hours?: number; severity?: string }) =>
    [...monitorKeys.all, "anomalies", params] as const,
  dashboard: () => [...monitorKeys.all, "dashboard"] as const,
  status: () => [...monitorKeys.all, "status"] as const,
  health: () => [...monitorKeys.all, "health"] as const,
};

/**
 * Hook to fetch system metrics
 */
export function useMetrics(phaseId?: string) {
  return useQuery<MetricSample[]>({
    queryKey: monitorKeys.metrics(phaseId),
    queryFn: () => getMetrics(phaseId),
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

/**
 * Hook to fetch anomalies
 */
export function useAnomalies(params?: { hours?: number; severity?: string }) {
  return useQuery<Anomaly[]>({
    queryKey: monitorKeys.anomalies(params),
    queryFn: () => getAnomalies(params),
    refetchInterval: 60000, // Refresh every minute
  });
}

/**
 * Hook to fetch dashboard summary
 */
export function useDashboardSummary() {
  return useQuery<DashboardSummary>({
    queryKey: monitorKeys.dashboard(),
    queryFn: getDashboardSummary,
    refetchInterval: 15000, // Refresh every 15 seconds
  });
}

/**
 * Hook to fetch monitoring status
 */
export function useMonitoringStatus() {
  return useQuery<MonitoringStatus>({
    queryKey: monitorKeys.status(),
    queryFn: getMonitoringStatus,
    refetchInterval: 30000,
  });
}

/**
 * Hook to fetch system health
 */
export function useSystemHealth() {
  return useQuery<SystemHealth>({
    queryKey: monitorKeys.health(),
    queryFn: getSystemHealth,
    refetchInterval: 30000,
  });
}

/**
 * Hook to acknowledge an anomaly
 */
export function useAcknowledgeAnomaly() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (anomalyId: string) => acknowledgeAnomaly(anomalyId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: monitorKeys.anomalies() });
      queryClient.invalidateQueries({ queryKey: monitorKeys.dashboard() });
    },
  });
}

/**
 * Hook to analyze agent trajectory
 */
export function useAnalyzeAgentTrajectory() {
  return useMutation({
    mutationFn: ({ agentId, force }: { agentId: string; force?: boolean }) =>
      analyzeAgentTrajectory(agentId, force),
  });
}

/**
 * Hook to trigger emergency analysis
 */
export function useTriggerEmergencyAnalysis() {
  return useMutation({
    mutationFn: (agentIds: string[]) => triggerEmergencyAnalysis(agentIds),
  });
}
