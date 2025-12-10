"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import { ArrowLeft, ArrowRight, AlertCircle, Bot } from "lucide-react"
import { useAgents, useAgentsHealth } from "@/hooks/useAgents"

const statusColor = (status: string) => {
  if (status === "aligned" || status === "active" || status === "idle") return "bg-emerald-100 text-emerald-700"
  if (status === "warning" || status === "degraded") return "bg-amber-100 text-amber-700"
  if (status === "drifting" || status === "busy") return "bg-orange-100 text-orange-700"
  return "bg-rose-100 text-rose-700"
}

const formatTimeAgo = (dateStr: string | null | undefined) => {
  if (!dateStr) return "N/A"
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

// Map agent status to trajectory status
const mapStatus = (status: string): string => {
  switch (status?.toLowerCase()) {
    case "active":
    case "idle":
      return "aligned"
    case "busy":
      return "drifting"
    case "error":
    case "offline":
      return "stuck"
    default:
      return "warning"
  }
}

export default function TrajectoriesPage() {
  const [filter, setFilter] = useState("all")
  const [search, setSearch] = useState("")
  
  const { data: agents, isLoading } = useAgents()
  const { data: healthData } = useAgentsHealth()

  // Build trajectory rows from agent data
  const trajectories = useMemo(() => {
    if (!agents) return []
    
    return agents.map((agent) => {
      // Find health data for this agent if available
      const health = healthData?.find((h) => h.agent_id === agent.agent_id)
      
      return {
        agentId: agent.agent_id,
        agent: agent.agent_id.slice(0, 12),
        type: agent.agent_type,
        alignment: 0.85, // Placeholder - no alignment score in current API
        status: mapStatus(agent.status),
        rawStatus: agent.status,
        lastEvent: agent.last_heartbeat || agent.created_at,
        note: health?.health_status || `${agent.agent_type} agent`,
        isHealthy: health ? !health.is_stale : true,
      }
    })
  }, [agents, healthData])

  const rows = useMemo(() => {
    return trajectories.filter((t) => {
      const matchesSearch =
        t.agent.toLowerCase().includes(search.toLowerCase()) ||
        t.type.toLowerCase().includes(search.toLowerCase())
      if (filter === "all") return matchesSearch
      return matchesSearch && t.status === filter
    })
  }, [filter, search, trajectories])

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/health">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div className="text-right">
          <h1 className="text-2xl font-bold">Trajectory Analysis</h1>
          <p className="text-muted-foreground">Alignment monitoring per agent</p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Active Trajectories</CardTitle>
            <CardDescription>Alignment score, drift, and idle detection</CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agent or project"
              className="w-[200px]"
            />
            <Select defaultValue="all" onValueChange={setFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Filter status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="aligned">Aligned</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="drifting">Drifting</SelectItem>
                <SelectItem value="stuck">Stuck</SelectItem>
              </SelectContent>
            </Select>
            <Button asChild variant="outline">
              <Link href="/health/interventions">
                Interventions
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-12 items-center rounded-lg bg-muted px-4 py-2 text-sm font-medium text-muted-foreground">
            <div className="col-span-2">Agent</div>
            <div className="col-span-2">Type</div>
            <div className="col-span-3">Status</div>
            <div className="col-span-2">Health</div>
            <div className="col-span-2">Last Active</div>
            <div className="col-span-1 text-right">Action</div>
          </div>
          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No agents match the current filter</p>
            </div>
          ) : (
            rows.map((row) => (
              <div key={row.agentId} className="grid grid-cols-12 items-center rounded-lg border px-4 py-3">
                <div className="col-span-2 font-medium font-mono text-sm">{row.agent}</div>
                <div className="col-span-2 text-muted-foreground capitalize">{row.type}</div>
                <div className="col-span-3 space-y-2">
                  <div className="flex items-center gap-2">
                    <Badge className={statusColor(row.rawStatus)} variant="outline">
                      {row.rawStatus}
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground">{row.note}</p>
                </div>
                <div className="col-span-2">
                  <Badge 
                    className={row.isHealthy ? "bg-emerald-100 text-emerald-700" : "bg-rose-100 text-rose-700"} 
                    variant="outline"
                  >
                    {row.isHealthy ? "Healthy" : "Unhealthy"}
                  </Badge>
                </div>
                <div className="col-span-2 text-sm text-muted-foreground">{formatTimeAgo(row.lastEvent)}</div>
                <div className="col-span-1 flex justify-end">
                  <Button size="sm" variant="outline" asChild>
                    <Link href={`/agents/${row.agentId}`}>Open</Link>
                  </Button>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  )
}

