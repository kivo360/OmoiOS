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
    <div className="flex gap-6 justify-center">
      {/* Main content card */}
      <div className="w-full max-w-lg">
        <div className="rounded-2xl border bg-card p-8 shadow-sm">
          {/* Header with progress */}
          {currentStep !== "complete" && (
            <div className="space-y-4 mb-8">
              {/* Back button */}
              {canGoBack && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={prevStep}
                  className="text-muted-foreground hover:text-foreground -ml-3"
                >
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Back
                </Button>
              )}

              {/* Progress bar */}
              <div className="space-y-2">
                <div className="flex justify-between text-sm text-muted-foreground">
                  <span>{STEP_TITLES[currentStep]}</span>
                  <span>{progress}% complete</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>
            </div>
          )}

          {/* Step content */}
          <StepComponent />
        </div>
      </div>

      {/* Sidebar checklist - hidden on mobile */}
      <div className={cn(
        "hidden lg:block transition-all duration-300 shrink-0",
        checklistExpanded ? "w-64" : "w-10"
      )}>
        <div className="sticky top-8">
          {/* Toggle button */}
          <Button
            variant="outline"
            size="icon"
            onClick={() => setChecklistExpanded(!checklistExpanded)}
            className="absolute -left-3 top-0 h-7 w-7 rounded-full bg-background shadow-sm z-10"
          >
            {checklistExpanded ? (
              <ChevronRight className="h-3.5 w-3.5" />
            ) : (
              <ChevronLeft className="h-3.5 w-3.5" />
            )}
          </Button>

          {/* Checklist content */}
          <div className={cn(
            "transition-all duration-300",
            checklistExpanded ? "opacity-100" : "opacity-0 pointer-events-none w-0 overflow-hidden"
          )}>
            <div className="p-4 rounded-2xl border bg-card shadow-sm">
              <OnboardingChecklist showPostOnboarding={currentStep === "complete"} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function isValidStep(step: string): step is OnboardingStep {
  return ["welcome", "github", "repo", "first-spec", "plan", "complete"].includes(step)
}
