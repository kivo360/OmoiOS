"use client"

import { useEffect } from "react"
import { useRouter } from "next/navigation"
import { Skeleton } from "@/components/ui/skeleton"
import {
  MarketingNavbar,
  HeroSection,
  PainPointsSection,
  LogoCloudSection,
  FeaturesSection,
  WorkflowSection,
  ProductShowcaseSection,
  NightShiftSection,
  StatsSection,
  PricingSection,
  FAQSection,
  WaitlistCTASection,
  FooterSection,
} from "@/components/marketing"
import { Announcement, AnnouncementTag, AnnouncementTitle } from "@/components/ui/announcement"
import { ArrowUpRightIcon, Bot, Cpu } from "lucide-react"
import Link from "next/link"

function LandingPage() {
  return (
    <div className="landing-page min-h-screen bg-landing-bg">
      {/* Announcement Banner - sticky at top, above navbar */}
      <div className="sticky top-0 z-[5001] flex justify-center bg-landing-bg-muted py-2.5">
        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link href="https://prompt.omoios.dev/" target="_blank" rel="noopener noreferrer">
            <Announcement themed className="themed cursor-pointer">
              <AnnouncementTag>Free for Limited Time</AnnouncementTag>
              <AnnouncementTitle>
                Try our AI Prompt Generator
                <ArrowUpRightIcon className="h-4 w-4 shrink-0 opacity-60" />
              </AnnouncementTitle>
            </Announcement>
          </Link>
          <Link href="/openclaw" className="flex items-center gap-2 rounded-full bg-landing-accent px-4 py-2 text-sm font-semibold text-white hover:bg-landing-accent-dark transition-colors">
            <Bot className="h-4 w-4" />
            <span>Deploy OpenClaw</span>
          </Link>
        </div>
      </div>

      {/* Floating Navigation */}
      <MarketingNavbar />

      {/* Hero Section */}
      <HeroSection />

      {/* OpenClaw CTA Section */}
      <section className="bg-landing-bg-muted py-12">
        <div className="container mx-auto px-4">
          <div className="mx-auto max-w-3xl rounded-2xl border-landing-border bg-white p-8 shadow-lg">
            <div className="mb-4 flex items-center gap-3">
              <div className="rounded-full bg-landing-accent p-3">
                <Bot className="h-6 w-6 text-white" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-landing-text">OpenClaw - Autonomous Bots</h3>
                <p className="text-sm text-landing-text-muted">Your personal AI assistant running on your devices</p>
              </div>
            </div>
            <p className="mb-6 text-base text-landing-text-muted">
              Deploy OpenClaw bots with proactive interval timers and excellent configurations.
              We handle the deployment so you don't have to lift a finger.
            </p>
            <Link
              href="/openclaw"
              className="landing-gradient-cta landing-card-hover inline-flex items-center justify-center rounded-lg px-8 py-4 font-semibold text-white"
            >
              Explore OpenClaw
              <Cpu className="ml-2 h-5 w-5" />
            </Link>
          </div>
        </div>
      </section>

      {/* Pain Points */}
      <PainPointsSection id="why" />

      {/* Logo Cloud */}
      <LogoCloudSection />

      {/* How It Works - Workflow Section */}
      <WorkflowSection />

      {/* Product Screenshots Showcase */}
      <ProductShowcaseSection id="product" />

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

  // Simple landing page - no auth redirect needed
  return <LandingPage />
}
