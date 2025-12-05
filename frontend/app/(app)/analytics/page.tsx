"use client"

import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { FileText, Bot, Ticket, GitCommit, ArrowRight, Plus } from "lucide-react"

// Mock data
const stats = [
  { label: "Active Specs", value: 5, icon: FileText },
  { label: "Active Agents", value: 3, icon: Bot },
  { label: "Open Tickets", value: 12, icon: Ticket },
  { label: "Recent Commits", value: 8, icon: GitCommit },
]

const activeSpecs = [
  { id: "1", name: "Auth System", progress: 80, status: "Executing", agents: 2, repo: "auth-system" },
  { id: "2", name: "Payment Gateway", progress: 60, status: "Design", agents: 1, repo: "payment-gateway" },
  { id: "3", name: "API Service", progress: 40, status: "Tasks", agents: 0, repo: "api-service" },
  { id: "4", name: "Frontend App", progress: 20, status: "Draft", agents: 0, repo: "frontend-app" },
]

const recentActivity = [
  { id: "1", message: 'Spec "Auth System" requirements approved', time: "2h ago", type: "spec" },
  { id: "2", message: 'Agent worker-1 completed task "Setup JWT"', time: "3h ago", type: "agent" },
  { id: "3", message: "Discovery: Bug found in login flow", time: "4h ago", type: "discovery" },
  { id: "4", message: "Guardian intervention sent to worker-2", time: "5h ago", type: "intervention" },
  { id: "5", message: 'Ticket "Add OAuth2" moved to Implementation', time: "6h ago", type: "ticket" },
]

export default function AnalyticsPage() {
  return (
    <div className="container mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">Overview of all projects and activity</p>
        </div>
        <Select defaultValue="all">
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by project" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Projects</SelectItem>
            <SelectItem value="auth">Auth System</SelectItem>
            <SelectItem value="payment">Payment Gateway</SelectItem>
            <SelectItem value="api">API Service</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <stat.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-bold">{stat.value}</p>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Active Specs Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Active Specs</CardTitle>
          <CardDescription>Current specifications in progress</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2">
            {activeSpecs.map((spec) => (
              <Card key={spec.id} className="border">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold">{spec.name}</h3>
                      <p className="text-sm text-muted-foreground">{spec.repo}</p>
                    </div>
                    <Badge variant="secondary">{spec.status}</Badge>
                  </div>
                  <div className="mt-4 space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>Progress</span>
                      <span className="font-medium">{spec.progress}%</span>
                    </div>
                    <Progress value={spec.progress} className="h-2" />
                  </div>
                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">
                      {spec.agents} active agent{spec.agents !== 1 ? "s" : ""}
                    </span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/projects/${spec.id}`}>View</Link>
                      </Button>
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/board/${spec.id}`}>Board</Link>
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest events across all projects</CardDescription>
          </div>
          <Button variant="outline" size="sm">
            View All Activity <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {recentActivity.map((activity) => (
              <div key={activity.id} className="flex items-center gap-4">
                <div className="h-2 w-2 rounded-full bg-primary" />
                <p className="flex-1 text-sm">{activity.message}</p>
                <span className="text-sm text-muted-foreground">{activity.time}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center gap-4">
            <Button asChild>
              <Link href="/projects/new">
                <Plus className="mr-2 h-4 w-4" /> New Spec
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/projects/new">
                <Plus className="mr-2 h-4 w-4" /> New Project
              </Link>
            </Button>
            <Button variant="outline" asChild>
              <Link href="/projects">View All Projects</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
