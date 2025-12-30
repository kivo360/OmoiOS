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
  PricingSection,
  FAQSection,
  WaitlistCTASection,
  FooterSection,
} from "@/components/marketing"
import { Announcement, AnnouncementTag, AnnouncementTitle } from "@/components/ui/announcement"
import { ArrowUpRightIcon } from "lucide-react"
import Link from "next/link"

function LandingPage() {
  return (
    <div className="min-h-screen bg-landing-bg">
      {/* Announcement Banner - sticky at top, above navbar */}
      <div className="sticky top-0 z-[5001] flex justify-center bg-landing-bg-muted py-2.5">
        <Link href="https://prompt.omoios.dev/" target="_blank" rel="noopener noreferrer">
          <Announcement themed className="themed cursor-pointer">
            <AnnouncementTag>Free for Limited Time</AnnouncementTag>
            <AnnouncementTitle>
              Try our AI Prompt Generator
              <ArrowUpRightIcon className="h-4 w-4 shrink-0 opacity-60" />
            </AnnouncementTitle>
          </Announcement>
        </Link>
      </div>

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

      {/* Pricing Section */}
      <PricingSection id="pricing" />

      {/* FAQ Section */}
      <FAQSection id="faq" />

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
