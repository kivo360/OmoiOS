# Frontend Components Scaffold

**Created**: 2025-05-19
**Status**: Scaffold Document
**Purpose**: Provides copy-paste ready React/TypeScript code for core UI components, leveraging ShadCN UI.

---

## 1. Shared UI Components

### `src/components/shared/StatusBadge.tsx`

Displays ticket/task status with appropriate coloring.

```tsx
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"

type StatusType = "backlog" | "todo" | "in_progress" | "done" | "canceled"

interface StatusBadgeProps {
  status: string
  className?: string
}

const statusMap: Record<string, { label: string; variant: "default" | "secondary" | "destructive" | "outline" }> = {
  backlog: { label: "Backlog", variant: "outline" },
  todo: { label: "To Do", variant: "secondary" },
  in_progress: { label: "In Progress", variant: "default" },
  done: { label: "Done", variant: "secondary" },
  canceled: { label: "Canceled", variant: "destructive" },
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const config = statusMap[status.toLowerCase()] || { label: status, variant: "outline" }
  
  return (
    <Badge variant={config.variant} className={cn("capitalize", className)}>
      {config.label}
    </Badge>
  )
}
```

### `src/components/shared/PriorityIcon.tsx`

Visual indicator for priority levels.

```tsx
import { ArrowUp, ArrowDown, Minus, AlertCircle } from "lucide-react"
import { cn } from "@/lib/utils"

interface PriorityIconProps {
  priority: "low" | "medium" | "high" | "critical"
  className?: string
}

export function PriorityIcon({ priority, className }: PriorityIconProps) {
  switch (priority.toLowerCase()) {
    case "critical":
      return <AlertCircle className={cn("h-4 w-4 text-red-600", className)} />
    case "high":
      return <ArrowUp className={cn("h-4 w-4 text-orange-500", className)} />
    case "medium":
      return <Minus className={cn("h-4 w-4 text-blue-500", className)} />
    case "low":
      return <ArrowDown className={cn("h-4 w-4 text-slate-500", className)} />
    default:
      return <Minus className={cn("h-4 w-4 text-slate-500", className)} />
  }
}
```

### `src/components/shared/NotificationCenter.tsx`

Notification dropdown.

```tsx
"use client"

import { Bell } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"

export function NotificationCenter() {
  // Mock notifications
  const notifications = [
    { id: 1, title: "Task Failed", description: "Agent X failed task Y", time: "2m ago", unread: true },
    { id: 2, title: "Project Approved", description: "Project Z is ready", time: "1h ago", unread: false },
  ]
  const unreadCount = notifications.filter(n => n.unread).length

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-600" />
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-80" align="end">
        <DropdownMenuLabel className="flex justify-between">
          Notifications
          {unreadCount > 0 && <Badge variant="secondary">{unreadCount} new</Badge>}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <ScrollArea className="h-[300px]">
          {notifications.map((notification) => (
            <DropdownMenuItem key={notification.id} className="flex flex-col items-start p-3 cursor-pointer">
              <div className="flex w-full justify-between items-start mb-1">
                <span className={`font-medium ${notification.unread ? "text-foreground" : "text-muted-foreground"}`}>
                  {notification.title}
                </span>
                <span className="text-xs text-muted-foreground">{notification.time}</span>
              </div>
              <p className="text-xs text-muted-foreground line-clamp-2">
                {notification.description}
              </p>
            </DropdownMenuItem>
          ))}
        </ScrollArea>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
```

---

## 2. Layout Components

### `src/components/layout/AppSidebar.tsx`

Main navigation sidebar.

```tsx
"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { LayoutDashboard, FolderKanban, Users, Settings, Search, BarChart3 } from "lucide-react"

interface SidebarNavProps extends React.HTMLAttributes<HTMLElement> {
  items: {
    href: string
    title: string
    icon: React.ElementType
  }[]
}

export function AppSidebar({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  const pathname = usePathname()
  
  const items = [
    { href: "/overview", title: "Overview", icon: LayoutDashboard },
    { href: "/projects", title: "Projects", icon: FolderKanban },
    { href: "/agents", title: "Agents", icon: Users },
    { href: "/stats", title: "Statistics", icon: BarChart3 },
    { href: "/search", title: "Search", icon: Search },
    { href: "/settings", title: "Settings", icon: Settings },
  ]

  return (
    <div className={cn("pb-12 w-64 border-r min-h-screen bg-background", className)} {...props}>
      <div className="space-y-4 py-4">
        <div className="px-3 py-2">
          <h2 className="mb-2 px-4 text-lg font-semibold tracking-tight">
            OmoiOS Dashboard
          </h2>
          <div className="space-y-1">
            <nav className="grid items-start gap-2">
              {items.map((item, index) => {
                 const Icon = item.icon
                 return (
                   <Link key={index} href={item.href}>
                     <span
                       className={cn(
                         "group flex items-center rounded-md px-3 py-2 text-sm font-medium hover:bg-accent hover:text-accent-foreground",
                         pathname.startsWith(item.href) ? "bg-accent text-accent-foreground" : "transparent"
                       )}
                     >
                       <Icon className="mr-2 h-4 w-4" />
                       <span>{item.title}</span>
                     </span>
                   </Link>
                 )
              })}
            </nav>
          </div>
        </div>
      </div>
    </div>
  )
}
```

### `src/components/layout/TopHeader.tsx`

Global header.

```tsx
import { UserAvatar } from "@/components/shared/UserAvatar"
import { NotificationCenter } from "@/components/shared/NotificationCenter"
import { Breadcrumb, BreadcrumbItem, BreadcrumbLink, BreadcrumbList, BreadcrumbSeparator } from "@/components/ui/breadcrumb"

export function TopHeader() {
  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container flex h-14 items-center">
        <div className="mr-4 hidden md:flex">
           {/* Breadcrumbs placeholder - use real path parsing in prod */}
           <Breadcrumb>
             <BreadcrumbList>
               <BreadcrumbItem>
                 <BreadcrumbLink href="/">Home</BreadcrumbLink>
               </BreadcrumbItem>
               <BreadcrumbSeparator />
               <BreadcrumbItem>
                 <BreadcrumbLink href="/projects">Projects</BreadcrumbLink>
               </BreadcrumbItem>
             </BreadcrumbList>
           </Breadcrumb>
        </div>
        <div className="flex flex-1 items-center justify-between space-x-2 md:justify-end">
          <div className="w-full flex-1 md:w-auto md:flex-none">
            {/* Optional global search input */}
          </div>
          <nav className="flex items-center gap-2">
            <NotificationCenter />
            <UserAvatar />
          </nav>
        </div>
      </div>
    </header>
  )
}
```

---

## 3. Kanban Components

### `src/components/kanban/TicketCard.tsx`

Draggable ticket card component using `dnd-kit`.

```tsx
"use client"

import { useDraggable } from "@dnd-kit/core"
import { Card, CardContent, CardFooter, CardHeader } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { PriorityIcon } from "@/components/shared/PriorityIcon"
import { cn } from "@/lib/utils"

interface Ticket {
  id: string
  title: string
  description: string
  priority: "low" | "medium" | "high" | "critical"
  status: string
  assignee?: {
    name: string
    avatarUrl?: string
  }
}

interface TicketCardProps {
  ticket: Ticket
}

export function TicketCard({ ticket }: TicketCardProps) {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: ticket.id,
    data: ticket,
  })

  const style = transform ? {
    transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`,
  } : undefined

  return (
    <div ref={setNodeRef} style={style} {...listeners} {...attributes}>
      <Card 
        className={cn(
          "cursor-grab active:cursor-grabbing hover:shadow-md transition-shadow",
          isDragging && "opacity-50 ring-2 ring-primary"
        )}
      >
        <CardHeader className="p-4 pb-2 flex flex-row items-start justify-between space-y-0">
          <span className="font-semibold text-sm line-clamp-2 leading-tight">
            {ticket.title}
          </span>
          <PriorityIcon priority={ticket.priority} />
        </CardHeader>
        <CardContent className="p-4 pt-0 pb-2">
          <p className="text-xs text-muted-foreground line-clamp-2">
            {ticket.description}
          </p>
        </CardContent>
        <CardFooter className="p-4 pt-2 flex justify-between items-center">
          <div className="flex items-center gap-2">
            <code className="text-[10px] text-muted-foreground bg-muted px-1 py-0.5 rounded">
              {ticket.id}
            </code>
          </div>
          {ticket.assignee && (
            <Avatar className="h-6 w-6">
              <AvatarImage src={ticket.assignee.avatarUrl} />
              <AvatarFallback className="text-[10px]">
                {ticket.assignee.name.slice(0, 2).toUpperCase()}
              </AvatarFallback>
            </Avatar>
          )}
        </CardFooter>
      </Card>
    </div>
  )
}
```

### `src/components/kanban/BoardColumn.tsx`

Droppable column container.

```tsx
"use client"

import { useDroppable } from "@dnd-kit/core"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import { TicketCard } from "./TicketCard"
import { cn } from "@/lib/utils"

interface BoardColumnProps {
  id: string
  title: string
  tickets: any[] 
  onAddTicket?: () => void
}

export function BoardColumn({ id, title, tickets, onAddTicket }: BoardColumnProps) {
  const { setNodeRef, isOver } = useDroppable({
    id: id,
  })

  return (
    <div className="flex flex-col h-full w-80 min-w-[20rem] bg-muted/50 rounded-lg border p-2">
      <div className="flex items-center justify-between p-2 mb-2">
        <h3 className="font-semibold text-sm flex items-center gap-2">
          {title}
          <Badge variant="secondary" className="text-xs px-2 py-0 h-5">
            {tickets.length}
          </Badge>
        </h3>
        <Button variant="ghost" size="icon" className="h-6 w-6" onClick={onAddTicket}>
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      
      <div 
        ref={setNodeRef} 
        className={cn(
          "flex-1 rounded-md transition-colors",
          isOver && "bg-accent/50"
        )}
      >
        <ScrollArea className="h-[calc(100vh-12rem)]">
          <div className="flex flex-col gap-3 p-1">
            {tickets.map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
            {tickets.length === 0 && (
              <div className="h-24 flex items-center justify-center border-2 border-dashed rounded-md border-muted-foreground/25">
                <span className="text-xs text-muted-foreground">No tickets</span>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
```

---

## 4. Project Components

### `src/components/project/ProjectCard.tsx`

Card view for project list.

```tsx
import Link from "next/link"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { ArrowRight, Users } from "lucide-react"

interface Project {
  id: string
  name: string
  description: string
  status: "active" | "archived" | "paused"
  progress: number
  ticketCount: number
  agentCount: number
}

interface ProjectCardProps {
  project: Project
}

export function ProjectCard({ project }: ProjectCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow">
      <CardHeader className="pb-3">
        <div className="flex justify-between items-start">
          <CardTitle className="text-lg font-bold">{project.name}</CardTitle>
          <Badge variant={project.status === "active" ? "default" : "secondary"}>
            {project.status}
          </Badge>
        </div>
        <CardDescription className="line-clamp-2 h-10">
          {project.description}
        </CardDescription>
      </CardHeader>
      <CardContent className="pb-3">
        <div className="space-y-2">
          <div className="flex justify-between text-xs text-muted-foreground">
            <span>Progress</span>
            <span>{Math.round(project.progress * 100)}%</span>
          </div>
          <Progress value={project.progress * 100} className="h-2" />
        </div>
        <div className="mt-4 flex gap-4 text-sm text-muted-foreground">
          <div className="flex items-center gap-1">
            <span className="font-semibold text-foreground">{project.ticketCount}</span> Tickets
          </div>
          <div className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            <span className="font-semibold text-foreground">{project.agentCount}</span> Agents
          </div>
        </div>
      </CardContent>
      <CardFooter>
        <Button asChild className="w-full" variant="outline">
          <Link href={`/projects/${project.id}/board`}>
            Open Project <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
  )
}
```

### `src/components/project/CreateProjectDialog.tsx`

Dialog for creating new projects.

```tsx
"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Plus } from "lucide-react"

export function CreateProjectDialog() {
  const [open, setOpen] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // API call logic
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" /> New Project
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Project</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Project Name</Label>
            <Input id="name" placeholder="e.g. Authentication Service" required />
          </div>
          <div className="space-y-2">
            <Label htmlFor="desc">Description</Label>
            <Textarea id="desc" placeholder="What is this project about?" />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button type="submit">Create Project</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
```

---

## 5. Graph Components

### `src/components/graph/GraphView.tsx`

React Flow wrapper for dependency graphs.

```tsx
"use client"

import ReactFlow, { 
  Controls, 
  Background, 
  useNodesState, 
  useEdgesState, 
  Node, 
  Edge,
  MiniMap 
} from "reactflow"
import "reactflow/dist/style.css"

interface GraphViewProps {
  initialNodes?: Node[]
  initialEdges?: Edge[]
}

const defaultNodes: Node[] = [
  { id: '1', position: { x: 0, y: 0 }, data: { label: 'Project Start' } },
  { id: '2', position: { x: 0, y: 100 }, data: { label: 'Phase 1' } },
];
const defaultEdges: Edge[] = [{ id: 'e1-2', source: '1', target: '2' }];

export function GraphView({ initialNodes = defaultNodes, initialEdges = defaultEdges }: GraphViewProps) {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  return (
    <div className="h-[600px] w-full border rounded-lg bg-background">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
      >
        <Background />
        <Controls />
        <MiniMap />
      </ReactFlow>
    </div>
  )
}
```

---

## 6. Exploration Components

### `src/components/exploration/ChatInterface.tsx`

AI Chat interaction area.

```tsx
"use client"

import { useState, useRef, useEffect } from "react"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Send, Loader2 } from "lucide-react"
import { cn } from "@/lib/utils"

interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export function ChatInterface() {
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const scrollRef = useRef<HTMLDivElement>(null)

  const handleSend = async () => {
    if (!input.trim()) return
    
    const newMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date()
    }
    
    setMessages(prev => [...prev, newMessage])
    setInput("")
    setIsLoading(true)
    
    // Simulate API call
    setTimeout(() => {
      setMessages(prev => [...prev, {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "I can help you define the requirements for that. What specific features are you looking for?",
        timestamp: new Date()
      }])
      setIsLoading(false)
    }, 1000)
  }

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" })
    }
  }, [messages])

  return (
    <div className="flex flex-col h-[600px] border rounded-lg bg-background">
      <ScrollArea className="flex-1 p-4">
        <div className="space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={cn(
                "flex w-max max-w-[80%] flex-col gap-2 rounded-lg px-3 py-2 text-sm",
                msg.role === "user"
                  ? "ml-auto bg-primary text-primary-foreground"
                  : "bg-muted"
              )}
            >
              {msg.content}
            </div>
          ))}
          {isLoading && (
            <div className="flex w-max max-w-[80%] flex-col gap-2 rounded-lg px-3 py-2 text-sm bg-muted">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          )}
          <div ref={scrollRef} />
        </div>
      </ScrollArea>
      <div className="p-4 border-t">
        <form
          onSubmit={(e) => {
            e.preventDefault()
            handleSend()
          }}
          className="flex gap-2"
        >
          <Textarea
            placeholder="Describe your project idea..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            className="min-h-[60px]"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
          />
          <Button type="submit" size="icon" disabled={isLoading || !input.trim()}>
            <Send className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </div>
  )
}
```

---

## 7. Agent Components

### `src/components/agent/AgentCard.tsx`

Card view for agents list.

```tsx
import Link from "next/link"
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Activity, ArrowRight } from "lucide-react"

interface Agent {
  id: string
  name: string
  status: "active" | "idle" | "offline"
  currentTask?: string
  capabilities: string[]
}

export function AgentCard({ agent }: { agent: Agent }) {
  return (
    <Card>
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <div className="flex items-center gap-3">
          <Avatar>
            <AvatarFallback>{agent.name.slice(0,2).toUpperCase()}</AvatarFallback>
          </Avatar>
          <div>
            <CardTitle className="text-base">{agent.name}</CardTitle>
            <div className="text-xs text-muted-foreground flex items-center gap-1 mt-1">
              <Activity className="h-3 w-3" /> {agent.status}
            </div>
          </div>
        </div>
        <Badge variant={agent.status === 'active' ? 'default' : 'secondary'}>
          {agent.status}
        </Badge>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground mt-2">
        {agent.currentTask ? (
          <p className="line-clamp-2">Working on: <span className="text-foreground">{agent.currentTask}</span></p>
        ) : (
          <p>Waiting for tasks...</p>
        )}
        <div className="flex flex-wrap gap-1 mt-3">
          {agent.capabilities.map(cap => (
            <Badge key={cap} variant="outline" className="text-[10px]">{cap}</Badge>
          ))}
        </div>
      </CardContent>
      <CardFooter>
        <Button asChild variant="ghost" size="sm" className="w-full">
          <Link href={`/agents/${agent.id}`}>View Details <ArrowRight className="ml-2 h-4 w-4" /></Link>
        </Button>
      </CardFooter>
    </Card>
  )
}
```

---

## 8. Audit Components

### `src/components/audit/AuditTrailViewer.tsx`

Timeline of events.

```tsx
import { ScrollArea } from "@/components/ui/scroll-area"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"

interface AuditEvent {
  id: string
  user: string
  action: string
  target: string
  timestamp: string
}

export function AuditTrailViewer({ events }: { events: AuditEvent[] }) {
  return (
    <ScrollArea className="h-[400px] pr-4">
      <div className="relative border-l border-muted ml-3 space-y-6">
        {events.map((event) => (
          <div key={event.id} className="ml-4 relative">
            <div className="absolute -left-[21px] top-1 rounded-full bg-background border p-0.5">
               <div className="h-2 w-2 rounded-full bg-primary" />
            </div>
            <div className="flex flex-col gap-1">
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm">{event.user}</span>
                <span className="text-muted-foreground text-sm">{event.action}</span>
              </div>
              <p className="text-sm text-foreground font-medium">{event.target}</p>
              <span className="text-xs text-muted-foreground">{event.timestamp}</span>
            </div>
          </div>
        ))}
      </div>
    </ScrollArea>
  )
}
```

---

## 15. Commit & Diff Components

### `src/components/commits/CommitDiffViewer.tsx`

Full commit diff viewer with file-by-file navigation.

```tsx
"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { FileDiffViewer } from "./FileDiffViewer"
import { GitCommit, User, Calendar, FileText, Download } from "lucide-react"

interface Commit {
  sha: string
  message: string
  author: string
  date: string
  files_changed: number
  insertions: number
  deletions: number
  agent_id?: string
  agent_name?: string
  ticket_id?: string
}

interface FileChange {
  path: string
  status: "added" | "modified" | "deleted" | "renamed"
  insertions: number
  deletions: number
  diff?: string
}

interface CommitDiffViewerProps {
  commit: Commit
  files: FileChange[]
}

export function CommitDiffViewer({ commit, files }: CommitDiffViewerProps) {
  const [selectedFile, setSelectedFile] = useState<FileChange | null>(files[0] || null)

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Commit Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CardTitle className="flex items-center gap-2">
                <GitCommit className="h-5 w-5" />
                Commit: {commit.sha.slice(0, 8)}
              </CardTitle>
              <p className="mt-2 text-sm text-foreground">{commit.message}</p>
            </div>
            <Button variant="outline" size="sm">
              <Download className="mr-2 h-4 w-4" /> Download Patch
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4" />
              {commit.author}
            </div>
            <div className="flex items-center gap-2">
              <Calendar className="h-4 w-4" />
              {new Date(commit.date).toLocaleString()}
            </div>
            {commit.agent_name && (
              <Badge variant="outline">Agent: {commit.agent_name}</Badge>
            )}
            <div className="flex items-center gap-2">
              <FileText className="h-4 w-4" />
              {commit.files_changed} files
            </div>
            <div className="flex items-center gap-2">
              <span className="text-green-600">+{commit.insertions}</span>
              <span className="text-red-600">-{commit.deletions}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* File List & Diff */}
      <div className="flex gap-4 flex-1 min-h-0">
        {/* File List */}
        <Card className="w-80 flex-shrink-0">
          <CardHeader>
            <CardTitle className="text-sm">Files Changed</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ScrollArea className="h-[600px]">
              {files.map((file) => (
                <button
                  key={file.path}
                  onClick={() => setSelectedFile(file)}
                  className={`w-full text-left p-3 hover:bg-muted transition-colors border-b ${
                    selectedFile?.path === file.path ? "bg-muted" : ""
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium truncate">{file.path}</span>
                    <Badge variant="outline" className="ml-2 text-xs">
                      {file.status}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                    <span className="text-green-600">+{file.insertions}</span>
                    <span className="text-red-600">-{file.deletions}</span>
                  </div>
                </button>
              ))}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* File Diff */}
        <Card className="flex-1 min-w-0">
          <CardHeader>
            <CardTitle className="text-sm">
              {selectedFile ? selectedFile.path : "Select a file"}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {selectedFile ? (
              <FileDiffViewer file={selectedFile} />
            ) : (
              <div className="flex items-center justify-center h-[600px] text-muted-foreground">
                Select a file to view diff
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

### `src/components/commits/FileDiffViewer.tsx`

Side-by-side or unified diff view for a single file.

```tsx
"use client"

import { useState } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Code2, Split } from "lucide-react"
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism"

interface FileChange {
  path: string
  status: "added" | "modified" | "deleted" | "renamed"
  insertions: number
  deletions: number
  diff?: string
  old_content?: string
  new_content?: string
}

interface FileDiffViewerProps {
  file: FileChange
}

export function FileDiffViewer({ file }: FileDiffViewerProps) {
  const [viewMode, setViewMode] = useState<"unified" | "split">("split")

  // Parse diff into line-by-line changes
  const parseDiff = (diff: string) => {
    const lines = diff.split("\n")
    const changes: Array<{
      line: number
      oldLine?: number
      newLine?: number
      type: "added" | "deleted" | "unchanged"
      content: string
    }> = []

    let oldLineNum = 0
    let newLineNum = 0

    for (const line of lines) {
      if (line.startsWith("@@")) {
        // Parse hunk header
        const match = line.match(/@@ -(\d+),?\d* \+(\d+),?\d* @@/)
        if (match) {
          oldLineNum = parseInt(match[1])
          newLineNum = parseInt(match[2])
        }
        continue
      }

      if (line.startsWith("+") && !line.startsWith("+++")) {
        changes.push({
          line: newLineNum++,
          newLine: newLineNum - 1,
          type: "added",
          content: line.slice(1),
        })
      } else if (line.startsWith("-") && !line.startsWith("---")) {
        changes.push({
          line: oldLineNum++,
          oldLine: oldLineNum - 1,
          type: "deleted",
          content: line.slice(1),
        })
      } else if (!line.startsWith("\\")) {
        changes.push({
          line: newLineNum++,
          oldLine: oldLineNum++,
          newLine: newLineNum - 1,
          type: "unchanged",
          content: line,
        })
      }
    }

    return changes
  }

  const changes = file.diff ? parseDiff(file.diff) : []

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center gap-2">
          <Tabs value={viewMode} onValueChange={(v) => setViewMode(v as any)}>
            <TabsList>
              <TabsTrigger value="split">
                <Split className="h-4 w-4 mr-2" /> Split
              </TabsTrigger>
              <TabsTrigger value="unified">
                <Code2 className="h-4 w-4 mr-2" /> Unified
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>
        <div className="text-sm text-muted-foreground">
          {file.insertions} insertions, {file.deletions} deletions
        </div>
      </div>

      <ScrollArea className="flex-1">
        {viewMode === "split" ? (
          <div className="grid grid-cols-2">
            {/* Old Content */}
            <div className="border-r">
              <div className="bg-muted/50 p-2 text-xs font-mono text-muted-foreground">
                {file.path} (old)
              </div>
              <div className="font-mono text-sm">
                {changes.map((change, idx) => (
                  <div
                    key={idx}
                    className={`px-4 py-0.5 ${
                      change.type === "deleted"
                        ? "bg-red-500/10 text-red-600"
                        : change.type === "unchanged"
                        ? "bg-background"
                        : "bg-muted/30"
                    }`}
                  >
                    {change.oldLine && (
                      <span className="inline-block w-12 text-right text-muted-foreground mr-4">
                        {change.oldLine}
                      </span>
                    )}
                    {change.type !== "added" && (
                      <span className={change.type === "deleted" ? "line-through" : ""}>
                        {change.content}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* New Content */}
            <div>
              <div className="bg-muted/50 p-2 text-xs font-mono text-muted-foreground">
                {file.path} (new)
              </div>
              <div className="font-mono text-sm">
                {changes.map((change, idx) => (
                  <div
                    key={idx}
                    className={`px-4 py-0.5 ${
                      change.type === "added"
                        ? "bg-green-500/10 text-green-600"
                        : change.type === "unchanged"
                        ? "bg-background"
                        : "bg-muted/30"
                    }`}
                  >
                    {change.newLine && (
                      <span className="inline-block w-12 text-right text-muted-foreground mr-4">
                        {change.newLine}
                      </span>
                    )}
                    {change.type !== "deleted" && <span>{change.content}</span>}
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="font-mono text-sm">
            {changes.map((change, idx) => (
              <div
                key={idx}
                className={`px-4 py-0.5 ${
                  change.type === "added"
                    ? "bg-green-500/10 text-green-600"
                    : change.type === "deleted"
                    ? "bg-red-500/10 text-red-600 line-through"
                    : "bg-background"
                }`}
              >
                <span className="inline-block w-12 text-right text-muted-foreground mr-4">
                  {change.newLine || change.oldLine || ""}
                </span>
                <span className={change.type === "deleted" ? "line-through" : ""}>
                  {change.content}
                </span>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>
    </div>
  )
}
```

### `src/components/commits/CommitList.tsx`

List of commits with filtering and search.

```tsx
"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { GitCommit, Search, Filter } from "lucide-react"
import Link from "next/link"

interface Commit {
  sha: string
  message: string
  author: string
  date: string
  files_changed: number
  insertions: number
  deletions: number
  agent_id?: string
  agent_name?: string
  ticket_id?: string
}

interface CommitListProps {
  commits: Commit[]
  ticketId?: string
  projectId?: string
}

export function CommitList({ commits, ticketId, projectId }: CommitListProps) {
  const [searchQuery, setSearchQuery] = useState("")

  const filteredCommits = commits.filter(
    (commit) =>
      commit.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      commit.sha.toLowerCase().includes(searchQuery.toLowerCase()) ||
      commit.author.toLowerCase().includes(searchQuery.toLowerCase())
  )

  return (
    <div className="flex flex-col gap-4">
      {/* Search & Filters */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search commits..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10"
          />
        </div>
        <Button variant="outline" size="icon">
          <Filter className="h-4 w-4" />
        </Button>
      </div>

      {/* Commit List */}
      <ScrollArea className="h-[600px]">
        <div className="flex flex-col gap-2">
          {filteredCommits.map((commit) => (
            <Link
              key={commit.sha}
              href={`/commits/${commit.sha}`}
              className="block"
            >
              <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-2">
                        <GitCommit className="h-4 w-4 text-muted-foreground" />
                        <code className="text-sm font-mono text-muted-foreground">
                          {commit.sha.slice(0, 8)}
                        </code>
                        {commit.agent_name && (
                          <Badge variant="outline" className="text-xs">
                            {commit.agent_name}
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm font-medium line-clamp-2 mb-2">
                        {commit.message}
                      </p>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground">
                        <span>{commit.author}</span>
                        <span>{new Date(commit.date).toLocaleDateString()}</span>
                        <span>{commit.files_changed} files</span>
                        <span className="text-green-600">+{commit.insertions}</span>
                        <span className="text-red-600">-{commit.deletions}</span>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}
```

---

## 16. Statistics & Charts Components

### `src/components/statistics/StatisticsDashboard.tsx`

Main statistics dashboard with multiple metric cards.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { TicketStats } from "./TicketStats"
import { AgentStats } from "./AgentStats"
import { CommitStats } from "./CommitStats"
import { CostChart } from "./CostChart"

export function StatisticsDashboard({ projectId }: { projectId?: string }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Statistics Dashboard</h1>
        <p className="text-muted-foreground">Analytics and insights for your project</p>
      </div>

      <Tabs defaultValue="overview" className="w-full">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="tickets">Tickets</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="commits">Commits</TabsTrigger>
          <TabsTrigger value="cost">Cost</TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Total Tickets</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">124</div>
                <p className="text-xs text-muted-foreground">+12% from last month</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Completion Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">87%</div>
                <p className="text-xs text-muted-foreground">+5% from last month</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Active Agents</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">5</div>
                <p className="text-xs text-muted-foreground">2 available</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader>
                <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">$1,234</div>
                <p className="text-xs text-muted-foreground">This month</p>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="tickets">
          <TicketStats projectId={projectId} />
        </TabsContent>

        <TabsContent value="agents">
          <AgentStats projectId={projectId} />
        </TabsContent>

        <TabsContent value="commits">
          <CommitStats projectId={projectId} />
        </TabsContent>

        <TabsContent value="cost">
          <CostChart projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

### `src/components/statistics/TicketStats.tsx`

Ticket-specific statistics with charts.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts"

const statusData = [
  { name: "Backlog", value: 12 },
  { name: "To Do", value: 8 },
  { name: "In Progress", value: 15 },
  { name: "Done", value: 89 },
]

const priorityData = [
  { name: "Critical", value: 5 },
  { name: "High", value: 18 },
  { name: "Medium", value: 45 },
  { name: "Low", value: 56 },
]

const COLORS = ["#ef4444", "#f59e0b", "#3b82f6", "#10b981"]

export function TicketStats({ projectId }: { projectId?: string }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <Card>
        <CardHeader>
          <CardTitle>Tickets by Status</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={statusData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {statusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Tickets by Priority</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={priorityData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" fill="#3b82f6" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
```

### `src/components/statistics/AgentStats.tsx`

Agent performance statistics.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from "recharts"

const agentPerformance = [
  { name: "Agent 1", tasks: 45, commits: 23, lines: 1234 },
  { name: "Agent 2", tasks: 38, commits: 19, lines: 987 },
  { name: "Agent 3", tasks: 52, commits: 31, lines: 1567 },
]

export function AgentStats({ projectId }: { projectId?: string }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Agent Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={agentPerformance}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="tasks" fill="#3b82f6" name="Tasks Completed" />
              <Bar dataKey="commits" fill="#10b981" name="Commits" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
```

### `src/components/statistics/CommitStats.tsx`

Commit and code change statistics.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from "recharts"

const commitData = [
  { date: "2025-01-01", commits: 12, insertions: 450, deletions: 120 },
  { date: "2025-01-02", commits: 8, insertions: 320, deletions: 80 },
  { date: "2025-01-03", commits: 15, insertions: 580, deletions: 150 },
]

export function CommitStats({ projectId }: { projectId?: string }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Commits Over Time</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={commitData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="commits" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
            </AreaChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  )
}
```

### `src/components/statistics/CostChart.tsx`

Cost tracking visualization.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const costData = [
  { date: "2025-01-01", cost: 45.2 },
  { date: "2025-01-02", cost: 52.8 },
  { date: "2025-01-03", cost: 38.5 },
]

export function CostChart({ projectId }: { projectId?: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost Over Time</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={costData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="cost" stroke="#f59e0b" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
```

---

## 17. Search Components

### `src/components/search/SearchBar.tsx`

Global search bar with autocomplete.

```tsx
"use client"

import { useState } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Search, FileText, User, GitCommit } from "lucide-react"
import { useRouter } from "next/navigation"

export function SearchBar() {
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState("")
  const router = useRouter()

  // Mock search results - would come from API
  const results = [
    { type: "ticket", id: "T-123", title: "Implement authentication", icon: FileText },
    { type: "agent", id: "agent-1", title: "worker-9a781fc3", icon: User },
    { type: "commit", id: "abc123", title: "Add OAuth2 provider", icon: GitCommit },
  ]

  const handleSelect = (item: any) => {
    if (item.type === "ticket") {
      router.push(`/board/${item.id}`)
    } else if (item.type === "agent") {
      router.push(`/agents/${item.id}`)
    } else if (item.type === "commit") {
      router.push(`/commits/${item.id}`)
    }
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <div className="relative w-full max-w-md">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search tickets, agents, commits..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setOpen(true)}
            className="pl-10"
          />
        </div>
      </PopoverTrigger>
      <PopoverContent className="w-[400px] p-0" align="start">
        <Command>
          <CommandInput placeholder="Search..." value={query} onValueChange={setQuery} />
          <CommandList>
            <CommandEmpty>No results found.</CommandEmpty>
            <CommandGroup heading="Results">
              {results.map((item) => {
                const Icon = item.icon
                return (
                  <CommandItem key={item.id} onSelect={() => handleSelect(item)}>
                    <Icon className="mr-2 h-4 w-4" />
                    <span>{item.title}</span>
                  </CommandItem>
                )
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}
```

### `src/components/search/SearchResults.tsx`

Full search results page component.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import Link from "next/link"

interface SearchResult {
  type: "ticket" | "task" | "agent" | "commit" | "file"
  id: string
  title: string
  description?: string
  metadata?: Record<string, any>
}

interface SearchResultsProps {
  query: string
  results: SearchResult[]
}

export function SearchResults({ query, results }: SearchResultsProps) {
  const grouped = results.reduce((acc, result) => {
    if (!acc[result.type]) acc[result.type] = []
    acc[result.type].push(result)
    return acc
  }, {} as Record<string, SearchResult[]>)

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-2xl font-bold">Search Results</h1>
        <p className="text-muted-foreground">Found {results.length} results for "{query}"</p>
      </div>

      <Tabs defaultValue="all" className="w-full">
        <TabsList>
          <TabsTrigger value="all">All ({results.length})</TabsTrigger>
          <TabsTrigger value="tickets">Tickets ({grouped.ticket?.length || 0})</TabsTrigger>
          <TabsTrigger value="agents">Agents ({grouped.agent?.length || 0})</TabsTrigger>
          <TabsTrigger value="commits">Commits ({grouped.commit?.length || 0})</TabsTrigger>
        </TabsList>

        <TabsContent value="all" className="space-y-2">
          {results.map((result) => (
            <Link key={result.id} href={`/${result.type}s/${result.id}`}>
              <Card className="hover:bg-muted/50 transition-colors">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <Badge variant="outline">{result.type}</Badge>
                        <span className="font-semibold">{result.title}</span>
                      </div>
                      {result.description && (
                        <p className="text-sm text-muted-foreground">{result.description}</p>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          ))}
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

---

## 18. Ticket Detail Components

### `src/components/tickets/TicketDetailView.tsx`

Comprehensive ticket detail view with tabs.

```tsx
"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Button } from "@/components/ui/button"
import { StatusBadge } from "@/components/shared/StatusBadge"
import { PriorityIcon } from "@/components/shared/PriorityIcon"
import { CommentThread } from "../comments/CommentThread"
import { CommitList } from "../commits/CommitList"
import { GraphView } from "../graph/GraphView"
import { FileText, MessageSquare, GitCommit, Network, History } from "lucide-react"

interface Ticket {
  id: string
  title: string
  description: string
  status: string
  priority: string
  phase_id: string
  created_at: string
  updated_at: string
}

interface TicketDetailViewProps {
  ticket: Ticket
}

export function TicketDetailView({ ticket }: TicketDetailViewProps) {
  return (
    <div className="flex flex-col gap-4">
      {/* Ticket Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-2">
                <StatusBadge status={ticket.status} />
                <PriorityIcon priority={ticket.priority} />
                <span className="text-sm text-muted-foreground">{ticket.phase_id}</span>
              </div>
              <CardTitle className="text-xl mb-2">{ticket.title}</CardTitle>
              <p className="text-muted-foreground">{ticket.description}</p>
            </div>
            <div className="flex gap-2">
              <Button variant="outline">Edit</Button>
              <Button>Assign Agent</Button>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Tabs */}
      <Tabs defaultValue="details" className="w-full">
        <TabsList>
          <TabsTrigger value="details">
            <FileText className="h-4 w-4 mr-2" /> Details
          </TabsTrigger>
          <TabsTrigger value="tasks">
            Tasks
          </TabsTrigger>
          <TabsTrigger value="commits">
            <GitCommit className="h-4 w-4 mr-2" /> Commits
          </TabsTrigger>
          <TabsTrigger value="graph">
            <Network className="h-4 w-4 mr-2" /> Graph
          </TabsTrigger>
          <TabsTrigger value="comments">
            <MessageSquare className="h-4 w-4 mr-2" /> Comments
          </TabsTrigger>
          <TabsTrigger value="audit">
            <History className="h-4 w-4 mr-2" /> Audit
          </TabsTrigger>
        </TabsList>

        <TabsContent value="details">
          <Card>
            <CardHeader>
              <CardTitle>Ticket Details</CardTitle>
            </CardHeader>
            <CardContent>
              {/* Details content */}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="commits">
          <CommitList commits={[]} ticketId={ticket.id} />
        </TabsContent>

        <TabsContent value="graph">
          <GraphView ticketId={ticket.id} />
        </TabsContent>

        <TabsContent value="comments">
          <CommentThread ticketId={ticket.id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

---

## 19. Comments & Collaboration Components

### `src/components/comments/CommentThread.tsx`

Threaded comment display with replies.

```tsx
"use client"

import { useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { CommentEditor } from "./CommentEditor"
import { MessageSquare, Reply } from "lucide-react"

interface Comment {
  id: string
  author: string
  author_avatar?: string
  content: string
  created_at: string
  replies?: Comment[]
  mentions?: string[]
  attachments?: Array<{ name: string; url: string }>
}

interface CommentThreadProps {
  ticketId: string
  comments?: Comment[]
}

export function CommentThread({ ticketId, comments = [] }: CommentThreadProps) {
  const [replyingTo, setReplyingTo] = useState<string | null>(null)

  return (
    <div className="flex flex-col gap-4">
      <CommentEditor ticketId={ticketId} />

      <div className="space-y-4">
        {comments.map((comment) => (
          <Card key={comment.id}>
            <CardContent className="p-4">
              <div className="flex gap-3">
                <Avatar>
                  <AvatarImage src={comment.author_avatar} />
                  <AvatarFallback>{comment.author.slice(0, 2).toUpperCase()}</AvatarFallback>
                </Avatar>
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="font-semibold text-sm">{comment.author}</span>
                    <span className="text-xs text-muted-foreground">
                      {new Date(comment.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-sm mb-2">{comment.content}</p>
                  {comment.attachments && comment.attachments.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-2">
                      {comment.attachments.map((att, idx) => (
                        <a
                          key={idx}
                          href={att.url}
                          className="text-xs text-primary hover:underline"
                        >
                          📎 {att.name}
                        </a>
                      ))}
                    </div>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setReplyingTo(replyingTo === comment.id ? null : comment.id)}
                  >
                    <Reply className="h-3 w-3 mr-1" /> Reply
                  </Button>
                  {replyingTo === comment.id && (
                    <div className="mt-2">
                      <CommentEditor ticketId={ticketId} parentId={comment.id} />
                    </div>
                  )}
                  {comment.replies && comment.replies.length > 0 && (
                    <div className="mt-4 ml-6 space-y-2">
                      {comment.replies.map((reply) => (
                        <Card key={reply.id}>
                          <CardContent className="p-3">
                            <div className="flex gap-2">
                              <Avatar className="h-6 w-6">
                                <AvatarFallback className="text-xs">
                                  {reply.author.slice(0, 2).toUpperCase()}
                                </AvatarFallback>
                              </Avatar>
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="text-xs font-semibold">{reply.author}</span>
                                  <span className="text-xs text-muted-foreground">
                                    {new Date(reply.created_at).toLocaleString()}
                                  </span>
                                </div>
                                <p className="text-xs mt-1">{reply.content}</p>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

### `src/components/comments/CommentEditor.tsx`

Rich text comment editor with mentions and attachments.

```tsx
"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Paperclip, Send } from "lucide-react"

interface CommentEditorProps {
  ticketId: string
  parentId?: string
}

export function CommentEditor({ ticketId, parentId }: CommentEditorProps) {
  const [content, setContent] = useState("")

  const handleSubmit = () => {
    // Submit comment via API
    console.log("Submitting comment", { ticketId, parentId, content })
    setContent("")
  }

  return (
    <div className="flex flex-col gap-2">
      <Textarea
        placeholder="Add a comment..."
        value={content}
        onChange={(e) => setContent(e.target.value)}
        rows={3}
      />
      <div className="flex items-center justify-between">
        <Button variant="ghost" size="sm">
          <Paperclip className="h-4 w-4 mr-2" /> Attach
        </Button>
        <Button onClick={handleSubmit} disabled={!content.trim()}>
          <Send className="h-4 w-4 mr-2" /> Post Comment
        </Button>
      </div>
    </div>
  )
}
```

---

## 20. GitHub Integration Components

### `src/components/github/GitHubIntegration.tsx`

GitHub repository connection and webhook management.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, XCircle, ExternalLink } from "lucide-react"

interface GitHubRepo {
  owner: string
  name: string
  connected: boolean
  webhook_active: boolean
}

export function GitHubIntegration({ projectId }: { projectId: string }) {
  const [repo, setRepo] = useState<GitHubRepo | null>(null)
  const [repoInput, setRepoInput] = useState("")
  
  // Note: useState import needed at top of file

  return (
    <Card>
      <CardHeader>
        <CardTitle>GitHub Integration</CardTitle>
        <CardDescription>Connect your GitHub repository for automatic commit tracking</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!repo ? (
          <div className="flex gap-2">
            <Input
              placeholder="owner/repo"
              value={repoInput}
              onChange={(e) => setRepoInput(e.target.value)}
            />
            <Button>Connect</Button>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="font-medium">{repo.owner}/{repo.name}</span>
                <a href={`https://github.com/${repo.owner}/${repo.name}`} target="_blank" rel="noopener noreferrer">
                  <ExternalLink className="h-4 w-4 text-muted-foreground" />
                </a>
              </div>
              <Badge variant={repo.connected ? "default" : "destructive"}>
                {repo.connected ? "Connected" : "Disconnected"}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">Webhook Status:</span>
              {repo.webhook_active ? (
                <div className="flex items-center gap-1 text-green-600">
                  <CheckCircle2 className="h-4 w-4" />
                  <span className="text-sm">Active</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-red-600">
                  <XCircle className="h-4 w-4" />
                  <span className="text-sm">Inactive</span>
                </div>
              )}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" size="sm">Reconnect</Button>
              <Button variant="outline" size="sm">Test Webhook</Button>
              <Button variant="destructive" size="sm">Disconnect</Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
```

---

## 21. Cost Tracking Components

### `src/components/cost/CostDashboard.tsx`

Cost tracking dashboard with breakdowns.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { CostChart } from "../statistics/CostChart"
import { CostBreakdown } from "./CostBreakdown"
import { BudgetAlerts } from "./BudgetAlerts"

export function CostDashboard({ projectId }: { projectId?: string }) {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Cost Tracking</h1>
        <p className="text-muted-foreground">Monitor and manage project costs</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Total Cost</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$1,234.56</div>
            <p className="text-xs text-muted-foreground">This month</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Budget</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$5,000.00</div>
            <p className="text-xs text-muted-foreground">Remaining: $3,765.44</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Forecast</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">$2,468</div>
            <p className="text-xs text-muted-foreground">End of month</p>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="chart" className="w-full">
        <TabsList>
          <TabsTrigger value="chart">Chart</TabsTrigger>
          <TabsTrigger value="breakdown">Breakdown</TabsTrigger>
          <TabsTrigger value="alerts">Alerts</TabsTrigger>
        </TabsList>

        <TabsContent value="chart">
          <CostChart projectId={projectId} />
        </TabsContent>

        <TabsContent value="breakdown">
          <CostBreakdown projectId={projectId} />
        </TabsContent>

        <TabsContent value="alerts">
          <BudgetAlerts projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
```

### `src/components/cost/CostBreakdown.tsx`

Cost breakdown by agent, task, or phase.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"

const costData = [
  { agent: "worker-1", tasks: 12, cost: 234.56 },
  { agent: "worker-2", tasks: 8, cost: 189.23 },
]

export function CostBreakdown({ projectId }: { projectId?: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Cost by Agent</CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Agent</TableHead>
              <TableHead>Tasks</TableHead>
              <TableHead className="text-right">Cost</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {costData.map((row) => (
              <TableRow key={row.agent}>
                <TableCell>{row.agent}</TableCell>
                <TableCell>{row.tasks}</TableCell>
                <TableCell className="text-right">${row.cost.toFixed(2)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  )
}
```

### `src/components/cost/BudgetAlerts.tsx`

Budget threshold warnings and alerts.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { AlertTriangle } from "lucide-react"

export function BudgetAlerts({ projectId }: { projectId?: string }) {
  return (
    <div className="space-y-4">
      <Alert>
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Budget Warning</AlertTitle>
        <AlertDescription>
          Project has used 75% of allocated budget. Consider reviewing costs.
        </AlertDescription>
      </Alert>
    </div>
  )
}
```

---

## 22. Authentication Components

### `src/components/auth/AuthGuard.tsx`

Route protection component that redirects unauthenticated users.

```tsx
"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Loader2 } from "lucide-react"

interface AuthGuardProps {
  children: React.ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null)

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem("auth_token")
      
      if (!token) {
        router.push("/auth/login")
        return
      }

      try {
        const res = await fetch("/api/v1/auth/me", {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })

        if (!res.ok) {
          localStorage.removeItem("auth_token")
          router.push("/auth/login")
          return
        }

        setIsAuthenticated(true)
      } catch (error) {
        localStorage.removeItem("auth_token")
        router.push("/auth/login")
      }
    }

    checkAuth()
  }, [router])

  if (isAuthenticated === null) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return null
  }

  return <>{children}</>
}
```

### `src/components/auth/LogoutButton.tsx`

Logout button component.

```tsx
"use client"

import { Button } from "@/components/ui/button"
import { LogOut } from "lucide-react"
import { useRouter } from "next/navigation"

export function LogoutButton() {
  const router = useRouter()

  const handleLogout = async () => {
    try {
      const token = localStorage.getItem("auth_token")
      if (token) {
        await fetch("/api/v1/auth/logout", {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        })
      }
    } catch (error) {
      console.error("Logout error:", error)
    } finally {
      localStorage.removeItem("auth_token")
      router.push("/auth/login")
    }
  }

  return (
    <Button variant="ghost" size="sm" onClick={handleLogout}>
      <LogOut className="mr-2 h-4 w-4" />
      Logout
    </Button>
  )
}
```

---

## 23. Specs Management Components

### `src/components/specs/SpecList.tsx`

List of specs with status and actions.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { FileText, Edit, Play, Plus } from "lucide-react"
import Link from "next/link"

interface Spec {
  id: string
  spec_name: string
  status: string
  requirements_count: number
  design_sections: number
  tasks_count: number
  properties_extracted: number
  tests_passed: number
  tests_failed: number
  linked_tickets: number
  created_at: string
}

export function SpecList({ projectId, specs }: { projectId: string; specs: Spec[] }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-between items-center">
        <h2 className="text-xl font-semibold">Specs</h2>
        <Button>
          <Plus className="mr-2 h-4 w-4" /> New Spec
        </Button>
      </div>

      <div className="grid gap-4">
        {specs.map((spec) => (
          <Card key={spec.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div>
                  <CardTitle>{spec.spec_name}</CardTitle>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant={spec.status === "completed" ? "default" : "secondary"}>
                      {spec.status}
                    </Badge>
                    <span className="text-sm text-muted-foreground">
                      Created {new Date(spec.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                <div>
                  <div className="text-sm text-muted-foreground">Requirements</div>
                  <div className="text-lg font-semibold">{spec.requirements_count}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Design Sections</div>
                  <div className="text-lg font-semibold">{spec.design_sections}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Tasks</div>
                  <div className="text-lg font-semibold">{spec.tasks_count}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">Properties</div>
                  <div className="text-lg font-semibold">
                    {spec.properties_extracted} | {spec.tests_passed}/{spec.tests_passed + spec.tests_failed} passed
                  </div>
                </div>
              </div>
              <div className="flex gap-2">
                <Link href={`/projects/${projectId}/specs/${spec.id}`}>
                  <Button variant="outline" size="sm">
                    <FileText className="mr-2 h-4 w-4" /> View Spec
                  </Button>
                </Link>
                <Button variant="outline" size="sm">
                  <Edit className="mr-2 h-4 w-4" /> Edit
                </Button>
                <Button variant="outline" size="sm">
                  <Play className="mr-2 h-4 w-4" /> Run Tests
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

### `src/components/specs/SpecViewer.tsx`

Spec viewer with tabs for requirements, design, and tasks.

```tsx
"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { FileText, Code, ListChecks } from "lucide-react"

interface SpecViewerProps {
  specId: string
  requirements?: string
  design?: string
  tasks?: string
}

export function SpecViewer({ specId, requirements, design, tasks }: SpecViewerProps) {
  return (
    <Tabs defaultValue="requirements" className="w-full">
      <TabsList>
        <TabsTrigger value="requirements">
          <FileText className="mr-2 h-4 w-4" /> Requirements
        </TabsTrigger>
        <TabsTrigger value="design">
          <Code className="mr-2 h-4 w-4" /> Design
        </TabsTrigger>
        <TabsTrigger value="tasks">
          <ListChecks className="mr-2 h-4 w-4" /> Tasks
        </TabsTrigger>
      </TabsList>

      <TabsContent value="requirements">
        <Card>
          <CardHeader>
            <CardTitle>Requirements (EARS Notation)</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px]">
              <pre className="whitespace-pre-wrap font-mono text-sm">{requirements || "No requirements"}</pre>
            </ScrollArea>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="design">
        <Card>
          <CardHeader>
            <CardTitle>Design Notes</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px]">
              <pre className="whitespace-pre-wrap font-mono text-sm">{design || "No design notes"}</pre>
            </ScrollArea>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent value="tasks">
        <Card>
          <CardHeader>
            <CardTitle>Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[600px]">
              <pre className="whitespace-pre-wrap font-mono text-sm">{tasks || "No tasks"}</pre>
            </ScrollArea>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  )
}
```

### `src/components/specs/PropertyExtractor.tsx`

Property extraction and PBT test runner.

```tsx
"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { CheckCircle2, XCircle, Play, Loader2 } from "lucide-react"

interface Property {
  id: string
  property_statement: string
  property_type: string
  test_generated: boolean
  last_test_result?: "passed" | "failed" | "not_run"
  test_cases?: number
}

export function PropertyExtractor({ specId, properties }: { specId: string; properties: Property[] }) {
  const [running, setRunning] = useState<string | null>(null)

  const handleRunTest = async (propertyId: string) => {
    setRunning(propertyId)
    // Call API to run PBT test
    await new Promise(resolve => setTimeout(resolve, 2000))
    setRunning(null)
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Extracted Properties</h3>
        <Button>Extract Properties</Button>
      </div>

      <div className="space-y-2">
        {properties.map((prop) => (
          <Card key={prop.id}>
            <CardContent className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline">{prop.property_type}</Badge>
                    {prop.last_test_result === "passed" && (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    )}
                    {prop.last_test_result === "failed" && (
                      <XCircle className="h-4 w-4 text-red-600" />
                    )}
                  </div>
                  <p className="text-sm">{prop.property_statement}</p>
                  {prop.test_cases && (
                    <p className="text-xs text-muted-foreground mt-1">
                      {prop.test_cases} test cases
                    </p>
                  )}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleRunTest(prop.id)}
                  disabled={running === prop.id || !prop.test_generated}
                >
                  {running === prop.id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Play className="h-4 w-4" />
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
```

---

## 24. Validation Review Components

### `src/components/validation/ValidationReviewPanel.tsx`

Validation review submission panel for validator agents.

```tsx
"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { CheckCircle2, XCircle } from "lucide-react"

interface ValidationReviewPanelProps {
  taskId: string
  onSubmit: (review: {
    validation_passed: boolean
    feedback: string
    evidence?: string
    recommendations?: string
  }) => void
}

export function ValidationReviewPanel({ taskId, onSubmit }: ValidationReviewPanelProps) {
  const [passed, setPassed] = useState<boolean | null>(null)
  const [feedback, setFeedback] = useState("")
  const [evidence, setEvidence] = useState("")
  const [recommendations, setRecommendations] = useState("")

  const handleSubmit = () => {
    if (passed === null) return
    
    onSubmit({
      validation_passed: passed,
      feedback,
      evidence,
      recommendations,
    })
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Validation Review</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label>Validation Result</Label>
          <RadioGroup value={passed === null ? "" : passed ? "passed" : "failed"} onValueChange={(v) => setPassed(v === "passed")}>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="passed" id="passed" />
              <Label htmlFor="passed" className="flex items-center gap-2 cursor-pointer">
                <CheckCircle2 className="h-4 w-4 text-green-600" />
                Passed
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <RadioGroupItem value="failed" id="failed" />
              <Label htmlFor="failed" className="flex items-center gap-2 cursor-pointer">
                <XCircle className="h-4 w-4 text-red-600" />
                Needs Work
              </Label>
            </div>
          </RadioGroup>
        </div>

        <div className="space-y-2">
          <Label htmlFor="feedback">Feedback</Label>
          <Textarea
            id="feedback"
            placeholder="Provide detailed feedback..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={4}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="evidence">Evidence</Label>
          <Textarea
            id="evidence"
            placeholder="Evidence supporting your review..."
            value={evidence}
            onChange={(e) => setEvidence(e.target.value)}
            rows={3}
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="recommendations">Recommendations</Label>
          <Textarea
            id="recommendations"
            placeholder="Recommendations for improvement..."
            value={recommendations}
            onChange={(e) => setRecommendations(e.target.value)}
            rows={3}
          />
        </div>

        <Button onClick={handleSubmit} disabled={passed === null || !feedback.trim()}>
          Submit Review
        </Button>
      </CardContent>
    </Card>
  )
}
```

---

## 25. Guardian Intervention Components

### `src/components/guardian/InterventionViewer.tsx`

Display Guardian interventions and steering messages.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AlertTriangle, MessageSquare, Clock } from "lucide-react"

interface Intervention {
  id: string
  action_type: "steering_message" | "cancel_task" | "reallocate" | "override_priority"
  target_entity: string
  reason: string
  message?: string
  timestamp: string
  delivered: boolean
}

export function InterventionViewer({ interventions }: { interventions: Intervention[] }) {
  return (
    <div className="space-y-4">
      {interventions.map((intervention) => (
        <Card key={intervention.id}>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-amber-600" />
                <CardTitle className="text-lg">
                  {intervention.action_type.replace("_", " ").replace(/\b\w/g, l => l.toUpperCase())}
                </CardTitle>
              </div>
              <Badge variant={intervention.delivered ? "default" : "secondary"}>
                {intervention.delivered ? "Delivered" : "Pending"}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Clock className="h-4 w-4" />
                {new Date(intervention.timestamp).toLocaleString()}
              </div>
              <p className="text-sm">{intervention.reason}</p>
              {intervention.message && (
                <div className="mt-3 p-3 bg-muted rounded-md">
                  <div className="flex items-center gap-2 mb-2">
                    <MessageSquare className="h-4 w-4" />
                    <span className="text-sm font-semibold">Intervention Message</span>
                  </div>
                  <p className="text-sm">{intervention.message}</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

---

## 26. Discovery Tracking Components

### `src/components/discovery/DiscoveryViewer.tsx`

Display agent discoveries and workflow branching.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Bug, Lightbulb, AlertCircle, Link2 } from "lucide-react"
import Link from "next/link"

interface Discovery {
  id: string
  discovery_type: "bug" | "optimization" | "missing_requirement" | "dependency_issue" | "security"
  description: string
  discovered_by: string
  discovered_at: string
  spawned_tasks: Array<{ id: string; title: string }>
  resolved: boolean
}

const typeIcons = {
  bug: Bug,
  optimization: Lightbulb,
  missing_requirement: AlertCircle,
  dependency_issue: Link2,
  security: AlertCircle,
}

export function DiscoveryViewer({ discoveries }: { discoveries: Discovery[] }) {
  return (
    <div className="space-y-4">
      {discoveries.map((discovery) => {
        const Icon = typeIcons[discovery.discovery_type] || AlertCircle
        
        return (
          <Card key={discovery.id}>
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex items-center gap-2">
                  <Icon className="h-5 w-5 text-amber-600" />
                  <CardTitle className="text-lg capitalize">
                    {discovery.discovery_type.replace("_", " ")}
                  </CardTitle>
                </div>
                <Badge variant={discovery.resolved ? "default" : "secondary"}>
                  {discovery.resolved ? "Resolved" : "Open"}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <p className="text-sm mb-3">{discovery.description}</p>
              <div className="flex items-center gap-4 text-xs text-muted-foreground mb-3">
                <span>Discovered by: {discovery.discovered_by}</span>
                <span>{new Date(discovery.discovered_at).toLocaleString()}</span>
              </div>
              {discovery.spawned_tasks.length > 0 && (
                <div>
                  <div className="text-sm font-semibold mb-2">Spawned Tasks:</div>
                  <div className="space-y-1">
                    {discovery.spawned_tasks.map((task) => (
                      <Link
                        key={task.id}
                        href={`/tasks/${task.id}`}
                        className="block text-sm text-primary hover:underline"
                      >
                        • {task.title}
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )
      })}
    </div>
  )
}
```

---

## 27. Time Tracking Components

### `src/components/time/TimeTracker.tsx`

Manual time entry component.

```tsx
"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Clock, Play, Square } from "lucide-react"

export function TimeTracker({ ticketId }: { ticketId: string }) {
  const [isRunning, setIsRunning] = useState(false)
  const [elapsed, setElapsed] = useState(0)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="h-5 w-5" />
          Time Tracker
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="text-center">
          <div className="text-3xl font-bold">
            {Math.floor(elapsed / 3600).toString().padStart(2, "0")}:
            {Math.floor((elapsed % 3600) / 60).toString().padStart(2, "0")}:
            {(elapsed % 60).toString().padStart(2, "0")}
          </div>
        </div>
        <div className="flex gap-2 justify-center">
          {!isRunning ? (
            <Button onClick={() => setIsRunning(true)}>
              <Play className="mr-2 h-4 w-4" /> Start
            </Button>
          ) : (
            <Button variant="destructive" onClick={() => setIsRunning(false)}>
              <Square className="mr-2 h-4 w-4" /> Stop
            </Button>
          )}
        </div>
        <div className="space-y-2">
          <Label>Manual Entry</Label>
          <div className="flex gap-2">
            <Input type="number" placeholder="Hours" />
            <Input type="number" placeholder="Minutes" />
            <Button variant="outline">Add</Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
```

### `src/components/time/TimeChart.tsx`

Time breakdown visualization.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"

const timeData = [
  { phase: "Initial", time: 120 },
  { phase: "Implementation", time: 480 },
  { phase: "Integration", time: 180 },
  { phase: "Refactoring", time: 90 },
]

export function TimeChart({ projectId }: { projectId?: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Time by Phase</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={timeData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="phase" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="time" fill="#3b82f6" />
          </BarChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  )
}
```

---

## 28. File Attachment Components

### `src/components/attachments/FileUploader.tsx`

Drag-and-drop file upload component.

```tsx
"use client"

import { useState, useCallback } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Upload, X } from "lucide-react"

interface FileUploaderProps {
  onUpload: (files: File[]) => void
  maxSize?: number
  accept?: string
}

export function FileUploader({ onUpload, maxSize = 10 * 1024 * 1024, accept }: FileUploaderProps) {
  const [files, setFiles] = useState<File[]>([])
  const [isDragging, setIsDragging] = useState(false)

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    
    const droppedFiles = Array.from(e.dataTransfer.files)
    const validFiles = droppedFiles.filter(f => f.size <= maxSize)
    setFiles(prev => [...prev, ...validFiles])
  }, [maxSize])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      const selectedFiles = Array.from(e.target.files)
      const validFiles = selectedFiles.filter(f => f.size <= maxSize)
      setFiles(prev => [...prev, ...validFiles])
    }
  }

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index))
  }

  const handleUpload = () => {
    onUpload(files)
    setFiles([])
  }

  return (
    <div className="space-y-4">
      <Card
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={isDragging ? "border-primary border-2" : ""}
      >
        <CardContent className="p-8 text-center">
          <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
          <p className="text-sm text-muted-foreground mb-4">
            Drag and drop files here, or click to select
          </p>
          <input
            type="file"
            multiple
            accept={accept}
            onChange={handleFileSelect}
            className="hidden"
            id="file-upload"
          />
          <Button variant="outline" onClick={() => document.getElementById("file-upload")?.click()}>
            Select Files
          </Button>
        </CardContent>
      </Card>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((file, index) => (
            <div key={index} className="flex items-center justify-between p-2 border rounded">
              <span className="text-sm truncate flex-1">{file.name}</span>
              <span className="text-xs text-muted-foreground mr-2">
                {(file.size / 1024).toFixed(1)} KB
              </span>
              <Button variant="ghost" size="sm" onClick={() => removeFile(index)}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <Button onClick={handleUpload} className="w-full">
            Upload {files.length} file{files.length !== 1 ? "s" : ""}
          </Button>
        </div>
      )}
    </div>
  )
}
```

### `src/components/attachments/FilePreview.tsx`

File preview modal/viewer.

```tsx
"use client"

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Download, X } from "lucide-react"

interface FilePreviewProps {
  file: {
    name: string
    url: string
    type: string
    size: number
  }
  open: boolean
  onClose: () => void
}

export function FilePreview({ file, open, onClose }: FilePreviewProps) {
  const isImage = file.type.startsWith("image/")
  const isPdf = file.type === "application/pdf"

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>{file.name}</DialogTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" asChild>
                <a href={file.url} download>
                  <Download className="mr-2 h-4 w-4" /> Download
                </a>
              </Button>
              <Button variant="ghost" size="sm" onClick={onClose}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </DialogHeader>
        <div className="max-h-[600px] overflow-auto">
          {isImage && <img src={file.url} alt={file.name} className="max-w-full" />}
          {isPdf && <iframe src={file.url} className="w-full h-[600px]" />}
          {!isImage && !isPdf && (
            <div className="text-center p-8 text-muted-foreground">
              Preview not available for this file type
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

---

## 29. Template Components

### `src/components/templates/TemplateSelector.tsx`

Template selection for ticket/task creation.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { FileText } from "lucide-react"

interface Template {
  id: string
  name: string
  description: string
  type: "ticket" | "task" | "project"
}

export function TemplateSelector({
  templates,
  onSelect,
}: {
  templates: Template[]
  onSelect: (template: Template) => void
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {templates.map((template) => (
        <Card
          key={template.id}
          className="hover:bg-muted/50 transition-colors cursor-pointer"
          onClick={() => onSelect(template)}
        >
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              {template.name}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground mb-4">{template.description}</p>
            <Badge variant="outline">{template.type}</Badge>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
```

---

## 30. Bulk Operations Components

### `src/components/bulk/BulkActionBar.tsx`

Bulk action toolbar for selected items.

```tsx
"use client"

import { Button } from "@/components/ui/button"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Trash2, Edit, CheckCircle2 } from "lucide-react"

interface BulkActionBarProps {
  selectedCount: number
  onBulkAction: (action: string) => void
}

export function BulkActionBar({ selectedCount, onBulkAction }: BulkActionBarProps) {
  if (selectedCount === 0) return null

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-background border-t p-4 shadow-lg z-50">
      <div className="flex items-center justify-between max-w-7xl mx-auto">
        <div className="text-sm font-medium">
          {selectedCount} item{selectedCount !== 1 ? "s" : ""} selected
        </div>
        <div className="flex gap-2">
          <Select onValueChange={onBulkAction}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Bulk actions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="update_status">
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4" />
                  Update Status
                </div>
              </SelectItem>
              <SelectItem value="assign">
                <div className="flex items-center gap-2">
                  <Edit className="h-4 w-4" />
                  Assign
                </div>
              </SelectItem>
              <SelectItem value="delete">
                <div className="flex items-center gap-2">
                  <Trash2 className="h-4 w-4" />
                  Delete
                </div>
              </SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </div>
  )
}
```

---

## 31. Help & Onboarding Components

### `src/components/help/HelpCenter.tsx`

Help documentation center.

```tsx
"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Search, Book, Video, HelpCircle } from "lucide-react"

export function HelpCenter() {
  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold">Help Center</h1>
        <p className="text-muted-foreground">Find answers and learn how to use the platform</p>
      </div>

      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input placeholder="Search help articles..." className="pl-10" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Book className="h-5 w-5" />
              Documentation
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Browse comprehensive guides and tutorials
            </p>
          </CardContent>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Video className="h-5 w-5" />
              Video Tutorials
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Watch step-by-step video guides
            </p>
          </CardContent>
        </Card>

        <Card className="hover:bg-muted/50 transition-colors cursor-pointer">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HelpCircle className="h-5 w-5" />
              FAQ
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Frequently asked questions
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
```

---

## 32. Theme Components

### `src/components/theme/ThemeToggle.tsx`

Dark mode toggle component.

```tsx
"use client"

import { Button } from "@/components/ui/button"
import { Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import { useEffect, useState } from "react"

export function ThemeToggle() {
  const { theme, setTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return <Button variant="ghost" size="icon" disabled><Sun className="h-4 w-4" /></Button>
  }

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
    >
      {theme === "dark" ? (
        <Sun className="h-4 w-4" />
      ) : (
        <Moon className="h-4 w-4" />
      )}
    </Button>
  )
}
```

---

## 33. Agent Spawner & Task Creator Components

### `src/components/agents/AgentSpawner.tsx`

Agent spawning dialog.

```tsx
"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Checkbox } from "@/components/ui/checkbox"
import { Plus } from "lucide-react"

export function AgentSpawner({ projectId }: { projectId?: string }) {
  const [open, setOpen] = useState(false)
  const [agentType, setAgentType] = useState("worker")
  const [phase, setPhase] = useState("PHASE_IMPLEMENTATION")
  const [allowDiscoveries, setAllowDiscoveries] = useState(true)

  const handleSpawn = async () => {
    // Call API to spawn agent
    await fetch("/api/v1/agents/spawn", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project_id: projectId,
        agent_type: agentType,
        phase_id: phase,
        allow_discoveries: allowDiscoveries,
      }),
    })
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" /> Spawn Agent
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Spawn Agent</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Agent Type</Label>
            <Select value={agentType} onValueChange={setAgentType}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="worker">Worker</SelectItem>
                <SelectItem value="validator">Validator</SelectItem>
                <SelectItem value="guardian">Guardian</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>Phase</Label>
            <Select value={phase} onValueChange={setPhase}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="PHASE_INITIAL">Initial</SelectItem>
                <SelectItem value="PHASE_IMPLEMENTATION">Implementation</SelectItem>
                <SelectItem value="PHASE_INTEGRATION">Integration</SelectItem>
                <SelectItem value="PHASE_REFACTORING">Refactoring</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="discoveries"
              checked={allowDiscoveries}
              onCheckedChange={(checked) => setAllowDiscoveries(checked as boolean)}
            />
            <Label htmlFor="discoveries" className="cursor-pointer">
              Allow discoveries (auto-spawn tasks)
            </Label>
          </div>

          <Button onClick={handleSpawn} className="w-full">
            Spawn Agent
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

### `src/components/tasks/TaskCreator.tsx`

Task creation dialog.

```tsx
"use client"

import { useState } from "react"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Input } from "@/components/ui/input"
import { Plus } from "lucide-react"

export function TaskCreator({ ticketId, projectId }: { ticketId?: string; projectId?: string }) {
  const [open, setOpen] = useState(false)
  const [description, setDescription] = useState("")
  const [priority, setPriority] = useState("medium")
  const [phase, setPhase] = useState("PHASE_IMPLEMENTATION")

  const handleCreate = async () => {
    await fetch("/api/v1/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ticket_id: ticketId,
        project_id: projectId,
        description,
        priority,
        phase_id: phase,
      }),
    })
    setOpen(false)
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus className="mr-2 h-4 w-4" /> Create Task
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create New Task</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Description</Label>
            <Textarea
              placeholder="Task description..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={4}
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Priority</Label>
              <Select value={priority} onValueChange={setPriority}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="critical">Critical</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Phase</Label>
              <Select value={phase} onValueChange={setPhase}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PHASE_INITIAL">Initial</SelectItem>
                  <SelectItem value="PHASE_IMPLEMENTATION">Implementation</SelectItem>
                  <SelectItem value="PHASE_INTEGRATION">Integration</SelectItem>
                  <SelectItem value="PHASE_REFACTORING">Refactoring</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <Button onClick={handleCreate} className="w-full" disabled={!description.trim()}>
            Create Task
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
```

---

## 34. Code Highlighting Components

### `src/components/shared/CodeBlock.tsx`

Reusable code block component with syntax highlighting.

```tsx
"use client"

import { Prism as SyntaxHighlighter } from "react-syntax-highlighter"
import { vscDarkPlus, oneLight } from "react-syntax-highlighter/dist/esm/styles/prism"
import { useTheme } from "next-themes"
import { Copy, Check } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState } from "react"
import { useClipboard } from "@/hooks/clipboard/useClipboard"

interface CodeBlockProps {
  code: string
  language?: string
  filename?: string
  showLineNumbers?: boolean
  highlightLines?: number[]
  className?: string
}

export function CodeBlock({
  code,
  language = "text",
  filename,
  showLineNumbers = true,
  highlightLines = [],
  className,
}: CodeBlockProps) {
  const { theme } = useTheme()
  const { copy, copied } = useClipboard()
  const isDark = theme === "dark"

  const handleCopy = () => {
    copy(code)
  }

  return (
    <div className={`relative group ${className}`}>
      {filename && (
        <div className="px-4 py-2 bg-muted border-b text-sm font-mono">
          {filename}
        </div>
      )}
      <div className="relative">
        <Button
          variant="ghost"
          size="sm"
          className="absolute top-2 right-2 z-10 opacity-0 group-hover:opacity-100 transition-opacity"
          onClick={handleCopy}
        >
          {copied ? (
            <Check className="h-4 w-4 text-green-600" />
          ) : (
            <Copy className="h-4 w-4" />
          )}
        </Button>
        <SyntaxHighlighter
          language={language}
          style={isDark ? vscDarkPlus : oneLight}
          showLineNumbers={showLineNumbers}
          lineNumberStyle={{ minWidth: "3em", paddingRight: "1em" }}
          customStyle={{
            margin: 0,
            borderRadius: filename ? "0 0 0.5rem 0.5rem" : "0.5rem",
            fontSize: "0.875rem",
          }}
          lineProps={(lineNumber) => {
            const isHighlighted = highlightLines.includes(lineNumber)
            return {
              style: {
                backgroundColor: isHighlighted
                  ? isDark
                    ? "rgba(255, 255, 0, 0.1)"
                    : "rgba(255, 255, 0, 0.2)"
                  : "transparent",
                display: "block",
                width: "100%",
              },
            }
          }}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  )
}
```

### `src/components/shared/InlineCode.tsx`

Inline code snippet component.

```tsx
"use client"

import { cn } from "@/lib/utils"

interface InlineCodeProps {
  children: React.ReactNode
  className?: string
}

export function InlineCode({ children, className }: InlineCodeProps) {
  return (
    <code
      className={cn(
        "relative rounded bg-muted px-[0.3rem] py-[0.2rem] font-mono text-sm font-semibold",
        className
      )}
    >
      {children}
    </code>
  )
}
```

### `src/components/shared/CodeEditor.tsx`

Editable code editor with syntax highlighting (for specs, requirements, etc.).

```tsx
"use client"

import { useState } from "react"
import { CodeBlock } from "./CodeBlock"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Edit, Save, X } from "lucide-react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface CodeEditorProps {
  code: string
  language?: string
  filename?: string
  onSave?: (code: string) => void
  readOnly?: boolean
}

export function CodeEditor({
  code: initialCode,
  language = "text",
  filename,
  onSave,
  readOnly = false,
}: CodeEditorProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [code, setCode] = useState(initialCode)

  const handleSave = () => {
    onSave?.(code)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setCode(initialCode)
    setIsEditing(false)
  }

  if (readOnly) {
    return <CodeBlock code={code} language={language} filename={filename} />
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{filename || "Code"}</CardTitle>
          {!isEditing ? (
            <Button variant="ghost" size="sm" onClick={() => setIsEditing(true)}>
              <Edit className="h-4 w-4 mr-2" /> Edit
            </Button>
          ) : (
            <div className="flex gap-2">
              <Button variant="ghost" size="sm" onClick={handleCancel}>
                <X className="h-4 w-4 mr-2" /> Cancel
              </Button>
              <Button size="sm" onClick={handleSave}>
                <Save className="h-4 w-4 mr-2" /> Save
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isEditing ? (
          <Textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="font-mono text-sm min-h-[400px]"
            placeholder="Enter code..."
          />
        ) : (
          <CodeBlock code={code} language={language} filename={filename} />
        )}
      </CardContent>
    </Card>
  )
}
```

---

## 35. Terminal Streaming Components

### `src/components/terminal/TerminalViewer.tsx`

Real-time terminal output viewer with streaming support.

```tsx
"use client"

import { useEffect, useRef, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Terminal, Copy, Trash2, Download } from "lucide-react"
import { useTerminalStream } from "@/hooks/terminal/useTerminalStream"
import { useClipboard } from "@/hooks/clipboard/useClipboard"
import { cn } from "@/lib/utils"

interface TerminalViewerProps {
  taskId?: string
  agentId?: string
  projectId?: string
  autoScroll?: boolean
  maxLines?: number
  className?: string
}

export function TerminalViewer({
  taskId,
  agentId,
  projectId,
  autoScroll = true,
  maxLines = 1000,
  className,
}: TerminalViewerProps) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const { output, isStreaming, clear } = useTerminalStream({
    taskId,
    agentId,
    projectId,
  })
  const { copy } = useClipboard()
  const [isPaused, setIsPaused] = useState(false)

  // Auto-scroll to bottom when new output arrives
  useEffect(() => {
    if (autoScroll && !isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [output, autoScroll, isPaused])

  const handleCopy = () => {
    copy(output.join("\n"))
  }

  const handleDownload = () => {
    const content = output.join("\n")
    const blob = new Blob([content], { type: "text/plain" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = `terminal-${taskId || agentId || "output"}-${Date.now()}.log`
    a.click()
    URL.revokeObjectURL(url)
  }

  // Truncate output if exceeds maxLines
  const displayOutput = output.length > maxLines 
    ? output.slice(-maxLines)
    : output

  return (
    <Card className={cn("flex flex-col", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-sm">
            <Terminal className="h-4 w-4" />
            Terminal Output
            {isStreaming && (
              <span className="text-xs text-muted-foreground font-normal">
                (streaming...)
              </span>
            )}
          </CardTitle>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsPaused(!isPaused)}
            >
              {isPaused ? "Resume" : "Pause"}
            </Button>
            <Button variant="ghost" size="sm" onClick={handleCopy}>
              <Copy className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={clear}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 min-h-0">
        <ScrollArea className="h-full" ref={scrollRef}>
          <div className="p-4 font-mono text-sm">
            {output.length > maxLines && (
              <div className="text-muted-foreground mb-2 text-xs">
                ... {output.length - maxLines} lines truncated (showing last {maxLines})
              </div>
            )}
            <pre className="whitespace-pre-wrap break-words">
              {displayOutput.map((line, idx) => (
                <div
                  key={idx}
                  className={cn(
                    "py-0.5",
                    line.startsWith("ERROR") || line.includes("error:")
                      ? "text-red-500"
                      : line.startsWith("WARN") || line.includes("warning:")
                      ? "text-yellow-500"
                      : line.startsWith("INFO") || line.includes("info:")
                      ? "text-blue-500"
                      : "text-foreground"
                  )}
                >
                  {line}
                </div>
              ))}
              {isStreaming && (
                <div className="inline-block w-2 h-4 bg-foreground animate-pulse ml-1" />
              )}
            </pre>
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
```

### `src/components/terminal/TerminalPanel.tsx`

Collapsible terminal panel for agent/task views.

```tsx
"use client"

import { useState } from "react"
import { TerminalViewer } from "./TerminalViewer"
import { Button } from "@/components/ui/button"
import { ChevronUp, ChevronDown, Terminal } from "lucide-react"
import { cn } from "@/lib/utils"

interface TerminalPanelProps {
  taskId?: string
  agentId?: string
  projectId?: string
  defaultOpen?: boolean
  className?: string
}

export function TerminalPanel({
  taskId,
  agentId,
  projectId,
  defaultOpen = false,
  className,
}: TerminalPanelProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)

  return (
    <div className={cn("border-t", className)}>
      <Button
        variant="ghost"
        className="w-full justify-between rounded-none"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4" />
          <span className="text-sm">Terminal Output</span>
        </div>
        {isOpen ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronUp className="h-4 w-4" />
        )}
      </Button>
      {isOpen && (
        <div className="h-[400px]">
          <TerminalViewer
            taskId={taskId}
            agentId={agentId}
            projectId={projectId}
          />
        </div>
      )}
    </div>
  )
}
```

---

## 36. Code Highlighting Configuration

### Syntax Highlighting Setup

**Recommended Library**: `react-syntax-highlighter` with Prism

**Installation**:
```bash
npm install react-syntax-highlighter @types/react-syntax-highlighter
```

**Theme Support**: 
- Dark mode: `vscDarkPlus`, `dracula`, `nightOwl`
- Light mode: `oneLight`, `prism`, `ghcolors`

**Language Detection**: Auto-detect from file extension or explicit `language` prop

**Performance**: Use dynamic imports for large language grammars:
```tsx
import dynamic from 'next/dynamic'

const SyntaxHighlighter = dynamic(
  () => import('react-syntax-highlighter').then(mod => mod.Prism),
  { ssr: false }
)
```

---

This completes the code highlighting and terminal streaming components documentation.
<｜tool▁calls▁begin｜><｜tool▁call▁begin｜>
read_file
