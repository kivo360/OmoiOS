"use client"

import { useState } from "react"
import Link from "next/link"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Search, Filter, SortAsc, Plus } from "lucide-react"
import { AgentCard, TimeGroupHeader } from "@/components/custom"
import { mockAgents } from "@/lib/mock"

export function AgentsPanel() {
  const [searchQuery, setSearchQuery] = useState("")

  const filteredAgents = mockAgents.filter((agent) =>
    agent.taskName.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const todayAgents = filteredAgents.filter((a) => a.status === "running")
  const weekAgents = filteredAgents.filter((a) => a.status === "completed")
  const erroredAgents = filteredAgents.filter((a) => a.status === "failed" || a.status === "blocked")

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-3 space-y-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-9 pl-8 text-sm"
            />
          </div>
          <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0">
            <Filter className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0">
            <SortAsc className="h-4 w-4" />
          </Button>
        </div>
        <Button className="w-full" size="sm" asChild>
          <Link href="/agents/spawn">
            <Plus className="mr-2 h-4 w-4" /> New Agent
          </Link>
        </Button>
      </div>

      {/* Agent List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {todayAgents.length > 0 && (
            <div className="space-y-1">
              <TimeGroupHeader>Today</TimeGroupHeader>
              {todayAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  id={agent.id}
                  taskName={agent.taskName}
                  status={agent.status}
                  timeAgo={agent.timeAgo}
                  additions={agent.additions}
                  deletions={agent.deletions}
                  repoName={agent.repoName}
                />
              ))}
            </div>
          )}

          {weekAgents.length > 0 && (
            <div className="space-y-1">
              <TimeGroupHeader>This Week</TimeGroupHeader>
              {weekAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  id={agent.id}
                  taskName={agent.taskName}
                  status={agent.status}
                  timeAgo={agent.timeAgo}
                  additions={agent.additions}
                  deletions={agent.deletions}
                  repoName={agent.repoName}
                />
              ))}
            </div>
          )}

          {erroredAgents.length > 0 && (
            <div className="space-y-1">
              <TimeGroupHeader>Errored</TimeGroupHeader>
              {erroredAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  id={agent.id}
                  taskName={agent.taskName}
                  status={agent.status}
                  timeAgo={agent.timeAgo}
                  additions={agent.additions}
                  deletions={agent.deletions}
                  repoName={agent.repoName}
                />
              ))}
            </div>
          )}

          {filteredAgents.length === 0 && (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No agents found
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  )
}
