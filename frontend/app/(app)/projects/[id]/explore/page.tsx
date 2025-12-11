"use client"

import { use, useState, useEffect, useRef } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ArrowLeft,
  Search,
  Sparkles,
  Send,
  FileCode,
  FolderTree,
  MessageSquare,
  Lightbulb,
  Code,
  GitBranch,
  Bot,
  Clock,
  ChevronRight,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react"
import { useProject } from "@/hooks/useProjects"
import {
  useConversations,
  useConversation,
  useCreateConversation,
  useSendMessage,
  useDeleteConversation,
  useProjectFiles,
  useSuggestions,
} from "@/hooks/useExplore"
import type { Message } from "@/lib/api/explore"

interface ExplorePageProps {
  params: Promise<{ id: string }>
}

export default function ExplorePage({ params }: ExplorePageProps) {
  const { id } = use(params)
  const scrollRef = useRef<HTMLDivElement>(null)
  const [query, setQuery] = useState("")
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [localMessages, setLocalMessages] = useState<Message[]>([])

  // Fetch data from API
  const { data: project, isLoading: projectLoading } = useProject(id)
  const { data: conversationsData, isLoading: conversationsLoading } = useConversations(id)
  const { data: conversationData } = useConversation(id, activeConversationId || undefined)
  const { data: filesData, isLoading: filesLoading } = useProjectFiles(id)
  const { data: suggestionsData } = useSuggestions(id)

  // Mutations
  const createConversationMutation = useCreateConversation(id)
  const sendMessageMutation = useSendMessage(id, activeConversationId || "")
  const deleteConversationMutation = useDeleteConversation(id)

  const conversations = conversationsData?.conversations || []
  const files = filesData?.files || []
  const suggestions = suggestionsData?.suggestions || [
    "Explain the authentication flow",
    "Show me the database schema",
    "What tests are failing?",
  ]

  // Set active conversation when data loads
  useEffect(() => {
    if (conversations.length > 0 && !activeConversationId) {
      setActiveConversationId(conversations[0].id)
    }
  }, [conversations, activeConversationId])

  // Update local messages when conversation changes
  useEffect(() => {
    if (conversationData?.conversation) {
      setLocalMessages(conversationData.conversation.messages)
    }
  }, [conversationData])

  // Scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [localMessages])

  const isLoading = projectLoading

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <Skeleton className="h-8 w-64" />
        <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
          <Skeleton className="h-[600px]" />
          <div className="space-y-4">
            <Skeleton className="h-48" />
            <Skeleton className="h-48" />
          </div>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold">Project not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/projects">Back to Projects</Link>
        </Button>
      </div>
    )
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim() || !activeConversationId) return

    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: query,
      timestamp: new Date().toISOString(),
    }

    // Optimistically add user message
    setLocalMessages((prev) => [...prev, userMessage])
    setQuery("")

    try {
      const response = await sendMessageMutation.mutateAsync(query)
      // Replace temp message with real ones
      setLocalMessages((prev) => [
        ...prev.filter((m) => m.id !== userMessage.id),
        response.user_message,
        response.assistant_message,
      ])
    } catch (error) {
      toast.error("Failed to send message")
      // Remove optimistic message on error
      setLocalMessages((prev) => prev.filter((m) => m.id !== userMessage.id))
    }
  }

  const handleNewConversation = async () => {
    try {
      const result = await createConversationMutation.mutateAsync()
      setActiveConversationId(result.conversation.id)
      setLocalMessages(result.conversation.messages)
      toast.success("New conversation created")
    } catch (error) {
      toast.error("Failed to create conversation")
    }
  }

  const handleDeleteConversation = async (convId: string) => {
    try {
      await deleteConversationMutation.mutateAsync(convId)
      if (activeConversationId === convId) {
        setActiveConversationId(null)
        setLocalMessages([])
      }
      toast.success("Conversation deleted")
    } catch (error) {
      toast.error("Failed to delete conversation")
    }
  }

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
  }

  const handleConversationClick = (convId: string) => {
    setActiveConversationId(convId)
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <Link
        href={`/projects/${id}`}
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Project
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold">AI Explore</h1>
          </div>
          <p className="mt-1 text-muted-foreground">
            Ask questions about {project.name} and explore the codebase with AI
          </p>
        </div>
        <Badge variant="outline" className="gap-1">
          <GitBranch className="h-3 w-3" />
          {project.github_repo || "No repo"}
        </Badge>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        {/* Main Chat Area */}
        <div className="space-y-4">
          <Card className="flex flex-col h-[600px]">
            <CardHeader className="border-b py-3">
              <CardTitle className="text-base flex items-center gap-2">
                <MessageSquare className="h-4 w-4" />
                Codebase Q&A
              </CardTitle>
            </CardHeader>
            <ScrollArea className="flex-1 p-4" ref={scrollRef}>
              <div className="space-y-4">
                {localMessages.map((message, index) => (
                  <div
                    key={message.id || index}
                    className={`flex gap-3 ${
                      message.role === "user" ? "justify-end" : ""
                    }`}
                  >
                    {message.role === "assistant" && (
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                        <Bot className="h-4 w-4 text-primary" />
                      </div>
                    )}
                    <div
                      className={`rounded-lg px-4 py-3 max-w-[80%] ${
                        message.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      <div
                        className={`text-sm whitespace-pre-wrap ${
                          message.role === "assistant" ? "prose prose-sm dark:prose-invert max-w-none" : ""
                        }`}
                        dangerouslySetInnerHTML={{
                          __html: message.content.replace(/\n/g, "<br/>").replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>").replace(/##\s(.+)/g, "<h4 class='font-semibold mt-2 mb-1'>$1</h4>").replace(/###\s(.+)/g, "<h5 class='font-medium mt-2 mb-1'>$1</h5>").replace(/-\s(.+)/g, "• $1"),
                        }}
                      />
                    </div>
                    {message.role === "user" && (
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary">
                        <span className="text-xs text-primary-foreground font-medium">U</span>
                      </div>
                    )}
                  </div>
                ))}
                {sendMessageMutation.isPending && (
                  <div className="flex gap-3">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10">
                      <Bot className="h-4 w-4 text-primary" />
                    </div>
                    <div className="bg-muted rounded-lg px-4 py-3">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
            <div className="border-t p-4">
              <form onSubmit={handleSubmit} className="flex gap-2">
                <Input
                  placeholder="Ask about the codebase..."
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  disabled={sendMessageMutation.isPending || !activeConversationId}
                />
                <Button type="submit" disabled={sendMessageMutation.isPending || !query.trim() || !activeConversationId}>
                  <Send className="h-4 w-4" />
                </Button>
              </form>
              <div className="mt-3 flex flex-wrap gap-2">
                {suggestions.slice(0, 3).map((suggestion, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => handleSuggestionClick(suggestion)}
                    disabled={sendMessageMutation.isPending}
                  >
                    <Lightbulb className="mr-1 h-3 w-3" />
                    {suggestion}
                  </Button>
                ))}
              </div>
            </div>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-4">
          {/* Recent Conversations */}
          <Card>
            <CardHeader className="py-3 flex flex-row items-center justify-between">
              <CardTitle className="text-sm">Conversations</CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleNewConversation}
                disabled={createConversationMutation.isPending}
              >
                {createConversationMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Plus className="h-4 w-4" />
                )}
              </Button>
            </CardHeader>
            <CardContent className="space-y-2">
              {conversationsLoading ? (
                <>
                  <Skeleton className="h-16 w-full" />
                  <Skeleton className="h-16 w-full" />
                </>
              ) : conversations.length === 0 ? (
                <p className="text-sm text-muted-foreground text-center py-4">
                  No conversations yet
                </p>
              ) : (
                conversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`w-full text-left rounded-lg border p-3 hover:bg-accent transition-colors cursor-pointer ${
                      activeConversationId === conv.id ? "bg-accent border-primary" : ""
                    }`}
                    onClick={() => handleConversationClick(conv.id)}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{conv.title}</p>
                        <p className="text-xs text-muted-foreground truncate mt-1">
                          {conv.last_message}
                        </p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 w-6 p-0 shrink-0"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteConversation(conv.id)
                        }}
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground mt-2">
                      <Clock className="h-3 w-3" />
                      {conv.timestamp}
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* File Explorer */}
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <FolderTree className="h-4 w-4" />
                Key Files
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {filesLoading ? (
                <>
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-full" />
                </>
              ) : (
                files.map((file) => (
                  <button
                    key={file.path}
                    className="w-full text-left flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent transition-colors text-sm"
                    onClick={() => {
                      setQuery(`Explain the code in ${file.path}`)
                    }}
                  >
                    <FileCode className="h-4 w-4 text-muted-foreground shrink-0" />
                    <span className="truncate font-mono text-xs">{file.path}</span>
                    <ChevronRight className="h-3 w-3 text-muted-foreground ml-auto shrink-0" />
                  </button>
                ))
              )}
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-sm">Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => setQuery("Generate a README for this project")}
              >
                <FileCode className="mr-2 h-4 w-4" />
                Generate README
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => setQuery("Find potential security issues")}
              >
                <Search className="mr-2 h-4 w-4" />
                Security Audit
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="w-full justify-start"
                onClick={() => setQuery("Suggest code improvements")}
              >
                <Code className="mr-2 h-4 w-4" />
                Code Review
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
