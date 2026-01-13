"use client"

import { useCallback, useEffect, useRef } from "react"
import { useRouter } from "next/navigation"
import { create } from "zustand"
import { persist } from "zustand/middleware"
import { useAuth } from "@/hooks/useAuth"
import { createSafeStorage } from "@/lib/storage/safeStorage"
import { api } from "@/lib/api/client"
import { track, trackEvent as analyticsTrackEvent, ANALYTICS_EVENTS } from "@/lib/analytics"
import {
  fetchOnboardingStatus,
  detectOnboardingState,
  updateOnboardingStep,
  completeOnboardingServer,
  setOnboardingCookie,
  type OnboardingDetectedState,
} from "@/lib/onboarding"

export type OnboardingStep =
  | "welcome"
  | "github"
  | "repo"
  | "first-spec"
  | "plan"
  | "complete"

// Extended checklist items for post-onboarding tasks
export type ChecklistItemId =
  | "welcome"
  | "github"
  | "repo"
  | "first-spec"
  | "plan"
  | "watch-agent"
  | "review-pr"
  | "invite-team"

export interface OnboardingData {
  role?: string
  githubConnected: boolean
  githubUsername?: string
  selectedRepo?: {
    owner: string
    name: string
    fullName: string
    language?: string
  }
  projectId?: string
  organizationId?: string
  firstSpecId?: string
  firstSpecText?: string
  firstSpecStatus?: "pending" | "running" | "completed" | "failed"
  selectedPlan?: string
}

export interface OnboardingState {
  currentStep: OnboardingStep
  completedSteps: OnboardingStep[]
  completedChecklistItems: ChecklistItemId[]
  isOnboardingComplete: boolean
  syncVersion: number
  data: OnboardingData
  detectedState: OnboardingDetectedState | null
  isLoading: boolean
  error: string | null

  // Actions
  setCurrentStep: (step: OnboardingStep) => void
  setCompletedSteps: (steps: OnboardingStep[]) => void
  addCompletedStep: (step: OnboardingStep) => void
  setCompletedChecklistItems: (items: ChecklistItemId[]) => void
  addCompletedChecklistItem: (item: ChecklistItemId) => void
  setIsOnboardingComplete: (complete: boolean) => void
  setSyncVersion: (version: number) => void
  setData: (data: Partial<OnboardingData>) => void
  setDetectedState: (state: OnboardingDetectedState | null) => void
  setIsLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  reset: () => void
  syncFromServer: (serverState: {
    current_step: string
    completed_steps: string[]
    completed_checklist_items: string[]
    is_completed: boolean
    sync_version: number
    data: Record<string, unknown>
  }) => void
}

const STEPS_ORDER: OnboardingStep[] = [
  "welcome",
  "github",
  "repo",
  "first-spec",
  "plan",
  "complete",
]

const initialData: OnboardingData = {
  githubConnected: false,
}

// Zustand store for shared state across all components
export const useOnboardingStore = create<OnboardingState>()(
  persist(
    (set, get) => ({
      currentStep: "welcome",
      completedSteps: [],
      completedChecklistItems: [],
      isOnboardingComplete: false,
      syncVersion: 0,
      data: initialData,
      detectedState: null,
      isLoading: false,
      error: null,

      setCurrentStep: (step) => set({ currentStep: step }),

      setCompletedSteps: (steps) => set({ completedSteps: steps }),

      addCompletedStep: (step) => set((state) => ({
        completedSteps: state.completedSteps.includes(step)
          ? state.completedSteps
          : [...state.completedSteps, step],
      })),

      setCompletedChecklistItems: (items) => set({ completedChecklistItems: items }),

      addCompletedChecklistItem: (item) => set((state) => ({
        completedChecklistItems: state.completedChecklistItems.includes(item)
          ? state.completedChecklistItems
          : [...state.completedChecklistItems, item],
      })),

      setIsOnboardingComplete: (complete) => set({ isOnboardingComplete: complete }),

      setSyncVersion: (version) => set({ syncVersion: version }),

      setData: (data) => set((state) => ({
        data: { ...state.data, ...data },
      })),

      setDetectedState: (detectedState) => set({ detectedState }),

      setIsLoading: (isLoading) => set({ isLoading }),

      setError: (error) => set({ error }),

      reset: () => set({
        currentStep: "welcome",
        completedSteps: [],
        completedChecklistItems: [],
        isOnboardingComplete: false,
        syncVersion: 0,
        data: initialData,
        detectedState: null,
        isLoading: false,
        error: null,
      }),

      syncFromServer: (serverState) => set({
        currentStep: serverState.current_step as OnboardingStep,
        completedSteps: serverState.completed_steps as OnboardingStep[],
        completedChecklistItems: serverState.completed_checklist_items as ChecklistItemId[],
        isOnboardingComplete: serverState.is_completed,
        syncVersion: serverState.sync_version,
        data: {
          ...get().data,
          ...(serverState.data as Partial<OnboardingData>),
        },
      }),
    }),
    {
      name: "omoios_onboarding_state",
      storage: createSafeStorage(),
      partialize: (state) => ({
        currentStep: state.currentStep,
        completedSteps: state.completedSteps,
        completedChecklistItems: state.completedChecklistItems,
        isOnboardingComplete: state.isOnboardingComplete,
        syncVersion: state.syncVersion,
        data: state.data,
      }),
    }
  )
)

// Hook that provides onboarding functionality
export function useOnboarding() {
  const router = useRouter()
  const { user, isLoading: authLoading } = useAuth()
  const hasSynced = useRef(false)
  const hasCheckedGitHub = useRef(false)

  // Get state from store
  const {
    currentStep,
    completedSteps,
    completedChecklistItems,
    isOnboardingComplete,
    syncVersion,
    data,
    detectedState,
    isLoading: storeLoading,
    error,
    setCurrentStep,
    addCompletedStep,
    addCompletedChecklistItem,
    setIsOnboardingComplete,
    setSyncVersion,
    setData,
    setDetectedState,
    setIsLoading,
    setError,
    syncFromServer,
  } = useOnboardingStore()

  // Sync with server on mount (only once)
  useEffect(() => {
    if (!user || hasSynced.current || authLoading) return

    const syncWithServer = async () => {
      try {
        const serverState = await fetchOnboardingStatus()

        // If server version is newer, update local state
        if (serverState.sync_version > syncVersion) {
          syncFromServer(serverState)
        }

        // Update cookie based on server state
        setOnboardingCookie(serverState.is_completed)

        hasSynced.current = true
      } catch (err) {
        console.log("Failed to sync onboarding with server:", err)
      }
    }

    syncWithServer()
  }, [user, authLoading, syncVersion, syncFromServer])

  // Detect completed steps on mount
  useEffect(() => {
    if (!user || authLoading) return

    const detect = async () => {
      try {
        const detected = await detectOnboardingState()
        setDetectedState(detected)
      } catch {
        // Detection failed, continue without it
      }
    }

    detect()
  }, [user, authLoading, setDetectedState])

  // Check GitHub connection on mount
  useEffect(() => {
    if (!user || hasCheckedGitHub.current || data.githubConnected) return

    const checkConnection = async () => {
      hasCheckedGitHub.current = true
      try {
        const response = await api.get<{ connected: boolean; username?: string }>(
          "/api/v1/github/connection-status"
        )
        if (response.connected) {
          setData({
            githubConnected: true,
            githubUsername: response.username,
          })
        }
      } catch {
        // Not connected, that's fine
      }
    }

    checkConnection()
  }, [user, data.githubConnected, setData])

  // Poll for first spec completion status
  useEffect(() => {
    if (!data.firstSpecId || data.firstSpecStatus === "completed" || data.firstSpecStatus === "failed") {
      return
    }

    const checkSpecStatus = async () => {
      try {
        const response = await api.get<{ status: string }>(`/api/v1/sandboxes/${data.firstSpecId}`)
        const status = response.status?.toLowerCase()

        if (status === "completed" || status === "success") {
          setData({ firstSpecStatus: "completed" })
          addCompletedChecklistItem("watch-agent")
          setIsOnboardingComplete(true)
          analyticsTrackEvent("onboarding_fully_completed", { firstSpecId: data.firstSpecId })
        } else if (status === "failed" || status === "error") {
          setData({ firstSpecStatus: "failed" })
        }
      } catch {
        // Silently ignore polling errors
      }
    }

    const interval = setInterval(checkSpecStatus, 10000)
    checkSpecStatus()

    return () => clearInterval(interval)
  }, [data.firstSpecId, data.firstSpecStatus, setData, addCompletedChecklistItem, setIsOnboardingComplete])

  // Navigation actions
  const goToStep = useCallback(async (step: OnboardingStep) => {
    setCurrentStep(step)
    analyticsTrackEvent("onboarding_step_viewed", { step })

    // Sync step change to server
    try {
      const response = await updateOnboardingStep(step, { ...data })
      setSyncVersion(response.sync_version)
    } catch {
      // Sync failed, continue anyway
    }
  }, [data, setCurrentStep, setSyncVersion])

  const completeStep = useCallback((step: OnboardingStep) => {
    addCompletedStep(step)
    // Also mark as checklist item
    addCompletedChecklistItem(step as ChecklistItemId)
    analyticsTrackEvent("onboarding_step_completed", { step })
  }, [addCompletedStep, addCompletedChecklistItem])

  const nextStep = useCallback(() => {
    const currentIndex = STEPS_ORDER.indexOf(currentStep)
    if (currentIndex < STEPS_ORDER.length - 1) {
      const nextStepName = STEPS_ORDER[currentIndex + 1]
      completeStep(currentStep)
      goToStep(nextStepName)
    }
  }, [currentStep, completeStep, goToStep])

  const prevStep = useCallback(() => {
    const currentIndex = STEPS_ORDER.indexOf(currentStep)
    if (currentIndex > 0) {
      goToStep(STEPS_ORDER[currentIndex - 1])
    }
  }, [currentStep, goToStep])

  const skipToStep = useCallback((targetStep: OnboardingStep) => {
    const targetIndex = STEPS_ORDER.indexOf(targetStep)
    const stepsToComplete = STEPS_ORDER.slice(0, targetIndex)

    stepsToComplete.forEach((step) => {
      addCompletedStep(step)
      addCompletedChecklistItem(step as ChecklistItemId)
    })
    setCurrentStep(targetStep)
  }, [setCurrentStep, addCompletedStep, addCompletedChecklistItem])

  const completeChecklistItem = useCallback((itemId: ChecklistItemId) => {
    addCompletedChecklistItem(itemId)
    analyticsTrackEvent("checklist_item_completed", { itemId })
  }, [addCompletedChecklistItem])

  const markOnboardingComplete = useCallback(() => {
    setIsOnboardingComplete(true)
    analyticsTrackEvent("onboarding_fully_completed", {
      completedItems: completedChecklistItems,
    })
  }, [completedChecklistItems, setIsOnboardingComplete])

  const updateData = useCallback((updates: Partial<OnboardingData>) => {
    setData(updates)
  }, [setData])

  const connectGitHub = useCallback(async () => {
    // Use the authenticated connect flow to ensure GitHub is linked to the CURRENT user
    // This prevents the issue where GitHub OAuth matches by email and redirects to old account
    try {
      const response = await api.post<{ auth_url: string; state: string }>(
        "/api/v1/auth/oauth/github/connect"
      )
      // Redirect to GitHub OAuth
      window.location.href = response.auth_url
    } catch (err) {
      console.error("Failed to start GitHub connect flow:", err)
      // Fallback to direct OAuth if the authenticated flow fails (e.g., not logged in)
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"
      const returnUrl = `${window.location.origin}/onboarding?step=repo`
      window.location.href = `${apiUrl}/api/v1/auth/oauth/github?onboarding=true&return_url=${encodeURIComponent(returnUrl)}`
    }
  }, [])

  const checkGitHubConnection = useCallback(async () => {
    try {
      const response = await api.get<{ connected: boolean; username?: string }>(
        "/api/v1/github/connection-status"
      )
      if (response.connected) {
        setData({
          githubConnected: true,
          githubUsername: response.username,
        })
        // If we're on GitHub step, auto-advance
        if (currentStep === "github") {
          goToStep("repo")
        }
      }
    } catch {
      // Not connected, that's fine
    }
  }, [currentStep, setData, goToStep])

  const submitFirstSpec = useCallback(async (specText: string) => {
    setIsLoading(true)
    setError(null)

    try {
      let projectId = data.projectId
      let organizationId = data.organizationId

      if (!projectId && data.selectedRepo) {
        if (!organizationId) {
          const orgResponse = await api.post<{ id: string }>("/api/v1/organizations", {
            name: `${user?.full_name || "My"}'s Workspace`,
            slug: user?.email?.split("@")[0] || "workspace",
          }).catch(async () => {
            const orgs = await api.get<Array<{ id: string }>>("/api/v1/organizations")
            return orgs[0]
          })
          organizationId = orgResponse.id
          setData({ organizationId })
        }

        const projectResponse = await api.post<{ id: string }>("/api/v1/projects", {
          name: data.selectedRepo.name,
          description: `Project for ${data.selectedRepo.fullName}`,
          github_owner: data.selectedRepo.owner,
          github_repo: data.selectedRepo.name,
          organization_id: organizationId,
        })
        projectId = projectResponse.id
        setData({ projectId })
      }

      const sandboxResponse = await api.post<{ id: string; sandbox_id: string }>("/api/v1/sandboxes", {
        project_id: projectId,
        prompt: specText,
        name: specText.slice(0, 50),
      })

      setData({
        firstSpecId: sandboxResponse.sandbox_id || sandboxResponse.id,
        firstSpecText: specText,
        firstSpecStatus: "running",
      })

      analyticsTrackEvent("first_spec_submitted", {
        specLength: specText.length,
        projectId,
      })

      nextStep()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit spec")
    } finally {
      setIsLoading(false)
    }
  }, [data, user, setData, setIsLoading, setError, nextStep])

  const completeOnboarding = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await completeOnboardingServer({ ...data })

      setIsOnboardingComplete(true)
      setCurrentStep("complete")
      setSyncVersion(response.sync_version)
      setOnboardingCookie(true)

      analyticsTrackEvent("onboarding_completed", {
        selectedPlan: data.selectedPlan,
        hasFirstSpec: !!data.firstSpecId,
      })

      if (data.firstSpecId) {
        const projectId = data.projectId || "all"
        router.push(`/board/${projectId}`)
      } else {
        router.push("/command")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete onboarding")
    } finally {
      setIsLoading(false)
    }
  }, [data, router, setIsLoading, setError, setIsOnboardingComplete, setCurrentStep, setSyncVersion])

  // Computed values
  const progress = Math.round(
    ((STEPS_ORDER.indexOf(currentStep) + 1) / STEPS_ORDER.length) * 100
  )
  const canGoBack = STEPS_ORDER.indexOf(currentStep) > 0
  const canSkip = currentStep === "plan"

  return {
    // State
    currentStep,
    completedSteps: completedSteps || [],
    completedChecklistItems: completedChecklistItems || [],
    isOnboardingComplete,
    syncVersion,
    data: data || initialData,
    detectedState,
    progress,
    isLoading: storeLoading || authLoading,
    error,

    // Navigation
    nextStep,
    prevStep,
    goToStep,
    skipToStep,
    completeStep,
    canGoBack,
    canSkip,

    // Checklist
    completeChecklistItem,
    markOnboardingComplete,

    // Actions
    updateData,
    connectGitHub,
    checkGitHubConnection,
    submitFirstSpec,
    completeOnboarding,
    clearError: () => setError(null),
  }
}

// Re-export trackEvent from analytics module for backwards compatibility
export { analyticsTrackEvent as trackEvent }
