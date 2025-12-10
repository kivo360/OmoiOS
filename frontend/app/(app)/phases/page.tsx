"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Workflow,
  Plus,
  Search,
  Ticket,
  Bot,
  ChevronRight,
  CheckCircle2,
  Clock,
  ArrowRight,
  Filter,
  Info,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { PHASES, getPhasesSorted } from "@/lib/phases-config"
import { useTasks } from "@/hooks/useTasks"
import { useAgents } from "@/hooks/useAgents"

export default function PhasesPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [filterStatus, setFilterStatus] = useState("all")
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  // Fetch real data
  const { data: tasks, isLoading: tasksLoading } = useTasks()
  const { data: agents, isLoading: agentsLoading } = useAgents()

  const isLoading = tasksLoading || agentsLoading

  // Compute task stats per phase from real data
  const phaseStats = useMemo(() => {
    const stats: Record<string, { total: number; done: number; active: number; pending: number }> = {}
    
    // Initialize stats for all phases
    PHASES.forEach((phase) => {
      stats[phase.id] = { total: 0, done: 0, active: 0, pending: 0 }
    })

    // Count tasks by phase
    tasks?.forEach((task) => {
      const phaseId = task.phase_id || "PHASE_BACKLOG"
      if (!stats[phaseId]) {
        stats[phaseId] = { total: 0, done: 0, active: 0, pending: 0 }
      }
      stats[phaseId].total++
      
      if (task.status === "completed") {
        stats[phaseId].done++
      } else if (task.status === "in_progress") {
        stats[phaseId].active++
      } else {
        stats[phaseId].pending++
      }
    })

    return stats
  }, [tasks])

  // Count active agents per phase (simplified - counts agents by phase_id if available)
  const agentsByPhase = useMemo(() => {
    const counts: Record<string, number> = {}
    PHASES.forEach((phase) => {
      counts[phase.id] = 0
    })

    agents?.forEach((agent) => {
      if (agent.status === "active" || agent.status === "busy") {
        // Agents don't have phase_id in our data model, so count all active agents
        // This is a simplification - in a real system you might track agent phase assignments
        counts["PHASE_IMPLEMENTATION"] = (counts["PHASE_IMPLEMENTATION"] || 0) + 1
      }
    })

    return counts
  }, [agents])

  // Build enriched phases with real stats
  const enrichedPhases = useMemo(() => {
    return getPhasesSorted().map((phase) => ({
      ...phase,
      taskStats: phaseStats[phase.id] || { total: 0, done: 0, active: 0, pending: 0 },
      activeAgents: agentsByPhase[phase.id] || 0,
    }))
  }, [phaseStats, agentsByPhase])

  const filteredPhases = enrichedPhases.filter((phase) => {
    const matchesSearch = phase.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      phase.description.toLowerCase().includes(searchQuery.toLowerCase())
    
    if (filterStatus === "all") return matchesSearch
    if (filterStatus === "active") return matchesSearch && phase.activeAgents > 0
    if (filterStatus === "terminal") return matchesSearch && phase.isTerminal
    if (filterStatus === "blocked") return matchesSearch && phase.id === "PHASE_BLOCKED"
    return matchesSearch
  })

  const getCompletionPercent = (stats: { total: number; done: number }) => {
    if (stats.total === 0) return 0
    return Math.round((stats.done / stats.total) * 100)
  }

  // Calculate totals
  const totalTasks = Object.values(phaseStats).reduce((sum, s) => sum + s.total, 0)
  const activeAgentsCount = agents?.filter((a) => a.status === "active" || a.status === "busy").length ?? 0

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workflow Phases</h1>
          <p className="text-muted-foreground">
            Configure and manage your project workflow phases
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button variant="outline">
              <Info className="mr-2 h-4 w-4" />
              About Phases
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Workflow Phases</DialogTitle>
              <DialogDescription>
                Phases define the workflow stages that tickets move through.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="rounded-lg bg-muted p-4">
                <p className="text-sm">
                  Phases are system-defined workflow stages. Each phase has:
                </p>
                <ul className="mt-2 text-sm text-muted-foreground list-disc list-inside space-y-1">
                  <li>Done criteria that must be met to proceed</li>
                  <li>Expected outputs (files, reports, etc.)</li>
                  <li>Allowed transitions to other phases</li>
                  <li>Phase-specific prompts for agents</li>
                </ul>
              </div>
              <div className="grid gap-2">
                <p className="text-sm font-medium">Standard Workflow:</p>
                <div className="flex flex-wrap items-center gap-2 text-xs">
                  {PHASES.filter(p => p.id !== "PHASE_BLOCKED").sort((a, b) => a.order - b.order).map((phase, i, arr) => (
                    <span key={phase.id} className="flex items-center gap-1">
                      <Badge variant="secondary" style={{ borderLeftColor: phase.color, borderLeftWidth: 3 }}>
                        {phase.name}
                      </Badge>
                      {i < arr.length - 1 && <ArrowRight className="h-3 w-3 text-muted-foreground" />}
                    </span>
                  ))}
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Workflow className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{PHASES.length}</p>
                <p className="text-sm text-muted-foreground">Total Phases</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                <Bot className="h-5 w-5 text-green-600" />
              </div>
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">{activeAgentsCount}</p>
                )}
                <p className="text-sm text-muted-foreground">Active Agents</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                <Clock className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">
                    {Object.values(phaseStats).reduce((sum, s) => sum + s.active, 0)}
                  </p>
                )}
                <p className="text-sm text-muted-foreground">In Progress</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10">
                <Ticket className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">{totalTasks}</p>
                )}
                <p className="text-sm text-muted-foreground">Total Tasks</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search phases..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[180px]">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Phases</SelectItem>
            <SelectItem value="active">Active (with agents)</SelectItem>
            <SelectItem value="terminal">Terminal Only</SelectItem>
            <SelectItem value="blocked">Blocked Phase</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" asChild>
          <Link href="/phases/gates">
            Phase Gate Approvals
            <ChevronRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>

      {/* Phase Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          // Loading skeletons
          Array.from({ length: 6 }).map((_, i) => (
            <Card key={i} className="h-full">
              <CardHeader className="pb-3">
                <div className="flex items-center gap-3">
                  <Skeleton className="h-10 w-10 rounded-lg" />
                  <div className="space-y-2">
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-3 w-24" />
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-2 w-full" />
                <Skeleton className="h-4 w-24" />
              </CardContent>
            </Card>
          ))
        ) : (
          filteredPhases.map((phase) => {
            const completionPercent = getCompletionPercent(phase.taskStats)
            
            return (
              <Link key={phase.id} href={`/phases/${phase.id}`}>
                <Card className="h-full transition-all hover:shadow-md hover:border-primary/30 cursor-pointer">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className="flex h-10 w-10 items-center justify-center rounded-lg text-white font-bold text-sm"
                          style={{ backgroundColor: phase.color }}
                        >
                          {phase.order}
                        </div>
                        <div>
                          <CardTitle className="text-base">{phase.name}</CardTitle>
                          <p className="text-xs text-muted-foreground font-mono">
                            {phase.id}
                          </p>
                        </div>
                      </div>
                      {phase.isTerminal && (
                        <Badge variant="outline" className="text-xs">Terminal</Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {phase.description}
                    </p>

                    {/* Task Stats */}
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>Tasks</span>
                        <span className="font-medium">
                          {phase.taskStats.done}/{phase.taskStats.total}
                        </span>
                      </div>
                      <Progress value={completionPercent} className="h-2" />
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <div className="flex items-center gap-3">
                          <span className="flex items-center gap-1">
                            <CheckCircle2 className="h-3 w-3 text-green-500" />
                            {phase.taskStats.done} done
                          </span>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3 text-blue-500" />
                            {phase.taskStats.active} active
                          </span>
                        </div>
                        <span>{completionPercent}%</span>
                      </div>
                    </div>

                    {/* Active Agents */}
                    <div className="flex items-center justify-between text-sm">
                      {phase.activeAgents > 0 ? (
                        <span className="flex items-center gap-1 text-green-600">
                          <Bot className="h-4 w-4" />
                          {phase.activeAgents} agents working
                        </span>
                      ) : (
                        <span className="text-muted-foreground">No active agents</span>
                      )}
                    </div>

                    {/* Transitions */}
                    {phase.transitions.length > 0 && (
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <ArrowRight className="h-3 w-3" />
                        <span className="truncate">
                          {phase.transitions.slice(0, 2).map(t => t.replace("PHASE_", "")).join(", ")}
                          {phase.transitions.length > 2 && ` +${phase.transitions.length - 2}`}
                        </span>
                      </div>
                    )}
                  </CardContent>
                </Card>
              </Link>
            )
          })
        )}
      </div>

      {/* Empty State */}
      {filteredPhases.length === 0 && (
        <Card className="py-12">
          <CardContent className="text-center">
            <Workflow className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 font-semibold">No phases found</h3>
            <p className="text-sm text-muted-foreground">
              {searchQuery ? "Try adjusting your search criteria" : "Create a custom phase to get started"}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
