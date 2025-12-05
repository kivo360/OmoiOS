"use client"

import { use, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  ArrowLeft,
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Clock,
  User,
  AlertCircle,
} from "lucide-react"

interface BoardPageProps {
  params: Promise<{ projectId: string }>
}

// Mock ticket data
const columns = [
  { id: "backlog", title: "Backlog", tickets: [] as any[] },
  { id: "todo", title: "To Do", tickets: [] as any[] },
  { id: "in-progress", title: "In Progress", tickets: [] as any[] },
  { id: "review", title: "Review", tickets: [] as any[] },
  { id: "done", title: "Done", tickets: [] as any[] },
]

const mockTickets = [
  { id: "1", title: "Setup authentication flow", status: "in-progress", priority: "high", assignee: "Agent-1", labels: ["auth"], blockers: 0 },
  { id: "2", title: "Implement JWT token validation", status: "todo", priority: "high", assignee: null, labels: ["auth", "security"], blockers: 1 },
  { id: "3", title: "Add OAuth2 providers", status: "backlog", priority: "medium", assignee: null, labels: ["auth"], blockers: 0 },
  { id: "4", title: "Create user profile endpoint", status: "review", priority: "medium", assignee: "Agent-2", labels: ["api"], blockers: 0 },
  { id: "5", title: "Add password reset flow", status: "todo", priority: "low", assignee: null, labels: ["auth"], blockers: 2 },
  { id: "6", title: "Rate limiting middleware", status: "done", priority: "high", assignee: "Agent-1", labels: ["security"], blockers: 0 },
]

// Group tickets by status
const groupedTickets = columns.map((col) => ({
  ...col,
  tickets: mockTickets.filter((t) => t.status === col.id),
}))

const priorityColors = {
  high: "destructive",
  medium: "warning",
  low: "secondary",
}

export default function BoardPage({ params }: BoardPageProps) {
  const { projectId } = use(params)
  const [searchQuery, setSearchQuery] = useState("")

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col">
      {/* Header */}
      <div className="border-b border-border p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Link
              href={`/projects/${projectId}`}
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Project
            </Link>
            <h1 className="text-xl font-bold">Kanban Board</h1>
          </div>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search tickets..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-[200px] pl-8"
              />
            </div>
            <Button variant="outline" size="icon">
              <Filter className="h-4 w-4" />
            </Button>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> Create Ticket
            </Button>
          </div>
        </div>
      </div>

      {/* Board */}
      <ScrollArea className="flex-1 p-4">
        <div className="flex gap-4 pb-4">
          {groupedTickets.map((column) => (
            <div
              key={column.id}
              className="flex w-[300px] shrink-0 flex-col rounded-lg bg-muted/30"
            >
              {/* Column Header */}
              <div className="flex items-center justify-between p-3">
                <div className="flex items-center gap-2">
                  <h2 className="font-semibold">{column.title}</h2>
                  <Badge variant="secondary" className="rounded-full">
                    {column.tickets.length}
                  </Badge>
                </div>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreHorizontal className="h-4 w-4" />
                </Button>
              </div>

              {/* Column Content */}
              <div className="flex-1 space-y-2 p-2 pt-0">
                {column.tickets.map((ticket) => (
                  <Link
                    key={ticket.id}
                    href={`/board/${projectId}/${ticket.id}`}
                  >
                    <Card className="cursor-pointer hover:border-primary/50 transition-colors">
                      <CardContent className="p-3 space-y-3">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-sm font-medium leading-tight">
                            {ticket.title}
                          </p>
                          <Badge
                            variant={priorityColors[ticket.priority as keyof typeof priorityColors] as any}
                            className="shrink-0 text-xs"
                          >
                            {ticket.priority}
                          </Badge>
                        </div>

                        <div className="flex flex-wrap gap-1">
                          {ticket.labels.map((label: string) => (
                            <Badge
                              key={label}
                              variant="outline"
                              className="text-xs"
                            >
                              {label}
                            </Badge>
                          ))}
                        </div>

                        <div className="flex items-center justify-between text-xs text-muted-foreground">
                          <div className="flex items-center gap-2">
                            {ticket.assignee ? (
                              <span className="flex items-center gap-1">
                                <User className="h-3 w-3" />
                                {ticket.assignee}
                              </span>
                            ) : (
                              <span className="text-muted-foreground/50">
                                Unassigned
                              </span>
                            )}
                          </div>
                          {ticket.blockers > 0 && (
                            <span className="flex items-center gap-1 text-warning">
                              <AlertCircle className="h-3 w-3" />
                              {ticket.blockers} blocker{ticket.blockers > 1 ? "s" : ""}
                            </span>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                ))}

                {/* Add ticket button */}
                <Button
                  variant="ghost"
                  className="w-full justify-start text-muted-foreground"
                  size="sm"
                >
                  <Plus className="mr-2 h-4 w-4" />
                  Add ticket
                </Button>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
