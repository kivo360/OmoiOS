"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { CardTitle, CardDescription } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import {
  CheckCircle,
  ArrowRight,
  Loader2,
  Bell,
  Mail,
  ExternalLink,
  Clock,
} from "lucide-react"
import { useOnboarding } from "@/hooks/useOnboarding"

export function CompleteStep() {
  const { data, completeOnboarding, isLoading } = useOnboarding()

  // Auto-complete onboarding after a short delay to show success state
  useEffect(() => {
    const timer = setTimeout(() => {
      // Don't auto-redirect, let user click
    }, 2000)
    return () => clearTimeout(timer)
  }, [])

  return (
    <div className="space-y-8 text-center">
      {/* Success icon */}
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-green-500/10">
        <CheckCircle className="h-10 w-10 text-green-600" />
      </div>

      {/* Header */}
      <div className="space-y-2">
        <CardTitle className="text-2xl">You&apos;re All Set!</CardTitle>
        <CardDescription className="text-base">
          Your agent is working on your first feature.
          {data.selectedPlan === "lifetime" && (
            <span className="block mt-1 text-emerald-600 font-medium">
              Welcome, Founding Member!
            </span>
          )}
        </CardDescription>
      </div>

      {/* Agent progress preview */}
      {data.firstSpecText && (
        <div className="p-4 rounded-lg bg-muted/50 text-left space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium">Your first feature</span>
            <Clock className="h-4 w-4 text-muted-foreground animate-pulse" />
          </div>
          <p className="text-sm text-muted-foreground line-clamp-2">
            &quot;{data.firstSpecText}&quot;
          </p>
          <Progress value={35} className="h-2" />
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>Planning → Building → Testing → PR</span>
            <span>~45 min</span>
          </div>
        </div>
      )}

      {/* Notification prompt */}
      <div className="space-y-3 p-4 rounded-lg border bg-card">
        <p className="text-sm font-medium">Get notified when your PR is ready</p>
        <div className="flex gap-2 justify-center">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              // Request notification permission
              if ("Notification" in window) {
                Notification.requestPermission()
              }
            }}
          >
            <Bell className="mr-2 h-4 w-4" />
            Browser
          </Button>
          <Button variant="outline" size="sm">
            <Mail className="mr-2 h-4 w-4" />
            Email
          </Button>
        </div>
      </div>

      {/* What's next */}
      <div className="text-left space-y-3">
        <p className="text-sm font-medium">What you can do now:</p>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <span>Watch your agent work in real-time</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <span>Add more features to the queue</span>
          </li>
          <li className="flex items-start gap-2">
            <CheckCircle className="h-4 w-4 text-primary mt-0.5 shrink-0" />
            <span>Invite team members to collaborate</span>
          </li>
        </ul>
      </div>

      {/* CTA */}
      <div className="space-y-3 pt-4">
        <Button size="lg" onClick={completeOnboarding} disabled={isLoading} className="w-full">
          {isLoading ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Loading...
            </>
          ) : data.firstSpecId ? (
            <>
              View Spec Progress
              <ArrowRight className="ml-2 h-5 w-5" />
            </>
          ) : (
            <>
              Go to Command Center
              <ArrowRight className="ml-2 h-5 w-5" />
            </>
          )}
        </Button>

        <p className="text-xs text-muted-foreground">
          You don&apos;t need to watch - come back in the morning for your PR!
        </p>
      </div>
    </div>
  )
}
