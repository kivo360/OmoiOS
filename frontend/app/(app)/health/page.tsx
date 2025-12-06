"use client"

import Link from "next/link"
import { ArrowRight, Activity, Shield, AlertTriangle, Bell, BarChart3 } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"

const overview = {
  alignment: 0.86,
  activeAgents: 7,
  interventions24h: 12,
  alerts: 3,
}

const services = [
  { name: "Guardian", status: "healthy", message: "Monitoring 7 agents", icon: Shield },
  { name: "Conductor", status: "healthy", message: "No duplicate work detected", icon: Activity },
  { name: "Discovery", status: "degraded", message: "High latency on similarity search", icon: AlertTriangle },
]

const recent = [
  { id: "int-142", type: "intervention", summary: "Steered worker-5 off idle loop", status: "success", time: "6m ago" },
  { id: "traj-221", type: "trajectory", summary: "Alignment dipped to 0.62 for worker-3", status: "warning", time: "18m ago" },
  { id: "int-139", type: "intervention", summary: "Constraint violation: external package install blocked", status: "success", time: "42m ago" },
  { id: "alert-077", type: "alert", summary: "Conductor flagged duplicate spec work", status: "open", time: "1h ago" },
]

const statusColor = (status: string) => {
  if (status === "healthy" || status === "success") return "bg-emerald-100 text-emerald-700"
  if (status === "warning" || status === "degraded") return "bg-amber-100 text-amber-700"
  return "bg-rose-100 text-rose-700"
}

export default function HealthOverviewPage() {
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
            <CardDescription>Average Alignment</CardDescription>
            <CardTitle className="text-3xl font-bold">{Math.round(overview.alignment * 100)}%</CardTitle>
          </CardHeader>
          <CardContent>
            <Progress value={overview.alignment * 100} className="h-2" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active Agents</CardDescription>
            <CardTitle className="text-3xl font-bold">{overview.activeAgents}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Monitored in real time</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Interventions (24h)</CardDescription>
            <CardTitle className="text-3xl font-bold">{overview.interventions24h}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Guardian + Conductor actions</CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Open Alerts</CardDescription>
            <CardTitle className="text-3xl font-bold">{overview.alerts}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">Need review</CardContent>
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
            <CardTitle>Recent Events</CardTitle>
            <CardDescription>Interventions, trajectory changes, alerts</CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/activity">Activity Timeline</Link>
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {recent.map((item) => (
            <div key={item.id} className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <Badge variant="secondary" className="capitalize">
                  {item.type}
                </Badge>
                <p className="text-sm">{item.summary}</p>
              </div>
              <div className="flex items-center gap-3 text-sm text-muted-foreground">
                <Badge className={statusColor(item.status)} variant="outline">
                  {item.status}
                </Badge>
                <span>{item.time}</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Separator />

      <div className="flex flex-wrap gap-3">
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

