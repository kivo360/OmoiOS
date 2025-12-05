"use client"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { PanelLeftClose, PanelLeft } from "lucide-react"
import { NavSection } from "./IconRail"
import {
  AgentsPanel,
  ProjectsPanel,
  AnalyticsPanel,
  SettingsPanel,
  OrganizationsPanel,
} from "@/components/panels"

interface ContextualPanelProps {
  activeSection: NavSection
  isCollapsed?: boolean
  onToggleCollapse?: () => void
  className?: string
}

export function ContextualPanel({
  activeSection,
  isCollapsed = false,
  onToggleCollapse,
  className,
}: ContextualPanelProps) {
  const renderPanel = () => {
    switch (activeSection) {
      case "command":
      case "agents":
        return <AgentsPanel />
      case "projects":
        return <ProjectsPanel />
      case "analytics":
        return <AnalyticsPanel />
      case "settings":
        return <SettingsPanel />
      case "organizations":
        return <OrganizationsPanel />
      default:
        return <AgentsPanel />
    }
  }

  if (isCollapsed) {
    return (
      <div className="flex h-full w-0 items-start justify-center overflow-hidden border-r">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="mt-4 h-8 w-8"
        >
          <PanelLeft className="h-4 w-4" />
        </Button>
      </div>
    )
  }

  return (
    <div
      className={cn(
        "flex h-full w-64 flex-col border-r bg-background transition-all duration-200",
        className
      )}
    >
      {/* Collapse Button */}
      <div className="absolute right-2 top-2 z-10">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="h-7 w-7 text-muted-foreground hover:text-foreground"
        >
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>

      {/* Panel Content */}
      <div className="relative flex-1 overflow-hidden pt-1">
        {renderPanel()}
      </div>
    </div>
  )
}
