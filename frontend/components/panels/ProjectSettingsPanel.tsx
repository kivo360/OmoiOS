"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import {
  Settings,
  Columns3,
  Workflow,
  GitBranch,
  ArrowLeft,
  Check,
  AlertCircle,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Extract project ID from pathname
function getProjectIdFromPath(pathname: string): string | null {
  const match = pathname.match(/\/projects\/([^/]+)/)
  return match ? match[1] : null
}

const settingsItems = [
  {
    href: "",
    label: "General",
    icon: Settings,
    description: "Basic project information",
  },
  {
    href: "/board",
    label: "Board",
    icon: Columns3,
    description: "Kanban board configuration",
  },
  {
    href: "/phases",
    label: "Phases",
    icon: Workflow,
    description: "Workflow phase management",
  },
  {
    href: "/github",
    label: "GitHub",
    icon: GitBranch,
    description: "Repository integration",
  },
]

export function ProjectSettingsPanel() {
  const pathname = usePathname()
  const projectId = getProjectIdFromPath(pathname)
  const basePath = `/projects/${projectId}/settings`

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b px-4 py-3">
        <Link
          href={projectId ? `/projects/${projectId}` : "/projects"}
          className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-3 w-3" />
          Back to Project
        </Link>
        <h2 className="mt-2 text-sm font-semibold">Project Settings</h2>
      </div>

      {/* Settings Navigation */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1">
          {settingsItems.map((item) => {
            const href = `${basePath}${item.href}`
            const isActive = pathname === href
            
            return (
              <Link
                key={item.href}
                href={href}
                className={cn(
                  "flex items-start gap-3 rounded-lg px-3 py-2.5 transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
                )}
              >
                <item.icon className="mt-0.5 h-4 w-4 shrink-0" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-muted-foreground/80 truncate">
                    {item.description}
                  </p>
                </div>
              </Link>
            )
          })}
        </div>
      </ScrollArea>

      {/* Status Footer */}
      <div className="border-t p-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">GitHub</span>
          <Badge variant="outline" className="text-xs gap-1">
            <Check className="h-3 w-3 text-green-500" />
            Connected
          </Badge>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Webhook</span>
          <Badge variant="outline" className="text-xs gap-1">
            <span className="h-2 w-2 rounded-full bg-green-500" />
            Active
          </Badge>
        </div>
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Phases</span>
          <span className="text-muted-foreground">8 configured</span>
        </div>
      </div>
    </div>
  )
}
