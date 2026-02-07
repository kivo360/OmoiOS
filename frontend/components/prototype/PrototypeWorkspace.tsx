"use client"

import { useState, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Loader2,
  Play,
  Send,
  Download,
  Square,
  AlertCircle,
} from "lucide-react"
import { PreviewPanel } from "@/components/preview/PreviewPanel"
import { usePrototype } from "@/hooks/usePrototype"
import type { PrototypeSession } from "@/lib/api/prototype"
import type { PreviewSession } from "@/lib/api/types"

const FRAMEWORKS = [
  { value: "react-vite", label: "React + Vite + TypeScript" },
  { value: "next", label: "Next.js + TypeScript + Tailwind" },
  { value: "vue-vite", label: "Vue + Vite + TypeScript" },
]

function statusLabel(status: string): string {
  switch (status) {
    case "creating":
      return "Creating..."
    case "ready":
      return "Ready"
    case "prompting":
      return "Generating..."
    case "exporting":
      return "Exporting..."
    case "stopped":
      return "Stopped"
    case "failed":
      return "Failed"
    default:
      return status
  }
}

function statusColor(status: string): string {
  switch (status) {
    case "ready":
      return "default"
    case "creating":
    case "prompting":
    case "exporting":
      return "secondary"
    case "failed":
      return "destructive"
    default:
      return "outline"
  }
}

/**
 * Convert a PrototypeSession's preview data into a PreviewSession shape
 * so we can reuse PreviewPanel.
 */
function toPreviewSession(session: PrototypeSession): PreviewSession | null {
  if (!session.preview_id) return null
  return {
    id: session.preview_id,
    sandbox_id: session.sandbox_id || "",
    task_id: null,
    project_id: null,
    status: session.status === "ready" ? "ready" : "pending",
    preview_url: session.preview_url,
    port: 3000,
    framework: session.framework,
    error_message: session.error_message,
    created_at: session.created_at,
    ready_at: null,
    stopped_at: null,
  }
}

export function PrototypeWorkspace() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [framework, setFramework] = useState("react-vite")
  const [promptInput, setPromptInput] = useState("")
  const [exportUrl, setExportUrl] = useState("")

  const {
    session,
    isLoading,
    startSession,
    isStarting,
    applyPrompt,
    isPrompting,
    exportToRepo,
    isExporting,
    endSession,
    isEnding,
  } = usePrototype(sessionId)

  const handleStart = useCallback(async () => {
    try {
      const newSession = await startSession(framework)
      setSessionId(newSession.id)
    } catch {
      // Error handled by mutation state
    }
  }, [framework, startSession])

  const handlePrompt = useCallback(async () => {
    if (!promptInput.trim() || !sessionId) return
    try {
      await applyPrompt(promptInput.trim())
      setPromptInput("")
    } catch {
      // Error handled by mutation state
    }
  }, [promptInput, sessionId, applyPrompt])

  const handleExport = useCallback(async () => {
    if (!exportUrl.trim() || !sessionId) return
    try {
      await exportToRepo({ repoUrl: exportUrl.trim() })
    } catch {
      // Error handled by mutation state
    }
  }, [exportUrl, sessionId, exportToRepo])

  const handleEnd = useCallback(() => {
    endSession()
    setSessionId(null)
  }, [endSession])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handlePrompt()
    }
  }

  // No active session — show framework selector
  if (!sessionId) {
    return (
      <div className="flex h-[calc(100vh-48px)] items-center justify-center">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Start Prototyping</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Framework</label>
              <Select value={framework} onValueChange={setFramework}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {FRAMEWORKS.map((fw) => (
                    <SelectItem key={fw.value} value={fw.value}>
                      {fw.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <Button
              className="w-full"
              onClick={handleStart}
              disabled={isStarting}
            >
              {isStarting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating sandbox...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Start Session
                </>
              )}
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  // Active session — split view
  const preview = session ? toPreviewSession(session) : null

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">Prototype</h1>
          {session && (
            <Badge variant={statusColor(session.status) as "default" | "secondary" | "destructive" | "outline"}>
              {session.status === "creating" || session.status === "prompting" || session.status === "exporting" ? (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              ) : null}
              {statusLabel(session.status)}
            </Badge>
          )}
          {session?.framework && (
            <Badge variant="outline" className="text-xs">
              {session.framework}
            </Badge>
          )}
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleEnd}
          disabled={isEnding}
          className="text-destructive hover:text-destructive"
        >
          {isEnding ? (
            <Loader2 className="mr-2 h-3 w-3 animate-spin" />
          ) : (
            <Square className="mr-2 h-3 w-3" />
          )}
          End Session
        </Button>
      </div>

      {/* Split view */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left panel: prompt + history */}
        <div className="flex w-[400px] shrink-0 flex-col border-r border-border">
          {/* Prompt input */}
          <div className="border-b border-border p-4 space-y-3">
            <Textarea
              placeholder="Describe what you want to build or change..."
              className="min-h-[100px] resize-none"
              value={promptInput}
              onChange={(e) => setPromptInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isPrompting || session?.status !== "ready"}
            />
            <Button
              className="w-full"
              onClick={handlePrompt}
              disabled={
                !promptInput.trim() ||
                isPrompting ||
                session?.status !== "ready"
              }
            >
              {isPrompting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                  Send Prompt
                </>
              )}
            </Button>
          </div>

          {/* Prompt history */}
          <ScrollArea className="flex-1">
            <div className="p-4 space-y-3">
              {session?.prompt_history && session.prompt_history.length > 0 ? (
                session.prompt_history.map((item, i) => (
                  <Card key={i}>
                    <CardContent className="p-3 space-y-2">
                      <p className="text-sm font-medium">{item.prompt}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.response_summary}
                      </p>
                      <p className="text-xs text-muted-foreground/60">
                        {new Date(item.timestamp).toLocaleTimeString()}
                      </p>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <p className="text-center text-sm text-muted-foreground py-8">
                  No prompts yet. Describe what you want to build.
                </p>
              )}
            </div>
          </ScrollArea>

          {/* Export section */}
          <div className="border-t border-border p-4 space-y-2">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="https://github.com/user/repo"
                className="flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm"
                value={exportUrl}
                onChange={(e) => setExportUrl(e.target.value)}
                disabled={isExporting}
              />
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
                disabled={
                  !exportUrl.trim() ||
                  isExporting ||
                  session?.status !== "ready"
                }
              >
                {isExporting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>

        {/* Right panel: live preview */}
        <div className="flex flex-1 flex-col overflow-hidden">
          {isLoading ? (
            <div className="flex flex-1 items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : session?.status === "failed" ? (
            <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
              <AlertCircle className="h-8 w-8 text-destructive" />
              <p className="text-sm font-medium text-destructive">
                Session failed
              </p>
              {session.error_message && (
                <p className="max-w-md text-center text-xs">
                  {session.error_message}
                </p>
              )}
            </div>
          ) : preview ? (
            <PreviewPanel
              preview={preview}
              onStop={handleEnd}
              isStopping={isEnding}
              onRefreshData={() => {}}
            />
          ) : (
            <div className="flex flex-1 items-center justify-center text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin" />
              <p className="ml-3 text-sm">Setting up sandbox...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
