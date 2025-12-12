"use client"

import { useState, useMemo } from "react"
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
  Search,
  Plus,
  Bot,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Terminal,
  Zap,
  TrendingUp,
  Heart,
  HeartOff,
} from "lucide-react"
import { useAgents, useAgentStatistics } from "@/hooks/useAgents"

const statusConfig: Record<string, { icon: typeof Bot; color: string; iconClass: string }> = {
  idle: { icon: Clock, color: "secondary", iconClass: "" },
  busy: { icon: Loader2, color: "warning", iconClass: "animate-spin" },
  working: { icon: Loader2, color: "warning", iconClass: "animate-spin" },
  completed: { icon: CheckCircle, color: "success", iconClass: "" },
  failed: { icon: XCircle, color: "destructive", iconClass: "" },
  timeout: { icon: AlertCircle, color: "warning", iconClass: "" },
  maintenance: { icon: AlertCircle, color: "secondary", iconClass: "" },
}

const healthConfig: Record<string, { icon: typeof Heart; color: string }> = {
  healthy: { icon: Heart, color: "success" },
  degraded: { icon: Heart, color: "warning" },
  unhealthy: { icon: HeartOff, color: "destructive" },
}

export default function AgentsPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")

  // Fetch agents and statistics from API
  const { data: agents, isLoading, error } = useAgents()
  const { data: statistics } = useAgentStatistics()

  // Filter agents
  const filteredAgents = useMemo(() => {
    if (!agents) return []
    
    return agents.filter((agent) => {
      const matchesSearch =
        agent.agent_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.agent_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.capabilities.some((c) => c.toLowerCase().includes(searchQuery.toLowerCase()))
    const matchesStatus = statusFilter === "all" || agent.status === statusFilter
    return matchesSearch && matchesStatus
  })
  }, [agents, searchQuery, statusFilter])

  // Calculate metrics from statistics or fallback to counting
  const totalAgents = statistics?.total_agents ?? agents?.length ?? 0
  const activeAgents = statistics?.by_status?.["busy"] ?? statistics?.by_status?.["working"] ?? 0
  const idleAgents = statistics?.by_status?.["idle"] ?? 0
  const healthyAgents = statistics?.by_health?.["healthy"] ?? 0
  const staleCount = statistics?.stale_count ?? 0

  const formatTimeAgo = (dateStr: string | null) => {
    if (!dateStr) return "Never"
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / (1000 * 60))
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Agents</h1>
            <p className="text-muted-foreground">View and manage AI agents</p>
          </div>
        </div>
        <div className="grid gap-4 md:grid-cols-5">
          {[1, 2, 3, 4, 5].map((i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <Skeleton className="h-4 w-20" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-8 w-12" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardHeader>
                <Skeleton className="h-5 w-32" />
                <Skeleton className="h-4 w-48" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-4 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto p-6">
        <Card className="p-12 text-center">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h3 className="mt-4 text-lg font-semibold">Failed to load agents</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {error instanceof Error ? error.message : "An error occurred"}
          </p>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Agents</h1>
          <p className="text-muted-foreground">View and manage AI agents</p>
        </div>
        <Button asChild>
          <Link href="/agents/spawn">
            <Plus className="mr-2 h-4 w-4" /> Spawn Agent
          </Link>
        </Button>
      </div>

      {/* Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Agents</CardTitle>
            <Bot className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalAgents}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active</CardTitle>
            <Zap className="h-4 w-4 text-warning" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-warning">{activeAgents}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Idle</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{idleAgents}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Healthy</CardTitle>
            <Heart className="h-4 w-4 text-success" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-success">{healthyAgents}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Stale</CardTitle>
            <AlertCircle className="h-4 w-4 text-destructive" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">{staleCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="idle">Idle</SelectItem>
            <SelectItem value="busy">Busy</SelectItem>
            <SelectItem value="working">Working</SelectItem>
            <SelectItem value="maintenance">Maintenance</SelectItem>
            <SelectItem value="timeout">Timeout</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Agents Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredAgents.map((agent) => {
          const config = statusConfig[agent.status] || statusConfig.idle
          const StatusIcon = config.icon
          const healthCfg = healthConfig[agent.health_status] || healthConfig.healthy
          const HealthIcon = healthCfg.icon

          return (
            <Card key={agent.agent_id} className="hover:border-primary/50 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Bot className="h-5 w-5 text-muted-foreground" />
                    <div>
                    <CardTitle className="text-base">
                        <Link href={`/agents/${agent.agent_id}`} className="hover:underline">
                          {agent.agent_type}
                      </Link>
                    </CardTitle>
                      <CardDescription className="text-xs font-mono">
                        {agent.agent_id.slice(0, 12)}...
                      </CardDescription>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Badge variant={config.color as "default" | "secondary" | "destructive" | "outline"}>
                    <StatusIcon className={`mr-1 h-3 w-3 ${config.iconClass}`} />
                    {agent.status}
                  </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Capabilities */}
                {agent.capabilities.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {agent.capabilities.slice(0, 3).map((cap) => (
                      <Badge key={cap} variant="outline" className="text-xs">
                        {cap}
                      </Badge>
                    ))}
                    {agent.capabilities.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{agent.capabilities.length - 3}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Health & Phase */}
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <HealthIcon className={`h-3 w-3 text-${healthCfg.color}`} />
                    <span>{agent.health_status}</span>
                  </div>
                  {agent.phase_id && (
                    <span className="truncate text-xs max-w-[140px]" title={agent.phase_id}>
                      {agent.phase_id}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{formatTimeAgo(agent.last_heartbeat)}</span>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/agents/${agent.agent_id}`}>Details</Link>
                    </Button>
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/agents/${agent.agent_id}/workspace`}>
                        <Terminal className="mr-1 h-3 w-3" />
                        Workspace
                      </Link>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Empty State */}
      {filteredAgents.length === 0 && !isLoading && (
        <Card className="p-12 text-center">
          <Bot className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No agents found</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {searchQuery || statusFilter !== "all"
              ? "Try adjusting your search or filters"
              : "Spawn your first agent to get started"}
          </p>
          <Button className="mt-4" asChild>
            <Link href="/agents/spawn">
              <Plus className="mr-2 h-4 w-4" /> Spawn Agent
            </Link>
          </Button>
        </Card>
      )}
    </div>
  )
}
