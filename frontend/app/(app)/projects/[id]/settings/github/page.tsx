"use client"

import { use, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import {
  ArrowLeft,
  Settings,
  Columns3,
  GitBranch,
  Workflow,
  Github,
  Check,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Link2,
  Unlink,
  Loader2,
  Webhook,
  Activity,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useProject } from "@/hooks/useProjects"
import { useConnectedRepositories, useConnectRepository, useSyncRepository } from "@/hooks/useGitHub"

interface GitHubSettingsPageProps {
  params: Promise<{ id: string }>
}

const settingsNav = [
  { href: "", label: "General", icon: Settings },
  { href: "/board", label: "Board", icon: Columns3 },
  { href: "/phases", label: "Phases", icon: Workflow },
  { href: "/github", label: "GitHub", icon: GitBranch },
]

export default function GitHubSettingsPage({ params }: GitHubSettingsPageProps) {
  const { id } = use(params)
  const pathname = usePathname()
  
  const { data: project, isLoading: projectLoading, error: projectError } = useProject(id)
  const { data: connectedRepos } = useConnectedRepositories()
  const syncMutation = useSyncRepository()
  const connectMutation = useConnectRepository()
  
  const [isSyncing, setIsSyncing] = useState(false)
  const [syncSettings, setSyncSettings] = useState({
    issues: true,
    commits: true,
    pullRequests: true,
    workflowRuns: false,
  })

  // Check if project is connected to GitHub
  const isConnected = Boolean(project?.github_owner && project?.github_repo)
  const selectedRepo = isConnected ? `${project?.github_owner}/${project?.github_repo}` : null

  const handleSync = async () => {
    setIsSyncing(true)
    try {
      await syncMutation.mutateAsync(id)
      toast.success("Sync completed successfully!")
    } catch (error) {
      toast.error("Sync failed. Please try again.")
    } finally {
      setIsSyncing(false)
    }
  }

  if (projectLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <Skeleton className="h-6 w-32" />
        <Skeleton className="h-8 w-64" />
        <div className="flex gap-6">
          <Skeleton className="h-64 w-48" />
          <Skeleton className="h-64 flex-1" />
        </div>
      </div>
    )
  }

  if (projectError || !project) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold">Project not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/projects">Back to Projects</Link>
        </Button>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Back Link */}
      <Link
        href={`/projects/${id}`}
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to {project.name}
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Project Settings</h1>
        <p className="text-muted-foreground">Manage settings for {project.name}</p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Navigation */}
        <nav className="w-48 shrink-0 space-y-1">
          {settingsNav.map((item) => {
            const isActive = pathname === `/projects/${id}/settings${item.href}`
            return (
              <Link
                key={item.href}
                href={`/projects/${id}/settings${item.href}`}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        {/* Main Content */}
        <div className="flex-1 space-y-6">
          {/* Connection Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Github className="h-5 w-5" />
                GitHub Connection
              </CardTitle>
              <CardDescription>
                Connect your GitHub repository to sync issues, commits, and pull requests
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {isConnected && selectedRepo ? (
                <>
                  <div className="flex items-center justify-between rounded-lg border bg-green-50 p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
                        <Check className="h-5 w-5 text-green-600" />
                      </div>
                      <div>
                        <p className="font-medium text-green-900">Connected</p>
                        <p className="text-sm text-green-700">
                          Repository: {selectedRepo}
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="border-green-300 text-green-700">
                      Active
                    </Badge>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label className="text-muted-foreground">GitHub Repository</Label>
                      <div className="flex items-center gap-2">
                        <GitBranch className="h-4 w-4" />
                        <span className="font-medium font-mono text-sm">{selectedRepo}</span>
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-muted-foreground">Actions</Label>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleSync}
                        disabled={isSyncing}
                      >
                        {isSyncing ? (
                          <>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Syncing...
                          </>
                        ) : (
                          <>
                            <RefreshCw className="mr-2 h-4 w-4" />
                            Sync Now
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-8">
                  <Github className="h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-4 font-medium">Not Connected</p>
                  <p className="text-sm text-muted-foreground">
                    Connect a GitHub repository to enable sync features
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    Edit the project settings to connect a repository
                  </p>
                  <Button className="mt-4" asChild>
                    <Link href={`/projects/${id}/settings`}>
                      <Settings className="mr-2 h-4 w-4" />
                      Edit Project Settings
                    </Link>
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {isConnected && (
            <>
              {/* Repository Details */}
              <Card>
                <CardHeader>
                  <CardTitle>Repository</CardTitle>
                  <CardDescription>
                    Connected GitHub repository for this project
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {selectedRepo && (
                    <div className="rounded-lg border p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <GitBranch className="h-4 w-4 text-muted-foreground" />
                          <span className="font-mono text-sm">{selectedRepo}</span>
                        </div>
                        <a
                          href={`https://github.com/${selectedRepo}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-muted-foreground hover:text-foreground"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </div>
                    </div>
                  )}
                  
                  <p className="text-xs text-muted-foreground">
                    To change the connected repository, edit the project settings on the General tab.
                  </p>
                </CardContent>
              </Card>

              {/* Webhook Info */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Webhook className="h-5 w-5" />
                    Webhook Configuration
                  </CardTitle>
                  <CardDescription>
                    Webhooks are automatically configured when a repository is connected
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <div className="flex items-center gap-3">
                      <div className="h-3 w-3 rounded-full bg-green-500" />
                      <div>
                        <p className="font-medium">Configured</p>
                        <p className="text-xs text-muted-foreground">
                          Webhook is automatically managed
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  <p className="text-xs text-muted-foreground">
                    The webhook is set up automatically to receive push events, pull requests, and issue updates from GitHub.
                  </p>
                </CardContent>
              </Card>

              {/* Auto-Sync Settings */}
              <Card>
                <CardHeader>
                  <CardTitle>Auto-Sync Settings</CardTitle>
                  <CardDescription>
                    Configure what data is automatically synchronized from GitHub
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Sync Issues</Label>
                      <p className="text-sm text-muted-foreground">
                        Import GitHub issues as tickets
                      </p>
                    </div>
                    <Switch
                      checked={syncSettings.issues}
                      onCheckedChange={(checked) =>
                        setSyncSettings({ ...syncSettings, issues: checked })
                      }
                    />
                  </div>
                  <Separator />
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Sync Commits</Label>
                      <p className="text-sm text-muted-foreground">
                        Track commits and link them to tickets
                      </p>
                    </div>
                    <Switch
                      checked={syncSettings.commits}
                      onCheckedChange={(checked) =>
                        setSyncSettings({ ...syncSettings, commits: checked })
                      }
                    />
                  </div>
                  <Separator />
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Sync Pull Requests</Label>
                      <p className="text-sm text-muted-foreground">
                        Import PRs and link them to tickets
                      </p>
                    </div>
                    <Switch
                      checked={syncSettings.pullRequests}
                      onCheckedChange={(checked) =>
                        setSyncSettings({ ...syncSettings, pullRequests: checked })
                      }
                    />
                  </div>
                  <Separator />
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <Label>Sync Workflow Runs</Label>
                      <p className="text-sm text-muted-foreground">
                        Track GitHub Actions workflow runs
                      </p>
                    </div>
                    <Switch
                      checked={syncSettings.workflowRuns}
                      onCheckedChange={(checked) =>
                        setSyncSettings({ ...syncSettings, workflowRuns: checked })
                      }
                    />
                  </div>
                </CardContent>
              </Card>

              {/* Actions */}
              <Card className="border-destructive/50">
                <CardHeader>
                  <CardTitle className="text-destructive">Danger Zone</CardTitle>
                  <CardDescription>
                    These actions can affect your GitHub integration
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="font-medium">Disconnect GitHub</p>
                      <p className="text-sm text-muted-foreground">
                        Remove the GitHub connection from this project
                      </p>
                    </div>
                    <Button variant="outline" asChild>
                      <Link href={`/projects/${id}/settings`}>
                        <Settings className="mr-2 h-4 w-4" />
                        Edit Project
                      </Link>
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    To disconnect the repository, edit the project settings and clear the GitHub repository field.
                  </p>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
