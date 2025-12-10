"use client"

import { use, useState, useMemo } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  Clock,
  CheckCircle,
  AlertCircle,
  Bot,
  GitCommit,
  Code,
  DollarSign,
  Calendar,
  BarChart3,
  Activity,
  Zap,
  Target,
  Timer,
  FileCode,
  Download,
} from "lucide-react"
import { useProject, useProjectStats } from "@/hooks/useProjects"
import { useAgents } from "@/hooks/useAgents"
import { useTickets } from "@/hooks/useTickets"
import { PHASES } from "@/lib/phases-config"

interface StatsPageProps {
  params: Promise<{ id: string }>
}

// Phase colors for display
const phaseColors: Record<string, string> = {
  "PHASE_BACKLOG": "#6b7280",
  "PHASE_REQUIREMENTS": "#8b5cf6",
  "PHASE_DESIGN": "#3b82f6",
  "PHASE_IMPLEMENTATION": "#22c55e",
  "PHASE_TESTING": "#f59e0b",
  "PHASE_REVIEW": "#ec4899",
  "PHASE_DONE": "#10b981",
}

export default function StatsPage({ params }: StatsPageProps) {
  const { id: projectId } = use(params)
  const [timeRange, setTimeRange] = useState("7d")

  const { data: project, isLoading: projectLoading, error: projectError } = useProject(projectId)
  const { data: projectStats, isLoading: statsLoading } = useProjectStats(projectId)
  const { data: agentsData } = useAgents()
  const { data: ticketsData } = useTickets()

  const isLoading = projectLoading || statsLoading

  // Calculate stats from real data
  const stats = useMemo(() => {
    if (!projectStats) return null

    const totalTickets = projectStats.total_tickets
    const completedTickets = projectStats.tickets_by_status["done"] || 0
    const inProgress = projectStats.tickets_by_status["in_progress"] || 0
    const blocked = projectStats.tickets_by_status["blocked"] || 0
    const pending = (projectStats.tickets_by_status["open"] || 0) + (projectStats.tickets_by_status["todo"] || 0)
    const completionRate = totalTickets > 0 ? Math.round((completedTickets / totalTickets) * 100) : 0

    return {
      overview: {
        totalTickets,
        completedTickets,
        inProgress,
        blocked,
        pending,
        completionRate,
        avgCycleTime: "N/A",
        velocityTrend: "N/A",
      },
      agents: {
        total: projectStats.active_agents || 0,
        active: projectStats.active_agents || 0,
        idle: 0,
        totalTasks: 0,
        completedTasks: 0,
        avgTaskTime: "N/A",
        topPerformer: "N/A",
      },
      code: {
        totalCommits: projectStats.total_commits || 0,
        linesAdded: 0,
        linesRemoved: 0,
        filesChanged: 0,
        avgCommitsPerDay: 0,
        testCoverage: 0,
        prsMerged: 0,
        prsOpen: 0,
      },
      cost: {
        totalTokens: 0,
        totalCost: 0,
        avgCostPerTicket: 0,
        costTrend: "N/A",
        breakdown: {
          analysis: 0,
          implementation: 0,
          testing: 0,
          documentation: 0,
        },
      },
    }
  }, [projectStats])

  // Calculate tickets by phase from real data
  const ticketsByPhase = useMemo(() => {
    if (!projectStats?.tickets_by_phase) return []
    
    return PHASES.map(phase => ({
      phase: phase.name,
      count: projectStats.tickets_by_phase[phase.id] || 0,
      color: phaseColors[phase.id] || "#6b7280",
    })).filter(p => p.count > 0 || PHASES.find(ph => ph.name === p.phase))
  }, [projectStats])

  // Get project-specific agents
  const projectAgents = useMemo(() => {
    if (!agentsData) return []
    return agentsData.filter(a => a.tags?.includes(`project:${projectId}`))
  }, [agentsData, projectId])

  // Weekly activity placeholder (would need time-series API)
  const weeklyActivity = [
    { day: "Mon", commits: 0, tasks: 0 },
    { day: "Tue", commits: 0, tasks: 0 },
    { day: "Wed", commits: 0, tasks: 0 },
    { day: "Thu", commits: 0, tasks: 0 },
    { day: "Fri", commits: 0, tasks: 0 },
    { day: "Sat", commits: 0, tasks: 0 },
    { day: "Sun", commits: 0, tasks: 0 },
  ]

  const maxBarHeight = Math.max(...weeklyActivity.map((d) => d.commits), 1)

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-7xl p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Skeleton className="h-4 w-24" />
            <div>
              <Skeleton className="h-8 w-48" />
              <Skeleton className="h-4 w-64 mt-2" />
            </div>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (projectError || !project) {
    return (
      <div className="container mx-auto max-w-7xl p-6 text-center">
        <h1 className="text-2xl font-bold">Project not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/projects">Back to Projects</Link>
        </Button>
      </div>
    )
  }

  // Use fallback values if stats not loaded yet
  const displayStats = stats || {
    overview: {
      totalTickets: 0,
      completedTickets: 0,
      inProgress: 0,
      blocked: 0,
      pending: 0,
      completionRate: 0,
      avgCycleTime: "N/A",
      velocityTrend: "N/A",
    },
    agents: {
      total: 0,
      active: 0,
      idle: 0,
      totalTasks: 0,
      completedTasks: 0,
      avgTaskTime: "N/A",
      topPerformer: "N/A",
    },
    code: {
      totalCommits: 0,
      linesAdded: 0,
      linesRemoved: 0,
      filesChanged: 0,
      avgCommitsPerDay: 0,
      testCoverage: 0,
      prsMerged: 0,
      prsOpen: 0,
    },
    cost: {
      totalTokens: 0,
      totalCost: 0,
      avgCostPerTicket: 0,
      costTrend: "N/A",
      breakdown: {
        analysis: 0,
        implementation: 0,
        testing: 0,
        documentation: 0,
      },
    },
  }

  return (
    <div className="container mx-auto max-w-7xl p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href={`/projects/${projectId}`}
            className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Project
          </Link>
          <div>
            <h1 className="text-2xl font-bold">{project.name} Statistics</h1>
            <p className="text-muted-foreground">
              Performance metrics and insights for your project
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[140px]">
              <Calendar className="mr-2 h-4 w-4" />
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="14d">Last 14 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
              <SelectItem value="90d">Last 90 days</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
            <Target className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{displayStats.overview.completionRate}%</div>
            <Progress value={displayStats.overview.completionRate} className="mt-2 h-2" />
            <p className="text-xs text-muted-foreground mt-2">
              {displayStats.overview.completedTickets} of {displayStats.overview.totalTickets} tickets
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Avg Cycle Time</CardTitle>
            <Timer className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{displayStats.overview.avgCycleTime}</div>
            <div className="flex items-center gap-1 mt-2">
              <Badge variant="outline" className="text-green-600">
                <TrendingDown className="mr-1 h-3 w-3" />
                15% faster
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              From ticket creation to completion
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{displayStats.agents.active}</div>
            <div className="flex items-center gap-2 mt-2">
              <span className="text-xs text-muted-foreground">
                {displayStats.agents.idle} idle
              </span>
              <span className="text-xs">•</span>
              <span className="text-xs text-muted-foreground">
                {displayStats.agents.total} total
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {displayStats.agents.completedTasks} tasks completed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${displayStats.cost.totalCost.toFixed(2)}</div>
            <div className="flex items-center gap-1 mt-2">
              <Badge variant="outline" className="text-green-600">
                <TrendingDown className="mr-1 h-3 w-3" />
                {displayStats.cost.costTrend}
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              ${displayStats.cost.avgCostPerTicket.toFixed(2)} avg per ticket
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Tabs for detailed stats */}
      <Tabs defaultValue="tickets" className="space-y-4">
        <TabsList>
          <TabsTrigger value="tickets">
            <CheckCircle className="mr-2 h-4 w-4" />
            Tickets
          </TabsTrigger>
          <TabsTrigger value="agents">
            <Bot className="mr-2 h-4 w-4" />
            Agents
          </TabsTrigger>
          <TabsTrigger value="code">
            <Code className="mr-2 h-4 w-4" />
            Code
          </TabsTrigger>
          <TabsTrigger value="cost">
            <DollarSign className="mr-2 h-4 w-4" />
            Cost
          </TabsTrigger>
        </TabsList>

        {/* Tickets Tab */}
        <TabsContent value="tickets" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            {/* Tickets by Phase */}
            <Card>
              <CardHeader>
                <CardTitle>Tickets by Phase</CardTitle>
                <CardDescription>Distribution across workflow phases</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {ticketsByPhase.map((phase) => (
                    <div key={phase.phase} className="flex items-center gap-3">
                      <div
                        className="h-3 w-3 rounded-full"
                        style={{ backgroundColor: phase.color }}
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium">{phase.phase}</span>
                          <span className="text-sm text-muted-foreground">{phase.count}</span>
                        </div>
                        <Progress
                          value={displayStats.overview.totalTickets > 0 ? (phase.count / displayStats.overview.totalTickets) * 100 : 0}
                          className="h-2"
                          style={
                            {
                              "--progress-background": phase.color,
                            } as React.CSSProperties
                          }
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Ticket Status Summary */}
            <Card>
              <CardHeader>
                <CardTitle>Status Summary</CardTitle>
                <CardDescription>Current ticket status breakdown</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-green-50 dark:bg-green-950/20">
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-4 w-4 text-green-600" />
                        <span className="text-sm">Completed</span>
                      </div>
                      <span className="font-bold text-green-600">
                        {displayStats.overview.completedTickets}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-blue-50 dark:bg-blue-950/20">
                      <div className="flex items-center gap-2">
                        <Activity className="h-4 w-4 text-blue-600" />
                        <span className="text-sm">In Progress</span>
                      </div>
                      <span className="font-bold text-blue-600">
                        {displayStats.overview.inProgress}
                      </span>
                    </div>
                  </div>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 rounded-lg bg-red-50 dark:bg-red-950/20">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="h-4 w-4 text-red-600" />
                        <span className="text-sm">Blocked</span>
                      </div>
                      <span className="font-bold text-red-600">
                        {displayStats.overview.blocked}
                      </span>
                    </div>
                    <div className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-800/20">
                      <div className="flex items-center gap-2">
                        <Clock className="h-4 w-4 text-gray-600" />
                        <span className="text-sm">Pending</span>
                      </div>
                      <span className="font-bold text-gray-600">
                        {displayStats.overview.pending}
                      </span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Velocity Trend</span>
                    <Badge variant="outline" className="text-green-600">
                      <TrendingUp className="mr-1 h-3 w-3" />
                      {displayStats.overview.velocityTrend}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Agents Tab */}
        <TabsContent value="agents" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Agent Performance</CardTitle>
                <CardDescription>Task completion by agent</CardDescription>
              </CardHeader>
              <CardContent>
                {projectAgents.length === 0 ? (
                  <div className="py-6 text-center text-muted-foreground">
                    <Bot className="mx-auto h-12 w-12 text-muted-foreground/30" />
                    <p className="mt-2">No agents assigned to this project</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {projectAgents.map((agent, i) => (
                      <div
                        key={agent.agent_id}
                        className={`p-4 rounded-lg ${i === 0 ? "bg-primary/5 border border-primary/20" : "bg-muted/50"}`}
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <Bot className="h-4 w-4" />
                            <span className="font-medium">{agent.agent_id.slice(0, 8)}</span>
                            {i === 0 && (
                              <Badge variant="default" className="text-xs">
                                <Zap className="mr-1 h-3 w-3" />
                                Top
                              </Badge>
                            )}
                          </div>
                          <Badge variant={agent.status === "active" ? "default" : "secondary"}>
                            {agent.status}
                          </Badge>
                        </div>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Type: </span>
                            <span className="font-medium">{agent.agent_type}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Phase: </span>
                            <span className="font-medium">{agent.phase_id?.replace("PHASE_", "") || "N/A"}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Agent Utilization</CardTitle>
                <CardDescription>Resource usage over time</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Total Tasks Completed</span>
                    <span className="text-2xl font-bold">{displayStats.agents.completedTasks}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Average Task Duration</span>
                    <span className="text-lg font-medium">{displayStats.agents.avgTaskTime}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm">Tasks in Queue</span>
                    <span className="text-lg font-medium">
                      {displayStats.agents.totalTasks - displayStats.agents.completedTasks}
                    </span>
                  </div>
                  <Progress
                    value={displayStats.agents.totalTasks > 0 ? (displayStats.agents.completedTasks / displayStats.agents.totalTasks) * 100 : 0}
                    className="h-3"
                  />
                  <p className="text-xs text-muted-foreground text-center">
                    {displayStats.agents.totalTasks > 0 ? Math.round((displayStats.agents.completedTasks / displayStats.agents.totalTasks) * 100) : 0}%
                    of tasks completed
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Code Tab */}
        <TabsContent value="code" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Code Activity</CardTitle>
                <CardDescription>Weekly commit and task activity</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex items-end justify-between h-40 gap-2">
                  {weeklyActivity.map((day) => (
                    <div key={day.day} className="flex-1 flex flex-col items-center gap-1">
                      <div
                        className="w-full bg-primary/80 rounded-t"
                        style={{ height: `${(day.commits / maxBarHeight) * 100}%` }}
                      />
                      <span className="text-xs text-muted-foreground">{day.day}</span>
                    </div>
                  ))}
                </div>
                <div className="flex items-center justify-center gap-6 mt-4 pt-4 border-t">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded bg-primary/80" />
                    <span className="text-sm text-muted-foreground">Commits</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Code Metrics</CardTitle>
                <CardDescription>Overall code statistics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <GitCommit className="h-4 w-4" />
                      Total Commits
                    </div>
                    <p className="text-2xl font-bold">{displayStats.code.totalCommits}</p>
                  </div>
                  <div className="space-y-1">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <FileCode className="h-4 w-4" />
                      Files Changed
                    </div>
                    <p className="text-2xl font-bold">{displayStats.code.filesChanged}</p>
                  </div>
                  <div className="space-y-1">
                    <div className="text-sm text-muted-foreground">Lines Added</div>
                    <p className="text-xl font-bold text-green-600">
                      +{displayStats.code.linesAdded.toLocaleString()}
                    </p>
                  </div>
                  <div className="space-y-1">
                    <div className="text-sm text-muted-foreground">Lines Removed</div>
                    <p className="text-xl font-bold text-red-600">
                      -{displayStats.code.linesRemoved.toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm">Test Coverage</span>
                    <span className="font-medium">{displayStats.code.testCoverage}%</span>
                  </div>
                  <Progress value={displayStats.code.testCoverage} className="h-2" />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Cost Tab */}
        <TabsContent value="cost" className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Cost Breakdown</CardTitle>
                <CardDescription>Token usage by activity type</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {Object.entries(displayStats.cost.breakdown).map(([key, value]) => (
                    <div key={key} className="flex items-center gap-3">
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium capitalize">{key}</span>
                          <span className="text-sm text-muted-foreground">{value}%</span>
                        </div>
                        <Progress value={value} className="h-2" />
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Usage Summary</CardTitle>
                <CardDescription>Token and cost metrics</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-muted/50">
                    <div className="text-sm text-muted-foreground">Total Tokens Used</div>
                    <p className="text-2xl font-bold">
                      {(displayStats.cost.totalTokens / 1000000).toFixed(2)}M
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="p-4 rounded-lg bg-muted/50">
                      <div className="text-sm text-muted-foreground">Total Cost</div>
                      <p className="text-xl font-bold">${displayStats.cost.totalCost.toFixed(2)}</p>
                    </div>
                    <div className="p-4 rounded-lg bg-muted/50">
                      <div className="text-sm text-muted-foreground">Cost/Ticket</div>
                      <p className="text-xl font-bold">
                        ${displayStats.cost.avgCostPerTicket.toFixed(2)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center justify-between pt-4 border-t">
                    <span className="text-sm text-muted-foreground">Cost Trend (vs last period)</span>
                    <Badge variant="outline" className="text-green-600">
                      <TrendingDown className="mr-1 h-3 w-3" />
                      {displayStats.cost.costTrend}
                    </Badge>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
