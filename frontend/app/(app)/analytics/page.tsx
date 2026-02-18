"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  FileText,
  Bot,
  Ticket,
  GitCommit,
  ArrowRight,
  Plus,
} from "lucide-react";
import { useProjects } from "@/hooks/useProjects";
import { useAgents } from "@/hooks/useAgents";
import { useTickets } from "@/hooks/useTickets";
import { useDashboardSummary } from "@/hooks/useMonitor";

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffHours / 24);

  if (diffHours < 1) return "just now";
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return `${Math.floor(diffDays / 7)}w ago`;
}

export default function AnalyticsPage() {
  const [projectFilter, setProjectFilter] = useState("all");

  const { data: projectsData, isLoading: projectsLoading } = useProjects();
  const { data: agentsData, isLoading: agentsLoading } = useAgents();
  const { data: ticketsData, isLoading: ticketsLoading } = useTickets();
  const { data: dashboardSummary, isLoading: dashboardLoading } =
    useDashboardSummary();

  const isLoading =
    projectsLoading || agentsLoading || ticketsLoading || dashboardLoading;

  // Calculate stats from real data
  const stats = useMemo(() => {
    const activeProjectsCount =
      projectsData?.projects?.filter((p) => p.status === "active").length || 0;
    const activeAgents =
      agentsData?.filter((a) => a.status === "active").length || 0;
    const tickets = ticketsData?.tickets || [];
    const openTickets = tickets.filter(
      (t) => t.status !== "done" && t.status !== "closed",
    ).length;

    return [
      { label: "Active Projects", value: activeProjectsCount, icon: FileText },
      { label: "Active Agents", value: activeAgents, icon: Bot },
      { label: "Open Tickets", value: openTickets, icon: Ticket },
      {
        label: "Total Agents",
        value: agentsData?.length || 0,
        icon: GitCommit,
      },
    ];
  }, [projectsData, agentsData, ticketsData]);

  // Transform projects to display format
  const activeProjects = useMemo(() => {
    if (!projectsData?.projects) return [];
    const tickets = ticketsData?.tickets || [];
    return projectsData.projects
      .filter((p) => p.status === "active")
      .slice(0, 4)
      .map((p) => {
        const projectTickets = tickets.filter((t) => t.project_id === p.id);
        const doneTickets = projectTickets.filter(
          (t) => t.status === "done" || t.status === "closed",
        ).length;
        const totalTickets = projectTickets.length;
        const progress =
          totalTickets > 0 ? Math.round((doneTickets / totalTickets) * 100) : 0;
        const projectAgents =
          agentsData?.filter((a) => a.tags?.includes(`project:${p.id}`))
            .length || 0;

        return {
          id: p.id,
          name: p.name,
          progress,
          status: p.status,
          agents: projectAgents,
          repo: p.github_repo || "No repo",
        };
      });
  }, [projectsData, ticketsData, agentsData]);

  // Recent activity from tickets
  const recentActivity = useMemo(() => {
    const tickets = ticketsData?.tickets || [];
    if (tickets.length === 0) return [];
    return [...tickets]
      .filter((t) => t.updated_at)
      .sort(
        (a, b) =>
          new Date(b.updated_at || 0).getTime() -
          new Date(a.updated_at || 0).getTime(),
      )
      .slice(0, 5)
      .map((t) => ({
        id: t.id,
        message: `Ticket "${t.title}" updated to ${t.status}`,
        time: t.updated_at ? formatTimeAgo(new Date(t.updated_at)) : "unknown",
        type: "ticket" as const,
      }));
  }, [ticketsData]);
  if (isLoading) {
    return (
      <div className="container mx-auto p-6 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <Skeleton className="h-8 w-48" />
            <Skeleton className="h-4 w-64 mt-2" />
          </div>
          <Skeleton className="h-10 w-[180px]" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Analytics Dashboard</h1>
          <p className="text-muted-foreground">
            Overview of all projects and activity
          </p>
        </div>
        <Select value={projectFilter} onValueChange={setProjectFilter}>
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Filter by project" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Projects</SelectItem>
            {projectsData?.projects?.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.name}
              </SelectItem>
            ))}
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

      {/* Active Projects Grid */}
      <Card>
        <CardHeader>
          <CardTitle>Active Projects</CardTitle>
          <CardDescription>Current projects in progress</CardDescription>
        </CardHeader>
        <CardContent>
          {activeProjects.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              <FileText className="mx-auto h-12 w-12 text-muted-foreground/30" />
              <p className="mt-2">No active projects</p>
              <Button variant="outline" className="mt-4" asChild>
                <Link href="/projects/new">Create Project</Link>
              </Button>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2">
              {activeProjects.map((project) => (
                <Card key={project.id} className="border">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold">{project.name}</h3>
                        <p className="text-sm text-muted-foreground">
                          {project.repo}
                        </p>
                      </div>
                      <Badge variant="secondary">{project.status}</Badge>
                    </div>
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span>Progress</span>
                        <span className="font-medium">{project.progress}%</span>
                      </div>
                      <Progress value={project.progress} className="h-2" />
                    </div>
                    <div className="mt-4 flex items-center justify-between">
                      <span className="text-sm text-muted-foreground">
                        {project.agents} active agent
                        {project.agents !== 1 ? "s" : ""}
                      </span>
                      <div className="flex gap-2">
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/projects/${project.id}`}>View</Link>
                        </Button>
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/board/${project.id}`}>Board</Link>
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Recent Activity */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Recent Activity</CardTitle>
            <CardDescription>Latest events across all projects</CardDescription>
          </div>
          <Button variant="outline" size="sm" asChild>
            <Link href="/activity">
              View All Activity <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </CardHeader>
        <CardContent>
          {recentActivity.length === 0 ? (
            <div className="py-6 text-center text-muted-foreground">
              <p>No recent activity</p>
            </div>
          ) : (
            <div className="space-y-4">
              {recentActivity.map((activity) => (
                <div key={activity.id} className="flex items-center gap-4">
                  <div className="h-2 w-2 rounded-full bg-primary" />
                  <p className="flex-1 text-sm">{activity.message}</p>
                  <span className="text-sm text-muted-foreground">
                    {activity.time}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <Card>
        <CardContent className="p-6">
          <div className="flex flex-wrap items-center gap-4">
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
  );
}
