"use client"

import { use, useState, useMemo } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  ArrowLeft,
  GitBranch,
  GitCommit,
  FolderGit2,
  AlertTriangle,
  Settings,
  Clock,
  CheckCircle,
  XCircle,
  Eye,
  FileCode,
  Plus,
  Minus,
} from "lucide-react"
import { useAgent } from "@/hooks/useAgents"
import { useAgentCommits } from "@/hooks/useCommits"
import type { Commit } from "@/lib/api/types"

interface WorkspacePageProps {
  params: Promise<{ agentId: string }>
}

// Commit display type with computed fields
interface CommitDisplay {
  id: string
  sha: string
  message: string
  author: string
  timestamp: string
  filesChanged: number
  additions: number
  deletions: number
  files: Array<{
    path: string
    additions: number
    deletions: number
    status: string
  }>
}

// Mock merge conflicts (no backend API for this yet)
const mockConflicts: Array<{
  id: string
  file: string
  status: string
  conflictType: string
  description: string
  ourChanges: string
  theirChanges: string
}> = []

function formatTimeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "unknown"
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
  const diffDays = Math.floor(diffHours / 24)

  if (diffHours < 1) return "just now"
  if (diffHours < 24) return `${diffHours} hours ago`
  if (diffDays < 7) return `${diffDays} days ago`
  return `${Math.floor(diffDays / 7)} weeks ago`
}

export default function WorkspacePage({ params }: WorkspacePageProps) {
  const { agentId } = use(params)
  const { data: agent, isLoading: agentLoading, error: agentError } = useAgent(agentId)
  const { data: commitsData, isLoading: commitsLoading } = useAgentCommits(agentId)
  const [selectedCommit, setSelectedCommit] = useState<CommitDisplay | null>(null)

  // Transform commits to display format
  const commits: CommitDisplay[] = useMemo(() => {
    if (!commitsData?.commits) return []
    return commitsData.commits.map((c) => ({
      id: c.commit_sha,
      sha: c.commit_sha.slice(0, 7),
      message: c.commit_message,
      author: c.agent_id?.slice(0, 8) || "unknown",
      timestamp: formatTimeAgo(c.commit_timestamp),
      filesChanged: c.files_changed || 0,
      additions: c.insertions || 0,
      deletions: c.deletions || 0,
      files: [], // Would need additional API call to get file details
    }))
  }, [commitsData])

  if (agentLoading) {
    return (
      <div className="container mx-auto max-w-5xl p-6 space-y-6">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (agentError || !agent) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold">Agent not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/agents">Back to Agents</Link>
        </Button>
      </div>
    )
  }

  const handleResolveConflict = (conflictId: string) => {
    toast.success("Conflict resolution initiated")
  }

  return (
    <div className="container mx-auto max-w-5xl p-6 space-y-6">
      {/* Header */}
      <div>
        <Link
          href={`/agents/${agentId}`}
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Agent
        </Link>
        <div className="mt-4 flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              <FolderGit2 className="h-6 w-6" />
              Workspace
            </h1>
            <p className="text-muted-foreground mt-1">
              {agent.phase_id?.replace("PHASE_", "") || "Agent workspace files and commits"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="gap-1">
              <GitBranch className="h-3 w-3" />
              feature/jwt-auth
            </Badge>
          </div>
        </div>
      </div>

      {/* Workspace Info Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Commits</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{commits.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Lines Changed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-green-600">
                +{commits.reduce((sum, c) => sum + c.additions, 0)}
              </span>
              <span className="text-2xl font-bold text-red-500">
                -{commits.reduce((sum, c) => sum + c.deletions, 0)}
              </span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Merge Conflicts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {mockConflicts.filter((c) => c.status === "unresolved").length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="commits" className="space-y-4">
        <TabsList>
          <TabsTrigger value="commits" className="gap-2">
            <GitCommit className="h-4 w-4" />
            Commits
          </TabsTrigger>
          <TabsTrigger value="conflicts" className="gap-2">
            <AlertTriangle className="h-4 w-4" />
            Merge Conflicts
            {mockConflicts.length > 0 && (
              <Badge variant="destructive" className="ml-1 h-5 w-5 rounded-full p-0 text-xs">
                {mockConflicts.length}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="settings" className="gap-2">
            <Settings className="h-4 w-4" />
            Settings
          </TabsTrigger>
        </TabsList>

        {/* Commits Tab */}
        <TabsContent value="commits" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Commit History</CardTitle>
              <CardDescription>
                All commits made by this agent in the workspace
              </CardDescription>
            </CardHeader>
            <CardContent>
              {commitsLoading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <Skeleton key={i} className="h-24 w-full" />
                  ))}
                </div>
              ) : commits.length === 0 ? (
                <div className="py-8 text-center text-muted-foreground">
                  <GitCommit className="mx-auto h-12 w-12 text-muted-foreground/30" />
                  <p className="mt-2">No commits yet</p>
                  <p className="text-sm">This agent hasn't made any commits</p>
                </div>
              ) : (
              <div className="space-y-3">
                {commits.map((commit) => (
                  <div
                    key={commit.id}
                    className="flex items-start justify-between rounded-lg border p-4 hover:bg-accent/50 transition-colors"
                  >
                    <div className="flex items-start gap-3">
                      <GitCommit className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div>
                        <p className="font-medium">{commit.message}</p>
                        <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                          <code className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">
                            {commit.sha}
                          </code>
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {commit.timestamp}
                          </span>
                          <span>{commit.filesChanged} files</span>
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs font-mono text-green-600">+{commit.additions}</span>
                          <span className="text-xs font-mono text-red-500">-{commit.deletions}</span>
                        </div>
                      </div>
                    </div>
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => setSelectedCommit(commit)}
                        >
                          <Eye className="mr-1 h-3 w-3" />
                          View
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl">
                        <DialogHeader>
                          <DialogTitle>{commit.message}</DialogTitle>
                          <DialogDescription>
                            Commit {commit.sha} • {commit.timestamp}
                          </DialogDescription>
                        </DialogHeader>
                        <ScrollArea className="max-h-[400px]">
                          <div className="space-y-3">
                            {commit.files.map((file) => (
                              <div
                                key={file.path}
                                className="flex items-center justify-between rounded-lg border p-3"
                              >
                                <div className="flex items-center gap-2">
                                  <FileCode className="h-4 w-4 text-muted-foreground" />
                                  <span className="font-mono text-sm">{file.path}</span>
                                  <Badge
                                    variant={
                                      file.status === "added"
                                        ? "default"
                                        : file.status === "deleted"
                                        ? "destructive"
                                        : "secondary"
                                    }
                                    className="text-xs"
                                  >
                                    {file.status}
                                  </Badge>
                                </div>
                                <div className="flex items-center gap-2 font-mono text-xs">
                                  <span className="text-green-600">+{file.additions}</span>
                                  <span className="text-red-500">-{file.deletions}</span>
                                </div>
                              </div>
                            ))}
                          </div>
                        </ScrollArea>
                      </DialogContent>
                    </Dialog>
                  </div>
                ))}
              </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Merge Conflicts Tab */}
        <TabsContent value="conflicts" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Merge Conflicts</CardTitle>
              <CardDescription>
                Files with conflicts that need resolution
              </CardDescription>
            </CardHeader>
            <CardContent>
              {mockConflicts.length === 0 ? (
                <div className="text-center py-8">
                  <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
                  <h3 className="mt-4 text-lg font-semibold">No Merge Conflicts</h3>
                  <p className="mt-2 text-sm text-muted-foreground">
                    All files are conflict-free
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {mockConflicts.map((conflict) => (
                    <div
                      key={conflict.id}
                      className="rounded-lg border border-destructive/50 p-4"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-start gap-3">
                          <AlertTriangle className="h-5 w-5 text-destructive mt-0.5" />
                          <div>
                            <p className="font-mono text-sm font-medium">{conflict.file}</p>
                            <p className="text-sm text-muted-foreground mt-1">
                              {conflict.description}
                            </p>
                            <Badge
                              variant={conflict.status === "unresolved" ? "destructive" : "default"}
                              className="mt-2"
                            >
                              {conflict.status}
                            </Badge>
                          </div>
                        </div>
                        <Button
                          size="sm"
                          onClick={() => handleResolveConflict(conflict.id)}
                        >
                          Resolve
                        </Button>
                      </div>
                      <div className="mt-4 grid gap-4 md:grid-cols-2">
                        <div className="rounded-md bg-muted p-3">
                          <p className="text-xs text-muted-foreground mb-2">Our Changes</p>
                          <code className="text-sm">{conflict.ourChanges}</code>
                        </div>
                        <div className="rounded-md bg-muted p-3">
                          <p className="text-xs text-muted-foreground mb-2">Their Changes</p>
                          <code className="text-sm">{conflict.theirChanges}</code>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Settings Tab */}
        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Workspace Configuration</CardTitle>
              <CardDescription>
                Workspace settings and metadata
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableBody>
                  <TableRow>
                    <TableCell className="font-medium">Workspace Path</TableCell>
                    <TableCell className="font-mono text-sm">
                      /workspaces/{agentId}
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">Git Branch</TableCell>
                    <TableCell className="font-mono text-sm">
                      feature/jwt-auth
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">Workspace Type</TableCell>
                    <TableCell>
                      <Badge variant="outline">Docker Container</Badge>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">Parent Agent</TableCell>
                    <TableCell className="text-muted-foreground">None (root)</TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">Retention Policy</TableCell>
                    <TableCell>
                      <Badge variant="secondary">7 days after completion</Badge>
                    </TableCell>
                  </TableRow>
                  <TableRow>
                    <TableCell className="font-medium">Created</TableCell>
                    <TableCell>{agent.created_at ? formatTimeAgo(agent.created_at) : "unknown"}</TableCell>
                  </TableRow>
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
