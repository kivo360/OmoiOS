"use client"

import { use } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
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
  Trash2,
  Save,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { mockProjects } from "@/lib/mock"

interface ProjectSettingsPageProps {
  params: Promise<{ id: string }>
}

const settingsNav = [
  { href: "", label: "General", icon: Settings },
  { href: "/board", label: "Board", icon: Columns3 },
  { href: "/phases", label: "Phases", icon: Workflow },
  { href: "/github", label: "GitHub", icon: GitBranch },
]

export default function ProjectSettingsPage({ params }: ProjectSettingsPageProps) {
  const { id } = use(params)
  const pathname = usePathname()
  const project = mockProjects.find((p) => p.id === id)

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
          {/* General Settings */}
          <Card>
            <CardHeader>
              <CardTitle>General Information</CardTitle>
              <CardDescription>Basic project settings and metadata</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Project Name</Label>
                  <Input id="name" defaultValue={project.name} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="status">Status</Label>
                  <Select defaultValue={project.status}>
                    <SelectTrigger id="status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="paused">Paused</SelectItem>
                      <SelectItem value="archived">Archived</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  defaultValue={project.description}
                  rows={3}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="repo">Repository</Label>
                <Input id="repo" defaultValue={project.repo} disabled />
                <p className="text-xs text-muted-foreground">
                  Repository cannot be changed after project creation
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>Configure how you receive project updates</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Agent Completions</Label>
                  <p className="text-sm text-muted-foreground">
                    Notify when agents complete tasks
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Agent Errors</Label>
                  <p className="text-sm text-muted-foreground">
                    Notify when agents encounter errors
                  </p>
                </div>
                <Switch defaultChecked />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Phase Transitions</Label>
                  <p className="text-sm text-muted-foreground">
                    Notify when tickets change phases
                  </p>
                </div>
                <Switch />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Daily Digest</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive a daily summary of project activity
                  </p>
                </div>
                <Switch />
              </div>
            </CardContent>
          </Card>

          {/* Agent Defaults */}
          <Card>
            <CardHeader>
              <CardTitle>Agent Defaults</CardTitle>
              <CardDescription>Default settings for new agents in this project</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="defaultPhase">Default Starting Phase</Label>
                  <Select defaultValue="implementation">
                    <SelectTrigger id="defaultPhase">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="backlog">Backlog</SelectItem>
                      <SelectItem value="requirements">Requirements</SelectItem>
                      <SelectItem value="design">Design</SelectItem>
                      <SelectItem value="implementation">Implementation</SelectItem>
                      <SelectItem value="testing">Testing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maxAgents">Max Concurrent Agents</Label>
                  <Input id="maxAgents" type="number" defaultValue="5" min="1" max="20" />
                </div>
              </div>
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto-spawn on Ticket Creation</Label>
                  <p className="text-sm text-muted-foreground">
                    Automatically spawn agents for new tickets
                  </p>
                </div>
                <Switch />
              </div>
            </CardContent>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </Button>
          </div>

          {/* Danger Zone */}
          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
              <CardDescription>Irreversible and destructive actions</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="font-medium">Archive Project</p>
                  <p className="text-sm text-muted-foreground">
                    Archive this project and stop all agents
                  </p>
                </div>
                <Button variant="outline">Archive</Button>
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="font-medium">Delete Project</p>
                  <p className="text-sm text-muted-foreground">
                    Permanently delete this project and all its data
                  </p>
                </div>
                <AlertDialog>
                  <AlertDialogTrigger asChild>
                    <Button variant="destructive">
                      <Trash2 className="mr-2 h-4 w-4" />
                      Delete
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                      <AlertDialogDescription>
                        This action cannot be undone. This will permanently delete the
                        project &quot;{project.name}&quot; and all associated tickets,
                        specs, and agent history.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                        Delete Project
                      </AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
