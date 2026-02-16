"use client"

import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { CheckCircle, ExternalLink, Star, GitPullRequest } from "lucide-react"
import { ShareButtons } from "./ShareButtons"
import { api } from "@/lib/api/client"
import type { Spec } from "@/lib/api/specs"

interface ShareResponse {
  share_url: string
  share_token: string
}

interface SpecCompletionModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  spec: Spec
}

export function SpecCompletionModal({ open, onOpenChange, spec }: SpecCompletionModalProps) {
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [isSharing, setIsSharing] = useState(false)

  const requirementsCount = spec.requirements?.length ?? 0
  const tasksCompleted = spec.tasks?.filter((t) => t.status === "completed").length ?? 0
  const totalTasks = spec.tasks?.length ?? 0
  const testCoverage = spec.execution?.test_coverage ?? spec.test_coverage ?? 0

  const handleEnableSharing = async () => {
    if (shareUrl) return // Already generated
    setIsSharing(true)
    try {
      const result = await api.post<ShareResponse>(`/api/v1/public/specs/${spec.id}/share`)
      setShareUrl(result.share_url)
    } catch {
      // Silently fail — user can retry
    } finally {
      setIsSharing(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle className="h-5 w-5 text-green-500" />
            Spec Complete!
          </DialogTitle>
          <DialogDescription>
            {spec.title}
          </DialogDescription>
        </DialogHeader>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4 py-4">
          <div className="text-center">
            <p className="text-2xl font-bold">{requirementsCount}</p>
            <p className="text-xs text-muted-foreground">Requirements</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold">{tasksCompleted}/{totalTasks}</p>
            <p className="text-xs text-muted-foreground">Tasks Done</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold">{testCoverage.toFixed(0)}%</p>
            <p className="text-xs text-muted-foreground">Coverage</p>
          </div>
        </div>

        {/* PR link */}
        {spec.pull_request_url && (
          <a
            href={spec.pull_request_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 rounded-md border p-3 text-sm hover:bg-muted transition-colors"
          >
            <GitPullRequest className="h-4 w-4 text-green-500" />
            <span className="flex-1 truncate">
              PR #{spec.pull_request_number}
            </span>
            <ExternalLink className="h-3 w-3 text-muted-foreground" />
          </a>
        )}

        {/* Share section */}
        <div className="space-y-3">
          <p className="text-sm font-medium">Share this spec</p>
          {shareUrl ? (
            <ShareButtons
              specTitle={spec.title}
              shareUrl={shareUrl}
              specId={spec.id}
              stats={{
                requirements: requirementsCount,
                tasks: totalTasks,
                coverage: testCoverage,
              }}
            />
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={handleEnableSharing}
              disabled={isSharing}
            >
              {isSharing ? "Generating link..." : "Generate shareable link"}
            </Button>
          )}
        </div>

        {/* GitHub Star CTA */}
        <div className="flex items-center justify-between pt-2">
          <a
            href="https://github.com/kivo360/OmoiOS"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button variant="outline" size="sm">
              <Star className="mr-2 h-4 w-4" />
              Star on GitHub
            </Button>
          </a>
          <Button variant="ghost" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
