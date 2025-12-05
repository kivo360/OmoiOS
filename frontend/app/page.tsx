"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowRight, Bot, GitBranch, Zap, Shield } from "lucide-react"

function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border">
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
        <div className="mx-auto max-w-3xl text-center">
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
            <Button variant="outline" size="lg" asChild>
              <Link href="/login">Sign in</Link>
            </Button>
          </div>
        </div>

        {/* Features */}
        <div className="mx-auto mt-32 max-w-5xl">
          <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 font-semibold">Autonomous Agents</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                AI agents that understand context and execute complex tasks independently.
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
                <Zap className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 font-semibold">Phase-Based Workflows</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Adaptive workflows that guide agents through requirements, design, and implementation.
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
                <GitBranch className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 font-semibold">GitHub Integration</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Seamlessly connect to your repositories and manage code changes.
              </p>
            </div>
            <div className="rounded-lg border border-border bg-card p-6">
              <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <h3 className="mt-4 font-semibold">Spec-Driven</h3>
              <p className="mt-2 text-sm text-muted-foreground">
                Define specifications and let agents handle the implementation details.
              </p>
            </div>
          </div>
        </div>
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
