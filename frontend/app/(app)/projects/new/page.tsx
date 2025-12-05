"use client"

import { useState } from "react"
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
import { mockRepositories } from "@/lib/mock"

export default function NewProjectPage() {
  const router = useRouter()
  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    repository: "",
    organizationId: "org-001", // Default org
  })

  const unconnectedRepos = mockRepositories.filter((r) => !r.isConnected)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000))

      toast.success("Project created successfully!")
      router.push("/projects")
    } catch (error) {
      toast.error("Failed to create project")
    } finally {
      setIsLoading(false)
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
                  setFormData({ ...formData, repository: value })
                  // Auto-fill name from repo
                  const repo = mockRepositories.find((r) => r.fullName === value)
                  if (repo && !formData.name) {
                    setFormData((prev) => ({
                      ...prev,
                      repository: value,
                      name: repo.name.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
                    }))
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a repository" />
                </SelectTrigger>
                <SelectContent>
                  {unconnectedRepos.map((repo) => (
                    <SelectItem key={repo.id} value={repo.fullName}>
                      <div className="flex items-center gap-2">
                        <FolderGit2 className="h-4 w-4" />
                        <span>{repo.fullName}</span>
                        {repo.isPrivate && (
                          <span className="text-xs text-muted-foreground">(private)</span>
                        )}
                      </div>
                    </SelectItem>
                  ))}
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
              <Button type="submit" disabled={isLoading || !formData.name || !formData.repository}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Project
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
