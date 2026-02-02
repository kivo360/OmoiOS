"use client"

import {
  OpenClawNavbar,
  OpenClawHeroSection,
  IsThisForYouSection,
  OpenClawFeaturesSection,
  BeforeAfterSection,
  OpenClawCronSection,
  OpenClawConfigSection,
  OpenClawUseCasesSection,
  OpenClawConsultingSection,
  OpenClawFooterSection,
} from "@/components/openclaw"

export default function OpenClawPage() {
  return (
    <div className="min-h-screen bg-landing-bg">
      <OpenClawNavbar />

      <OpenClawHeroSection />

      <IsThisForYouSection />

      <OpenClawFeaturesSection />

      <BeforeAfterSection />

      <OpenClawUseCasesSection />

      <OpenClawCronSection />

      <OpenClawConfigSection />

      <OpenClawConsultingSection />

      <OpenClawFooterSection />
    </div>
  )
}
