"use client"

import { useEffect } from "react"
import { Button } from "@/components/ui/button"
import { CardTitle, CardDescription } from "@/components/ui/card"
import { Github, Shield, GitBranch, Loader2, CheckCircle } from "lucide-react"
import { useOnboarding } from "@/hooks/useOnboarding"

export function GitHubStep() {
  const {
    data,
    isLoading,
    connectGitHub,
    checkGitHubConnection,
    nextStep,
  } = useOnboarding()

  // Check connection status on mount
  useEffect(() => {
    checkGitHubConnection()
  }, [checkGitHubConnection])

  // If already connected, show success and auto-advance
  if (data.githubConnected) {
    return (
      <div className="space-y-6 text-center">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-green-500/10">
          <CheckCircle className="h-8 w-8 text-green-600" />
        </div>

        <div className="space-y-2">
          <CardTitle className="text-2xl">GitHub Connected!</CardTitle>
          <CardDescription>
            Connected as <span className="font-medium text-foreground">@{data.githubUsername}</span>
          </CardDescription>
        </div>

        <Button size="lg" onClick={nextStep} className="w-full">
          Continue to Select Repository
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <CardTitle className="text-2xl">Connect Your Code</CardTitle>
        <CardDescription>
          OmoiOS needs GitHub access to create branches and pull requests for you.
        </CardDescription>
      </div>

      {/* GitHub button */}
      <div className="rounded-xl border-2 border-dashed border-muted-foreground/25 p-8 text-center bg-muted/30">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-[#24292e]">
          <Github className="h-8 w-8 text-white" />
        </div>

        <p className="mt-4 text-sm text-muted-foreground max-w-xs mx-auto">
          Click below to authorize OmoiOS with GitHub. You&apos;ll choose which repos to share.
        </p>

        <Button
          size="lg"
          onClick={connectGitHub}
          disabled={isLoading}
          className="mt-6 w-full max-w-xs bg-[#24292e] hover:bg-[#24292e]/90"
        >
          {isLoading ? (
            <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          ) : (
            <Github className="mr-2 h-5 w-5" />
          )}
          Connect GitHub
        </Button>
      </div>

      {/* Security reassurances */}
      <div className="space-y-3">
        <SecurityItem
          icon={<Shield className="h-4 w-4" />}
          text="You choose which repos we can access"
        />
        <SecurityItem
          icon={<GitBranch className="h-4 w-4" />}
          text="We never push to main without your approval"
        />
        <SecurityItem
          icon={<Github className="h-4 w-4" />}
          text="Disconnect anytime in settings"
        />
      </div>
    </div>
  )
}

function SecurityItem({ icon, text }: { icon: React.ReactNode; text: string }) {
  return (
    <div className="flex items-center gap-3 text-sm text-muted-foreground">
      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
        {icon}
      </div>
      {text}
    </div>
  )
}
