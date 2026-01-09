"use client"

import Link from "next/link"
import { OmoiOSLogo } from "@/components/ui/omoios-logo"

export default function OnboardingLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col items-center bg-background p-4">
      {/* Logo */}
      <Link href="/" className="my-8">
        <OmoiOSLogo size="xl" />
      </Link>

      {/* Onboarding Content - wider than auth pages */}
      <div className="w-full max-w-4xl flex-1">
        {children}
      </div>

      {/* Footer */}
      <footer className="mt-12 text-center text-sm text-muted-foreground">
        <p>© {new Date().getFullYear()} OmoiOS. All rights reserved.</p>
      </footer>
    </div>
  )
}
