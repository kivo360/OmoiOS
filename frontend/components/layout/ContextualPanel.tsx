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
  GraphFiltersPanel,
  DiagnosticContextPanel,
  ActivityFiltersPanel,
  ProjectSettingsPanel,
  PhasesPanel,
  HealthPanel,
  TasksPanel,
} from "@/components/panels"

interface ContextualPanelProps {
  activeSection: NavSection
  pathname?: string
  isCollapsed?: boolean
  onToggleCollapse?: () => void
  className?: string
}

export function ContextualPanel({
  activeSection,
  pathname = "",
  isCollapsed = false,
  onToggleCollapse,
  className,
}: ContextualPanelProps) {
  // Route-aware panel selection
  // Specific routes get specialized panels regardless of activeSection
  const renderPanel = () => {
    // Project settings pages get Project Settings panel
    if (pathname.includes("/projects/") && pathname.includes("/settings")) {
      return <ProjectSettingsPanel />
    }

    // Health pages get Health panel
    if (pathname.startsWith("/health")) {
      return <HealthPanel />
    }

    // Graph pages get Graph Filters
    if (pathname.startsWith("/graph")) {
      return <GraphFiltersPanel />
    }

    // Diagnostic pages get Diagnostic Context
    if (pathname.startsWith("/diagnostic")) {
      return <DiagnosticContextPanel />
    }

    // Activity page gets Activity Filters
    if (pathname === "/activity" || pathname.startsWith("/activity")) {
      return <ActivityFiltersPanel />
    }

    // Board pages can use Projects panel for project context
    if (pathname.startsWith("/board")) {
      return <ProjectsPanel />
    }

    // Phases pages get Phases panel
    if (pathname.startsWith("/phases")) {
      return <PhasesPanel />
    }

    // Sandbox pages get Tasks panel
    if (pathname.startsWith("/sandbox")) {
      return <TasksPanel pathname={pathname} />
    }

    // Default: use activeSection-based panels
    switch (activeSection) {
      case "command":
      case "sandboxes":
        // Use TasksPanel for sandbox-first workflow
        return <TasksPanel />
      case "projects":
        return <ProjectsPanel />
      case "phases":
        return <PhasesPanel />
      case "analytics":
        return <AnalyticsPanel />
      case "settings":
        return <SettingsPanel />
      case "organizations":
        return <OrganizationsPanel />
      default:
        return <TasksPanel />
    }
  }

  if (isCollapsed) {
    return (
      <div className="flex h-full w-10 flex-col items-center border-r bg-background pt-3">
        <Button
          variant="ghost"
          size="icon"
          onClick={onToggleCollapse}
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
          title="Expand sidebar"
        >
          <PanelLeft className="h-4 w-4" />
        </Button>
      </div>
    )
  }

  return (
    <div
      className={cn(
        "relative flex h-full w-64 flex-col border-r bg-background transition-all duration-200",
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
          title="Collapse sidebar"
        >
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>

      {/* Panel Content */}
      <div className="flex-1 overflow-hidden pt-1">
        {renderPanel()}
      </div>
    </div>
  )
}
