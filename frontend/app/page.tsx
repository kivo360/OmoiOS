"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { ArrowRight, Bot, GitBranch, Zap, Shield } from "lucide-react"
import { TicketJourney } from "@/components/landing/TicketJourney"
import { WorkflowDiagram } from "@/components/landing/WorkflowDiagram"
import { NightShiftLog } from "@/components/landing/NightShiftLog"

const features = [
  {
    icon: Bot,
    title: "Autonomous Agents",
    description: "AI agents that understand context and execute complex tasks independently.",
  },
  {
    icon: Zap,
    title: "Phase-Based Workflows",
    description: "Adaptive workflows that guide agents through requirements, design, and implementation.",
  },
  {
    icon: GitBranch,
    title: "GitHub Integration",
    description: "Seamlessly connect to your repositories and manage code changes.",
  },
  {
    icon: Shield,
    title: "Spec-Driven",
    description: "Define specifications and let agents handle the implementation details.",
  },
]

function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <Link href="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
              <span className="text-sm font-bold text-primary-foreground">O</span>
            </div>
            <span className="font-semibold">OmoiOS</span>
          </Link>
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
            <Button size="sm" asChild>
              <Link href="/register">Get started</Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Hero */}
      <main className="container mx-auto px-4 py-20">
        <section className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
            Build software with
            <span className="block text-primary">autonomous AI agents</span>
          </h1>
          <p className="mt-6 text-lg text-muted-foreground">
            OmoiOS orchestrates multiple AI agents through adaptive, phase-based workflows
            to build software from requirements to deployment.
          </p>
          <div className="mt-10 flex items-center justify-center gap-4">
            <Button size="lg" asChild>
              <Link href="/register">
                Start building <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
            <Button variant="ghost" size="lg" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        </section>

        {/* Features */}
        <section className="mx-auto mt-32 max-w-5xl">
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => (
              <Card
                key={feature.title}
                className="transition-all hover:bg-accent"
              >
                <CardHeader className="pb-2">
                  <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
                    <feature.icon className="h-5 w-5 text-primary" />
                  </div>
                  <CardTitle className="mt-4 text-base">{feature.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Workflow Diagram Section */}
        <section className="mx-auto mt-32 max-w-5xl">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-bold tracking-tight">
              How It Works
            </h2>
            <p className="mt-4 text-muted-foreground">
              From a single input to a production-ready pull request—orchestrated by specialized agents.
            </p>
          </div>
          <WorkflowDiagram />
        </section>

        {/* Ticket Journey Section */}
        <section className="mx-auto mt-32 max-w-5xl">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-bold tracking-tight">
              Watch a Ticket Come to Life
            </h2>
            <p className="mt-4 text-muted-foreground">
              See how a single feature request flows through autonomous phases—from
              requirements to production.
            </p>
          </div>
          <Card className="bg-muted/50 p-6">
            <TicketJourney
              autoPlay={true}
              speed="normal"
              showPhaseInstructions={true}
              showFeedbackLoops={true}
            />
          </Card>
        </section>

        {/* Night Shift Section */}
        <section className="mx-auto mt-32 max-w-3xl">
          <div className="mb-12 text-center">
            <h2 className="text-3xl font-bold tracking-tight">
              While You Sleep
            </h2>
            <p className="mt-4 text-muted-foreground">
              Wake up to completed tasks. Agents work autonomously through the night.
            </p>
          </div>
          <NightShiftLog autoPlay={true} />
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border py-8">
        <div className="container mx-auto px-4 text-center text-sm text-muted-foreground">
          © {new Date().getFullYear()} OmoiOS. All rights reserved.
        </div>
      </footer>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="space-y-4 text-center">
        <Skeleton className="mx-auto h-12 w-12 rounded-lg" />
        <Skeleton className="h-4 w-32" />
      </div>
    </div>
  )
}

export default function RootPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)

  useEffect(() => {
    // Check for auth token
    const token = localStorage.getItem("auth_token")
    if (token) {
      setIsAuthenticated(true)
      router.replace("/command")
    } else {
      setIsLoading(false)
    }
  }, [router])

  if (isLoading && isAuthenticated) {
    return <LoadingState />
  }

  return <LandingPage />
}
