"use client"

import { usePathname } from "next/navigation"
import Link from "next/link"
import { cn } from "@/lib/utils"
import {
  Terminal,
  FolderGit2,
  Bot,
  BarChart3,
  Settings,
  Building2,
  Workflow,
} from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip"

export type NavSection = "command" | "projects" | "phases" | "agents" | "analytics" | "organizations" | "settings"

interface NavItem {
  id: NavSection
  label: string
  icon: React.ComponentType<{ className?: string }>
  href: string
  badge?: number
  badgeType?: "default" | "warning" | "destructive"
}

const mainNavItems: NavItem[] = [
  { id: "command", label: "Command", icon: Terminal, href: "/command" },
  { id: "projects", label: "Projects", icon: FolderGit2, href: "/projects" },
  { id: "phases", label: "Phases", icon: Workflow, href: "/phases" },
  { id: "agents", label: "Agents", icon: Bot, href: "/agents", badge: 3 },
  { id: "analytics", label: "Analytics", icon: BarChart3, href: "/analytics" },
  { id: "organizations", label: "Organizations", icon: Building2, href: "/organizations" },
]

const bottomNavItems: NavItem[] = [
  { id: "settings", label: "Settings", icon: Settings, href: "/settings" },
]

interface IconRailProps {
  activeSection?: NavSection
  onSectionChange?: (section: NavSection) => void
  className?: string
}

export function IconRail({ activeSection, onSectionChange, className }: IconRailProps) {
  const pathname = usePathname()

  const getActiveSection = (): NavSection => {
    if (activeSection) return activeSection
    if (pathname.startsWith("/command")) return "command"
    if (pathname.startsWith("/projects")) return "projects"
    if (pathname.startsWith("/phases")) return "phases"
    if (pathname.startsWith("/agents") || pathname.startsWith("/board")) return "agents"
    if (pathname.startsWith("/analytics")) return "analytics"
    if (pathname.startsWith("/organizations")) return "organizations"
    if (pathname.startsWith("/settings")) return "settings"
    return "command"
  }

  const currentSection = getActiveSection()

  const handleClick = (item: NavItem) => {
    onSectionChange?.(item.id)
  }

  return (
    <TooltipProvider delayDuration={0}>
      <div
        className={cn(
          "flex h-full w-14 flex-col items-center border-r bg-sidebar py-4",
          className
        )}
      >
        {/* Logo */}
        <Link
          href="/command"
          className="mb-6 flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground font-bold text-lg"
        >
          O
        </Link>

        {/* Main Navigation */}
        <nav className="flex flex-1 flex-col items-center gap-2">
          {mainNavItems.map((item) => {
            const isActive = currentSection === item.id
            const Icon = item.icon

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    onClick={() => handleClick(item)}
                    className={cn(
                      "relative flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                    {item.badge && item.badge > 0 && (
                      <span
                        className={cn(
                          "absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full px-1 text-[10px] font-medium",
                          item.badgeType === "warning"
                            ? "bg-warning text-warning-foreground"
                            : item.badgeType === "destructive"
                            ? "bg-destructive text-destructive-foreground"
                            : "bg-primary text-primary-foreground"
                        )}
                      >
                        {item.badge > 9 ? "9+" : item.badge}
                      </span>
                    )}
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={8}>
                  {item.label}
                </TooltipContent>
              </Tooltip>
            )
          })}
        </nav>

        {/* Bottom Navigation */}
        <nav className="flex flex-col items-center gap-2">
          {bottomNavItems.map((item) => {
            const isActive = currentSection === item.id
            const Icon = item.icon

            return (
              <Tooltip key={item.id}>
                <TooltipTrigger asChild>
                  <Link
                    href={item.href}
                    onClick={() => handleClick(item)}
                    className={cn(
                      "flex h-10 w-10 items-center justify-center rounded-lg transition-colors",
                      isActive
                        ? "bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                    )}
                  >
                    <Icon className="h-5 w-5" />
                  </Link>
                </TooltipTrigger>
                <TooltipContent side="right" sideOffset={8}>
                  {item.label}
                </TooltipContent>
              </Tooltip>
            )
          })}
        </nav>
      </div>
    </TooltipProvider>
  )
}
