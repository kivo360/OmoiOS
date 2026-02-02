"use client"

import {
  OpenClawHeroSection,
  IsThisForYouSection,
  OpenClawFeaturesSection,
  BeforeAfterSection,
  OpenClawCronSection,
  OpenClawConfigSection,
  OpenClawUseCasesSection,
  OpenClawConsultingSection,
} from "@/components/openclaw"
import { MarketingNavbar, FooterSection } from "@/components/marketing"

export default function OpenClawPage() {
  return (
    <div className="min-h-screen bg-landing-bg">
      <MarketingNavbar />

      <OpenClawHeroSection />

      <IsThisForYouSection />

      <OpenClawFeaturesSection />

      <BeforeAfterSection />

      <OpenClawUseCasesSection />

      <OpenClawCronSection />

      <OpenClawConfigSection />

      <OpenClawConsultingSection />

      <FooterSection />
    </div>
  )
}
