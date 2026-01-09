"use client"

import { useEffect, useState } from "react"
import { useSearchParams } from "next/navigation"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { ArrowLeft, ChevronRight, ChevronLeft } from "lucide-react"
import { useOnboarding, type OnboardingStep } from "@/hooks/useOnboarding"
import { OnboardingChecklist } from "./OnboardingChecklist"
import { WelcomeStep } from "./steps/WelcomeStep"
import { GitHubStep } from "./steps/GitHubStep"
import { RepoSelectStep } from "./steps/RepoSelectStep"
import { FirstSpecStep } from "./steps/FirstSpecStep"
import { PlanSelectStep } from "./steps/PlanSelectStep"
import { CompleteStep } from "./steps/CompleteStep"
import { cn } from "@/lib/utils"

const STEP_COMPONENTS: Record<OnboardingStep, React.ComponentType> = {
  welcome: WelcomeStep,
  github: GitHubStep,
  repo: RepoSelectStep,
  "first-spec": FirstSpecStep,
  plan: PlanSelectStep,
  complete: CompleteStep,
}

const STEP_TITLES: Record<OnboardingStep, string> = {
  welcome: "Welcome",
  github: "Connect GitHub",
  repo: "Select Repository",
  "first-spec": "First Feature",
  plan: "Choose Plan",
  complete: "All Set!",
}

export function OnboardingWizard() {
  const searchParams = useSearchParams()
  const [checklistExpanded, setChecklistExpanded] = useState(true)
  const {
    currentStep,
    progress,
    canGoBack,
    prevStep,
    goToStep,
    checkGitHubConnection,
  } = useOnboarding()

  // Handle return from GitHub OAuth
  useEffect(() => {
    const step = searchParams.get("step")
    const githubConnected = searchParams.get("github_connected")

    if (githubConnected === "true") {
      checkGitHubConnection()
    }

    if (step && isValidStep(step)) {
      goToStep(step as OnboardingStep)
    }
  }, [searchParams, goToStep, checkGitHubConnection])

  const StepComponent = STEP_COMPONENTS[currentStep]

  return (
    <div className="flex gap-8 w-full">
      {/* Main content area */}
      <div className={cn(
        "flex-1 transition-all duration-300",
        checklistExpanded ? "max-w-xl" : "max-w-2xl mx-auto"
      )}>
        {/* Card wrapper for main content */}
        <div className="rounded-xl border bg-card p-8 shadow-sm">
          {/* Header with progress */}
          <div className="space-y-4 mb-6">
            {/* Back button */}
            {canGoBack && currentStep !== "complete" && (
              <Button
                variant="ghost"
                size="sm"
                onClick={prevStep}
                className="text-muted-foreground hover:text-foreground -ml-2"
              >
                <ArrowLeft className="h-4 w-4 mr-1" />
                Back
              </Button>
            )}

            {/* Progress bar */}
            {currentStep !== "complete" && (
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>{STEP_TITLES[currentStep]}</span>
                  <span>{progress}% complete</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            )}
          </div>

          {/* Step content */}
          <div className="min-h-[400px]">
            <StepComponent />
          </div>
        </div>
      </div>

      {/* Sidebar checklist */}
      <div className={cn(
        "relative transition-all duration-300 shrink-0",
        checklistExpanded ? "w-72" : "w-8"
      )}>
        {/* Toggle button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setChecklistExpanded(!checklistExpanded)}
          className="absolute -left-4 top-4 h-8 w-8 rounded-full border bg-background shadow-sm z-10"
        >
          {checklistExpanded ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </Button>

        {/* Checklist content */}
        <div className={cn(
          "transition-all duration-300",
          checklistExpanded ? "opacity-100" : "opacity-0 pointer-events-none"
        )}>
          <div className="p-5 rounded-xl border bg-card shadow-sm sticky top-4">
            <OnboardingChecklist showPostOnboarding={currentStep === "complete"} />
          </div>
        </div>
      </div>
    </div>
  )
}

function isValidStep(step: string): step is OnboardingStep {
  return ["welcome", "github", "repo", "first-spec", "plan", "complete"].includes(step)
}
