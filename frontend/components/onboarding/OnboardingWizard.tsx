"use client"

import { useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import { useOnboarding, type OnboardingStep } from "@/hooks/useOnboarding"
import { WelcomeStep } from "./steps/WelcomeStep"
import { GitHubStep } from "./steps/GitHubStep"
import { RepoSelectStep } from "./steps/RepoSelectStep"
import { FirstSpecStep } from "./steps/FirstSpecStep"
import { PlanSelectStep } from "./steps/PlanSelectStep"
import { CompleteStep } from "./steps/CompleteStep"

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
    <div className="w-full max-w-lg mx-auto space-y-6">
      {/* Header with progress */}
      <div className="space-y-4">
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
  )
}

function isValidStep(step: string): step is OnboardingStep {
  return ["welcome", "github", "repo", "first-spec", "plan", "complete"].includes(step)
}
