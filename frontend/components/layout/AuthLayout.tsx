"use client"

import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { OmoiOSLogo } from "@/components/ui/omoios-logo"

interface AuthLayoutProps {
  children: React.ReactNode
  title: string
  description?: string
  showBackLink?: boolean
  backLinkHref?: string
  backLinkText?: string
}

export function AuthLayout({
  children,
  title,
  description,
  showBackLink = false,
  backLinkHref = "/login",
  backLinkText = "Back to login",
}: AuthLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background p-4">
      {/* Logo */}
      <Link href="/" className="mb-8">
        <OmoiOSLogo size="xl" />
      </Link>

      {/* Auth Card */}
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">{title}</CardTitle>
          {description && (
            <CardDescription>{description}</CardDescription>
          )}
        </CardHeader>
        <CardContent>
          {children}
        </CardContent>
      </Card>

      {/* Back link */}
      {showBackLink && (
        <p className="mt-6 text-sm text-muted-foreground">
          <Link href={backLinkHref} className="hover:text-foreground underline-offset-4 hover:underline">
            {backLinkText}
          </Link>
        </p>
      )}

      {/* Footer */}
      <footer className="mt-12 text-center text-sm text-muted-foreground">
        <p>© {new Date().getFullYear()} OmoiOS. All rights reserved.</p>
      </footer>
    </div>
  )
}
