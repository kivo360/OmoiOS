"use client"

import { useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Search,
  Plus,
  Bot,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  AlertCircle,
  Terminal,
} from "lucide-react"
import { mockAgents } from "@/lib/mock"
import { LineChanges } from "@/components/custom"

const statusConfig = {
  running: { icon: Loader2, color: "warning", iconClass: "animate-spin" },
  completed: { icon: CheckCircle, color: "success", iconClass: "" },
  failed: { icon: XCircle, color: "destructive", iconClass: "" },
  blocked: { icon: AlertCircle, color: "warning", iconClass: "" },
}

export default function AgentsPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")

  const filteredAgents = mockAgents.filter((agent) => {
    const matchesSearch = agent.taskName.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesStatus = statusFilter === "all" || agent.status === statusFilter
    return matchesSearch && matchesStatus
  })

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Agents</h1>
          <p className="text-muted-foreground">View and manage AI agents</p>
        </div>
        <Button asChild>
          <Link href="/agents/spawn">
            <Plus className="mr-2 h-4 w-4" /> Spawn Agent
          </Link>
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search agents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Status</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="blocked">Blocked</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Agents Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredAgents.map((agent) => {
          const config = statusConfig[agent.status]
          const StatusIcon = config.icon

          return (
            <Card key={agent.id} className="hover:border-primary/50 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Bot className="h-5 w-5 text-muted-foreground" />
                    <CardTitle className="text-base">
                      <Link href={`/agents/${agent.id}`} className="hover:underline">
                        {agent.taskName}
                      </Link>
                    </CardTitle>
                  </div>
                  <Badge variant={config.color as any}>
                    <StatusIcon className={`mr-1 h-3 w-3 ${config.iconClass}`} />
                    {agent.status}
                  </Badge>
                </div>
                {agent.repoName && (
                  <CardDescription>{agent.repoName}</CardDescription>
                )}
              </CardHeader>
              <CardContent className="space-y-4">
                {(agent.additions || agent.deletions) && (
                  <LineChanges
                    additions={agent.additions || 0}
                    deletions={agent.deletions || 0}
                  />
                )}

                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    <span>{agent.timeAgo}</span>
                  </div>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/agents/${agent.id}`}>Details</Link>
                    </Button>
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/agents/${agent.id}/workspace`}>
                        <Terminal className="mr-1 h-3 w-3" />
                        Workspace
                      </Link>
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Empty State */}
      {filteredAgents.length === 0 && (
        <Card className="p-12 text-center">
          <Bot className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No agents found</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            {searchQuery || statusFilter !== "all"
              ? "Try adjusting your search or filters"
              : "Spawn your first agent to get started"}
          </p>
          <Button className="mt-4" asChild>
            <Link href="/agents/spawn">
              <Plus className="mr-2 h-4 w-4" /> Spawn Agent
            </Link>
          </Button>
        </Card>
      )}
    </div>
  )
}
