/**
 * React Query hooks for Spec-Driven Settings management
 *
 * Manages settings for the spec-driven development workflow, including:
 * - Auto-execution mode (auto/manual)
 * - Coverage requirements
 * - Parallel execution toggles
 * - Validation mode (strict/relaxed)
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";

// Types for spec-driven settings
export interface SpecDrivenSettings {
  id: string;
  user_id: string;
  // Execution mode
  auto_execute: boolean;
  execution_mode: "auto" | "manual";
  // Coverage settings
  coverage_threshold: number; // 0-100
  enforce_coverage: boolean;
  // Parallel execution
  parallel_execution: boolean;
  max_parallel_tasks: number;
  // Validation
  validation_mode: "strict" | "relaxed" | "none";
  require_tests: boolean;
  require_docs: boolean;
  // Advanced
  auto_merge: boolean;
  notify_on_completion: boolean;
  created_at: string;
  updated_at: string;
}

export interface SpecDrivenSettingsUpdate {
  auto_execute?: boolean;
  execution_mode?: "auto" | "manual";
  coverage_threshold?: number;
  enforce_coverage?: boolean;
  parallel_execution?: boolean;
  max_parallel_tasks?: number;
  validation_mode?: "strict" | "relaxed" | "none";
  require_tests?: boolean;
  require_docs?: boolean;
  auto_merge?: boolean;
  notify_on_completion?: boolean;
}

// Default settings
export const DEFAULT_SETTINGS: Omit<
  SpecDrivenSettings,
  "id" | "user_id" | "created_at" | "updated_at"
> = {
  auto_execute: true,
  execution_mode: "auto",
  coverage_threshold: 80,
  enforce_coverage: true,
  parallel_execution: true,
  max_parallel_tasks: 3,
  validation_mode: "strict",
  require_tests: true,
  require_docs: false,
  auto_merge: false,
  notify_on_completion: true,
};

// Risky configuration checks
export interface SettingsWarning {
  field: string;
  message: string;
  severity: "warning" | "error";
}

export function getSettingsWarnings(
  settings: Partial<SpecDrivenSettings>,
): SettingsWarning[] {
  const warnings: SettingsWarning[] = [];

  if (settings.auto_merge && settings.validation_mode === "none") {
    warnings.push({
      field: "auto_merge",
      message:
        "Auto-merge with no validation is risky. Consider enabling validation.",
      severity: "warning",
    });
  }

  if (
    settings.coverage_threshold !== undefined &&
    settings.coverage_threshold < 50 &&
    settings.enforce_coverage
  ) {
    warnings.push({
      field: "coverage_threshold",
      message: "Coverage threshold below 50% may result in low-quality code.",
      severity: "warning",
    });
  }

  if (
    settings.parallel_execution &&
    settings.max_parallel_tasks !== undefined &&
    settings.max_parallel_tasks > 5
  ) {
    warnings.push({
      field: "max_parallel_tasks",
      message: "Running more than 5 parallel tasks may impact performance.",
      severity: "warning",
    });
  }

  if (!settings.require_tests && settings.auto_merge) {
    warnings.push({
      field: "require_tests",
      message: "Auto-merge without required tests could introduce bugs.",
      severity: "error",
    });
  }

  return warnings;
}

// Validation
export interface ValidationError {
  field: string;
  message: string;
}

export function validateSettings(
  settings: Partial<SpecDrivenSettings>,
): ValidationError[] {
  const errors: ValidationError[] = [];

  if (settings.coverage_threshold !== undefined) {
    if (settings.coverage_threshold < 0 || settings.coverage_threshold > 100) {
      errors.push({
        field: "coverage_threshold",
        message: "Coverage must be between 0 and 100",
      });
    }
  }

  if (settings.max_parallel_tasks !== undefined) {
    if (settings.max_parallel_tasks < 1 || settings.max_parallel_tasks > 10) {
      errors.push({
        field: "max_parallel_tasks",
        message: "Parallel tasks must be between 1 and 10",
      });
    }
  }

  return errors;
}

// Query keys
export const specDrivenSettingsKeys = {
  all: ["spec-driven-settings"] as const,
  detail: () => [...specDrivenSettingsKeys.all, "detail"] as const,
};

// API functions
async function fetchSpecDrivenSettings(): Promise<SpecDrivenSettings> {
  const response = await api.get<SpecDrivenSettings>(
    "/api/v1/settings/spec-driven",
  );
  return response;
}

async function updateSpecDrivenSettings(
  data: SpecDrivenSettingsUpdate,
): Promise<SpecDrivenSettings> {
  const response = await api.patch<SpecDrivenSettings>(
    "/api/v1/settings/spec-driven",
    data,
  );
  return response;
}

async function resetSpecDrivenSettings(): Promise<SpecDrivenSettings> {
  const response = await api.post<SpecDrivenSettings>(
    "/api/v1/settings/spec-driven/reset",
    {},
  );
  return response;
}

/**
 * Hook to fetch spec-driven settings
 */
export function useSpecDrivenSettings() {
  return useQuery({
    queryKey: specDrivenSettingsKeys.detail(),
    queryFn: fetchSpecDrivenSettings,
  });
}

/**
 * Hook to update spec-driven settings
 */
export function useUpdateSpecDrivenSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: SpecDrivenSettingsUpdate) =>
      updateSpecDrivenSettings(data),
    onSuccess: (data) => {
      queryClient.setQueryData(specDrivenSettingsKeys.detail(), data);
    },
  });
}

/**
 * Hook to reset spec-driven settings to defaults
 */
export function useResetSpecDrivenSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => resetSpecDrivenSettings(),
    onSuccess: (data) => {
      queryClient.setQueryData(specDrivenSettingsKeys.detail(), data);
    },
  });
}
