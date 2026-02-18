/**
 * Onboarding debug tools
 *
 * Exposes debugging utilities on window.omoiosDebug.onboarding
 * for development and support purposes.
 */

import {
  getLocalOnboardingState,
  clearLocalOnboardingState,
  setOnboardingCookie,
  fetchOnboardingStatus,
  resetOnboardingServer,
  completeOnboardingServer,
  detectAndHealInconsistencies,
  type OnboardingServerStatus,
  type OnboardingLocalState,
  type SyncResult,
} from "./sync";
import { useOnboardingStore } from "@/hooks/useOnboarding";

// Debug interface exposed on window
interface OnboardingDebugTools {
  getState: () => OnboardingLocalState | null;
  getStoreState: () => ReturnType<typeof useOnboardingStore.getState>;
  getServerState: () => Promise<OnboardingServerStatus>;
  reset: () => Promise<void>;
  complete: () => Promise<void>;
  skipToStep: (step: string) => void;
  clearLocal: () => void;
  sync: () => Promise<SyncResult>;
  getCookie: () => boolean;
  setCookie: (value: boolean) => void;
  help: () => void;
}

declare global {
  interface Window {
    omoiosDebug?: {
      onboarding?: OnboardingDebugTools;
      [key: string]: unknown;
    };
  }
}

/**
 * Initialize onboarding debug tools on window object.
 * Only enabled in development or when debug flag is set.
 */
export function initOnboardingDebug(): void {
  if (typeof window === "undefined") return;

  // Only enable in development or with debug flag
  const isDebugEnabled =
    process.env.NODE_ENV === "development" ||
    localStorage.getItem("omoios_debug") === "true";

  if (!isDebugEnabled) return;

  // Initialize debug namespace
  window.omoiosDebug = window.omoiosDebug || {};

  window.omoiosDebug.onboarding = {
    /**
     * Get current localStorage onboarding state (raw)
     */
    getState: () => {
      return getLocalOnboardingState();
    },

    /**
     * Get current Zustand store state (React state)
     */
    getStoreState: () => {
      return useOnboardingStore.getState();
    },

    /**
     * Fetch current server onboarding state
     */
    getServerState: async () => {
      return fetchOnboardingStatus();
    },

    /**
     * Reset onboarding to beginning (calls API + resets Zustand store)
     */
    reset: async () => {
      try {
        await resetOnboardingServer();
        // Reset Zustand store
        useOnboardingStore.getState().reset();
        // Clear cookie
        setOnboardingCookie(false);
        console.log(
          "Onboarding reset successfully. UI should update automatically.",
        );
      } catch (error) {
        console.error("Failed to reset onboarding:", error);
        throw error;
      }
    },

    /**
     * Force complete onboarding (calls API + updates Zustand store)
     */
    complete: async () => {
      try {
        const response = await completeOnboardingServer({});
        // Update Zustand store
        const store = useOnboardingStore.getState();
        store.setIsOnboardingComplete(true);
        store.setCurrentStep("complete");
        store.setSyncVersion(response.sync_version);
        // Set cookie
        setOnboardingCookie(true);
        console.log(
          "Onboarding marked complete. UI should update automatically.",
        );
      } catch (error) {
        console.error("Failed to complete onboarding:", error);
        throw error;
      }
    },

    /**
     * Skip to a specific onboarding step (updates Zustand store)
     */
    skipToStep: (step: string) => {
      const store = useOnboardingStore.getState();
      store.setCurrentStep(step as Parameters<typeof store.setCurrentStep>[0]);
      console.log(`Skipped to step: ${step}. UI should update automatically.`);
    },

    /**
     * Clear localStorage state only (doesn't affect server or Zustand)
     */
    clearLocal: () => {
      clearLocalOnboardingState();
      setOnboardingCookie(false);
      console.log("Local storage cleared. Refresh the page to see changes.");
    },

    /**
     * Force sync with server
     */
    sync: async () => {
      const result = await detectAndHealInconsistencies();
      // If healed, also update Zustand store
      if (result.status === "healed" || result.status === "synced") {
        const serverState = await fetchOnboardingStatus();
        useOnboardingStore.getState().syncFromServer(serverState);
      }
      console.log("Sync result:", result);
      return result;
    },

    /**
     * Get current onboarding cookie value
     */
    getCookie: () => {
      return document.cookie.includes("omoios_onboarding_completed=true");
    },

    /**
     * Set onboarding cookie directly
     */
    setCookie: (value: boolean) => {
      setOnboardingCookie(value);
      console.log(`Onboarding cookie set to: ${value}`);
    },

    /**
     * Show help message with available commands
     */
    help: () => {
      console.log(`
Available onboarding debug commands:

  omoiosDebug.onboarding.getState()         - View localStorage state (raw)
  omoiosDebug.onboarding.getStoreState()    - View Zustand store state (React)
  omoiosDebug.onboarding.getServerState()   - Fetch server state
  omoiosDebug.onboarding.reset()            - Reset onboarding (API + store)
  omoiosDebug.onboarding.complete()         - Force complete (API + store)
  omoiosDebug.onboarding.skipToStep("plan") - Jump to specific step
  omoiosDebug.onboarding.clearLocal()       - Clear localStorage only
  omoiosDebug.onboarding.sync()             - Force sync with server
  omoiosDebug.onboarding.getCookie()        - Get onboarding cookie
  omoiosDebug.onboarding.setCookie(true)    - Set onboarding cookie

Steps: welcome, github, repo, first-spec, plan, complete

To enable debug tools in production:
  localStorage.setItem("omoios_debug", "true")
  location.reload()
      `);
    },
  };

  console.log(
    "Onboarding debug tools enabled. Type: omoiosDebug.onboarding.help()",
  );
}
