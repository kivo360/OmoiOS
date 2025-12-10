"use client"

import { use, useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  ArrowLeft,
  GitCommit,
  Clock,
  User,
  FileCode,
  Plus,
  Minus,
  ChevronRight,
  Copy,
  AlertCircle,
  Eye,
  EyeOff,
  Ticket,
} from "lucide-react"
import { useCommit, useCommitDiff } from "@/hooks/useCommits"

interface CommitPageProps {
  params: Promise<{ commitSha: string }>
}

export default function CommitPage({ params }: CommitPageProps) {
  const { commitSha } = use(params)
  const { data: commit, isLoading, error } = useCommit(commitSha)
  const { data: diff, isLoading: isDiffLoading } = useCommitDiff(commitSha)
  
  const files = diff?.files || []
  const [expandedFiles, setExpandedFiles] = useState<string[]>([])
  const [showWhitespace, setShowWhitespace] = useState(false)

  // Initialize expanded files when diff loads
  useState(() => {
    if (files.length > 0 && expandedFiles.length === 0) {
      setExpandedFiles(files.map((f) => f.path))
    }
  })

  const toggleFile = (path: string) => {
    setExpandedFiles((prev) =>
      prev.includes(path) ? prev.filter((p) => p !== path) : [...prev, path]
    )
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast.success("Copied to clipboard")
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "added":
        return "text-green-600"
      case "removed":
      case "deleted":
        return "text-red-500"
      case "modified":
        return "text-amber-500"
      default:
        return "text-muted-foreground"
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "added":
        return <Badge className="bg-green-100 text-green-700 hover:bg-green-100">Added</Badge>
      case "removed":
      case "deleted":
        return <Badge className="bg-red-100 text-red-700 hover:bg-red-100">Deleted</Badge>
      case "modified":
        return <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100">Modified</Badge>
      default:
        return <Badge variant="secondary">{status}</Badge>
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString()
  }

  if (isLoading) {
    return (
      <div className="container mx-auto max-w-6xl p-6 space-y-6">
        <Skeleton className="h-8 w-24" />
        <Card>
          <CardHeader>
            <Skeleton className="h-6 w-3/4" />
            <Skeleton className="h-4 w-1/2 mt-2" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-2/3 mt-2" />
          </CardContent>
        </Card>
      </div>
    )
  }

  if (error || !commit) {
    return (
      <div className="container mx-auto max-w-6xl p-6">
        <Link
          href="/agents"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground mb-6"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back
        </Link>
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
            <h2 className="text-lg font-semibold">Commit Not Found</h2>
            <p className="text-sm text-muted-foreground">
              The commit {commitSha} could not be found.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  const shortSha = commit.commit_sha.substring(0, 7)
  const totalAdditions = commit.insertions || 0
  const totalDeletions = commit.deletions || 0
  const filesChanged = commit.files_changed || files.length

  return (
    <div className="container mx-auto max-w-6xl p-6 space-y-6">
      <Link
        href="/agents"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back
      </Link>

      {/* Commit Header */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="text-xl">{commit.commit_message || "Commit"}</CardTitle>
              <CardDescription>
                Linked via {commit.link_method || "automatic detection"}
              </CardDescription>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => copyToClipboard(commit.commit_sha)}
              >
                <Copy className="mr-1 h-3 w-3" />
                {shortSha}
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-center gap-4 text-sm">
            <div className="flex items-center gap-2">
              <User className="h-4 w-4 text-muted-foreground" />
              <span>{commit.agent_id}</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span>{formatDate(commit.commit_timestamp)}</span>
            </div>
            <div className="flex items-center gap-2">
              <Ticket className="h-4 w-4 text-muted-foreground" />
              <Link href={`/board/default/${commit.ticket_id}`} className="hover:underline">
                {commit.ticket_id}
              </Link>
            </div>
            <div className="flex items-center gap-2">
              <GitCommit className="h-4 w-4 text-muted-foreground" />
              <span className="font-mono text-xs">{commit.commit_sha}</span>
            </div>
          </div>

          {/* Stats */}
          <div className="mt-4 flex items-center gap-6">
            <div className="flex items-center gap-2">
              <FileCode className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">{filesChanged} files changed</span>
            </div>
            <div className="flex items-center gap-1">
              <Plus className="h-4 w-4 text-green-600" />
              <span className="text-sm text-green-600">{totalAdditions}</span>
            </div>
            <div className="flex items-center gap-1">
              <Minus className="h-4 w-4 text-red-500" />
              <span className="text-sm text-red-500">{totalDeletions}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* File Changes */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Changed Files</h2>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowWhitespace(!showWhitespace)}
          >
            {showWhitespace ? (
              <EyeOff className="mr-1 h-4 w-4" />
            ) : (
              <Eye className="mr-1 h-4 w-4" />
            )}
            Whitespace
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() =>
              setExpandedFiles(
                expandedFiles.length === files.length
                  ? []
                  : files.map((f) => f.path)
              )
            }
            disabled={files.length === 0}
          >
            {expandedFiles.length === files.length ? "Collapse All" : "Expand All"}
          </Button>
        </div>
      </div>

      {isDiffLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <div className="p-4">
                <Skeleton className="h-5 w-2/3" />
              </div>
            </Card>
          ))}
        </div>
      ) : files.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FileCode className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-sm text-muted-foreground">
              No file diff data available for this commit.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {files.map((file) => (
            <Card key={file.path} className="overflow-hidden">
              <Collapsible
                open={expandedFiles.includes(file.path)}
                onOpenChange={() => toggleFile(file.path)}
              >
                <CollapsibleTrigger asChild>
                  <button className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors">
                    <div className="flex items-center gap-3">
                      <ChevronRight 
                        className={`h-4 w-4 transition-transform duration-200 ${
                          expandedFiles.includes(file.path) ? "rotate-90" : ""
                        }`} 
                      />
                      <FileCode className={`h-4 w-4 ${getStatusColor(file.status)}`} />
                      <span className="font-mono text-sm">{file.path}</span>
                      {getStatusBadge(file.status)}
                    </div>
                    <div className="flex items-center gap-3 text-sm font-mono">
                      {file.additions > 0 && (
                        <span className="text-green-600">+{file.additions}</span>
                      )}
                      {file.deletions > 0 && (
                        <span className="text-red-500">-{file.deletions}</span>
                      )}
                    </div>
                  </button>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <div className="border-t bg-muted/30 p-4">
                    {file.patch ? (
                      <pre className="font-mono text-xs overflow-x-auto whitespace-pre-wrap">
                        {file.patch}
                      </pre>
                    ) : (
                      <p className="text-sm text-muted-foreground text-center py-4">
                        Patch content not available. View on GitHub for full diff.
                      </p>
                    )}
                  </div>
                </CollapsibleContent>
              </Collapsible>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
