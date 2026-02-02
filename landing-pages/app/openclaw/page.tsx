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
} from "@/components/openclaw"
import { FooterSection } from "@/components/marketing"

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

      <FooterSection />
    </div>
  )
}
