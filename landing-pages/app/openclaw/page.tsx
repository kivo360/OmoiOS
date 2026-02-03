"use client"

import {
  OpenClawNavbar,
  OpenClawHeroSection,
  IsThisForYouSection,
  OpenClawFeaturesSection,
  OpenClawCronSection,
  OpenClawConsultingSection,
  OpenClawFooterSection,
  FAQSection,
} from "@/components/openclaw"

export default function OpenClawPage() {
  return (
    <div className="min-h-screen bg-landing-bg">
      <OpenClawNavbar />

      {/* Hero: Your AI Assistant That Handles Clients While You Sleep */}
      <OpenClawHeroSection />

      {/* Problem: Sound familiar? */}
      <IsThisForYouSection />

      {/* Solution: What if your WhatsApp replied for you? */}
      <OpenClawFeaturesSection />

      {/* How It Works: 3 simple steps */}
      <OpenClawCronSection />

      {/* Pricing: $49 / $99 one-time + $29/mo maintenance */}
      <OpenClawConsultingSection />

      {/* FAQ */}
      <FAQSection />

      <OpenClawFooterSection />
    </div>
  )
}
