"use client"

import { use, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import { Checkbox } from "@/components/ui/checkbox"
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
import { mockProjects } from "@/lib/mock"

interface GitHubSettingsPageProps {
  params: Promise<{ id: string }>
}

const settingsNav = [
  { href: "", label: "General", icon: Settings },
  { href: "/board", label: "Board", icon: Columns3 },
  { href: "/phases", label: "Phases", icon: Workflow },
  { href: "/github", label: "GitHub", icon: GitBranch },
]

// Mock GitHub data
const mockGitHubConnection = {
  isConnected: true,
  username: "kevinhill",
  avatar: "https://github.com/kevinhill.png",
  organization: "omoi-os",
  selectedRepo: "omoi-os/omoios-core",
  webhookStatus: "active",
  webhookUrl: "https://api.omoios.com/webhooks/github/abc123",
  lastSync: "2 minutes ago",
  syncSettings: {
    issues: true,
    commits: true,
    pullRequests: true,
    workflowRuns: false,
  },
}

const mockRepositories = [
  { id: "1", fullName: "omoi-os/omoios-core", private: false },
  { id: "2", fullName: "omoi-os/omoios-frontend", private: false },
  { id: "3", fullName: "omoi-os/omoios-agents", private: true },
  { id: "4", fullName: "kevinhill/personal-project", private: true },
]

export default function GitHubSettingsPage({ params }: GitHubSettingsPageProps) {
  const { id } = use(params)
  const pathname = usePathname()
  const project = mockProjects.find((p) => p.id === id)
  const [isConnected, setIsConnected] = useState(mockGitHubConnection.isConnected)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<"success" | "error" | null>(null)
  const [syncSettings, setSyncSettings] = useState(mockGitHubConnection.syncSettings)

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

  const handleTestWebhook = () => {
    setIsTesting(true)
    setTestResult(null)
    setTimeout(() => {
      setIsTesting(false)
      setTestResult("success")
    }, 2000)
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
              {isConnected ? (
                <>
                  <div className="flex items-center justify-between rounded-lg border bg-green-50 p-4">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-full bg-green-100">
                        <Check className="h-5 w-5 text-green-600" />
                      </div>
                      <div>
                        <p className="font-medium text-green-900">Connected</p>
                        <p className="text-sm text-green-700">
                          Authenticated as @{mockGitHubConnection.username}
                        </p>
                      </div>
                    </div>
                    <Badge variant="outline" className="border-green-300 text-green-700">
                      Active
                    </Badge>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label className="text-muted-foreground">GitHub Account</Label>
                      <div className="flex items-center gap-2">
                        <img
                          src={mockGitHubConnection.avatar}
                          alt={mockGitHubConnection.username}
                          className="h-6 w-6 rounded-full"
                        />
                        <span className="font-medium">@{mockGitHubConnection.username}</span>
                        {mockGitHubConnection.organization && (
                          <Badge variant="secondary">{mockGitHubConnection.organization}</Badge>
                        )}
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label className="text-muted-foreground">Last Sync</Label>
                      <p className="flex items-center gap-2 text-sm">
                        <Activity className="h-4 w-4 text-green-500" />
                        {mockGitHubConnection.lastSync}
                      </p>
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-8">
                  <Github className="h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-4 font-medium">Not Connected</p>
                  <p className="text-sm text-muted-foreground">
                    Connect your GitHub account to enable sync features
                  </p>
                  <Button className="mt-4" onClick={() => setIsConnected(true)}>
                    <Github className="mr-2 h-4 w-4" />
                    Authorize GitHub
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {isConnected && (
            <>
              {/* Repository Selection */}
              <Card>
                <CardHeader>
                  <CardTitle>Repository</CardTitle>
                  <CardDescription>
                    Select the GitHub repository to link with this project
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="repo">Select Repository</Label>
                    <Select defaultValue={mockGitHubConnection.selectedRepo}>
                      <SelectTrigger id="repo">
                        <SelectValue placeholder="Select a repository" />
                      </SelectTrigger>
                      <SelectContent>
                        {mockRepositories.map((repo) => (
                          <SelectItem key={repo.id} value={repo.fullName}>
                            <span className="flex items-center gap-2">
                              {repo.fullName}
                              {repo.private && (
                                <Badge variant="outline" className="text-xs">Private</Badge>
                              )}
                            </span>
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {mockGitHubConnection.selectedRepo && (
                    <div className="rounded-lg border p-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <GitBranch className="h-4 w-4 text-muted-foreground" />
                          <span className="font-mono text-sm">{mockGitHubConnection.selectedRepo}</span>
                        </div>
                        <a
                          href={`https://github.com/${mockGitHubConnection.selectedRepo}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-muted-foreground hover:text-foreground"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Webhook Configuration */}
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Webhook className="h-5 w-5" />
                    Webhook Configuration
                  </CardTitle>
                  <CardDescription>
                    Configure the webhook that receives events from GitHub
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label>Webhook URL</Label>
                    <div className="flex gap-2">
                      <Input
                        value={mockGitHubConnection.webhookUrl}
                        readOnly
                        className="font-mono text-sm"
                      />
                      <Button variant="outline" size="icon">
                        <Link2 className="h-4 w-4" />
                      </Button>
                    </div>
                    <p className="text-xs text-muted-foreground">
                      This URL is automatically configured in your GitHub repository
                    </p>
                  </div>

                  <div className="flex items-center justify-between rounded-lg border p-3">
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          "h-3 w-3 rounded-full",
                          mockGitHubConnection.webhookStatus === "active"
                            ? "bg-green-500"
                            : "bg-red-500"
                        )}
                      />
                      <div>
                        <p className="font-medium">
                          {mockGitHubConnection.webhookStatus === "active" ? "Active" : "Inactive"}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          Webhook status
                        </p>
                      </div>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleTestWebhook}
                      disabled={isTesting}
                    >
                      {isTesting ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Testing...
                        </>
                      ) : (
                        <>
                          <RefreshCw className="mr-2 h-4 w-4" />
                          Test Webhook
                        </>
                      )}
                    </Button>
                  </div>

                  {testResult && (
                    <div
                      className={cn(
                        "flex items-center gap-2 rounded-lg p-3",
                        testResult === "success"
                          ? "bg-green-50 text-green-700"
                          : "bg-red-50 text-red-700"
                      )}
                    >
                      {testResult === "success" ? (
                        <>
                          <Check className="h-4 w-4" />
                          <span className="text-sm">Webhook test successful!</span>
                        </>
                      ) : (
                        <>
                          <AlertCircle className="h-4 w-4" />
                          <span className="text-sm">Webhook test failed. Please check your configuration.</span>
                        </>
                      )}
                    </div>
                  )}
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
                      <p className="font-medium">Reauthorize GitHub</p>
                      <p className="text-sm text-muted-foreground">
                        Refresh your GitHub permissions and token
                      </p>
                    </div>
                    <Button variant="outline">
                      <RefreshCw className="mr-2 h-4 w-4" />
                      Reauthorize
                    </Button>
                  </div>
                  <Separator />
                  <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                      <p className="font-medium">Disconnect GitHub</p>
                      <p className="text-sm text-muted-foreground">
                        Remove the GitHub connection from this project
                      </p>
                    </div>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="destructive">
                          <Unlink className="mr-2 h-4 w-4" />
                          Disconnect
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Disconnect GitHub?</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will remove the GitHub connection from this project.
                            Synced data will be preserved, but no new data will be synced.
                            You can reconnect at any time.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction
                            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                            onClick={() => setIsConnected(false)}
                          >
                            Disconnect
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
