"use client"

import { use } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import {
  ArrowLeft,
  ExternalLink,
  Terminal,
  GitCommit,
  MessageSquare,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Bot,
  Send,
} from "lucide-react"
import { useAgent, useAgentHealth } from "@/hooks/useAgents"

interface AgentDetailPageProps {
  params: Promise<{ agentId: string }>
}

const statusConfig: Record<string, { icon: typeof Loader2; color: string; iconClass: string; label: string }> = {
  healthy: { icon: CheckCircle, color: "success", iconClass: "", label: "Healthy" },
  unhealthy: { icon: XCircle, color: "destructive", iconClass: "", label: "Unhealthy" },
  stale: { icon: AlertCircle, color: "warning", iconClass: "", label: "Stale" },
  available: { icon: CheckCircle, color: "success", iconClass: "", label: "Available" },
  busy: { icon: Loader2, color: "warning", iconClass: "animate-spin", label: "Busy" },
  offline: { icon: XCircle, color: "destructive", iconClass: "", label: "Offline" },
}

export default function AgentDetailPage({ params }: AgentDetailPageProps) {
  const { agentId } = use(params)
  const { data: agent, isLoading, error } = useAgent(agentId)
  const { data: health } = useAgentHealth(agentId)

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-[calc(100vh-48px)] flex-col">
        <div className="border-b border-border p-4">
          <Skeleton className="h-4 w-32 mb-2" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-6" />
            <Skeleton className="h-7 w-48" />
          </div>
        </div>
        <div className="flex-1 p-6">
          <Skeleton className="h-[400px] w-full" />
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    return (
      <div className="container mx-auto p-6 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
        <h1 className="mt-4 text-2xl font-bold">Failed to load agent</h1>
        <p className="mt-2 text-muted-foreground">
          {error instanceof Error ? error.message : "An error occurred"}
        </p>
        <Button className="mt-4" asChild>
          <Link href="/agents">Back to Agents</Link>
        </Button>
      </div>
    )
  }

  if (!agent) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold">Agent not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/agents">Back to Agents</Link>
        </Button>
      </div>
    )
  }

  const healthStatus = health?.health_status || agent.health_status || "available"
  const config = statusConfig[healthStatus] || statusConfig.available
  const StatusIcon = config.icon

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col">
      {/* Header */}
      <div className="border-b border-border p-4">
        <div className="flex items-start justify-between">
          <div>
            <Link
              href="/agents"
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Agents
            </Link>
            <div className="mt-2 flex items-center gap-3">
              <Bot className="h-6 w-6" />
              <h1 className="text-xl font-bold">{agent.agent_id}</h1>
              <Badge variant={config.color as "default" | "destructive" | "secondary" | "outline"}>
                <StatusIcon className={`mr-1 h-3 w-3 ${config.iconClass}`} />
                {config.label}
              </Badge>
              <Badge variant="outline">{agent.agent_type}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              Phase: {agent.phase_id} • Capabilities: {agent.capabilities?.join(", ") || "None"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" asChild>
              <a href="#" target="_blank" rel="noopener noreferrer">
                Open in Cursor <ExternalLink className="ml-2 h-4 w-4" />
              </a>
            </Button>
            <Button variant="outline" asChild>
              <Link href={`/agents/${agentId}/workspace`}>
                <Terminal className="mr-2 h-4 w-4" /> Workspace
              </Link>
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Main Content */}
        <div className="flex-1 overflow-auto p-6">
          <Tabs defaultValue="details" className="space-y-4">
            <TabsList>
              <TabsTrigger value="details">Details</TabsTrigger>
              <TabsTrigger value="health">Health</TabsTrigger>
              <TabsTrigger value="activity">Activity</TabsTrigger>
            </TabsList>

            <TabsContent value="details" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Agent Information</CardTitle>
                  <CardDescription>Configuration and status details</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Agent ID</p>
                      <p className="text-sm font-mono">{agent.agent_id}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Agent Type</p>
                      <p className="text-sm">{agent.agent_type}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Phase</p>
                      <p className="text-sm">{agent.phase_id}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Status</p>
                      <p className="text-sm capitalize">{agent.status || "Unknown"}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Health Status</p>
                      <p className="text-sm capitalize">{agent.health_status || "Unknown"}</p>
                    </div>
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Last Heartbeat</p>
                      <p className="text-sm">
                        {agent.last_heartbeat 
                          ? new Date(agent.last_heartbeat).toLocaleString() 
                          : "Never"}
                      </p>
                    </div>
                    <div className="md:col-span-2">
                      <p className="text-sm font-medium text-muted-foreground">Capabilities</p>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {agent.capabilities?.map((cap) => (
                          <Badge key={cap} variant="outline">{cap}</Badge>
                        )) || <span className="text-sm text-muted-foreground">None configured</span>}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="health" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Health Metrics</CardTitle>
                  <CardDescription>Current health status and metrics</CardDescription>
                </CardHeader>
                <CardContent>
                  {health ? (
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Health Status</p>
                        <Badge 
                          variant={health.health_status === "healthy" ? "default" : "destructive"}
                          className="mt-1"
                        >
                          {health.health_status}
                        </Badge>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Last Heartbeat</p>
                        <p className="text-sm">
                          {health.last_heartbeat 
                            ? new Date(health.last_heartbeat).toLocaleString() 
                            : "Never"}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Seconds Since Heartbeat</p>
                        <p className="text-sm">{health.seconds_since_heartbeat ?? "N/A"}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Is Stale</p>
                        <Badge variant={health.is_stale ? "destructive" : "default"} className="mt-1">
                          {health.is_stale ? "Yes" : "No"}
                        </Badge>
                      </div>
                    </div>
                  ) : (
                    <p className="text-sm text-muted-foreground">
                      No health data available for this agent.
                    </p>
                  )}
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="activity" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Agent Activity</CardTitle>
                  <CardDescription>Recent activity log (placeholder)</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Activity tracking will be available once the agent starts processing tasks.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Info Sidebar */}
        <div className="w-[350px] border-l border-border flex flex-col">
          <div className="border-b border-border p-4">
            <h2 className="font-semibold flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Quick Actions
            </h2>
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              <div className="rounded-lg bg-muted p-3">
                <p className="text-sm font-medium">Agent Status</p>
                <p className="text-xs text-muted-foreground mt-1 capitalize">
                  {agent.status || "Unknown"}
                </p>
              </div>
              <div className="rounded-lg bg-muted p-3">
                <p className="text-sm font-medium">Health</p>
                <p className="text-xs text-muted-foreground mt-1 capitalize">
                  {agent.health_status || "Unknown"}
                </p>
              </div>
              {agent.last_heartbeat && (
                <div className="rounded-lg bg-muted p-3">
                  <p className="text-sm font-medium">Last Active</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {new Date(agent.last_heartbeat).toLocaleString()}
                  </p>
                </div>
              )}
            </div>
          </ScrollArea>
          <div className="border-t border-border p-4">
            <div className="flex gap-2">
              <Textarea
                placeholder="Send command to agent..."
                className="min-h-[60px] resize-none"
              />
              <Button size="icon" className="shrink-0">
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
