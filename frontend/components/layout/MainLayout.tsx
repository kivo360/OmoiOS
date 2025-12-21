"use client"

import { useState, useEffect, useCallback } from "react"
import { usePathname } from "next/navigation"
import { IconRail, NavSection } from "./IconRail"
import { ContextualPanel } from "./ContextualPanel"
import { MinimalHeader } from "./MinimalHeader"

interface MainLayoutProps {
  children: React.ReactNode
}

export function MainLayout({ children }: MainLayoutProps) {
  const pathname = usePathname()
  const [activeSection, setActiveSection] = useState<NavSection>("command")
  const [isPanelCollapsed, setIsPanelCollapsed] = useState(false)

  // Sync active section with current route
  useEffect(() => {
    if (pathname.startsWith("/command")) setActiveSection("command")
    else if (pathname.startsWith("/projects") || pathname.startsWith("/board")) setActiveSection("projects")
    else if (pathname.startsWith("/sandboxes") || pathname.startsWith("/sandbox/")) setActiveSection("sandboxes")
    else if (pathname.startsWith("/phases")) setActiveSection("phases")
    else if (pathname.startsWith("/analytics")) setActiveSection("analytics")
    else if (pathname.startsWith("/organizations")) setActiveSection("organizations")
    else if (pathname.startsWith("/settings")) setActiveSection("settings")
  }, [pathname])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check for Cmd/Ctrl key
      if (e.metaKey || e.ctrlKey) {
        switch (e.key) {
          case "1":
            e.preventDefault()
            setActiveSection("command")
            break
          case "2":
            e.preventDefault()
            setActiveSection("projects")
            break
          case "3":
            e.preventDefault()
            setActiveSection("sandboxes")
            break
          case "4":
            e.preventDefault()
            setActiveSection("analytics")
            break
          case "b":
            e.preventDefault()
            setIsPanelCollapsed((prev) => !prev)
            break
        }
      }
    }

    window.addEventListener("keydown", handleKeyDown)
    return () => window.removeEventListener("keydown", handleKeyDown)
  }, [])

  const handleSectionChange = useCallback((section: NavSection) => {
    setActiveSection(section)
  }, [])

  const handleTogglePanel = useCallback(() => {
    setIsPanelCollapsed((prev) => !prev)
  }, [])

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Icon Rail */}
      <IconRail
        activeSection={activeSection}
        onSectionChange={handleSectionChange}
      />

      {/* Contextual Panel */}
      <ContextualPanel
        activeSection={activeSection}
        pathname={pathname}
        isCollapsed={isPanelCollapsed}
        onToggleCollapse={handleTogglePanel}
      />

      {/* Main Content Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <MinimalHeader />

        {/* Page Content */}
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  )
}
