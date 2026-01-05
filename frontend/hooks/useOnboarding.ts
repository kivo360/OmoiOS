"use client"

import { useState, useCallback, useEffect } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/hooks/useAuth"
import { api } from "@/lib/api/client"

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

export interface OnboardingState {
  currentStep: OnboardingStep
  completedSteps: OnboardingStep[]
  completedChecklistItems: ChecklistItemId[]
  isOnboardingComplete: boolean
  data: {
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
}

const STEPS_ORDER: OnboardingStep[] = [
  "welcome",
  "github",
  "repo",
  "first-spec",
  "plan",
  "complete",
]

const STORAGE_KEY = "omoios_onboarding_state"

export function useOnboarding() {
  const router = useRouter()
  const { user, isLoading: authLoading } = useAuth()

  const [state, setState] = useState<OnboardingState>(() => {
    // Try to restore from localStorage on client
    if (typeof window !== "undefined") {
      const saved = localStorage.getItem(STORAGE_KEY)
      if (saved) {
        try {
          return JSON.parse(saved)
        } catch {
          // Invalid JSON, start fresh
        }
      }
    }
    return {
      currentStep: "welcome",
      completedSteps: [],
      completedChecklistItems: [],
      isOnboardingComplete: false,
      data: {
        githubConnected: false,
      },
    }
  })

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Persist state changes
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    }
  }, [state])

  // Check if GitHub is already connected on mount
  useEffect(() => {
    if (user && !state.data.githubConnected) {
      checkGitHubConnection()
    }
  }, [user])

  const checkGitHubConnection = async () => {
    try {
      // Use the correct backend endpoint for GitHub connection status
      const response = await api.get<{ connected: boolean; username?: string }>(
        "/api/v1/github/connection-status"
      )
      if (response.connected) {
        updateData({
          githubConnected: true,
          githubUsername: response.username,
        })
        // If we're on GitHub step, auto-advance
        if (state.currentStep === "github") {
          goToStep("repo")
        }
      }
    } catch {
      // Not connected, that's fine
    }
  }

  const updateData = useCallback((updates: Partial<OnboardingState["data"]>) => {
    setState(prev => ({
      ...prev,
      data: { ...prev.data, ...updates },
    }))
  }, [])

  const goToStep = useCallback((step: OnboardingStep) => {
    setState(prev => ({
      ...prev,
      currentStep: step,
    }))

    // Track analytics
    trackEvent("onboarding_step_viewed", { step })
  }, [])

  const completeStep = useCallback((step: OnboardingStep) => {
    setState(prev => {
      const newCompletedSteps = prev.completedSteps.includes(step)
        ? prev.completedSteps
        : [...prev.completedSteps, step]

      // Also mark the corresponding checklist item as complete
      const checklistItemId = step as ChecklistItemId
      const newCompletedChecklistItems = prev.completedChecklistItems.includes(checklistItemId)
        ? prev.completedChecklistItems
        : [...prev.completedChecklistItems, checklistItemId]

      return {
        ...prev,
        completedSteps: newCompletedSteps,
        completedChecklistItems: newCompletedChecklistItems,
      }
    })

    // Track analytics
    trackEvent("onboarding_step_completed", { step })
  }, [])

  // Complete a checklist item (for post-onboarding tasks)
  const completeChecklistItem = useCallback((itemId: ChecklistItemId) => {
    setState(prev => {
      if (prev.completedChecklistItems.includes(itemId)) {
        return prev
      }
      return {
        ...prev,
        completedChecklistItems: [...prev.completedChecklistItems, itemId],
      }
    })
    trackEvent("checklist_item_completed", { itemId })
  }, [])

  // Mark onboarding as fully complete (when first spec finishes running)
  const markOnboardingComplete = useCallback(() => {
    setState(prev => ({
      ...prev,
      isOnboardingComplete: true,
    }))
    trackEvent("onboarding_fully_completed", {
      completedItems: state.completedChecklistItems,
    })
  }, [state.completedChecklistItems])

  const nextStep = useCallback(() => {
    const currentIndex = STEPS_ORDER.indexOf(state.currentStep)
    if (currentIndex < STEPS_ORDER.length - 1) {
      const nextStepName = STEPS_ORDER[currentIndex + 1]
      completeStep(state.currentStep)
      goToStep(nextStepName)
    }
  }, [state.currentStep, completeStep, goToStep])

  const prevStep = useCallback(() => {
    const currentIndex = STEPS_ORDER.indexOf(state.currentStep)
    if (currentIndex > 0) {
      goToStep(STEPS_ORDER[currentIndex - 1])
    }
  }, [state.currentStep, goToStep])

  const skipToStep = useCallback((targetStep: OnboardingStep) => {
    // Mark all steps up to (but not including) target as completed
    const targetIndex = STEPS_ORDER.indexOf(targetStep)
    const stepsToComplete = STEPS_ORDER.slice(0, targetIndex)

    setState(prev => ({
      ...prev,
      currentStep: targetStep,
      completedSteps: [...new Set([...prev.completedSteps, ...stepsToComplete])],
    }))
  }, [])

  const completeOnboarding = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      // Save onboarding completion to backend
      await api.post("/api/v1/users/onboarding/complete", {
        data: state.data,
      }).catch(() => {
        // Endpoint may not exist yet, continue anyway
        console.log("Onboarding endpoint not available, continuing...")
      })

      // Clear localStorage
      localStorage.removeItem(STORAGE_KEY)

      // Track completion
      trackEvent("onboarding_completed", {
        selectedPlan: state.data.selectedPlan,
        hasFirstSpec: !!state.data.firstSpecId,
      })

      // Redirect based on whether spec was submitted
      if (state.data.firstSpecId) {
        // Redirect to board to watch agent progress in real-time
        const projectId = state.data.projectId || "all"
        router.push(`/board/${projectId}`)
      } else {
        router.push("/command")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to complete onboarding")
    } finally {
      setIsLoading(false)
    }
  }, [state.data, router])

  const connectGitHub = useCallback(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"
    const returnUrl = `${window.location.origin}/onboarding?step=repo`
    window.location.href = `${apiUrl}/api/v1/auth/oauth/github?onboarding=true&return_url=${encodeURIComponent(returnUrl)}`
  }, [])

  const submitFirstSpec = useCallback(async (specText: string) => {
    setIsLoading(true)
    setError(null)

    try {
      // Create project if not exists
      let projectId = state.data.projectId
      let organizationId = state.data.organizationId

      if (!projectId && state.data.selectedRepo) {
        // First ensure we have an organization
        if (!organizationId) {
          const orgResponse = await api.post<{ id: string }>("/api/v1/organizations", {
            name: `${user?.full_name || "My"}'s Workspace`,
            slug: user?.email?.split("@")[0] || "workspace",
          }).catch(async () => {
            // Org might already exist, try to get it
            const orgs = await api.get<Array<{ id: string }>>("/api/v1/organizations")
            return orgs[0]
          })
          organizationId = orgResponse.id
          updateData({ organizationId })
        }

        // Create project
        const projectResponse = await api.post<{ id: string }>("/api/v1/projects", {
          name: state.data.selectedRepo.name,
          description: `Project for ${state.data.selectedRepo.fullName}`,
          github_owner: state.data.selectedRepo.owner,
          github_repo: state.data.selectedRepo.name,
          organization_id: organizationId,
        })
        projectId = projectResponse.id
        updateData({ projectId })
      }

      // Submit spec/start sandbox
      const sandboxResponse = await api.post<{ id: string; sandbox_id: string }>("/api/v1/sandboxes", {
        project_id: projectId,
        prompt: specText,
        name: specText.slice(0, 50),
      })

      updateData({
        firstSpecId: sandboxResponse.sandbox_id || sandboxResponse.id,
        firstSpecText: specText,
        firstSpecStatus: "running",
      })

      trackEvent("first_spec_submitted", {
        specLength: specText.length,
        projectId,
      })

      nextStep()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit spec")
    } finally {
      setIsLoading(false)
    }
  }, [state.data, user, updateData, nextStep])

  const progress = Math.round(
    ((STEPS_ORDER.indexOf(state.currentStep) + 1) / STEPS_ORDER.length) * 100
  )

  const canGoBack = STEPS_ORDER.indexOf(state.currentStep) > 0
  const canSkip = state.currentStep === "plan" // Only plan step is skippable

  // Poll for first spec completion status (placed after all function definitions)
  useEffect(() => {
    if (!state.data.firstSpecId || state.data.firstSpecStatus === "completed" || state.data.firstSpecStatus === "failed") {
      return
    }

    const checkSpecStatus = async () => {
      try {
        const response = await api.get<{ status: string }>(`/api/v1/sandboxes/${state.data.firstSpecId}`)
        const status = response.status?.toLowerCase()

        if (status === "completed" || status === "success") {
          setState(prev => ({
            ...prev,
            isOnboardingComplete: true,
            completedChecklistItems: prev.completedChecklistItems.includes("watch-agent")
              ? prev.completedChecklistItems
              : [...prev.completedChecklistItems, "watch-agent"],
            data: { ...prev.data, firstSpecStatus: "completed" },
          }))
          trackEvent("onboarding_fully_completed", { firstSpecId: state.data.firstSpecId })
        } else if (status === "failed" || status === "error") {
          setState(prev => ({
            ...prev,
            data: { ...prev.data, firstSpecStatus: "failed" },
          }))
        }
      } catch {
        // Silently ignore polling errors
      }
    }

    // Poll every 10 seconds
    const interval = setInterval(checkSpecStatus, 10000)
    // Also check immediately
    checkSpecStatus()

    return () => clearInterval(interval)
  }, [state.data.firstSpecId, state.data.firstSpecStatus])

  return {
    // State
    currentStep: state.currentStep,
    completedSteps: state.completedSteps,
    completedChecklistItems: state.completedChecklistItems,
    isOnboardingComplete: state.isOnboardingComplete,
    data: state.data,
    progress,
    isLoading: isLoading || authLoading,
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

// Analytics helper
function trackEvent(eventName: string, data?: Record<string, unknown>) {
  // Placeholder for analytics - integrate with your analytics provider
  console.log(`[Analytics] ${eventName}`, data)

  // Example: PostHog, Mixpanel, etc.
  // posthog?.capture(eventName, data)
}

export { trackEvent }
