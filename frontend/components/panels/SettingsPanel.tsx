"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
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
  Globe,
  Settings,
  ChevronRight,
} from "lucide-react"

const settingsNav = [
  {
    label: "Account",
    items: [
      { label: "Profile", href: "/settings/profile", icon: User, description: "Personal info" },
      { label: "Security", href: "/settings/security", icon: Shield, description: "Password & 2FA" },
      { label: "Notifications", href: "/settings/notifications", icon: Bell, description: "Alerts" },
      { label: "Appearance", href: "/settings/appearance", icon: Palette, description: "Theme" },
    ],
  },
  {
    label: "Developer",
    items: [
      { label: "API Keys", href: "/settings/api-keys", icon: Key, description: "Access tokens" },
      { label: "Integrations", href: "/settings/integrations", icon: Globe, description: "Coming soon", disabled: true },
    ],
  },
  {
    label: "Organization",
    items: [
      { label: "Team", href: "/organizations", icon: Building2, description: "Members" },
      { label: "Billing", href: "/settings/billing", icon: CreditCard, description: "Coming soon", disabled: true },
    ],
  },
]

export function SettingsPanel() {
  const pathname = usePathname()

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b px-4 py-3">
        <Link
          href="/settings"
          className="flex items-center gap-2 text-sm font-semibold hover:text-primary transition-colors"
        >
          <Settings className="h-4 w-4" />
          Settings
        </Link>
        <p className="mt-1 text-xs text-muted-foreground">Manage your account</p>
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
                const isActive = pathname === item.href || 
                  (item.href !== "/settings" && pathname.startsWith(item.href))
                const isDisabled = item.disabled
                
                return (
                  <Link
                    key={item.href}
                    href={isDisabled ? "#" : item.href}
                    className={cn(
                      "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                      isActive
                        ? "bg-accent text-accent-foreground"
                        : isDisabled
                        ? "opacity-50 cursor-not-allowed"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
                    )}
                    onClick={(e) => isDisabled && e.preventDefault()}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{item.label}</span>
                        {isDisabled && (
                          <Badge variant="secondary" className="text-[10px] px-1 py-0">
                            Soon
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground/80 truncate">
                        {item.description}
                      </p>
                    </div>
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
          className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground transition-colors"
        >
          <HelpCircle className="h-4 w-4" />
          <span>Help & Support</span>
          <ChevronRight className="ml-auto h-4 w-4" />
        </Link>
        <button
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-destructive hover:bg-destructive/10 transition-colors"
          onClick={() => {
            localStorage.removeItem("auth_token")
            window.location.href = "/login"
          }}
        >
          <LogOut className="h-4 w-4" />
          <span>Sign out</span>
        </button>
      </div>
    </div>
  )
}
