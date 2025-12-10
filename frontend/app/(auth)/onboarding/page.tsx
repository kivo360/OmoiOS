"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { CardDescription, CardTitle } from "@/components/ui/card"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Progress } from "@/components/ui/progress"
import { Loader2, ArrowRight, Building2, User, Github, CheckCircle } from "lucide-react"
import { useAuth } from "@/hooks/useAuth"
import { api } from "@/lib/api/client"

type Step = "role" | "organization" | "github" | "complete"

export default function OnboardingPage() {
  const router = useRouter()
  const { user } = useAuth()
  const [currentStep, setCurrentStep] = useState<Step>("role")
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    role: "",
    organizationName: "",
    organizationType: "personal",
    githubConnected: false,
  })

  const steps: Step[] = ["role", "organization", "github", "complete"]
  const currentStepIndex = steps.indexOf(currentStep)
  const progress = ((currentStepIndex + 1) / steps.length) * 100

  const handleNext = () => {
    const nextIndex = currentStepIndex + 1
    if (nextIndex < steps.length) {
      setCurrentStep(steps[nextIndex])
    }
  }

  const handleSkip = () => {
    handleNext()
  }

  const handleComplete = async () => {
    setIsLoading(true)
    try {
      // Save onboarding data (API endpoint may not exist yet)
      await api.post("/api/v1/users/onboarding", formData).catch(() => {
        // Silently fail if endpoint doesn't exist
        console.log("Onboarding endpoint not available, skipping...")
      })
    } finally {
      setIsLoading(false)
      router.push("/command")
    }
  }

  const connectGitHub = () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:18000"
    window.location.href = `${apiUrl}/api/v1/auth/oauth/github?onboarding=true`
  }

  return (
    <div className="space-y-6">
      {/* Welcome message */}
      {user?.full_name && currentStepIndex === 0 && (
        <div className="text-center text-sm text-muted-foreground">
          Welcome, {user.full_name}! 👋
        </div>
      )}

      {/* Progress */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm text-muted-foreground">
          <span>Step {currentStepIndex + 1} of {steps.length}</span>
          <span>{Math.round(progress)}% complete</span>
        </div>
        <Progress value={progress} className="h-2" />
      </div>

      {/* Step: Role */}
      {currentStep === "role" && (
        <div className="space-y-6">
          <div className="text-center">
            <CardTitle className="text-2xl">What describes you best?</CardTitle>
            <CardDescription>This helps us personalize your experience</CardDescription>
          </div>

          <RadioGroup
            value={formData.role}
            onValueChange={(value) => setFormData({ ...formData, role: value })}
            className="space-y-3"
          >
            {[
              { value: "engineering_manager", label: "Engineering Manager" },
              { value: "senior_engineer", label: "Senior Engineer" },
              { value: "tech_lead", label: "Technical Lead" },
              { value: "developer", label: "Developer" },
              { value: "other", label: "Other" },
            ].map((option) => (
              <div key={option.value} className="flex items-center space-x-3 rounded-md border p-3 hover:bg-accent">
                <RadioGroupItem value={option.value} id={option.value} />
                <Label htmlFor={option.value} className="flex-1 cursor-pointer">
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>

          <div className="flex justify-between">
            <Button variant="ghost" onClick={handleSkip}>Skip</Button>
            <Button onClick={handleNext} disabled={!formData.role}>
              Continue <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step: Organization */}
      {currentStep === "organization" && (
        <div className="space-y-6">
          <div className="text-center">
            <CardTitle className="text-2xl">Set up your workspace</CardTitle>
            <CardDescription>Create an organization to manage your projects</CardDescription>
          </div>

          <div className="space-y-4">
            <RadioGroup
              value={formData.organizationType}
              onValueChange={(value) => setFormData({ ...formData, organizationType: value })}
              className="grid grid-cols-2 gap-4"
            >
              <div className="flex items-center space-x-3 rounded-md border p-4 hover:bg-accent">
                <RadioGroupItem value="personal" id="personal" />
                <Label htmlFor="personal" className="flex cursor-pointer items-center gap-2">
                  <User className="h-4 w-4" />
                  Personal
                </Label>
              </div>
              <div className="flex items-center space-x-3 rounded-md border p-4 hover:bg-accent">
                <RadioGroupItem value="team" id="team" />
                <Label htmlFor="team" className="flex cursor-pointer items-center gap-2">
                  <Building2 className="h-4 w-4" />
                  Team
                </Label>
              </div>
            </RadioGroup>

            {formData.organizationType === "team" && (
              <div className="space-y-2">
                <Label htmlFor="orgName">Organization Name</Label>
                <Input
                  id="orgName"
                  placeholder="Acme Inc."
                  value={formData.organizationName}
                  onChange={(e) => setFormData({ ...formData, organizationName: e.target.value })}
                />
              </div>
            )}
          </div>

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setCurrentStep("role")}>Back</Button>
            <Button onClick={handleNext}>
              Continue <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Step: GitHub */}
      {currentStep === "github" && (
        <div className="space-y-6">
          <div className="text-center">
            <CardTitle className="text-2xl">Connect GitHub</CardTitle>
            <CardDescription>
              Connect your GitHub account to access your repositories
            </CardDescription>
          </div>

          <div className="rounded-lg border p-6 text-center">
            <Github className="mx-auto h-12 w-12 text-muted-foreground" />
            <p className="mt-4 text-sm text-muted-foreground">
              OmoiOS needs access to your repositories to create agents and manage code.
            </p>
            <Button onClick={connectGitHub} className="mt-4 w-full">
              <Github className="mr-2 h-4 w-4" />
              Connect GitHub
            </Button>
          </div>

          <div className="flex justify-between">
            <Button variant="ghost" onClick={() => setCurrentStep("organization")}>Back</Button>
            <Button variant="outline" onClick={handleNext}>
              Skip for now
            </Button>
          </div>
        </div>
      )}

      {/* Step: Complete */}
      {currentStep === "complete" && (
        <div className="space-y-6 text-center">
          <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10">
            <CheckCircle className="h-8 w-8 text-green-600" />
          </div>
          <div>
            <CardTitle className="text-2xl">You&apos;re all set!</CardTitle>
            <CardDescription className="mt-2">
              Your workspace is ready. Start by creating your first project.
            </CardDescription>
          </div>

          <Button onClick={handleComplete} className="w-full" disabled={isLoading}>
            {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Go to Command Center
          </Button>
        </div>
      )}
    </div>
  )
}
