"use client"

import * as React from "react"
import { useRouter } from "next/navigation"
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command"
import {
  FolderKanban,
  Bot,
  LayoutDashboard,
  GitGraph,
  Settings,
  User,
  Bell,
  Palette,
  Shield,
  Key,
  Activity,
  BarChart3,
  FileText,
  Search,
  Zap,
  Clock,
  ArrowRight,
  Ticket,
  GitCommit,
  Network,
  Gauge,
  MonitorCheck,
} from "lucide-react"

// Mock data - in a real app, this would come from an API or context
const mockProjects = [
  { id: "senseii-games", name: "Senseii Games", status: "active" },
  { id: "api-service", name: "API Service", status: "active" },
  { id: "database-infrastructure", name: "Database Infrastructure", status: "active" },
  { id: "auth-system", name: "Auth System", status: "active" },
  { id: "payment-gateway", name: "Payment Gateway", status: "paused" },
]

const mockAgents = [
  { id: "agent-1", name: "worker-1", task: "Improve senseii game performance" },
  { id: "agent-2", name: "worker-2", task: "Fix groq API integration" },
  { id: "agent-3", name: "orchestrator", task: "System orchestration" },
]

const mockTickets = [
  { id: "TICKET-042", title: "OAuth2 Authentication", project: "auth-system" },
  { id: "TICKET-038", title: "Database Schema Updates", project: "database" },
  { id: "TICKET-045", title: "Rate Limiting", project: "api-service" },
]

interface CommandPaletteProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CommandPalette({ open, onOpenChange }: CommandPaletteProps) {
  const router = useRouter()
  const [search, setSearch] = React.useState("")

  const runCommand = React.useCallback(
    (command: () => void) => {
      onOpenChange(false)
      command()
    },
    [onOpenChange]
  )

  // Filter based on search
  const filteredProjects = mockProjects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase())
  )
  const filteredAgents = mockAgents.filter(
    (a) =>
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.task.toLowerCase().includes(search.toLowerCase())
  )
  const filteredTickets = mockTickets.filter(
    (t) =>
      t.id.toLowerCase().includes(search.toLowerCase()) ||
      t.title.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput
        placeholder="Type a command or search..."
        value={search}
        onValueChange={setSearch}
      />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Quick Navigation */}
        <CommandGroup heading="Navigation">
          <CommandItem onSelect={() => runCommand(() => router.push("/"))}>
            <LayoutDashboard className="mr-2 h-4 w-4" />
            Command Center
            <CommandShortcut>⌘H</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push("/projects"))}>
            <FolderKanban className="mr-2 h-4 w-4" />
            Projects
            <CommandShortcut>⌘P</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push("/agents"))}>
            <Bot className="mr-2 h-4 w-4" />
            Agents
            <CommandShortcut>⌘A</CommandShortcut>
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push("/activity"))}>
            <Activity className="mr-2 h-4 w-4" />
            Activity
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push("/phases"))}>
            <Gauge className="mr-2 h-4 w-4" />
            Phases
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push("/phases/gates"))}>
            <MonitorCheck className="mr-2 h-4 w-4" />
            Quality Gates
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Projects - shown when searching or always show recent */}
        {(search.length > 0 ? filteredProjects.length > 0 : true) && (
          <CommandGroup heading="Projects">
            {(search.length > 0 ? filteredProjects : mockProjects.slice(0, 3)).map(
              (project) => (
                <CommandItem
                  key={project.id}
                  onSelect={() =>
                    runCommand(() => router.push(`/projects/${project.id}`))
                  }
                >
                  <FolderKanban className="mr-2 h-4 w-4" />
                  <span className="flex-1">{project.name}</span>
                  {project.status === "paused" && (
                    <span className="text-xs text-muted-foreground">Paused</span>
                  )}
                  <ArrowRight className="h-3 w-3 text-muted-foreground" />
                </CommandItem>
              )
            )}
            {search.length === 0 && (
              <CommandItem onSelect={() => runCommand(() => router.push("/projects"))}>
                <Search className="mr-2 h-4 w-4 text-muted-foreground" />
                <span className="text-muted-foreground">View all projects...</span>
              </CommandItem>
            )}
          </CommandGroup>
        )}

        <CommandSeparator />

        {/* Agents */}
        {(search.length > 0 ? filteredAgents.length > 0 : true) && (
          <CommandGroup heading="Agents">
            {(search.length > 0 ? filteredAgents : mockAgents.slice(0, 3)).map(
              (agent) => (
                <CommandItem
                  key={agent.id}
                  onSelect={() =>
                    runCommand(() => router.push(`/agents/${agent.id}`))
                  }
                >
                  <Bot className="mr-2 h-4 w-4" />
                  <div className="flex flex-col">
                    <span>{agent.name}</span>
                    <span className="text-xs text-muted-foreground truncate max-w-[250px]">
                      {agent.task}
                    </span>
                  </div>
                </CommandItem>
              )
            )}
          </CommandGroup>
        )}

        {/* Tickets - only shown when searching */}
        {search.length > 0 && filteredTickets.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Tickets">
              {filteredTickets.map((ticket) => (
                <CommandItem
                  key={ticket.id}
                  onSelect={() =>
                    runCommand(() =>
                      router.push(`/board/${ticket.project}/${ticket.id}`)
                    )
                  }
                >
                  <Ticket className="mr-2 h-4 w-4" />
                  <span className="font-mono text-xs mr-2">{ticket.id}</span>
                  <span className="truncate">{ticket.title}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        <CommandSeparator />

        {/* Quick Actions */}
        <CommandGroup heading="Quick Actions">
          <CommandItem onSelect={() => runCommand(() => router.push("/projects/new"))}>
            <Zap className="mr-2 h-4 w-4" />
            Create New Project
          </CommandItem>
          <CommandItem onSelect={() => runCommand(() => router.push("/agents/new"))}>
            <Bot className="mr-2 h-4 w-4" />
            Spawn New Agent
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Tools */}
        <CommandGroup heading="Tools">
          <CommandItem
            onSelect={() =>
              runCommand(() => router.push("/graph/senseii-games"))
            }
          >
            <GitGraph className="mr-2 h-4 w-4" />
            Dependency Graph
          </CommandItem>
          <CommandItem
            onSelect={() =>
              runCommand(() => router.push("/diagnostic/ticket/TICKET-042"))
            }
          >
            <Network className="mr-2 h-4 w-4" />
            Diagnostic View
          </CommandItem>
          <CommandItem
            onSelect={() =>
              runCommand(() => router.push("/commits/abc123"))
            }
          >
            <GitCommit className="mr-2 h-4 w-4" />
            Recent Commits
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Settings */}
        <CommandGroup heading="Settings">
          <CommandItem onSelect={() => runCommand(() => router.push("/settings"))}>
            <Settings className="mr-2 h-4 w-4" />
            Settings
            <CommandShortcut>⌘,</CommandShortcut>
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/settings/profile"))}
          >
            <User className="mr-2 h-4 w-4" />
            Profile
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/settings/appearance"))}
          >
            <Palette className="mr-2 h-4 w-4" />
            Appearance
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/settings/notifications"))}
          >
            <Bell className="mr-2 h-4 w-4" />
            Notifications
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/settings/security"))}
          >
            <Shield className="mr-2 h-4 w-4" />
            Security
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/settings/sessions"))}
          >
            <Clock className="mr-2 h-4 w-4" />
            Sessions
          </CommandItem>
          <CommandItem
            onSelect={() => runCommand(() => router.push("/settings/api-keys"))}
          >
            <Key className="mr-2 h-4 w-4" />
            API Keys
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  )
}
