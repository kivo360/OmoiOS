"use client"

import Link from "next/link"
import { ArrowRight, Activity, Shield, AlertTriangle, Loader2, Cpu } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { useSystemHealth, useDashboardSummary, useAnomalies } from "@/hooks/useMonitor"
import { useAgents } from "@/hooks/useAgents"

const statusColor = (status: string) => {
  if (status === "healthy" || status === "success" || status === "acknowledged") return "bg-emerald-100 text-emerald-700"
  if (status === "warning" || status === "degraded" || status === "medium") return "bg-amber-100 text-amber-700"
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

export default function HealthOverviewPage() {
  const { data: health, isLoading: healthLoading } = useSystemHealth()
  const { data: dashboard, isLoading: dashboardLoading } = useDashboardSummary()
  const { data: anomalies, isLoading: anomaliesLoading } = useAnomalies({ hours: 24 })
  const { data: agents } = useAgents()

  const isLoading = healthLoading || dashboardLoading

  // Calculate active agents count
  const activeAgents = agents?.filter(
    (a) => a.status === "active" || a.status === "idle"
  ).length ?? 0

  // Calculate open alerts (unacknowledged anomalies)
  const openAlerts = anomalies?.filter((a) => !a.acknowledged_at).length ?? 0

  // Service status derived from health data
  const healthStatus = health?.overall_status ?? "unknown"
  const services = [
    {
      name: "Guardian",
      status: healthStatus === "healthy" ? "healthy" : "degraded",
      message: `Monitoring ${activeAgents} agents`,
      icon: Shield,
    },
    {
      name: "System",
      status: healthStatus,
      message: `Last updated: ${health?.last_updated ? formatTimeAgo(health.last_updated) : "N/A"}`,
      icon: Activity,
    },
    {
      name: "Alerts",
      status: openAlerts > 0 ? "warning" : "healthy",
      message: openAlerts > 0 ? `${openAlerts} anomalies need review` : "No open alerts",
      icon: AlertTriangle,
    },
  ]

  return (
    <div className="container mx-auto p-6 space-y-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">System Health</h1>
          <p className="text-muted-foreground">Guardian, Conductor, and monitoring status</p>
        </div>
        <div className="flex gap-2">
          <Button asChild variant="outline">
            <Link href="/health/settings">Settings</Link>
          </Button>
          <Button asChild>
            <Link href="/health/interventions">
              View Interventions
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>System Status</CardDescription>
            {isLoading ? (
              <Skeleton className="h-9 w-24" />
            ) : (
              <CardTitle className="text-3xl font-bold capitalize">{healthStatus}</CardTitle>
            )}
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <Skeleton className="h-2 w-full" />
            ) : (
              <Progress
                value={healthStatus === "healthy" ? 100 : healthStatus === "degraded" ? 60 : 30}
                className="h-2"
              />
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active Agents</CardDescription>
            {isLoading ? (
              <Skeleton className="h-9 w-16" />
            ) : (
              <CardTitle className="text-3xl font-bold">{dashboard?.active_agents ?? activeAgents}</CardTitle>
            )}
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Monitored in real time</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pending Tasks</CardDescription>
            {isLoading ? (
              <Skeleton className="h-9 w-16" />
            ) : (
              <CardTitle className="text-3xl font-bold">{dashboard?.total_tasks_pending ?? 0}</CardTitle>
            )}
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Tasks awaiting processing</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Open Alerts</CardDescription>
            {anomaliesLoading ? (
              <Skeleton className="h-9 w-16" />
            ) : (
              <CardTitle className="text-3xl font-bold">{openAlerts}</CardTitle>
            )}
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            {dashboard?.recent_anomalies ?? 0} anomalies in 24h
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Service Status</CardTitle>
            <CardDescription>Guardian, Conductor, Discovery health</CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/health/trajectories">View Trajectories</Link>
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {services.map((svc) => (
            <div key={svc.name} className="flex items-center justify-between rounded-lg border p-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <svc.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="font-semibold">{svc.name}</p>
                  <p className="text-sm text-muted-foreground">{svc.message}</p>
                </div>
              </div>
              <Badge className={statusColor(svc.status)} variant="outline">
                {svc.status}
              </Badge>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Anomalies</CardTitle>
            <CardDescription>System anomalies and alerts</CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/activity">Activity Timeline</Link>
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {anomaliesLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : anomalies && anomalies.length > 0 ? (
            anomalies.slice(0, 5).map((anomaly) => (
              <div key={anomaly.anomaly_id} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Badge variant="secondary" className="capitalize">
                    {anomaly.anomaly_type}
                  </Badge>
                  <p className="text-sm">{anomaly.description}</p>
                </div>
                <div className="flex items-center gap-3 text-sm text-muted-foreground">
                  <Badge className={statusColor(anomaly.acknowledged_at ? "acknowledged" : anomaly.severity)} variant="outline">
                    {anomaly.acknowledged_at ? "acknowledged" : anomaly.severity}
                  </Badge>
                  <span>{formatTimeAgo(anomaly.detected_at)}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">No recent anomalies</p>
          )}
        </CardContent>
      </Card>

      <Separator />

      <div className="flex flex-wrap gap-3">
        <Button asChild variant="outline">
          <Link href="/health/resources">
            <Cpu className="mr-2 h-4 w-4" />
            Resource Monitor <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/health/trajectories">
            Trajectory Analysis <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/health/interventions">
            Intervention History <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
        <Button asChild variant="outline">
          <Link href="/health/settings">
            Monitoring Settings <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>
    </div>
  )
}

