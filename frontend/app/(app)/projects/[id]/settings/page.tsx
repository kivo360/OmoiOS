"use client";

import { use, useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Skeleton } from "@/components/ui/skeleton";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
} from "@/components/ui/alert-dialog";
import {
  ArrowLeft,
  Settings,
  Columns3,
  GitBranch,
  Workflow,
  Trash2,
  Save,
  Loader2,
  AlertCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import {
  useProject,
  useUpdateProject,
  useDeleteProject,
} from "@/hooks/useProjects";

interface ProjectSettingsPageProps {
  params: Promise<{ id: string }>;
}

const settingsNav = [
  { href: "", label: "General", icon: Settings },
  { href: "/board", label: "Board", icon: Columns3 },
  { href: "/phases", label: "Phases", icon: Workflow },
  { href: "/github", label: "GitHub", icon: GitBranch },
];

export default function ProjectSettingsPage({
  params,
}: ProjectSettingsPageProps) {
  const { id } = use(params);
  const pathname = usePathname();
  const router = useRouter();

  const { data: project, isLoading, error } = useProject(id);
  const updateMutation = useUpdateProject();
  const deleteMutation = useDeleteProject();

  const [formData, setFormData] = useState({
    name: "",
    description: "",
    status: "active" as "active" | "paused" | "archived" | "completed",
  });
  const [notifications, setNotifications] = useState({
    agentCompletions: true,
    agentErrors: true,
    phaseTransitions: false,
    dailyDigest: false,
  });

  useEffect(() => {
    if (project) {
      setFormData({
        name: project.name || "",
        description: project.description || "",
        status: project.status,
      });
    }
  }, [project]);

  const handleSave = async () => {
    try {
      await updateMutation.mutateAsync({
        projectId: id,
        data: {
          name: formData.name,
          description: formData.description || undefined,
          // Note: status and settings would need to match backend schema
        },
      });
      toast.success("Project settings updated");
    } catch (err) {
      toast.error("Failed to update project");
    }
  };

  const handleDelete = async () => {
    try {
      await deleteMutation.mutateAsync(id);
      toast.success("Project deleted");
      router.push("/projects");
    } catch (err) {
      toast.error("Failed to delete project");
    }
  };

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-8 w-64" />
        <div className="flex gap-6">
          <Skeleton className="h-40 w-48" />
          <div className="flex-1 space-y-4">
            <Skeleton className="h-60 w-full" />
            <Skeleton className="h-40 w-full" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !project) {
    return (
      <div className="container mx-auto p-6">
        <Card className="border-destructive/50">
          <CardContent className="p-6 text-center">
            <AlertCircle className="mx-auto h-12 w-12 text-destructive/50" />
            <h3 className="mt-4 text-lg font-semibold">Project not found</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              The project may not exist or you don&apos;t have access.
            </p>
            <Button className="mt-4" asChild>
              <Link href="/projects">Back to Projects</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    );
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
        <p className="text-muted-foreground">
          Manage settings for {project.name}
        </p>
      </div>

      <div className="flex gap-6">
        {/* Sidebar Navigation */}
        <nav className="w-48 shrink-0 space-y-1">
          {settingsNav.map((item) => {
            const isActive =
              pathname === `/projects/${id}/settings${item.href}`;
            return (
              <Link
                key={item.href}
                href={`/projects/${id}/settings${item.href}`}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  isActive
                    ? "bg-accent text-accent-foreground"
                    : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                )}
              >
                <item.icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Main Content */}
        <div className="flex-1 space-y-6">
          {/* General Settings */}
          <Card>
            <CardHeader>
              <CardTitle>General Information</CardTitle>
              <CardDescription>
                Basic project settings and metadata
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="name">Project Name</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="status">Status</Label>
                  <Select
                    value={formData.status}
                    onValueChange={(
                      value: "active" | "paused" | "archived" | "completed",
                    ) => setFormData({ ...formData, status: value })}
                  >
                    <SelectTrigger id="status">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="paused">Paused</SelectItem>
                      <SelectItem value="archived">Archived</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  rows={3}
                />
              </div>
              {project.github_repo && (
                <div className="space-y-2">
                  <Label>Repository</Label>
                  <div className="flex items-center h-10 px-3 rounded-md border bg-muted text-sm">
                    {project.github_owner}/{project.github_repo}
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Repository cannot be changed after project creation
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Notifications */}
          <Card>
            <CardHeader>
              <CardTitle>Notifications</CardTitle>
              <CardDescription>
                Configure how you receive project updates
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Agent Completions</Label>
                  <p className="text-sm text-muted-foreground">
                    Notify when agents complete tasks
                  </p>
                </div>
                <Switch
                  checked={notifications.agentCompletions}
                  onCheckedChange={(checked) =>
                    setNotifications({
                      ...notifications,
                      agentCompletions: checked,
                    })
                  }
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Agent Errors</Label>
                  <p className="text-sm text-muted-foreground">
                    Notify when agents encounter errors
                  </p>
                </div>
                <Switch
                  checked={notifications.agentErrors}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, agentErrors: checked })
                  }
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Phase Transitions</Label>
                  <p className="text-sm text-muted-foreground">
                    Notify when tickets change phases
                  </p>
                </div>
                <Switch
                  checked={notifications.phaseTransitions}
                  onCheckedChange={(checked) =>
                    setNotifications({
                      ...notifications,
                      phaseTransitions: checked,
                    })
                  }
                />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Daily Digest</Label>
                  <p className="text-sm text-muted-foreground">
                    Receive a daily summary of project activity
                  </p>
                </div>
                <Switch
                  checked={notifications.dailyDigest}
                  onCheckedChange={(checked) =>
                    setNotifications({ ...notifications, dailyDigest: checked })
                  }
                />
              </div>
              <p className="text-xs text-muted-foreground pt-2">
                Note: Notification settings are stored locally. Backend support
                coming soon.
              </p>
            </CardContent>
          </Card>

          {/* Agent Defaults */}
          <Card>
            <CardHeader>
              <CardTitle>Agent Defaults</CardTitle>
              <CardDescription>
                Default settings for new agents in this project
              </CardDescription>
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
                      <SelectItem value="implementation">
                        Implementation
                      </SelectItem>
                      <SelectItem value="testing">Testing</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maxAgents">Max Concurrent Agents</Label>
                  <Input
                    id="maxAgents"
                    type="number"
                    defaultValue="5"
                    min="1"
                    max="20"
                  />
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
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-2 h-4 w-4" />
              )}
              Save Changes
            </Button>
          </div>

          {/* Danger Zone */}
          <Card className="border-destructive/50">
            <CardHeader>
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
              <CardDescription>
                Irreversible and destructive actions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <p className="font-medium">Archive Project</p>
                  <p className="text-sm text-muted-foreground">
                    Archive this project and stop all agents
                  </p>
                </div>
                <Button
                  variant="outline"
                  onClick={() => {
                    setFormData({ ...formData, status: "archived" });
                    toast.info(
                      "Status set to archived. Click Save to confirm.",
                    );
                  }}
                >
                  Archive
                </Button>
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
                    <Button
                      variant="destructive"
                      disabled={deleteMutation.isPending}
                    >
                      {deleteMutation.isPending ? (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      ) : (
                        <Trash2 className="mr-2 h-4 w-4" />
                      )}
                      Delete
                    </Button>
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>
                        Are you absolutely sure?
                      </AlertDialogTitle>
                      <AlertDialogDescription>
                        This action cannot be undone. This will permanently
                        delete the project &quot;{project.name}&quot; and all
                        associated tickets, specs, and agent history.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction
                        onClick={handleDelete}
                        className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                      >
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
  );
}
