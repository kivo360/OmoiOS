"use client"

import { useMemo } from "react"
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { MinimalHeader } from "@/components/layout"
import { RecentAgentsSidebar, RecentAgent } from "@/components/command"
import { useAgents } from "@/hooks/useAgents"

function formatTimeAgo(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)
  const diffWeeks = Math.floor(diffDays / 7)

  if (diffHours < 1) return "just now"
  if (diffHours < 24) return `${diffHours}h`
  if (diffDays < 7) return `${diffDays}d`
  return `${diffWeeks}w`
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const { data: agentsData } = useAgents()

  // Transform API agents to RecentAgent format
  const recentAgents: RecentAgent[] = useMemo(() => {
    if (!agentsData) return []
    
    return agentsData
      .slice(0, 10) // Limit to 10 recent agents
      .map((agent) => {
        const createdAt = agent.created_at ? new Date(agent.created_at) : new Date()
        const statusMap: Record<string, "running" | "completed" | "failed"> = {
          active: "running",
          idle: "completed",
          error: "failed",
          terminated: "completed",
        }
        
        return {
          id: agent.agent_id,
          taskName: `${agent.agent_type} Agent`,
          status: statusMap[agent.status] || "completed",
          timeAgo: formatTimeAgo(createdAt),
          repoName: agent.phase_id || agent.agent_type,
          createdAt,
          // Note: additions/deletions would come from commits API if needed
        }
      })
  }, [agentsData])

  return (
    <SidebarProvider defaultOpen={true}>
      <RecentAgentsSidebar agents={recentAgents} />
      <SidebarInset>
        <MinimalHeader />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
