"use client"

import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar"
import { MinimalHeader } from "@/components/layout"
import { RecentAgentsSidebar, RecentAgent } from "@/components/command"

// Mock data for recent agents (will be replaced with real data later)
const mockAgents: RecentAgent[] = [
  {
    id: "1",
    taskName: "Improve senseii games...",
    status: "running",
    timeAgo: "2h",
    additions: 1539,
    deletions: 209,
    repoName: "senseii-games",
    createdAt: new Date(),
  },
  {
    id: "2",
    taskName: "Fix groq integration",
    status: "completed",
    timeAgo: "1d",
    additions: 29,
    deletions: 10,
    repoName: "api-service",
    createdAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
  },
  {
    id: "3",
    taskName: "Fix gaming backend",
    status: "completed",
    timeAgo: "2d",
    additions: 87,
    deletions: 34,
    repoName: "gaming-service",
    createdAt: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000),
  },
  {
    id: "4",
    taskName: "Fix foreign key issue",
    status: "completed",
    timeAgo: "1w",
    additions: 12,
    deletions: 5,
    repoName: "database",
    createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000),
  },
  {
    id: "5",
    taskName: "Database migration failed",
    status: "failed",
    timeAgo: "3d",
    repoName: "backend",
    createdAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
  },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <SidebarProvider defaultOpen={true}>
      <RecentAgentsSidebar agents={mockAgents} />
      <SidebarInset>
        <MinimalHeader />
        <main className="flex-1 overflow-auto">
          {children}
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
