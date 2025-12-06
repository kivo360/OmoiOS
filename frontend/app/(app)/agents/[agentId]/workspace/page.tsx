"use client"

import { use, useState } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
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
import { mockAgents } from "@/lib/mock"

interface WorkspacePageProps {
  params: Promise<{ agentId: string }>
}

// Mock commits data
const mockCommits = [
  {
    id: "commit-1",
    sha: "a1b2c3d",
    message: "feat: Implement JWT authentication middleware",
    author: "worker-1",
    timestamp: "2 hours ago",
    filesChanged: 3,
    additions: 156,
    deletions: 12,
    files: [
      { path: "src/middleware/auth.ts", additions: 89, deletions: 5, status: "modified" },
      { path: "src/auth/jwt.ts", additions: 67, deletions: 0, status: "added" },
      { path: "src/types/auth.ts", additions: 0, deletions: 7, status: "deleted" },
    ],
  },
  {
    id: "commit-2",
    sha: "e4f5g6h",
    message: "fix: Token validation edge case",
    author: "worker-1",
    timestamp: "3 hours ago",
    filesChanged: 1,
    additions: 23,
    deletions: 8,
    files: [
      { path: "src/auth/jwt.ts", additions: 23, deletions: 8, status: "modified" },
    ],
  },
  {
    id: "commit-3",
    sha: "i7j8k9l",
    message: "test: Add unit tests for auth module",
    author: "worker-1",
    timestamp: "4 hours ago",
    filesChanged: 2,
    additions: 245,
    deletions: 0,
    files: [
      { path: "tests/auth/jwt.test.ts", additions: 189, deletions: 0, status: "added" },
      { path: "tests/middleware/auth.test.ts", additions: 56, deletions: 0, status: "added" },
    ],
  },
]

// Mock merge conflicts
const mockConflicts = [
  {
    id: "conflict-1",
    file: "src/config/database.ts",
    status: "unresolved",
    conflictType: "content",
    description: "Conflicting changes in database configuration",
    ourChanges: "connection pool size: 10",
    theirChanges: "connection pool size: 20",
  },
]

export default function WorkspacePage({ params }: WorkspacePageProps) {
  const { agentId } = use(params)
  const agent = mockAgents.find((a) => a.id === agentId)
  const [selectedCommit, setSelectedCommit] = useState<typeof mockCommits[0] | null>(null)

  if (!agent) {
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
              {agent.repoName || "Agent workspace files and commits"}
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
            <div className="text-2xl font-bold">{mockCommits.length}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Lines Changed</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-green-600">
                +{mockCommits.reduce((sum, c) => sum + c.additions, 0)}
              </span>
              <span className="text-2xl font-bold text-red-500">
                -{mockCommits.reduce((sum, c) => sum + c.deletions, 0)}
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
              <div className="space-y-3">
                {mockCommits.map((commit) => (
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
                    <TableCell>{agent.timeAgo}</TableCell>
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
