"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import {
  Workflow,
  Bot,
  CheckCircle2,
  Clock,
  AlertCircle,
  ChevronRight,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Mock phase data for sidebar
const sidebarPhases = [
  {
    id: "PHASE_BACKLOG",
    name: "Backlog",
    taskStats: { total: 45, done: 0, active: 0 },
    activeAgents: 0,
    color: "#6B7280",
  },
  {
    id: "PHASE_REQUIREMENTS",
    name: "Requirements",
    taskStats: { total: 28, done: 22, active: 2 },
    activeAgents: 2,
    color: "#3B82F6",
  },
  {
    id: "PHASE_DESIGN",
    name: "Design",
    taskStats: { total: 18, done: 15, active: 1 },
    activeAgents: 1,
    color: "#8B5CF6",
  },
  {
    id: "PHASE_IMPLEMENTATION",
    name: "Implementation",
    taskStats: { total: 52, done: 38, active: 5 },
    activeAgents: 5,
    color: "#F59E0B",
  },
  {
    id: "PHASE_TESTING",
    name: "Testing",
    taskStats: { total: 24, done: 20, active: 2 },
    activeAgents: 2,
    color: "#10B981",
  },
  {
    id: "PHASE_DEPLOYMENT",
    name: "Deployment",
    taskStats: { total: 12, done: 10, active: 1 },
    activeAgents: 1,
    color: "#EC4899",
  },
  {
    id: "PHASE_DONE",
    name: "Done",
    taskStats: { total: 120, done: 120, active: 0 },
    activeAgents: 0,
    color: "#059669",
  },
]

export function PhasesPanel() {
  const pathname = usePathname()
  
  const totalAgents = sidebarPhases.reduce((sum, p) => sum + p.activeAgents, 0)
  const totalTasks = sidebarPhases.reduce((sum, p) => sum + p.taskStats.total, 0)
  const totalDone = sidebarPhases.reduce((sum, p) => sum + p.taskStats.done, 0)

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b px-4 py-3">
        <h2 className="text-sm font-semibold">Workflow Phases</h2>
        <p className="text-xs text-muted-foreground">
          {totalAgents} agents active
        </p>
      </div>

      {/* Quick Stats */}
      <div className="border-b px-4 py-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-muted-foreground">Overall Progress</span>
          <span className="font-medium">{Math.round((totalDone / totalTasks) * 100)}%</span>
        </div>
        <Progress value={(totalDone / totalTasks) * 100} className="h-1.5" />
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>{totalDone} done</span>
          <span>{totalTasks - totalDone} remaining</span>
        </div>
      </div>

      {/* Phase List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-1">
          {sidebarPhases.map((phase) => {
            const isActive = pathname === `/phases/${phase.id}`
            const completionPercent = phase.taskStats.total > 0
              ? Math.round((phase.taskStats.done / phase.taskStats.total) * 100)
              : 0
            
            return (
              <Link
                key={phase.id}
                href={`/phases/${phase.id}`}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2.5 transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
                )}
              >
                <div
                  className="h-3 w-3 rounded-full shrink-0"
                  style={{ backgroundColor: phase.color }}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <p className="text-sm font-medium truncate">{phase.name}</p>
                    {phase.activeAgents > 0 && (
                      <Badge variant="secondary" className="text-[10px] h-4 px-1">
                        <Bot className="h-2.5 w-2.5 mr-0.5" />
                        {phase.activeAgents}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <Progress value={completionPercent} className="h-1 flex-1" />
                    <span className="text-[10px] text-muted-foreground w-8 text-right">
                      {completionPercent}%
                    </span>
                  </div>
                </div>
              </Link>
            )
          })}
        </div>
      </ScrollArea>

      {/* Quick Actions */}
      <div className="border-t p-3 space-y-2">
        <Link
          href="/phases/gates"
          className={cn(
            "flex items-center justify-between rounded-lg px-3 py-2 text-sm transition-colors",
            pathname === "/phases/gates"
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
          )}
        >
          <div className="flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span>Gate Approvals</span>
          </div>
          <Badge variant="secondary" className="text-xs">3</Badge>
        </Link>
        <Link
          href="/phases"
          className={cn(
            "flex items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors",
            pathname === "/phases"
              ? "bg-accent text-accent-foreground"
              : "text-muted-foreground hover:bg-accent/50 hover:text-accent-foreground"
          )}
        >
          <Workflow className="h-4 w-4" />
          <span>View All Phases</span>
          <ChevronRight className="ml-auto h-4 w-4" />
        </Link>
      </div>
    </div>
  )
}
