"use client"

import { use } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import {
  ArrowLeft,
  ExternalLink,
  Terminal,
  GitCommit,
  MessageSquare,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Bot,
  Send,
} from "lucide-react"
import { mockAgents } from "@/lib/mock"
import { LineChanges } from "@/components/custom"

interface AgentDetailPageProps {
  params: Promise<{ agentId: string }>
}

const statusConfig = {
  running: { icon: Loader2, color: "warning", iconClass: "animate-spin", label: "Running" },
  completed: { icon: CheckCircle, color: "success", iconClass: "", label: "Completed" },
  failed: { icon: XCircle, color: "destructive", iconClass: "", label: "Failed" },
  blocked: { icon: AlertCircle, color: "warning", iconClass: "", label: "Blocked" },
}

// Mock agent activity
const mockActivity = [
  { id: "1", type: "thought", content: "Analyzing the codebase structure...", time: "2 min ago" },
  { id: "2", type: "action", content: "Explored 15 files in src/", time: "3 min ago" },
  { id: "3", type: "thought", content: "I'll need to modify the authentication module...", time: "4 min ago" },
  { id: "4", type: "code", content: "Created src/auth/jwt.ts", time: "5 min ago" },
  { id: "5", type: "code", content: "Modified src/middleware/auth.ts", time: "6 min ago" },
  { id: "6", type: "thought", content: "Testing the implementation...", time: "7 min ago" },
]

export default function AgentDetailPage({ params }: AgentDetailPageProps) {
  const { agentId } = use(params)
  const agent = mockAgents.find((a) => a.id === agentId)

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

  const config = statusConfig[agent.status]
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
              <h1 className="text-xl font-bold">{agent.taskName}</h1>
              <Badge variant={config.color as any}>
                <StatusIcon className={`mr-1 h-3 w-3 ${config.iconClass}`} />
                {config.label}
              </Badge>
            </div>
            {agent.repoName && (
              <p className="mt-1 text-sm text-muted-foreground">{agent.repoName}</p>
            )}
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
          <Tabs defaultValue="activity" className="space-y-4">
            <TabsList>
              <TabsTrigger value="activity">Activity</TabsTrigger>
              <TabsTrigger value="commits">Commits</TabsTrigger>
              <TabsTrigger value="reasoning">Reasoning</TabsTrigger>
            </TabsList>

            <TabsContent value="activity" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Agent Activity</CardTitle>
                  <CardDescription>Real-time agent thoughts and actions</CardDescription>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-[400px]">
                    <div className="space-y-4">
                      {mockActivity.map((item) => (
                        <div key={item.id} className="flex gap-3">
                          <div className={`mt-1 h-2 w-2 rounded-full ${
                            item.type === "thought" ? "bg-info" :
                            item.type === "action" ? "bg-warning" :
                            "bg-success"
                          }`} />
                          <div className="flex-1">
                            <p className="text-sm">{item.content}</p>
                            <p className="text-xs text-muted-foreground">{item.time}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </ScrollArea>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="commits" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Code Changes</CardTitle>
                  <CardDescription>Commits made by this agent</CardDescription>
                </CardHeader>
                <CardContent>
                  {(agent.additions || agent.deletions) && (
                    <div className="mb-4">
                      <LineChanges
                        additions={agent.additions || 0}
                        deletions={agent.deletions || 0}
                        showLabels
                      />
                    </div>
                  )}
                  <div className="space-y-3">
                    {[
                      { sha: "abc1234", message: "feat: Add JWT authentication", time: "2 hours ago" },
                      { sha: "def5678", message: "fix: Token validation bug", time: "3 hours ago" },
                    ].map((commit) => (
                      <div key={commit.sha} className="flex items-center gap-3 rounded-lg border p-3">
                        <GitCommit className="h-4 w-4 text-muted-foreground" />
                        <div className="flex-1">
                          <p className="text-sm font-medium">{commit.message}</p>
                          <p className="text-xs text-muted-foreground">
                            {commit.sha} • {commit.time}
                          </p>
                        </div>
                        <Button variant="outline" size="sm">View</Button>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="reasoning" className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle>Diagnostic Reasoning</CardTitle>
                  <CardDescription>Understanding why decisions were made</CardDescription>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground">
                    Reasoning chain and decision tree will be displayed here.
                  </p>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>

        {/* Chat Sidebar */}
        <div className="w-[350px] border-l border-border flex flex-col">
          <div className="border-b border-border p-4">
            <h2 className="font-semibold flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Follow-ups
            </h2>
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              <div className="rounded-lg bg-muted p-3">
                <p className="text-sm">Agent started working on the task...</p>
                <p className="text-xs text-muted-foreground mt-1">{agent.timeAgo}</p>
              </div>
            </div>
          </ScrollArea>
          <div className="border-t border-border p-4">
            <div className="flex gap-2">
              <Textarea
                placeholder="Ask follow-up questions..."
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
