"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Skeleton } from "@/components/ui/skeleton"
import {
  MarketingNavbar,
  HeroSection,
  LogoCloudSection,
  FeaturesSection,
  WorkflowSection,
  NightShiftSection,
  StatsSection,
  WaitlistCTASection,
  FooterSection,
} from "@/components/marketing"

function LandingPage() {
  return (
    <div className="min-h-screen bg-landing-bg">
      {/* Floating Navigation */}
      <MarketingNavbar />

      {/* Hero Section */}
      <HeroSection />

      {/* Logo Cloud */}
      <LogoCloudSection />

      {/* How It Works - Workflow Section */}
      <WorkflowSection />

      {/* Features Bento Grid */}
      <FeaturesSection id="features" />

      {/* Night Shift Section */}
      <NightShiftSection />

      {/* Stats Section */}
      <StatsSection />

      {/* Waitlist CTA Section */}
      <WaitlistCTASection />

      {/* Footer */}
      <FooterSection />
    </div>
  )
}

function LoadingState() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-landing-bg">
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
