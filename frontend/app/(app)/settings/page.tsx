"use client"

import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { User, Key, Shield, Palette, Bell, Globe, ChevronRight } from "lucide-react"

const settingsLinks = [
  {
    href: "/settings/profile",
    icon: User,
    title: "Profile",
    description: "Manage your personal information, timezone, and language preferences",
  },
  {
    href: "/settings/security",
    icon: Shield,
    title: "Security",
    description: "Change password, enable 2FA, and manage active sessions",
  },
  {
    href: "/settings/notifications",
    icon: Bell,
    title: "Notifications",
    description: "Configure how and when you receive notifications",
  },
  {
    href: "/settings/appearance",
    icon: Palette,
    title: "Appearance",
    description: "Customize theme, colors, fonts, and layout preferences",
  },
  {
    href: "/settings/api-keys",
    icon: Key,
    title: "API Keys",
    description: "Create and manage API keys for programmatic access",
  },
  {
    href: "/settings/integrations",
    icon: Globe,
    title: "Integrations",
    description: "Connect third-party services like GitHub and Slack",
    disabled: true,
  },
]

export default function SettingsPage() {
  return (
    <div className="container mx-auto max-w-4xl p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-muted-foreground">Manage your account and preferences</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {settingsLinks.map((item) => (
          <Link
            key={item.href}
            href={item.disabled ? "#" : item.href}
            className={item.disabled ? "pointer-events-none" : ""}
          >
            <Card className={`h-full transition-all hover:border-primary/50 hover:shadow-sm ${item.disabled ? "opacity-60" : ""}`}>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <item.icon className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-base">{item.title}</CardTitle>
                      {item.disabled && (
                        <Badge variant="secondary" className="text-xs mt-1">
                          Coming soon
                        </Badge>
                      )}
                    </div>
                  </div>
                  {!item.disabled && (
                    <ChevronRight className="h-5 w-5 text-muted-foreground" />
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <CardDescription>{item.description}</CardDescription>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>
    </div>
  )
}
