"use client"

import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Separator } from "@/components/ui/separator"
import { useSystemHealth, useDashboardSummary } from "@/hooks/useMonitor"

const shortcuts = [
  { label: "Overview", href: "/health" },
  { label: "Trajectories", href: "/health/trajectories" },
  { label: "Interventions", href: "/health/interventions" },
  { label: "Settings", href: "/health/settings" },
]

export function HealthPanel() {
  const { data: health, isLoading: healthLoading } = useSystemHealth()
  const { data: dashboard, isLoading: dashboardLoading } = useDashboardSummary()
  
  const isLoading = healthLoading || dashboardLoading
  
  // Compute summary values from API data
  const activeAgents = dashboard?.active_agents ?? 0
  const openAlerts = dashboard?.recent_anomalies ?? 0
  const healthStatus = health?.overall_status ?? "unknown"
  
  // Get status color
  const statusVariant = healthStatus === "healthy" 
    ? "secondary" 
    : healthStatus === "degraded" 
      ? "outline" 
      : "destructive"

  return (
    <div className="flex h-full flex-col">
      <div className="p-4 pb-2">
        <h2 className="text-sm font-semibold">System Health</h2>
        <p className="text-xs text-muted-foreground">Guardian, trajectories, interventions</p>
      </div>

      <div className="px-4 pb-3">
        <Card>
          <CardContent className="p-3 space-y-2">
            {isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-full" />
              </div>
            ) : (
              <>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Status</span>
                  <Badge variant={statusVariant} className="capitalize">
                    {healthStatus}
                  </Badge>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Active agents</span>
                  <span className="font-medium">{activeAgents}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Tasks pending</span>
                  <span className="font-medium">{dashboard?.total_tasks_pending ?? 0}</span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-muted-foreground">Open alerts</span>
                  <Badge variant={openAlerts > 0 ? "destructive" : "secondary"}>
                    {openAlerts}
                  </Badge>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      <Separator />

      <div className="flex-1 overflow-auto px-2 py-3 space-y-1.5">
        {shortcuts.map((item) => (
          <Button key={item.href} variant="ghost" className="w-full justify-start" asChild>
            <Link href={item.href}>{item.label}</Link>
          </Button>
        ))}
      </div>
    </div>
  )
}

