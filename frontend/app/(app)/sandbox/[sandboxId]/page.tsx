"use client"

import { use, useState, useRef, useEffect, useMemo } from "react"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ArrowLeft,
  Terminal,
  Send,
  Loader2,
  AlertCircle,
  Bot,
  CheckCircle,
  Clock,
  PlayCircle,
  XCircle,
  Wifi,
  WifiOff,
  RefreshCw,
} from "lucide-react"
import { useSandboxMonitor, useSandboxTask } from "@/hooks/useSandbox"
import { EventRenderer } from "@/components/sandbox"

interface SandboxDetailPageProps {
  params: Promise<{ sandboxId: string }>
}

// Status badge configuration
const statusConfig: Record<string, { icon: typeof Loader2; color: string; iconClass: string; label: string }> = {
  pending: { icon: Clock, color: "secondary", iconClass: "", label: "Pending" },
  in_progress: { icon: PlayCircle, color: "warning", iconClass: "", label: "Running" },
  running: { icon: Loader2, color: "warning", iconClass: "animate-spin", label: "Running" },
  completed: { icon: CheckCircle, color: "success", iconClass: "", label: "Completed" },
  failed: { icon: XCircle, color: "destructive", iconClass: "", label: "Failed" },
  cancelled: { icon: XCircle, color: "secondary", iconClass: "", label: "Cancelled" },
}

// Event types to filter out
const HIDDEN_EVENT_TYPES = [
  "agent.heartbeat",
  "SANDBOX_HEARTBEAT",
]

// Normalize content for comparison (remove whitespace differences)
function normalizeContent(content: string): string {
  return content.replace(/\s+/g, "").toLowerCase()
}

// Helper to generate a content-based key for file operations
function getFileContentKey(event: { event_type: string; event_data: unknown }): string | null {
  const data = event.event_data as Record<string, unknown>
  
  // For tool_completed events with Write/Edit
  if (event.event_type === "agent.tool_completed") {
    const tool = data?.tool as string
    const toolInput = data?.tool_input as Record<string, unknown> | undefined
    
    if (tool === "Write") {
      const filePath = toolInput?.filePath || toolInput?.file_path || ""
      const content = (toolInput?.content as string) || ""
      // Include normalized content in key to differentiate different writes to same file
      return `file:${filePath}:${normalizeContent(content).slice(0, 100)}`
    }
    
    if (tool === "Edit") {
      const filePath = toolInput?.filePath || toolInput?.file_path || ""
      const oldString = (toolInput?.oldString as string) || ""
      const newString = (toolInput?.newString as string) || ""
      // Include both old and new content to differentiate different edits
      return `file:${filePath}:${normalizeContent(oldString).slice(0, 50)}:${normalizeContent(newString).slice(0, 50)}`
    }
  }
  
  // For file_edited events
  if (event.event_type === "agent.file_edited") {
    const filePath = data?.file_path as string || ""
    const diff = (data?.diff_preview as string) || (data?.full_diff as string) || ""
    return `file:${filePath}:${normalizeContent(diff).slice(0, 100)}`
  }
  
  return null
}

// Helper to generate a tool use key for deduplication
function getToolUseKey(event: { event_type: string; event_data: unknown }): string | null {
  const data = event.event_data as Record<string, unknown>
  const tool = data?.tool as string
  const toolInput = data?.tool_input || data?.input
  
  if (!tool) return null
  
  // Create a key from tool name and input
  // For Write/Edit, use the file path
  if (tool === "Write" || tool === "Edit" || tool === "Read") {
    const input = toolInput as Record<string, unknown> | undefined
    const filePath = input?.filePath || input?.file_path || ""
    return `${tool}:${filePath}`
  }
  
  // For Bash, use the command
  if (tool === "Bash") {
    const input = toolInput as Record<string, unknown> | undefined
    const command = input?.command || ""
    return `${tool}:${command}`
  }
  
  // For other tools, use tool name and stringified input
  return `${tool}:${JSON.stringify(toolInput || {})}`
}

export default function SandboxDetailPage({ params }: SandboxDetailPageProps) {
  const { sandboxId } = use(params)
  const [messageInput, setMessageInput] = useState("")
  const scrollRef = useRef<HTMLDivElement>(null)
  
  // Fetch task info for this sandbox
  const { data: task, isLoading: isLoadingTask, error: taskError } = useSandboxTask(sandboxId)
  
  // Monitor sandbox events
  const {
    events,
    isConnected,
    isConnecting,
    isLoadingHistory,
    sendMessage,
    isSendingMessage,
    refresh,
  } = useSandboxMonitor(sandboxId)

  // Filter and sort events, deduplicating redundant events
  const visibleEvents = useMemo(() => {
    // Collect all tool_completed content keys for deduplication
    const completedToolKeys = new Set<string>()
    const completedFileContentKeys = new Set<string>()
    
    // First pass: collect keys from tool_completed events
    for (const event of events) {
      if (event.event_type === "agent.tool_completed") {
        const toolKey = getToolUseKey(event)
        if (toolKey) completedToolKeys.add(toolKey)
        
        // Track file content keys
        const contentKey = getFileContentKey(event)
        if (contentKey) completedFileContentKeys.add(contentKey)
      }
    }
    
    // Track which content keys we've already rendered
    const renderedContentKeys = new Set<string>()
    
    // Filter out events
    return events
      .filter((e) => {
        // Skip hidden event types
        if (HIDDEN_EVENT_TYPES.includes(e.event_type)) return false
        
        // Skip tool_use events if there's a corresponding tool_completed
        if (e.event_type === "agent.tool_use") {
          const key = getToolUseKey(e)
          if (key && completedToolKeys.has(key)) return false
        }
        
        // Skip file_edited events if we have a tool_completed with the same content
        if (e.event_type === "agent.file_edited") {
          const contentKey = getFileContentKey(e)
          if (contentKey) {
            // Check if any tool_completed has similar content
            for (const completedKey of completedFileContentKeys) {
              // Extract file path from both keys and compare
              const fileEditPath = contentKey.split(":")[1]
              const completedPath = completedKey.split(":")[1]
              if (fileEditPath === completedPath) {
                // Same file - skip file_edited in favor of tool_completed
                return false
              }
            }
          }
        }
        
        // For tool_completed with Write/Edit, dedupe exact same content
        if (e.event_type === "agent.tool_completed") {
          const data = e.event_data as Record<string, unknown>
          const tool = data?.tool as string
          if (tool === "Write" || tool === "Edit") {
            const contentKey = getFileContentKey(e)
            if (contentKey) {
              if (renderedContentKeys.has(contentKey)) return false
              renderedContentKeys.add(contentKey)
            }
          }
        }
        
        return true
      })
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
  }, [events])

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [visibleEvents.length])

  // Handle sending a message
  const handleSendMessage = async () => {
    if (!messageInput.trim() || isSendingMessage) return
    
    await sendMessage(messageInput.trim())
    setMessageInput("")
  }

  // Handle enter key
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  // Loading state
  if (isLoadingTask) {
    return (
      <div className="flex h-[calc(100vh-48px)] flex-col">
        <div className="border-b border-border p-4">
          <Skeleton className="h-4 w-32 mb-2" />
          <div className="flex items-center gap-3">
            <Skeleton className="h-6 w-6" />
            <Skeleton className="h-7 w-48" />
          </div>
        </div>
        <div className="flex-1 p-6">
          <Skeleton className="h-[400px] w-full" />
        </div>
      </div>
    )
  }

  // Error state
  if (taskError) {
    return (
      <div className="container mx-auto p-6 text-center">
        <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
        <h1 className="mt-4 text-2xl font-bold">Failed to load sandbox</h1>
        <p className="mt-2 text-muted-foreground">
          {taskError instanceof Error ? taskError.message : "An error occurred"}
        </p>
        <Button className="mt-4" asChild>
          <Link href="/command">Back to Command</Link>
        </Button>
      </div>
    )
  }

  const status = task?.status || "pending"
  const config = statusConfig[status] || statusConfig.pending
  const StatusIcon = config.icon

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col">
      {/* Header */}
      <div className="border-b border-border p-4">
        <div className="flex items-start justify-between">
          <div>
            <Link
              href="/command"
              className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Command
            </Link>
            <div className="mt-2 flex items-center gap-3">
              <Bot className="h-6 w-6" />
              <h1 className="text-xl font-bold">{task?.title || "Sandbox"}</h1>
              <Badge variant={config.color as "default" | "destructive" | "secondary" | "outline"}>
                <StatusIcon className={`mr-1 h-3 w-3 ${config.iconClass}`} />
                {config.label}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground font-mono">
              {sandboxId}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Connection status */}
            <div className="flex items-center gap-1.5 text-sm">
              {isConnecting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  <span className="text-muted-foreground">Connecting...</span>
                </>
              ) : isConnected ? (
                <>
                  <Wifi className="h-4 w-4 text-green-500" />
                  <span className="text-green-600">Live</span>
                </>
              ) : (
                <>
                  <WifiOff className="h-4 w-4 text-muted-foreground" />
                  <span className="text-muted-foreground">Disconnected</span>
                </>
              )}
            </div>
            <Button variant="outline" size="sm" onClick={refresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Main Content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <Tabs defaultValue="events" className="flex-1 flex flex-col overflow-hidden">
            <div className="border-b border-border px-4">
              <TabsList className="h-10">
                <TabsTrigger value="events">Events</TabsTrigger>
                <TabsTrigger value="details">Details</TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="events" className="m-0 p-0 data-[state=inactive]:hidden data-[state=active]:flex data-[state=active]:flex-1 data-[state=active]:flex-col data-[state=active]:overflow-hidden">
              {/* Events scroll area */}
              <ScrollArea className="flex-1" ref={scrollRef}>
                <div className="p-4 space-y-3">
                  {isLoadingHistory ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                    </div>
                  ) : visibleEvents.length === 0 ? (
                    <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
                      <Terminal className="h-12 w-12 mb-4 opacity-50" />
                      <p>No events yet</p>
                      <p className="text-sm">Events will appear here as the agent works</p>
                    </div>
                  ) : (
                    visibleEvents.map((event) => (
                      <EventRenderer key={event.id} event={event} />
                    ))
                  )}
                </div>
              </ScrollArea>

              {/* Message input */}
              <div className="border-t border-border p-4">
                <div className="flex gap-2">
                  <Textarea
                    placeholder="Send a message to the agent..."
                    className="min-h-[60px] resize-none"
                    value={messageInput}
                    onChange={(e) => setMessageInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={isSendingMessage}
                  />
                  <Button 
                    size="icon" 
                    className="shrink-0 h-[60px] w-[60px]"
                    onClick={handleSendMessage}
                    disabled={!messageInput.trim() || isSendingMessage}
                  >
                    {isSendingMessage ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Send className="h-4 w-4" />
                    )}
                  </Button>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="details" className="m-0 p-0 data-[state=inactive]:hidden data-[state=active]:flex data-[state=active]:flex-1 data-[state=active]:flex-col data-[state=active]:overflow-auto">
              <div className="p-4 space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Task Information</CardTitle>
                    <CardDescription>Details about the task associated with this sandbox</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Task ID</p>
                        <p className="text-sm font-mono">{task?.id || "N/A"}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Sandbox ID</p>
                        <p className="text-sm font-mono">{sandboxId}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Status</p>
                        <Badge variant={config.color as "default" | "destructive" | "secondary" | "outline"} className="mt-1">
                          {task?.status || "Unknown"}
                        </Badge>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Priority</p>
                        <p className="text-sm capitalize">{task?.priority || "Normal"}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Task Type</p>
                        <p className="text-sm">{task?.task_type || "N/A"}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Phase</p>
                        <p className="text-sm">{task?.phase_id || "N/A"}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Created</p>
                        <p className="text-sm">
                          {task?.created_at 
                            ? new Date(task.created_at).toLocaleString() 
                            : "N/A"}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Started</p>
                        <p className="text-sm">
                          {task?.started_at 
                            ? new Date(task.started_at).toLocaleString() 
                            : "Not started"}
                        </p>
                      </div>
                      {task?.completed_at && (
                        <div>
                          <p className="text-sm font-medium text-muted-foreground">Completed</p>
                          <p className="text-sm">
                            {new Date(task.completed_at).toLocaleString()}
                          </p>
                        </div>
                      )}
                      {task?.description && (
                        <div className="md:col-span-2">
                          <p className="text-sm font-medium text-muted-foreground">Description</p>
                          <p className="text-sm mt-1">{task.description}</p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Event Summary</CardTitle>
                    <CardDescription>Overview of events in this sandbox</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="grid gap-4 md:grid-cols-3">
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Total Events</p>
                        <p className="text-2xl font-bold">{events.length}</p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">Tool Uses</p>
                        <p className="text-2xl font-bold">
                          {events.filter((e) => e.event_type === "agent.tool_use" || e.event_type === "agent.tool_completed").length}
                        </p>
                      </div>
                      <div>
                        <p className="text-sm font-medium text-muted-foreground">File Edits</p>
                        <p className="text-2xl font-bold">
                          {events.filter((e) => e.event_type === "agent.file_edited").length}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}
