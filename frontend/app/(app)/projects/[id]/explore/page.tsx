"use client"

import { use, useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
} from "lucide-react"
import { mockProjects } from "@/lib/mock"

interface ExplorePageProps {
  params: Promise<{ id: string }>
}

// Mock conversation history
const mockConversations = [
  {
    id: "conv-1",
    title: "Authentication flow analysis",
    lastMessage: "The auth module uses JWT tokens with refresh...",
    timestamp: "2 hours ago",
  },
  {
    id: "conv-2",
    title: "Database schema questions",
    lastMessage: "The user table has the following relations...",
    timestamp: "1 day ago",
  },
  {
    id: "conv-3",
    title: "API endpoint documentation",
    lastMessage: "Here are all the REST endpoints...",
    timestamp: "3 days ago",
  },
]

// Mock suggestions
const mockSuggestions = [
  "Explain the authentication flow",
  "Show me the database schema",
  "What tests are failing?",
  "Find unused dependencies",
  "Summarize recent changes",
]

// Mock file structure
const mockFiles = [
  { path: "src/auth/jwt.ts", type: "file", lines: 156 },
  { path: "src/auth/middleware.ts", type: "file", lines: 89 },
  { path: "src/api/routes.ts", type: "file", lines: 234 },
  { path: "src/db/models/user.ts", type: "file", lines: 67 },
  { path: "src/db/models/project.ts", type: "file", lines: 92 },
]

// Mock AI response
const mockResponses = [
  {
    role: "user",
    content: "Explain the authentication flow in this project",
  },
  {
    role: "assistant",
    content: `## Authentication Flow

The project uses **JWT-based authentication** with the following flow:

1. **Login Request**: User submits credentials to \`POST /api/auth/login\`
2. **Validation**: Server validates credentials against the database
3. **Token Generation**: On success, generates access + refresh tokens
4. **Token Storage**: Client stores tokens (access in memory, refresh in httpOnly cookie)

### Key Files:
- \`src/auth/jwt.ts\` - Token generation and validation
- \`src/auth/middleware.ts\` - Route protection middleware
- \`src/api/routes/auth.ts\` - Auth endpoints

### Security Features:
- Access tokens expire in 15 minutes
- Refresh tokens expire in 7 days
- Tokens are signed with RS256 algorithm`,
  },
]

export default function ExplorePage({ params }: ExplorePageProps) {
  const { id } = use(params)
  const project = mockProjects.find((p) => p.id === id)
  const [query, setQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [messages, setMessages] = useState(mockResponses)

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
    if (!query.trim()) return

    setIsLoading(true)
    setMessages([...messages, { role: "user", content: query }])
    setQuery("")

    // Simulate AI response
    await new Promise((resolve) => setTimeout(resolve, 1500))

    setMessages((prev) => [
      ...prev,
      {
        role: "assistant",
        content: `I've analyzed your question about "${query}". Here's what I found in the codebase...\n\nThis is a mock response. In the real implementation, this would connect to the AI service to analyze the project codebase and provide relevant insights.`,
      },
    ])
    setIsLoading(false)
  }

  const handleSuggestionClick = (suggestion: string) => {
    setQuery(suggestion)
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
          {project.repo}
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
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                {messages.map((message, index) => (
                  <div
                    key={index}
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
                {isLoading && (
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
                  disabled={isLoading}
                />
                <Button type="submit" disabled={isLoading || !query.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </form>
              <div className="mt-3 flex flex-wrap gap-2">
                {mockSuggestions.slice(0, 3).map((suggestion, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                    onClick={() => handleSuggestionClick(suggestion)}
                    disabled={isLoading}
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
            <CardHeader className="py-3">
              <CardTitle className="text-sm">Recent Conversations</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {mockConversations.map((conv) => (
                <button
                  key={conv.id}
                  className="w-full text-left rounded-lg border p-3 hover:bg-accent transition-colors"
                  onClick={() => toast.info("Loading conversation...")}
                >
                  <p className="text-sm font-medium truncate">{conv.title}</p>
                  <p className="text-xs text-muted-foreground truncate mt-1">
                    {conv.lastMessage}
                  </p>
                  <div className="flex items-center gap-1 text-xs text-muted-foreground mt-2">
                    <Clock className="h-3 w-3" />
                    {conv.timestamp}
                  </div>
                </button>
              ))}
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
              {mockFiles.map((file) => (
                <button
                  key={file.path}
                  className="w-full text-left flex items-center gap-2 rounded-md px-2 py-1.5 hover:bg-accent transition-colors text-sm"
                  onClick={() => {
                    setQuery(`Explain the code in ${file.path}`)
                    toast.info(`Analyzing ${file.path}...`)
                  }}
                >
                  <FileCode className="h-4 w-4 text-muted-foreground shrink-0" />
                  <span className="truncate font-mono text-xs">{file.path}</span>
                  <ChevronRight className="h-3 w-3 text-muted-foreground ml-auto shrink-0" />
                </button>
              ))}
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
