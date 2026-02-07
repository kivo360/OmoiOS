"use client"

import { useCallback, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Loader2,
  AlertCircle,
  Square,
  Globe,
  RefreshCw,
  ExternalLink,
} from "lucide-react"
import type { PreviewSession } from "@/lib/api/types"

interface PreviewPanelProps {
  preview: PreviewSession
  onStop: () => void
  isStopping: boolean
  onRefreshData: () => void
}

export function PreviewPanel({
  preview,
  onStop,
  isStopping,
  onRefreshData,
}: PreviewPanelProps) {
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const refreshIframe = useCallback(() => {
    if (iframeRef.current) {
      // Reload iframe by re-setting src
      const src = iframeRef.current.src
      iframeRef.current.src = ""
      iframeRef.current.src = src
    }
  }, [])

  const openInNewTab = useCallback(() => {
    if (preview.preview_url) {
      window.open(preview.preview_url, "_blank", "noopener,noreferrer")
    }
  }, [preview.preview_url])

  // Pending / Starting state
  if (preview.status === "pending" || preview.status === "starting") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin" />
        <p className="text-sm">
          {preview.status === "pending"
            ? "Waiting for dev server..."
            : "Dev server starting..."}
        </p>
      </div>
    )
  }

  // Failed state
  if (preview.status === "failed") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
        <AlertCircle className="h-8 w-8 text-destructive" />
        <p className="text-sm font-medium text-destructive">Preview failed</p>
        {preview.error_message && (
          <p className="max-w-md text-center text-xs">{preview.error_message}</p>
        )}
        <Button variant="outline" size="sm" onClick={onRefreshData}>
          <RefreshCw className="mr-2 h-3 w-3" />
          Retry
        </Button>
      </div>
    )
  }

  // Stopped state
  if (preview.status === "stopped") {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-3 text-muted-foreground">
        <Square className="h-8 w-8" />
        <p className="text-sm">Preview stopped</p>
        {preview.stopped_at && (
          <p className="text-xs">
            Stopped at {new Date(preview.stopped_at).toLocaleString()}
          </p>
        )}
      </div>
    )
  }

  // Ready state — toolbar + iframe
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-2 border-b border-border px-3 py-2">
        <Globe className="h-4 w-4 text-muted-foreground shrink-0" />
        <code className="flex-1 truncate text-xs text-muted-foreground">
          {preview.preview_url}
        </code>
        {preview.framework && (
          <Badge variant="secondary" className="shrink-0 text-xs">
            {preview.framework}
          </Badge>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={refreshIframe}
          title="Refresh preview"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0"
          onClick={openInNewTab}
          title="Open in new tab"
        >
          <ExternalLink className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 shrink-0 text-destructive hover:text-destructive"
          onClick={onStop}
          disabled={isStopping}
          title="Stop preview"
        >
          {isStopping ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Square className="h-3.5 w-3.5" />
          )}
        </Button>
      </div>

      {/* Iframe */}
      <iframe
        ref={iframeRef}
        src={preview.preview_url || undefined}
        className="flex-1 border-0"
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
        title="Live Preview"
      />
    </div>
  )
}
