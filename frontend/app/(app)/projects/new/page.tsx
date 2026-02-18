"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  ArrowLeft,
  Loader2,
  FolderGit2,
  Github,
  Lock,
  Globe,
} from "lucide-react";
import { useCreateProject, useProjects } from "@/hooks/useProjects";
import { useGitHubRepos } from "@/hooks/useGitHubRepos";
import { useIsProviderConnected } from "@/hooks/useOAuth";
import { useOrganizations } from "@/hooks/useOrganizations";

export default function NewProjectPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    repository: "",
  });

  const createMutation = useCreateProject();
  const { data: projectsData } = useProjects();
  const { data: organizations, isLoading: orgsLoading } = useOrganizations();
  const { isConnected: isGitHubConnected, isLoading: isCheckingConnection } =
    useIsProviderConnected("github");
  const { data: repos, isLoading: reposLoading } = useGitHubRepos(
    { sort: "updated" },
    isGitHubConnected && !isCheckingConnection, // Only fetch if GitHub is connected
  );

  // Get the user's first organization (default organization)
  const defaultOrganization = organizations?.[0];

  // Get repos that are not already connected to projects
  const availableRepos = useMemo(() => {
    if (!repos) return [];

    // Get list of repos already connected to projects
    const connectedRepoNames = new Set(
      projectsData?.projects
        ?.filter((p) => p.github_owner && p.github_repo)
        .map((p) => `${p.github_owner}/${p.github_repo}`) || [],
    );

    // Filter out already connected repos
    return repos.filter((r) => !connectedRepoNames.has(r.full_name));
  }, [repos, projectsData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!defaultOrganization) {
      toast.error(
        "No organization found. Please create an organization first.",
      );
      return;
    }

    // Parse owner/repo from selection
    const [github_owner, github_repo] = formData.repository.split("/");

    try {
      await createMutation.mutateAsync({
        name: formData.name,
        organization_id: defaultOrganization.id,
        description: formData.description || undefined,
        github_owner,
        github_repo,
      });

      toast.success("Project created successfully!");
      router.push("/projects");
    } catch (error) {
      toast.error("Failed to create project");
    }
  };

  return (
    <div className="container mx-auto max-w-2xl p-6 space-y-6">
      {/* Back Link */}
      <Link
        href="/projects"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Projects
      </Link>

      {/* Form Card */}
      <Card>
        <CardHeader>
          <CardTitle>Create New Project</CardTitle>
          <CardDescription>
            Connect a GitHub repository to start managing your project
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Repository Selection */}
            <div className="space-y-2">
              <Label htmlFor="repository">GitHub Repository</Label>
              {isCheckingConnection ? (
                <Skeleton className="h-10 w-full" />
              ) : !isGitHubConnected ? (
                <div className="flex flex-col items-center justify-center rounded-lg border border-dashed p-6">
                  <Github className="h-10 w-10 text-muted-foreground/50 mb-3" />
                  <p className="text-sm font-medium">GitHub Not Connected</p>
                  <p className="text-xs text-muted-foreground mt-1 mb-3">
                    Connect your GitHub account to select a repository
                  </p>
                  <Button size="sm" asChild>
                    <Link href="/settings/integrations">Connect GitHub</Link>
                  </Button>
                </div>
              ) : (
                <>
                  <Select
                    value={formData.repository}
                    onValueChange={(value) => {
                      // Auto-fill name from repo
                      const repoName = value.split("/")[1] || "";
                      if (!formData.name) {
                        setFormData({
                          ...formData,
                          repository: value,
                          name: repoName
                            .replace(/-/g, " ")
                            .replace(/\b\w/g, (c) => c.toUpperCase()),
                        });
                      } else {
                        setFormData({ ...formData, repository: value });
                      }
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue
                        placeholder={
                          reposLoading
                            ? "Loading repositories..."
                            : "Select a repository"
                        }
                      />
                    </SelectTrigger>
                    <SelectContent className="max-h-80">
                      {reposLoading ? (
                        <div className="py-6 text-center text-sm text-muted-foreground">
                          <Loader2 className="h-4 w-4 animate-spin mx-auto mb-2" />
                          Loading repositories...
                        </div>
                      ) : availableRepos.length === 0 ? (
                        <div className="py-6 text-center text-sm text-muted-foreground">
                          No available repositories
                        </div>
                      ) : (
                        availableRepos.map((repo) => (
                          <SelectItem
                            key={repo.full_name}
                            value={repo.full_name}
                          >
                            <div className="flex items-center gap-2">
                              <FolderGit2 className="h-4 w-4 flex-shrink-0" />
                              <span className="truncate">{repo.full_name}</span>
                              {repo.private ? (
                                <Lock className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                              ) : (
                                <Globe className="h-3 w-3 text-muted-foreground flex-shrink-0" />
                              )}
                            </div>
                          </SelectItem>
                        ))
                      )}
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Only repositories not connected to existing projects are
                    shown ({availableRepos.length} available)
                  </p>
                </>
              )}
            </div>

            {/* Project Name */}
            <div className="space-y-2">
              <Label htmlFor="name">Project Name</Label>
              <Input
                id="name"
                placeholder="My Awesome Project"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                required
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label htmlFor="description">Description (optional)</Label>
              <Textarea
                id="description"
                placeholder="Describe what this project is about..."
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                rows={3}
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4">
              <Button type="button" variant="outline" asChild>
                <Link href="/projects">Cancel</Link>
              </Button>
              <Button
                type="submit"
                disabled={
                  createMutation.isPending ||
                  !formData.name ||
                  orgsLoading ||
                  !defaultOrganization
                }
              >
                {createMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                Create Project
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
