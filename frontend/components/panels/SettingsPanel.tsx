"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  User,
  Key,
  Shield,
  Bell,
  Palette,
  Building2,
  CreditCard,
  HelpCircle,
  LogOut,
} from "lucide-react"
import { Separator } from "@/components/ui/separator"

const settingsNav = [
  {
    label: "Account",
    items: [
      { label: "Profile", href: "/settings/profile", icon: User },
      { label: "API Keys", href: "/settings/api-keys", icon: Key },
      { label: "Sessions", href: "/settings/sessions", icon: Shield },
      { label: "Notifications", href: "/settings/notifications", icon: Bell },
    ],
  },
  {
    label: "Preferences",
    items: [
      { label: "Appearance", href: "/settings/appearance", icon: Palette },
    ],
  },
  {
    label: "Organization",
    items: [
      { label: "Team", href: "/organizations", icon: Building2 },
      { label: "Billing", href: "/settings/billing", icon: CreditCard },
    ],
  },
]

export function SettingsPanel() {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-3">
        <h3 className="font-semibold">Settings</h3>
        <p className="text-xs text-muted-foreground">Manage your account</p>
      </div>

      {/* Navigation */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {settingsNav.map((section) => (
            <div key={section.label} className="space-y-1">
              <div className="px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {section.label}
              </div>
              {section.items.map((item) => {
                const Icon = item.icon
                const isActive = pathname === item.href
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary font-medium"
                        : "text-muted-foreground hover:bg-accent hover:text-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                )
              })}
            </div>
          ))}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t p-3 space-y-1">
        <Link
          href="/help"
          className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
        >
          <HelpCircle className="h-4 w-4" />
          Help & Support
        </Link>
        <button
          className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm text-destructive hover:bg-destructive/10 transition-colors"
          onClick={() => {
            localStorage.removeItem("auth_token")
            window.location.href = "/login"
          }}
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </div>
  )
}
