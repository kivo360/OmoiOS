# Frontend Components Scaffold

**Created**: 2025-05-19
**Status**: Scaffold Document
**Purpose**: Provides copy-paste ready React/TypeScript code for core UI components, leveraging ShadCN UI.

---

## 1. Shared UI Components

### `src/components/shared/StatusBadge.tsx`

Displays ticket/task status with appropriate coloring, animations, and theme support.

```tsx
"use client"

import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import { useMemo } from "react"
import { motion } from "framer-motion"

type StatusType = "backlog" | "todo" | "in_progress" | "done" | "canceled"

interface StatusBadgeProps {
  status: string
  className?: string
  showIcon?: boolean
  animated?: boolean
}

const STATUS_CONFIG = {
  backlog: { 
    label: "Backlog", 
    variant: "outline" as const,
    color: "text-slate-600 dark:text-slate-400",
    bg: "bg-slate-100 dark:bg-slate-800 border-slate-300 dark:border-slate-700",
    icon: "○"
  },
  todo: { 
    label: "To Do", 
    variant: "secondary" as const,
    color: "text-blue-600 dark:text-blue-400",
    bg: "bg-blue-100 dark:bg-blue-900/30 border-blue-300 dark:border-blue-700",
    icon: "◐"
  },
  in_progress: { 
    label: "In Progress", 
    variant: "default" as const,
    color: "text-amber-600 dark:text-amber-400",
    bg: "bg-amber-100 dark:bg-amber-900/30 border-amber-300 dark:border-amber-700",
    icon: "◑"
  },
  done: { 
    label: "Done", 
    variant: "secondary" as const,
    color: "text-green-600 dark:text-green-400",
    bg: "bg-green-100 dark:bg-green-900/30 border-green-300 dark:border-green-700",
    icon: "●"
  },
  canceled: { 
    label: "Canceled", 
    variant: "destructive" as const,
    color: "text-red-600 dark:text-red-400",
    bg: "bg-red-100 dark:bg-red-900/30 border-red-300 dark:border-red-700",
    icon: "✕"
  },
} as const

export function StatusBadge({ status, className, showIcon = false, animated = false }: StatusBadgeProps) {
  const config = useMemo(() => {
    const normalizedStatus = status.toLowerCase()
    return STATUS_CONFIG[normalizedStatus as StatusType] || {
      label: status,
      variant: "outline" as const,
      color: "text-muted-foreground",
      bg: "bg-muted border-border",
      icon: "•"
    }
  }, [status])
  
  const BadgeComponent = animated ? motion.div : "div"
  
  return (
    <BadgeComponent
      {...(animated && {
        whileHover: { scale: 1.05 },
        whileTap: { scale: 0.95 },
      })}
    >
      <Badge 
        variant={config.variant} 
        className={cn(
          "capitalize font-medium transition-all duration-200",
          config.color,
          config.bg,
          "border shadow-sm",
          "hover:shadow-md",
          className
        )}
      >
        {showIcon && <span className="mr-1.5">{config.icon}</span>}
      {config.label}
    </Badge>
    </BadgeComponent>
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

Real-time notification dropdown with WebSocket updates and dynamic state management.

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
import { useNotifications } from "@/hooks/useNotifications"
import { useWebSocketSubscription } from "@/hooks/useWebSocket"
import { formatDistanceToNow } from "date-fns"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"

export function NotificationCenter() {
  const { 
    data: notifications = [], 
    markAsRead, 
    markAllAsRead,
    isLoading 
  } = useNotifications()
  
  // Subscribe to real-time notification updates
  useWebSocketSubscription({
    eventType: "notification.new",
    onMessage: (data) => {
      // React Query will automatically refetch via WebSocket handler
    },
  })

  const unreadCount = notifications.filter(n => n.unread).length

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button 
          variant="ghost" 
          size="icon" 
          className="relative hover:bg-accent/50 transition-all duration-200"
        >
          <Bell className="h-5 w-5" />
          <AnimatePresence>
          {unreadCount > 0 && (
              <motion.span
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                className="absolute -top-1 -right-1 h-5 w-5 rounded-full bg-gradient-to-br from-red-500 to-red-600 flex items-center justify-center shadow-lg"
              >
                <span className="text-[10px] font-bold text-white">
                  {unreadCount > 9 ? "9+" : unreadCount}
                </span>
              </motion.span>
          )}
          </AnimatePresence>
        </Button>
      </DropdownMenuTrigger>
      
      <DropdownMenuContent 
        className={cn(
          "w-80 sm:w-96 shadow-xl border-border/50 backdrop-blur-sm",
          "bg-background/95 supports-[backdrop-filter]:bg-background/80"
        )} 
        align="end"
        sideOffset={8}
      >
        <DropdownMenuLabel className="flex justify-between items-center py-3 px-4 border-b">
          <span className="font-semibold text-base">Notifications</span>
          <div className="flex items-center gap-2">
            {unreadCount > 0 && (
              <>
                <Badge 
                  variant="secondary" 
                  className="bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
                >
                  {unreadCount} new
                </Badge>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={markAllAsRead}
                  className="h-7 text-xs hover:bg-primary/10"
                >
                  Mark all read
                </Button>
              </>
            )}
          </div>
        </DropdownMenuLabel>
        
        <ScrollArea className="h-[400px]">
          <AnimatePresence mode="popLayout">
            {notifications.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex flex-col items-center justify-center py-12 text-muted-foreground"
              >
                <Bell className="h-12 w-12 mb-3 opacity-20" />
                <p className="text-sm">No notifications</p>
              </motion.div>
            ) : (
              notifications.map((notification, index) => (
                <motion.div
                  key={notification.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <DropdownMenuItem 
                    className={cn(
                      "flex flex-col items-start p-4 cursor-pointer transition-all duration-200",
                      "hover:bg-accent/50 focus:bg-accent/50",
                      "border-b border-border/30 last:border-0",
                      notification.unread && "bg-primary/5 hover:bg-primary/10"
                    )}
                    onClick={() => markAsRead(notification.id)}
                  >
                    <div className="flex w-full justify-between items-start mb-2">
                      <div className="flex items-center gap-2">
                        {notification.unread && (
                          <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                        )}
                        <span className={cn(
                          "font-medium text-sm",
                          notification.unread ? "text-foreground" : "text-muted-foreground"
                        )}>
                  {notification.title}
                </span>
              </div>
                      <span className="text-[10px] text-muted-foreground whitespace-nowrap ml-2">
                        {formatDistanceToNow(new Date(notification.time), { addSuffix: true })}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2 w-full">
                {notification.description}
              </p>
            </DropdownMenuItem>
                </motion.div>
              ))
            )}
          </AnimatePresence>
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

Droppable column container with Zustand state management, animations, and responsive design.

```tsx
"use client"

import { useDroppable } from "@dnd-kit/core"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Plus } from "lucide-react"
import { TicketCard } from "./TicketCard"
import { cn } from "@/lib/utils"
import { motion, AnimatePresence } from "framer-motion"
import { useKanbanStore } from "@/stores/kanbanStore"

interface BoardColumnProps {
  id: string
  title: string
  tickets: any[] 
  onAddTicket?: () => void
  color?: "backlog" | "todo" | "in_progress" | "done"
}

const COLUMN_COLORS = {
  backlog: "from-slate-500/10 to-slate-600/10 border-slate-500/30 hover:border-slate-500/50",
  todo: "from-blue-500/10 to-blue-600/10 border-blue-500/30 hover:border-blue-500/50",
  in_progress: "from-amber-500/10 to-amber-600/10 border-amber-500/30 hover:border-amber-500/50",
  done: "from-green-500/10 to-green-600/10 border-green-500/30 hover:border-green-500/50",
}

export function BoardColumn({ id, title, tickets, onAddTicket, color }: BoardColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id })
  const hoveredColumn = useKanbanStore((state) => state.hoveredColumn)

  const columnColorClass = color ? COLUMN_COLORS[color] : "from-muted/50 to-muted border-border hover:border-border"

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(
        "flex flex-col h-full",
        // Responsive widths
        "w-full sm:w-80 md:w-[22rem] lg:w-80 xl:w-96",
        "min-w-[18rem] sm:min-w-[20rem]",
        // Modern styling with gradient
        "bg-gradient-to-br rounded-xl border-2 p-3 sm:p-4",
        "shadow-sm hover:shadow-lg transition-all duration-300",
        columnColorClass,
        hoveredColumn === id && "ring-2 ring-primary/50 ring-offset-2 ring-offset-background"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-2 sm:p-3 mb-3 rounded-lg bg-background/40 backdrop-blur-sm">
        <div className="flex items-center gap-2 sm:gap-3">
          <h3 className="font-semibold text-sm sm:text-base tracking-tight">
          {title}
          </h3>
          <Badge 
            variant="secondary" 
            className={cn(
              "text-xs px-2.5 py-0.5 h-5 min-w-[2.5rem] justify-center tabular-nums",
              "bg-background/80 backdrop-blur-sm shadow-sm",
              "transition-all duration-200 hover:scale-110"
            )}
          >
            {tickets.length}
          </Badge>
        </div>
        <Button 
          variant="ghost" 
          size="icon" 
          className={cn(
            "h-7 w-7 sm:h-8 sm:w-8 rounded-full",
            "hover:bg-primary/10 hover:text-primary hover:scale-110",
            "transition-all duration-200 shadow-sm"
          )}
          onClick={onAddTicket}
          aria-label={`Add ticket to ${title}`}
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>
      
      {/* Drop Zone */}
      <div 
        ref={setNodeRef} 
        className={cn(
          "flex-1 rounded-lg transition-all duration-200",
          "min-h-[10rem]",
          isOver && "bg-primary/10 ring-2 ring-primary/50 ring-offset-2 ring-offset-background scale-[1.02]"
        )}
      >
        <ScrollArea className="h-[calc(100vh-16rem)] sm:h-[calc(100vh-14rem)]">
          <motion.div 
            className="flex flex-col gap-3 p-1 sm:p-2"
            layout
          >
            <AnimatePresence mode="popLayout">
            {tickets.map((ticket) => (
                <motion.div
                  key={ticket.id}
                  layout
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8, x: -100 }}
                  transition={{ duration: 0.2 }}
                >
                  <TicketCard ticket={ticket} />
                </motion.div>
            ))}
            </AnimatePresence>
            
            {tickets.length === 0 && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className={cn(
                  "h-32 sm:h-40 flex items-center justify-center",
                  "border-2 border-dashed rounded-lg",
                  "border-muted-foreground/20 bg-background/30",
                  "backdrop-blur-sm transition-all duration-200",
                  isOver && "border-primary/50 bg-primary/5"
                )}
              >
                <div className="text-center space-y-2">
                  <p className="text-xs sm:text-sm text-muted-foreground font-medium">
                    {isOver ? "Drop here" : "No tickets"}
                  </p>
                  {!isOver && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={onAddTicket}
                      className="text-xs hover:bg-primary/10"
                    >
                      <Plus className="h-3 w-3 mr-1" />
                      Add ticket
                    </Button>
            )}
          </div>
              </motion.div>
            )}
          </motion.div>
        </ScrollArea>
      </div>
    </motion.div>
  )
}
```

---

## 4. Project Components

### `src/components/project/ProjectCard.tsx`

Dynamic project card with React Query integration, loading states, and enhanced Tailwind styling.

```tsx
"use client"

import { useProject } from "@/hooks/useProjects"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { ArrowRight, Users, AlertCircle, RefreshCw, FolderKanban } from "lucide-react"
import { motion } from "framer-motion"
import { cn } from "@/lib/utils"

interface ProjectCardProps {
  projectId: string
}

export function ProjectCard({ projectId }: ProjectCardProps) {
  const { data: project, isLoading, isError, refetch } = useProject(projectId)

  if (isLoading) {
  return (
    <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="pb-3 space-y-3">
        <div className="flex justify-between items-start">
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-5 w-16" />
          </div>
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </CardHeader>
        <CardContent className="pb-3 space-y-4">
          <Skeleton className="h-2 w-full" />
          <div className="flex gap-4">
            <Skeleton className="h-8 w-20" />
            <Skeleton className="h-8 w-20" />
          </div>
        </CardContent>
        <CardFooter>
          <Skeleton className="h-10 w-full" />
        </CardFooter>
      </Card>
    )
  }

  if (isError) {
    return (
      <Card className="border-destructive/50 shadow-md">
        <CardContent className="pt-6">
          <Alert variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription className="flex items-center justify-between">
              <span>Failed to load project</span>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={() => refetch()}
                className="ml-2 hover:bg-destructive/10"
              >
                <RefreshCw className="h-3 w-3 mr-2" />
                Retry
              </Button>
            </AlertDescription>
          </Alert>
        </CardContent>
      </Card>
    )
  }

  if (!project) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      whileHover={{ y: -4 }}
      className="h-full"
    >
      <Card className={cn(
        "group h-full flex flex-col",
        "hover:shadow-xl hover:shadow-primary/5 transition-all duration-300",
        "border-border/40 hover:border-primary/50",
        "bg-gradient-to-br from-background to-muted/20"
      )}>
        <CardHeader className="pb-3 space-y-3">
          <div className="flex justify-between items-start gap-2">
            <div className="flex items-start gap-2">
              <div className="mt-0.5 p-2 rounded-lg bg-primary/10 text-primary">
                <FolderKanban className="h-4 w-4" />
              </div>
              <CardTitle className="text-lg font-bold group-hover:text-primary transition-colors leading-tight">
                {project.name}
              </CardTitle>
            </div>
            <Badge 
              variant={project.status === "active" ? "default" : "secondary"}
              className={cn(
                "transition-all shrink-0",
                project.status === "active" && "bg-green-500 hover:bg-green-600 shadow-sm"
              )}
            >
            {project.status}
          </Badge>
        </div>
          <CardDescription className="line-clamp-2 min-h-[2.5rem] text-muted-foreground/80">
          {project.description}
        </CardDescription>
      </CardHeader>
        
        <CardContent className="pb-3 space-y-4 flex-1">
        <div className="space-y-2">
            <div className="flex justify-between text-xs text-muted-foreground font-medium">
            <span>Progress</span>
              <span className="font-semibold text-foreground tabular-nums">
                {Math.round(project.progress * 100)}%
              </span>
          </div>
            <div className="relative">
              <Progress 
                value={project.progress * 100} 
                className="h-2 transition-all duration-500"
              />
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-transparent via-white/20 to-transparent animate-shimmer" />
        </div>
          </div>
          
          <div className="flex gap-3 text-sm">
            <div className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg",
              "bg-primary/5 hover:bg-primary/10",
              "transition-colors group/stat cursor-default"
            )}>
              <div className="flex items-center justify-center w-7 h-7 rounded-full bg-primary/10 group-hover/stat:bg-primary/20 transition-colors">
                <span className="font-bold text-primary text-xs tabular-nums">{project.ticketCount}</span>
              </div>
              <span className="text-xs font-medium text-muted-foreground">Tickets</span>
            </div>
            <div className={cn(
              "flex items-center gap-2 px-3 py-2 rounded-lg",
              "bg-blue-500/5 hover:bg-blue-500/10",
              "transition-colors group/stat cursor-default"
            )}>
              <div className="flex items-center justify-center w-7 h-7 rounded-full bg-blue-500/10 group-hover/stat:bg-blue-500/20 transition-colors">
                <Users className="h-3.5 w-3.5 text-blue-600 dark:text-blue-400" />
          </div>
          <div className="flex items-center gap-1">
                <span className="text-xs font-bold text-foreground tabular-nums">{project.agentCount}</span>
                <span className="text-xs font-medium text-muted-foreground">Agents</span>
              </div>
          </div>
        </div>
      </CardContent>
        
        <CardFooter className="pt-3">
          <Button 
            asChild 
            className="w-full group/button shadow-sm" 
            variant="outline"
          >
            <Link href={`/projects/${project.id}/board`} className="flex items-center justify-center">
              <span>Open Project</span>
              <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover/button:translate-x-1" />
          </Link>
        </Button>
      </CardFooter>
    </Card>
    </motion.div>
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

Global search bar with Zustand state, search history, and real-time results.

```tsx
"use client"

import { useEffect, useId } from "react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { Badge } from "@/components/ui/badge"
import { Search, FileText, User, GitCommit, X, Clock, TrendingUp } from "lucide-react"
import { useRouter } from "next/navigation"
import { useSearchStore } from "@/stores/searchStore"
import { useSearchResults } from "@/hooks/useSearch"
import { useDebouncedValue } from "@/hooks/useDebouncedValue"
import { useKeyboardShortcut } from "@/hooks/useKeyboardShortcut"
import { cn } from "@/lib/utils"
import { motion, AnimatePresence } from "framer-motion"

export function SearchBar() {
  const searchId = useId()
  const router = useRouter()
  const [open, setOpen] = useState(false)
  
  const { query, searchHistory, setQuery, addToHistory, removeFromHistory } = useSearchStore()
  const debouncedQuery = useDebouncedValue(query, 300)

  const { data: results = [], isLoading } = useSearchResults(debouncedQuery, {
    enabled: debouncedQuery.length > 0
  })
  
  // Keyboard shortcut: Cmd+K or Ctrl+K
  useKeyboardShortcut(['meta', 'k'], () => setOpen(true))
  useKeyboardShortcut(['ctrl', 'k'], () => setOpen(true))

  const handleSelect = (item: any) => {
    const routes = {
      ticket: `/board/${item.id}`,
      agent: `/agents/${item.id}`,
      commit: `/commits/${item.id}`,
      file: `/files/${item.id}`,
    }
    
    addToHistory(query)
    router.push(routes[item.type as keyof typeof routes])
    setOpen(false)
    setQuery("")
  }
  
  const handleHistorySelect = (historyQuery: string) => {
    setQuery(historyQuery)
  }

  const clearSearch = () => {
    setQuery("")
  }

  const iconMap = {
    ticket: FileText,
    agent: User,
    commit: GitCommit,
    file: FileText,
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <motion.div 
          className="relative w-full max-w-md group"
          whileFocus={{ scale: 1.02 }}
        >
          <label htmlFor={searchId} className="sr-only">
            Search tickets, agents, commits
          </label>
          <Search className={cn(
            "absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4",
            "text-muted-foreground group-focus-within:text-primary",
            "transition-colors duration-200"
          )} />
          <Input
            id={searchId}
            placeholder="Search... (⌘K)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setOpen(true)}
            className={cn(
              "pl-10 pr-10",
              "focus-visible:ring-2 focus-visible:ring-primary/20 focus-visible:border-primary",
              "transition-all duration-200 shadow-sm",
              "hover:shadow-md"
            )}
            aria-autocomplete="list"
            aria-controls={`${searchId}-listbox`}
            aria-expanded={open}
          />
          {query && (
            <Button
              variant="ghost"
              size="icon"
              className={cn(
                "absolute right-1 top-1/2 -translate-y-1/2 h-7 w-7",
                "hover:bg-muted rounded-full transition-all",
                "opacity-0 group-focus-within:opacity-100 group-hover:opacity-100"
              )}
              onClick={clearSearch}
              aria-label="Clear search"
            >
              <X className="h-3 w-3" />
            </Button>
          )}
        </motion.div>
      </PopoverTrigger>
      
      <PopoverContent 
        className={cn(
          "w-[var(--radix-popover-trigger-width)] p-0",
          "border-border/50 shadow-xl backdrop-blur-sm",
          "bg-background/95 supports-[backdrop-filter]:bg-background/80"
        )} 
        align="start"
        sideOffset={8}
      >
        <Command shouldFilter={false}>
          <CommandInput 
            placeholder="Search..." 
            value={query} 
            onValueChange={setQuery}
            className="border-none focus:ring-0"
          />
          <CommandList id={`${searchId}-listbox`} role="listbox">
            {isLoading ? (
              <div className="p-4 text-sm text-center text-muted-foreground flex items-center justify-center gap-2">
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-primary border-t-transparent" />
                Searching...
              </div>
            ) : (
              <>
                {!query && searchHistory.length > 0 && (
                  <CommandGroup heading="Recent Searches" className="p-2">
                    <AnimatePresence mode="popLayout">
                      {searchHistory.slice(0, 5).map((historyItem, index) => (
                        <motion.div
                          key={historyItem}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: 10 }}
                          transition={{ delay: index * 0.05 }}
                        >
                          <CommandItem
                            onSelect={() => handleHistorySelect(historyItem)}
                            className="flex items-center justify-between group/history"
                          >
                            <div className="flex items-center gap-2">
                              <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                              <span className="text-sm">{historyItem}</span>
                            </div>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 w-6 p-0 opacity-0 group-hover/history:opacity-100 transition-opacity"
                              onClick={(e) => {
                                e.stopPropagation()
                                removeFromHistory(historyItem)
                              }}
                            >
                              <X className="h-3 w-3" />
                            </Button>
                          </CommandItem>
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </CommandGroup>
                )}
                
                <CommandEmpty className="p-4 text-sm text-center text-muted-foreground">
                  {query ? 'No results found' : 'Start typing to search'}
                </CommandEmpty>
                
                {results.length > 0 && (
                  <CommandGroup heading={`Results (${results.length})`} className="p-2">
                    <AnimatePresence mode="popLayout">
                      {results.map((item, index) => {
                        const Icon = iconMap[item.type as keyof typeof iconMap] || FileText
                        
                return (
                          <motion.div
                            key={item.id}
                            initial={{ opacity: 0, y: -10 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: 10 }}
                            transition={{ delay: index * 0.05 }}
                          >
                            <CommandItem 
                              onSelect={() => handleSelect(item)}
                              className={cn(
                                "flex items-center gap-3 px-3 py-2.5 rounded-md",
                                "cursor-pointer transition-all",
                                "hover:bg-accent/50 focus:bg-accent/50",
                                "aria-selected:bg-accent"
                              )}
                              role="option"
                            >
                              <div className="flex-shrink-0 p-2 rounded-lg bg-primary/10">
                                <Icon className="h-4 w-4 text-primary" />
                              </div>
                              <div className="flex-1 min-w-0">
                                <span className="text-sm font-medium truncate block">
                                  {item.title}
                                </span>
                                {item.description && (
                                  <span className="text-xs text-muted-foreground truncate block">
                                    {item.description}
                                  </span>
                                )}
                              </div>
                              <Badge variant="outline" className="text-xs flex-shrink-0">
                                {item.type}
                              </Badge>
                  </CommandItem>
                          </motion.div>
                )
              })}
                    </AnimatePresence>
            </CommandGroup>
                )}
              </>
            )}
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

## 35. Terminal Streaming Components (Xterm.js)

### `src/components/terminal/TerminalViewer.tsx`

Real-time terminal output viewer using Xterm.js for full terminal emulation.

```tsx
"use client"

import { useEffect, useRef, useState } from "react"
import { Terminal as XTerm } from "xterm"
import { FitAddon } from "xterm-addon-fit"
import { WebLinksAddon } from "xterm-addon-web-links"
import { SearchAddon } from "xterm-addon-search"
import { Unicode11Addon } from "xterm-addon-unicode11"
import { SerializeAddon } from "xterm-addon-serialize"
import "xterm/css/xterm.css"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Terminal, Copy, Trash2, Download, Maximize2, Minimize2 } from "lucide-react"
import { useTerminalStream } from "@/hooks/terminal/useTerminalStream"
import { useClipboard } from "@/hooks/clipboard/useClipboard"
import { cn } from "@/lib/utils"

interface TerminalViewerProps {
  taskId?: string
  agentId?: string
  projectId?: string
  className?: string
  options?: {
    fontSize?: number
    fontFamily?: string
    theme?: any
    cursorBlink?: boolean
    cursorStyle?: "block" | "underline" | "bar"
  }
}

export function TerminalViewer({
  taskId,
  agentId,
  projectId,
  className,
  options = {},
}: TerminalViewerProps) {
  const terminalRef = useRef<HTMLDivElement>(null)
  const xtermRef = useRef<XTerm | null>(null)
  const fitAddonRef = useRef<FitAddon | null>(null)
  const serializeAddonRef = useRef<SerializeAddon | null>(null)
  const { isStreaming, clear, write } = useTerminalStream({
    taskId,
    agentId,
    projectId,
    onData: (data) => {
      xtermRef.current?.write(data)
    },
  })
  const { copy } = useClipboard()
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Initialize Xterm.js (only once)
  useEffect(() => {
    if (!terminalRef.current || xtermRef.current) return

    const xterm = new XTerm({
      fontSize: options.fontSize || 14,
      fontFamily: options.fontFamily || "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace",
      cursorBlink: options.cursorBlink ?? true,
      cursorStyle: options.cursorStyle || "block",
      theme: options.theme || {
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        cursor: "hsl(var(--foreground))",
        selection: "hsl(var(--accent))",
        black: "#000000",
        red: "#cd3131",
        green: "#0dbc79",
        yellow: "#e5e510",
        blue: "#2472c8",
        magenta: "#bc3fbc",
        cyan: "#11a8cd",
        white: "#e5e5e5",
        brightBlack: "#666666",
        brightRed: "#f14c4c",
        brightGreen: "#23d18b",
        brightYellow: "#f5f543",
        brightBlue: "#3b8eea",
        brightMagenta: "#d670d6",
        brightCyan: "#29b8db",
        brightWhite: "#e5e5e5",
      },
      allowProposedApi: true,
    })

    const fitAddon = new FitAddon()
    const webLinksAddon = new WebLinksAddon()
    const searchAddon = new SearchAddon()
    const unicode11Addon = new Unicode11Addon()
    const serializeAddon = new SerializeAddon()

    xterm.loadAddon(fitAddon)
    xterm.loadAddon(webLinksAddon)
    xterm.loadAddon(searchAddon)
    xterm.loadAddon(unicode11Addon)
    xterm.loadAddon(serializeAddon)

    xterm.open(terminalRef.current)
    fitAddon.fit()

    xtermRef.current = xterm
    fitAddonRef.current = fitAddon
    serializeAddonRef.current = serializeAddon

    // Note: Auto-copy on selection can be annoying, so we'll just enable selection
    // Users can manually copy via Ctrl/Cmd+C or the copy button

    // Handle paste
    xterm.attachCustomKeyEventHandler((event) => {
      if ((event.ctrlKey || event.metaKey) && event.key === "v") {
        navigator.clipboard.readText().then((text) => {
          xterm.paste(text)
        })
        return false
      }
      return true
    })

    // Handle resize
    const handleResize = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit()
      }
    }
    window.addEventListener("resize", handleResize)

    return () => {
      window.removeEventListener("resize", handleResize)
      xterm.dispose()
      xtermRef.current = null
      fitAddonRef.current = null
    }
  }, []) // Only initialize once

  // Update theme when it changes (without reinitializing)
  useEffect(() => {
    if (xtermRef.current && options.theme) {
      xtermRef.current.options.theme = options.theme
    }
  }, [options.theme])

  // Handle fullscreen
  useEffect(() => {
    if (isFullscreen && fitAddonRef.current) {
      fitAddonRef.current.fit()
    }
  }, [isFullscreen])

  const handleCopy = () => {
    if (xtermRef.current?.hasSelection()) {
      const selection = xtermRef.current.getSelection()
      if (selection) {
        copy(selection)
      }
    } else {
      // Copy all terminal content
      xtermRef.current?.selectAll()
      const allContent = xtermRef.current?.getSelection() || ""
      copy(allContent)
      xtermRef.current?.clearSelection()
    }
  }

  const handleDownload = () => {
    if (serializeAddonRef.current) {
      // Use SerializeAddon for better export
      const content = serializeAddonRef.current.serialize()
      const blob = new Blob([content], { type: "text/plain" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `terminal-${taskId || agentId || "output"}-${Date.now()}.log`
      a.click()
      URL.revokeObjectURL(url)
    }
  }

  const handleClear = () => {
    xtermRef.current?.clear()
    clear()
  }

  const handleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
    if (!isFullscreen) {
      terminalRef.current?.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }

  return (
    <Card className={cn("flex flex-col", className, isFullscreen && "fixed inset-0 z-50 m-0 rounded-none")}>
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
            <Button variant="ghost" size="sm" onClick={handleFullscreen}>
              {isFullscreen ? (
                <Minimize2 className="h-4 w-4" />
              ) : (
                <Maximize2 className="h-4 w-4" />
              )}
            </Button>
            <Button variant="ghost" size="sm" onClick={handleCopy}>
              <Copy className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleDownload}>
              <Download className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={handleClear}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="p-0 flex-1 min-h-0">
        <div
          ref={terminalRef}
          className="h-full w-full"
          style={{ minHeight: "400px" }}
        />
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

## 37. Xterm.js Terminal Configuration

### Installation

**Core Package**:
```bash
npm install xterm
```

**Official Addons**:
```bash
npm install xterm-addon-fit xterm-addon-web-links xterm-addon-search xterm-addon-unicode11 xterm-addon-serialize
```

**Optional Addons**:
```bash
npm install xterm-addon-image xterm-addon-ligatures xterm-addon-clipboard xterm-addon-attach
```

### Available Xterm.js Addons

#### Core Addons (Recommended)

1. **FitAddon** (`xterm-addon-fit`)
   - Auto-resize terminal to fit container
   - Essential for responsive layouts
   - Usage: `fitAddon.fit()` on resize

2. **WebLinksAddon** (`xterm-addon-web-links`)
   - Makes URLs clickable in terminal
   - Opens links in new tab
   - Great for error messages with stack traces

3. **SearchAddon** (`xterm-addon-search`)
   - Text search within terminal
   - Keyboard shortcuts (Ctrl+F)
   - Highlight search results

4. **Unicode11Addon** (`xterm-addon-unicode11`)
   - Unicode 11 support
   - Better emoji and special character rendering
   - Useful for internationalized output

5. **SerializeAddon** (`xterm-addon-serialize`)
   - Serialize terminal state
   - Save/restore terminal content
   - Export terminal output

#### Optional Addons

6. **ImageAddon** (`xterm-addon-image`)
   - Display images in terminal
   - Useful for ASCII art, diagrams
   - Supports various image formats

7. **LigaturesAddon** (`xterm-addon-ligatures`)
   - Font ligature support
   - Better code readability (->, =>, etc.)
   - Requires ligature-enabled fonts (Fira Code, JetBrains Mono)

8. **ClipboardAddon** (`xterm-addon-clipboard`)
   - Enhanced clipboard integration
   - Better copy/paste handling
   - Cross-platform support

9. **AttachAddon** (`xterm-addon-attach`)
   - Direct WebSocket attachment
   - Alternative to manual WebSocket handling
   - Simplifies connection management

10. **WebglAddon** (`xterm-addon-webgl`)
    - WebGL-based renderer
    - Better performance for large outputs
    - Hardware acceleration

### Xterm.js Setup

**Required CSS**: Import Xterm.js styles in your global CSS or layout:
```tsx
// app/layout.tsx or app/globals.css
import "xterm/css/xterm.css"
```

**Dynamic Import** (Recommended for Next.js):
```tsx
// components/terminal/TerminalViewer.tsx
import dynamic from 'next/dynamic'

export const TerminalViewer = dynamic(
  () => import('./TerminalViewer').then(mod => mod.TerminalViewer),
  { ssr: false }
)
```

### Enhanced TerminalViewer with All Addons

```tsx
"use client"

import { useEffect, useRef, useState } from "react"
import { Terminal as XTerm } from "xterm"
import { FitAddon } from "xterm-addon-fit"
import { WebLinksAddon } from "xterm-addon-web-links"
import { SearchAddon } from "xterm-addon-search"
import { Unicode11Addon } from "xterm-addon-unicode11"
import { SerializeAddon } from "xterm-addon-serialize"
import { ImageAddon } from "xterm-addon-image"
import { LigaturesAddon } from "xterm-addon-ligatures"
import "xterm/css/xterm.css"
// ... rest of component

// In initialization:
const fitAddon = new FitAddon()
const webLinksAddon = new WebLinksAddon()
const searchAddon = new SearchAddon()
const unicode11Addon = new Unicode11Addon()
const serializeAddon = new SerializeAddon()
const imageAddon = new ImageAddon()
const ligaturesAddon = new LigaturesAddon()

xterm.loadAddon(fitAddon)
xterm.loadAddon(webLinksAddon)
xterm.loadAddon(searchAddon)
xterm.loadAddon(unicode11Addon)
xterm.loadAddon(serializeAddon)
xterm.loadAddon(imageAddon)
xterm.loadAddon(ligaturesAddon)
```

### Terminal Options

**Theme Configuration**:
```typescript
const terminalTheme = {
  // Light mode
  light: {
    background: "#ffffff",
    foreground: "#000000",
    cursor: "#000000",
    selection: "#e5e5e5",
    // ... ANSI colors
  },
  // Dark mode
  dark: {
    background: "hsl(var(--background))",
    foreground: "hsl(var(--foreground))",
    cursor: "hsl(var(--foreground))",
    selection: "hsl(var(--accent))",
    // ... ANSI colors
  }
}
```

**Performance Considerations**:
- Use `scrollback` limit to prevent memory issues (default: 1000)
- Use `fastScrollModifier` for better scrolling performance
- Consider WebGL renderer for very large outputs
- Limit `scrollback` based on use case

### WebSocket Integration

Xterm.js works seamlessly with WebSocket streaming:
- Write data directly to terminal: `xterm.write(data)`
- Handle ANSI escape sequences automatically
- Support for colors, formatting, and cursor control
- Use `AttachAddon` for direct WebSocket attachment (alternative approach)

### Addon Usage Examples

**SerializeAddon** - Export terminal content:
```typescript
const serializeAddon = new SerializeAddon()
xterm.loadAddon(serializeAddon)

// Export terminal content
const content = serializeAddon.serialize()
// Save to file or send to server
```

**SearchAddon** - Search functionality:
```typescript
const searchAddon = new SearchAddon()
xterm.loadAddon(searchAddon)

// Programmatic search
searchAddon.findNext("error")
searchAddon.findPrevious("error")
```

**ImageAddon** - Display images:
```typescript
const imageAddon = new ImageAddon()
xterm.loadAddon(imageAddon)

// Display image (via ANSI escape sequences from server)
// Server sends: \x1b]1337;File=...;inline=1:base64encodedimage\x07
```

**AttachAddon** - Direct WebSocket attachment (Alternative approach):
```typescript
import { AttachAddon } from 'xterm-addon-attach'

// Alternative to manual WebSocket handling
const ws = new WebSocket('ws://localhost:8080/terminal')
const attachAddon = new AttachAddon(ws)
xterm.loadAddon(attachAddon)

// Automatically handles:
// - Writing incoming data to terminal
// - Sending terminal input to WebSocket
// - Connection lifecycle
```

### Recommended Addon Combinations

**For Agent Terminal Streaming**:
- ✅ FitAddon (essential)
- ✅ WebLinksAddon (clickable error URLs)
- ✅ SearchAddon (find errors/logs)
- ✅ Unicode11Addon (emoji support)
- ✅ SerializeAddon (export logs)
- ⚠️ AttachAddon (if using direct WebSocket, otherwise use manual handling)

**For Code Display**:
- ✅ LigaturesAddon (better code readability)
- ✅ Unicode11Addon (special characters)

**For Performance**:
- ✅ WebglAddon (large outputs, hardware acceleration)

---

## 38. Zustand Store Integration

### `stores/uiStore.ts`

Global UI state with persistence and SSR support.

```typescript
import { create } from 'zustand'
import { devtools, persist, createJSONStorage } from 'zustand/middleware'

interface UIStore {
  // Theme
  theme: 'light' | 'dark' | 'system'
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  
  // Sidebar
  sidebarCollapsed: boolean
  toggleSidebar: () => void
  
  // Terminal
  terminalOpen: boolean
  terminalHeight: number
  setTerminalOpen: (open: boolean) => void
  setTerminalHeight: (height: number) => void
  
  // Modals
  activeModal: string | null
  modalData: any
  openModal: (modalId: string, data?: any) => void
  closeModal: () => void
  
  // Toasts
  toasts: Array<{
    id: string
    type: 'success' | 'error' | 'warning' | 'info'
    message: string
  }>
  addToast: (toast: Omit<UIStore['toasts'][0], 'id'>) => void
  removeToast: (id: string) => void
}

export const useUIStore = create<UIStore>()(
  devtools(
    persist(
      (set, get) => ({
        theme: 'system',
        setTheme: (theme) => set({ theme }),
        
        sidebarCollapsed: false,
        toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
        
        terminalOpen: false,
        terminalHeight: 400,
        setTerminalOpen: (open) => set({ terminalOpen: open }),
        setTerminalHeight: (height) => set({ terminalHeight: height }),
        
        activeModal: null,
        modalData: null,
        openModal: (modalId, data) => set({ activeModal: modalId, modalData: data }),
        closeModal: () => set({ activeModal: null, modalData: null }),
        
        toasts: [],
        addToast: (toast) => {
          const id = `toast-${Date.now()}-${Math.random()}`
          set((state) => ({
            toasts: [...state.toasts, { ...toast, id }]
          }))
          setTimeout(() => get().removeToast(id), 5000)
        },
        removeToast: (id) => set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id)
        })),
      }),
      {
        name: 'ui-store',
        storage: createJSONStorage(() => localStorage),
        partialize: (state) => ({
          theme: state.theme,
          sidebarCollapsed: state.sidebarCollapsed,
          terminalHeight: state.terminalHeight,
        }),
      }
    ),
    { name: 'UIStore' }
  )
)
```

### `stores/kanbanStore.ts`

Kanban board state with WebSocket sync and React Query bridge.

```typescript
import { create } from 'zustand'
import { devtools, persist, subscribeWithSelector } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'

interface Ticket {
  id: string
  title: string
  status: string
  priority: string
}

interface Column {
  id: string
  title: string
  tickets: string[]
}

interface KanbanStore {
  columns: Column[]
  tickets: Record<string, Ticket>
  selectedTickets: Set<string>
  draggedTicket: string | null
  hoveredColumn: string | null
  
  setColumns: (columns: Column[]) => void
  setTickets: (tickets: Record<string, Ticket>) => void
  moveTicket: (ticketId: string, fromColumn: string, toColumn: string, index?: number) => void
  selectTicket: (ticketId: string) => void
  clearSelection: () => void
  setDraggedTicket: (ticketId: string | null) => void
  setHoveredColumn: (columnId: string | null) => void
}

export const useKanbanStore = create<KanbanStore>()(
  devtools(
    subscribeWithSelector(
      immer((set) => ({
        columns: [],
        tickets: {},
        selectedTickets: new Set(),
        draggedTicket: null,
        hoveredColumn: null,
        
        setColumns: (columns) => set({ columns }),
        setTickets: (tickets) => set({ tickets }),
        
        moveTicket: (ticketId, fromColumn, toColumn, index) =>
          set((state) => {
            const fromCol = state.columns.find((c) => c.id === fromColumn)
            if (fromCol) {
              fromCol.tickets = fromCol.tickets.filter((id) => id !== ticketId)
            }
            
            const toCol = state.columns.find((c) => c.id === toColumn)
            if (toCol) {
              toCol.tickets.splice(index ?? toCol.tickets.length, 0, ticketId)
            }
            
            if (state.tickets[ticketId]) {
              state.tickets[ticketId].status = toColumn
            }
          }),
        
        selectTicket: (ticketId) =>
          set((state) => {
            state.selectedTickets.add(ticketId)
          }),
        
        clearSelection: () => set({ selectedTickets: new Set() }),
        setDraggedTicket: (ticketId) => set({ draggedTicket: ticketId }),
        setHoveredColumn: (columnId) => set({ hoveredColumn: columnId }),
      }))
    ),
    { name: 'KanbanStore' }
  )
)
```

### `stores/searchStore.ts`

Search state with history persistence.

```typescript
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface SearchStore {
  query: string
  searchHistory: string[]
  selectedTypes: string[]
  
  setQuery: (query: string) => void
  addToHistory: (query: string) => void
  clearHistory: () => void
  setSelectedTypes: (types: string[]) => void
}

export const useSearchStore = create<SearchStore>()(
  persist(
    (set, get) => ({
      query: '',
      searchHistory: [],
      selectedTypes: [],
      
      setQuery: (query) => set({ query }),
      
      addToHistory: (query) => {
        if (!query.trim()) return
        set((state) => ({
          searchHistory: [query, ...state.searchHistory.filter((q) => q !== query)].slice(0, 50)
        }))
      },
      
      clearHistory: () => set({ searchHistory: [] }),
      setSelectedTypes: (types) => set({ selectedTypes: types }),
    }),
    {
      name: 'search-store',
      partialize: (state) => ({
        searchHistory: state.searchHistory,
      }),
    }
  )
)
```

---

## 39. Custom Middleware Implementations

### `middleware/websocket-sync.ts`

WebSocket synchronization middleware for real-time state updates.

```typescript
import { StateCreator, StoreMutatorIdentifier } from 'zustand'
import { produce } from 'immer'

type WebSocketSync = <
  T,
  Mps extends [StoreMutatorIdentifier, unknown][] = [],
  Mcs extends [StoreMutatorIdentifier, unknown][] = []
>(
  config: StateCreator<T, Mps, Mcs>,
  options: WebSocketSyncOptions<T>
) => StateCreator<T, Mps, Mcs>

interface WebSocketSyncOptions<T> {
  getWebSocket: () => WebSocket | null
  eventTypes: string[]
  onMessage: (message: any, currentState: T) => Partial<T> | ((state: T) => T)
  syncToServer?: boolean
  shouldSync?: (prevState: T, nextState: T) => boolean
  serialize?: (state: T) => any
}

export const websocketSync: WebSocketSync = (config, options) => (set, get, api) => {
  let unsubscribe: (() => void) | null = null
  
  const setupWebSocketListener = () => {
    const ws = options.getWebSocket()
    if (!ws) return
    
    const handleMessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        
        if (options.eventTypes.includes(data.type || data.event_type)) {
          const update = options.onMessage(data, get())
          
          if (typeof update === 'function') {
            set(produce(update))
          } else {
            set(update as any)
          }
        }
      } catch (error) {
        console.error('WebSocket message parsing error:', error)
      }
    }
    
    ws.addEventListener('message', handleMessage)
    
    unsubscribe = () => {
      ws.removeEventListener('message', handleMessage)
    }
  }
  
  const enhancedSet: typeof set = (partial, replace) => {
    const prevState = get()
    set(partial, replace)
    const nextState = get()
    
    if (options.syncToServer) {
      const shouldSync = options.shouldSync?.(prevState, nextState) ?? true
      
      if (shouldSync) {
        const ws = options.getWebSocket()
        const payload = options.serialize?.(nextState) ?? nextState
        
        if (ws?.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'STATE_UPDATE',
            payload,
          }))
        }
      }
    }
  }
  
  if (typeof window !== 'undefined') {
    setupWebSocketListener()
  }
  
  ;(api as any).destroy = () => {
    unsubscribe?.()
  }
  
  return config(enhancedSet, get, api)
}
```

### `middleware/react-query-bridge.ts`

React Query integration middleware for automatic cache invalidation.

```typescript
import { QueryClient, QueryKey } from '@tanstack/react-query'
import { StateCreator, StoreMutatorIdentifier } from 'zustand'

type ReactQueryBridge = <
  T,
  Mps extends [StoreMutatorIdentifier, unknown][] = [],
  Mcs extends [StoreMutatorIdentifier, unknown][] = []
>(
  config: StateCreator<T, Mps, Mcs>,
  options: ReactQueryBridgeOptions<T>
) => StateCreator<T, Mps, Mcs>

interface ReactQueryBridgeOptions<T> {
  queryClient: QueryClient
  
  invalidationRules: Array<{
    shouldInvalidate: (prevState: T, nextState: T) => boolean
    queryKeys: QueryKey[] | ((state: T) => QueryKey[])
    optimisticUpdate?: (state: T) => Array<{
      queryKey: QueryKey
      updater: (old: any) => any
    }>
  }>
  
  syncRules?: Array<{
    queryKey: QueryKey
    toState: (data: any) => Partial<T>
    shouldSync?: (data: any) => boolean
  }>
}

export const reactQueryBridge: ReactQueryBridge = (config, options) => (set, get, api) => {
  const { queryClient, invalidationRules, syncRules } = options
  
  const enhancedSet: typeof set = (partial, replace) => {
    const prevState = get()
    set(partial, replace)
    const nextState = get()
    
    invalidationRules.forEach((rule) => {
      if (rule.shouldInvalidate(prevState, nextState)) {
        const keys = typeof rule.queryKeys === 'function' 
          ? rule.queryKeys(nextState) 
          : rule.queryKeys
        
        if (rule.optimisticUpdate) {
          const updates = rule.optimisticUpdate(nextState)
          updates.forEach(({ queryKey, updater }) => {
            queryClient.setQueryData(queryKey, updater)
          })
        }
        
        keys.forEach((key) => {
          queryClient.invalidateQueries({ queryKey: key })
        })
      }
    })
  }
  
  if (typeof window !== 'undefined' && syncRules) {
    syncRules.forEach(({ queryKey, toState, shouldSync }) => {
      const unsubscribe = queryClient.getQueryCache().subscribe((event) => {
        if (event?.query?.queryKey !== queryKey) return
        
        const data = queryClient.getQueryData(queryKey)
        
        if (data && (!shouldSync || shouldSync(data))) {
          const stateUpdate = toState(data)
          set(stateUpdate as any)
        }
      })
      
      ;(api as any)._unsubscribers = (api as any)._unsubscribers || []
      ;(api as any)._unsubscribers.push(unsubscribe)
    })
  }
  
  return config(enhancedSet, get, api)
}
```

---

## 40. Enhanced Tailwind CSS Utilities

### Tailwind Config Extensions

Add to `tailwind.config.js`:

```javascript
module.exports = {
  theme: {
    extend: {
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '112': '28rem',
      },
      animation: {
        'shimmer': 'shimmer 2s linear infinite',
        'fade-in': 'fadeIn 0.3s ease-in-out',
        'slide-in': 'slideIn 0.3s ease-out',
        'bounce-subtle': 'bounceSubtle 1s ease-in-out infinite',
      },
      keyframes: {
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideIn: {
          '0%': { transform: 'translateY(-10px)', opacity: '0' },
          '100%': { transform: 'translateY(0)', opacity: '1' },
        },
        bounceSubtle: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
      },
      boxShadow: {
        'glow': '0 0 20px rgba(59, 130, 246, 0.3)',
        'glow-lg': '0 0 40px rgba(59, 130, 246, 0.4)',
      },
    },
  },
}
```

### Custom CSS Classes

Add to `globals.css`:

```css
@layer utilities {
  .text-balance {
    text-wrap: balance;
  }
  
  .scrollbar-thin::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }
  
  .scrollbar-thin::-webkit-scrollbar-track {
    @apply bg-transparent;
  }
  
  .scrollbar-thin::-webkit-scrollbar-thumb {
    @apply bg-muted-foreground/20 rounded-full;
  }
  
  .scrollbar-thin::-webkit-scrollbar-thumb:hover {
    @apply bg-muted-foreground/30;
  }
  
  .glass-panel {
    @apply bg-background/80 backdrop-blur-md border border-border/50;
  }
  
  .gradient-border {
    @apply relative before:absolute before:inset-0 before:rounded-lg before:p-[1px] before:bg-gradient-to-br before:from-primary before:to-primary/50 before:-z-10;
  }
}
```

---

This completes the code highlighting and terminal streaming components documentation with comprehensive Xterm.js addon support, Zustand state management integration, custom middleware implementations, and enhanced Tailwind CSS utilities.
