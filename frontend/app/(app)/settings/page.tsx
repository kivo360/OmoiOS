"use client"

import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { User, Key, Shield, Palette, Bell, Globe } from "lucide-react"

const settingsLinks = [
  {
    href: "/settings/profile",
    icon: User,
    title: "Profile",
    description: "Manage your personal information and preferences",
  },
  {
    href: "/settings/api-keys",
    icon: Key,
    title: "API Keys",
    description: "Create and manage API keys for programmatic access",
  },
  {
    href: "/settings/sessions",
    icon: Shield,
    title: "Active Sessions",
    description: "View and manage your active login sessions",
  },
  {
    href: "/settings/preferences",
    icon: Palette,
    title: "Preferences",
    description: "Customize your application experience",
    disabled: true,
  },
  {
    href: "/settings/notifications",
    icon: Bell,
    title: "Notifications",
    description: "Configure notification preferences",
    disabled: true,
  },
  {
    href: "/settings/integrations",
    icon: Globe,
    title: "Integrations",
    description: "Connect third-party services",
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
            className={item.disabled ? "pointer-events-none opacity-50" : ""}
          >
            <Card className="h-full hover:border-primary/50 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                    <item.icon className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <CardTitle className="text-base">{item.title}</CardTitle>
                    {item.disabled && (
                      <span className="text-xs text-muted-foreground">Coming soon</span>
                    )}
                  </div>
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
