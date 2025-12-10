"use client"

import { useState, useMemo } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ArrowLeft, Loader2, FolderGit2 } from "lucide-react"
import { useCreateProject, useProjects } from "@/hooks/useProjects"
import { useConnectedRepositories } from "@/hooks/useGitHub"

export default function NewProjectPage() {
  const router = useRouter()
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    repository: "",
  })

  const createMutation = useCreateProject()
  const { data: projectsData } = useProjects()
  const { data: connectedRepos } = useConnectedRepositories()

  // Get repos that are not already connected to projects
  const availableRepos = useMemo(() => {
    if (!connectedRepos) return []
    
    // Get list of repos already connected to projects
    const connectedRepoNames = new Set(
      projectsData?.projects
        ?.filter((p) => p.github_owner && p.github_repo)
        .map((p) => `${p.github_owner}/${p.github_repo}`) || []
    )
    
    // Filter out already connected repos
    return connectedRepos.filter(
      (r) => !connectedRepoNames.has(`${r.owner}/${r.repo}`)
    )
  }, [connectedRepos, projectsData])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    // Parse owner/repo from selection
    const [github_owner, github_repo] = formData.repository.split("/")

    try {
      await createMutation.mutateAsync({
        name: formData.name,
        description: formData.description || undefined,
        github_owner,
        github_repo,
      })

      toast.success("Project created successfully!")
      router.push("/projects")
    } catch (error) {
      toast.error("Failed to create project")
    }
  }

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
              <Select
                value={formData.repository}
                onValueChange={(value) => {
                  // Auto-fill name from repo
                  const repoName = value.split("/")[1] || ""
                  if (!formData.name) {
                    setFormData({
                      ...formData,
                      repository: value,
                      name: repoName.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
                    })
                  } else {
                    setFormData({ ...formData, repository: value })
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a repository" />
                </SelectTrigger>
                <SelectContent>
                  {availableRepos.length === 0 ? (
                    <SelectItem value="" disabled>
                      No available repositories
                    </SelectItem>
                  ) : (
                    availableRepos.map((repo) => (
                      <SelectItem key={`${repo.owner}/${repo.repo}`} value={`${repo.owner}/${repo.repo}`}>
                        <div className="flex items-center gap-2">
                          <FolderGit2 className="h-4 w-4" />
                          <span>{repo.owner}/{repo.repo}</span>
                        </div>
                      </SelectItem>
                    ))
                  )}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Only repositories not connected to existing projects are shown
              </p>
            </div>

            {/* Project Name */}
            <div className="space-y-2">
              <Label htmlFor="name">Project Name</Label>
              <Input
                id="name"
                placeholder="My Awesome Project"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
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
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                rows={3}
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4">
              <Button type="button" variant="outline" asChild>
                <Link href="/projects">Cancel</Link>
              </Button>
              <Button type="submit" disabled={createMutation.isPending || !formData.name}>
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Project
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
