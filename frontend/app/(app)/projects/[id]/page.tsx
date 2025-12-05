"use client"

import { use } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  ArrowLeft,
  Settings,
  GitBranch,
  Bot,
  Ticket,
  FileText,
  Activity,
  BarChart3,
  ExternalLink,
  Play,
} from "lucide-react"
import { mockProjects, mockAgents } from "@/lib/mock"

interface ProjectPageProps {
  params: Promise<{ id: string }>
}

export default function ProjectPage({ params }: ProjectPageProps) {
  const { id } = use(params)
  const project = mockProjects.find((p) => p.id === id)
  const projectAgents = mockAgents.filter((a) => a.projectId === id)

  if (!project) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold">Project not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/projects">Back to Projects</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Back Link */}
      <Link
        href="/projects"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Projects
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{project.name}</h1>
            <Badge variant={project.status === "active" ? "default" : "secondary"}>
              {project.status}
            </Badge>
          </div>
          <p className="mt-1 text-muted-foreground">{project.description}</p>
          <div className="mt-2 flex items-center gap-2 text-sm text-muted-foreground">
            <GitBranch className="h-4 w-4" />
            <a
              href={`https://github.com/${project.repo}`}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-foreground hover:underline"
            >
              {project.repo}
              <ExternalLink className="ml-1 inline h-3 w-3" />
            </a>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" asChild>
            <Link href={`/projects/${id}/settings`}>
              <Settings className="mr-2 h-4 w-4" /> Settings
            </Link>
          </Button>
          <Button asChild>
            <Link href={`/agents/spawn?projectId=${id}`}>
              <Play className="mr-2 h-4 w-4" /> Spawn Agent
            </Link>
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Ticket className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{project.ticketCount}</p>
                <p className="text-sm text-muted-foreground">Tickets</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Bot className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{project.activeAgents}</p>
                <p className="text-sm text-muted-foreground">Active Agents</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <FileText className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">3</p>
                <p className="text-sm text-muted-foreground">Specs</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Activity className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">85%</p>
                <p className="text-sm text-muted-foreground">Completion</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-4">
        <Button variant="outline" asChild>
          <Link href={`/board/${id}`}>
            <Ticket className="mr-2 h-4 w-4" /> Kanban Board
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/projects/${id}/specs`}>
            <FileText className="mr-2 h-4 w-4" /> Specifications
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/graph/${id}`}>
            <BarChart3 className="mr-2 h-4 w-4" /> Dependency Graph
          </Link>
        </Button>
        <Button variant="outline" asChild>
          <Link href={`/projects/${id}/explore`}>
            <Activity className="mr-2 h-4 w-4" /> AI Explore
          </Link>
        </Button>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="overview" className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="agents">Agents ({projectAgents.length})</TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Project Progress</CardTitle>
              <CardDescription>Overall completion status</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Requirements</span>
                  <span className="text-muted-foreground">100%</span>
                </div>
                <Progress value={100} />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Design</span>
                  <span className="text-muted-foreground">90%</span>
                </div>
                <Progress value={90} />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Implementation</span>
                  <span className="text-muted-foreground">75%</span>
                </div>
                <Progress value={75} />
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Testing</span>
                  <span className="text-muted-foreground">50%</span>
                </div>
                <Progress value={50} />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="agents" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Project Agents</CardTitle>
              <CardDescription>Agents working on this project</CardDescription>
            </CardHeader>
            <CardContent>
              {projectAgents.length === 0 ? (
                <p className="text-sm text-muted-foreground">No agents have worked on this project yet.</p>
              ) : (
                <div className="space-y-3">
                  {projectAgents.map((agent) => (
                    <div key={agent.id} className="flex items-center justify-between rounded-lg border p-3">
                      <div>
                        <p className="font-medium">{agent.taskName}</p>
                        <p className="text-sm text-muted-foreground">{agent.timeAgo}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={agent.status === "completed" ? "default" : "secondary"}>
                          {agent.status}
                        </Badge>
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/agents/${agent.id}`}>View</Link>
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="activity" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest events in this project</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { message: "Agent completed authentication implementation", time: "2 hours ago" },
                  { message: "New ticket created: Add OAuth2 support", time: "4 hours ago" },
                  { message: "Spec requirements approved", time: "1 day ago" },
                  { message: "Project created", time: "2 days ago" },
                ].map((item, i) => (
                  <div key={i} className="flex items-center gap-4">
                    <div className="h-2 w-2 rounded-full bg-primary" />
                    <p className="flex-1 text-sm">{item.message}</p>
                    <span className="text-sm text-muted-foreground">{item.time}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
