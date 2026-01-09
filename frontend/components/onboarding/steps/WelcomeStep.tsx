"use client"

import { Button } from "@/components/ui/button"
import { CardTitle, CardDescription } from "@/components/ui/card"
import { ArrowRight, Moon, Code, GitPullRequest, Sparkles } from "lucide-react"
import { useOnboarding } from "@/hooks/useOnboarding"
import { useAuth } from "@/hooks/useAuth"

export function WelcomeStep() {
  const { nextStep } = useOnboarding()
  const { user } = useAuth()

  const firstName = user?.full_name?.split(" ")[0] || "there"

  const handleGetStarted = () => {
    console.log("Get Started clicked, calling nextStep...")
    nextStep()
    console.log("nextStep called")
  }

  return (
    <div className="space-y-8 text-center">
      {/* Welcome header */}
      <div className="space-y-2">
        <CardTitle className="text-3xl">
          Hey {firstName}! Ready to ship while you sleep?
        </CardTitle>
        <CardDescription className="text-lg">
          Let&apos;s get you set up in under 2 minutes.
        </CardDescription>
      </div>

      {/* How it works - visual steps */}
      <div className="grid gap-4 text-left">
        <StepPreview
          number={1}
          icon={<Code className="h-5 w-5" />}
          title="Describe what to build"
          description="Tell us what feature you want in plain English"
        />
        <StepPreview
          number={2}
          icon={<Moon className="h-5 w-5" />}
          title="Go to sleep"
          description="Agents work through the night writing code"
        />
        <StepPreview
          number={3}
          icon={<GitPullRequest className="h-5 w-5" />}
          title="Wake up to a PR"
          description="Review and merge your completed feature"
        />
      </div>

      {/* Value proposition */}
      <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-1">
          <Sparkles className="h-4 w-4 text-primary" />
          <span>Your time: 5 min</span>
        </div>
        <div className="h-4 w-px bg-border" />
        <div>AI work: 8 hours</div>
        <div className="h-4 w-px bg-border" />
        <div>Result: Feature shipped</div>
      </div>

      {/* CTA */}
      <Button size="lg" onClick={handleGetStarted} className="w-full">
        Let&apos;s Get Started
        <ArrowRight className="ml-2 h-5 w-5" />
      </Button>
    </div>
  )
}

function StepPreview({
  number,
  icon,
  title,
  description,
}: {
  number: number
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="flex items-start gap-4 p-4 rounded-lg bg-muted/50">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary font-semibold">
        {number}
      </div>
      <div className="space-y-1">
        <div className="flex items-center gap-2 font-medium">
          {icon}
          {title}
        </div>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
    </div>
  )
}
