/**
 * Onboarding sync service
 *
 * Handles synchronization between localStorage and server state,
 * including auto-detection of inconsistencies and self-healing.
 */

import { api } from "@/lib/api/client";

// Types
export interface OnboardingServerStatus {
  is_completed: boolean;
  current_step: string;
  completed_steps: string[];
  completed_checklist_items: string[];
  completed_at: string | null;
  data: Record<string, unknown>;
  sync_version: number;
}

export interface OnboardingLocalState {
  currentStep: string;
  completedSteps: string[];
  completedChecklistItems: string[];
  completedAt: string | null;
  isOnboardingComplete: boolean;
  data: {
    githubConnected: boolean;
    githubUsername?: string;
    selectedRepo?: {
      owner: string;
      name: string;
      fullName: string;
      language?: string;
    };
    projectId?: string;
    organizationId?: string;
    firstSpecId?: string;
    firstSpecText?: string;
    firstSpecStatus?: "pending" | "running" | "completed" | "failed";
    selectedPlan?: string;
    [key: string]: unknown;
  };
  lastSyncedAt?: string;
  syncVersion: number;
}

export interface DetectedStepState {
  completed: boolean;
  current: Record<string, unknown> | null;
  can_change: boolean;
}

export interface OnboardingDetectedState {
  github: DetectedStepState;
  organization: DetectedStepState;
  repo: DetectedStepState;
  plan: DetectedStepState;
  suggested_step: string;
}

export interface SyncResult {
  status: "synced" | "healed" | "conflict" | "error";
  action?: string;
  error?: string;
}

// Constants
const STORAGE_KEY = "omoios_onboarding_state";
const ONBOARDING_COOKIE_NAME = "omoios_onboarding_completed";

// Utility functions
export function getLocalOnboardingState(): OnboardingLocalState | null {
  if (typeof window === "undefined") return null;

  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;

  try {
    return JSON.parse(raw) as OnboardingLocalState;
  } catch {
    return null;
  }
}

export function setLocalOnboardingState(state: OnboardingLocalState): void {
  if (typeof window === "undefined") return;

  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      ...state,
      lastSyncedAt: new Date().toISOString(),
    }),
  );
}

export function clearLocalOnboardingState(): void {
  if (typeof window === "undefined") return;

  localStorage.removeItem(STORAGE_KEY);
}

export function setOnboardingCookie(completed: boolean): void {
  if (typeof window === "undefined") return;

  if (completed) {
    // Set cookie for 1 year
    document.cookie = `${ONBOARDING_COOKIE_NAME}=true; path=/; max-age=31536000; SameSite=Lax`;
  } else {
    // Remove cookie by setting expiry in the past
    document.cookie = `${ONBOARDING_COOKIE_NAME}=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT`;
  }
}

export function getOnboardingCookie(): boolean {
  if (typeof window === "undefined") return false;

  return document.cookie.includes(`${ONBOARDING_COOKIE_NAME}=true`);
}

// API functions
export async function fetchOnboardingStatus(): Promise<OnboardingServerStatus> {
  return api.get<OnboardingServerStatus>("/api/v1/onboarding/status");
}

export async function detectOnboardingState(): Promise<OnboardingDetectedState> {
  return api.get<OnboardingDetectedState>("/api/v1/onboarding/detect");
}

export async function updateOnboardingStep(
  step: string,
  data: Record<string, unknown> = {},
): Promise<OnboardingServerStatus> {
  return api.post<OnboardingServerStatus>("/api/v1/onboarding/step", {
    step,
    data,
  });
}

export async function completeOnboardingServer(
  data: Record<string, unknown> = {},
): Promise<OnboardingServerStatus> {
  return api.post<OnboardingServerStatus>("/api/v1/onboarding/complete", {
    data,
  });
}

export async function resetOnboardingServer(): Promise<OnboardingServerStatus> {
  return api.post<OnboardingServerStatus>("/api/v1/onboarding/reset");
}

export async function syncOnboardingToServer(
  localState: OnboardingLocalState,
): Promise<OnboardingServerStatus> {
  return api.post<OnboardingServerStatus>("/api/v1/onboarding/sync", {
    current_step: localState.currentStep,
    completed_steps: localState.completedSteps,
    completed_checklist_items: localState.completedChecklistItems,
    data: localState.data,
    local_sync_version: localState.syncVersion,
  });
}

// Sync functions
export function syncLocalFromServer(serverState: OnboardingServerStatus): void {
  const localState: OnboardingLocalState = {
    currentStep: serverState.current_step,
    completedSteps: serverState.completed_steps,
    completedChecklistItems: serverState.completed_checklist_items,
    completedAt: serverState.completed_at,
    isOnboardingComplete: serverState.is_completed,
    data: {
      githubConnected: false,
      ...(serverState.data as Record<string, unknown>),
    },
    syncVersion: serverState.sync_version,
  };

  setLocalOnboardingState(localState);
  setOnboardingCookie(serverState.is_completed);
}

/**
 * Detect and heal inconsistencies between local and server state.
 * Server is always the source of truth.
 */
export async function detectAndHealInconsistencies(): Promise<SyncResult> {
  try {
    const localState = getLocalOnboardingState();
    const serverState = await fetchOnboardingStatus();

    // Case 1: Server says complete, local says incomplete
    if (serverState.is_completed && !localState?.isOnboardingComplete) {
      syncLocalFromServer(serverState);
      return { status: "healed", action: "local_updated_from_server" };
    }

    // Case 2: Local says complete, server says incomplete
    // Trust server (source of truth), reset local
    if (!serverState.is_completed && localState?.isOnboardingComplete) {
      syncLocalFromServer(serverState);
      return { status: "healed", action: "local_reset_from_server" };
    }

    // Case 3: Steps mismatch - server wins
    if (serverState.current_step !== localState?.currentStep) {
      syncLocalFromServer(serverState);
      return { status: "healed", action: "step_synced" };
    }

    // Case 4: Sync version mismatch - server with higher version wins
    if (localState && serverState.sync_version > localState.syncVersion) {
      syncLocalFromServer(serverState);
      return { status: "healed", action: "version_synced" };
    }

    // Case 5: Cookie missing but should be set
    const cookie = getOnboardingCookie();
    if (serverState.is_completed && !cookie) {
      setOnboardingCookie(true);
      return { status: "healed", action: "cookie_restored" };
    }

    // Case 6: Cookie set but shouldn't be
    if (!serverState.is_completed && cookie) {
      setOnboardingCookie(false);
      return { status: "healed", action: "cookie_cleared" };
    }

    // Case 7: No local state - initialize from server
    if (!localState) {
      syncLocalFromServer(serverState);
      return { status: "healed", action: "local_initialized" };
    }

    return { status: "synced" };
  } catch (error) {
    // If API fails, check localStorage as fallback
    const localState = getLocalOnboardingState();
    if (localState?.isOnboardingComplete) {
      setOnboardingCookie(true);
    }

    return {
      status: "error",
      error: error instanceof Error ? error.message : "Sync failed",
    };
  }
}

/**
 * Initial sync on app mount.
 * Fetches server state and updates local state accordingly.
 */
export async function initialSync(): Promise<SyncResult> {
  return detectAndHealInconsistencies();
}

/**
 * Check if user needs onboarding based on server state.
 */
export async function checkOnboardingNeeded(): Promise<boolean> {
  try {
    const serverState = await fetchOnboardingStatus();
    return !serverState.is_completed;
  } catch {
    // Fallback to local state
    const localState = getLocalOnboardingState();
    return !localState?.isOnboardingComplete;
  }
}
