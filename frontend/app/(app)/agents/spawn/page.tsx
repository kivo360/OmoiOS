"use client"

import { useState, Suspense } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { ArrowLeft, Loader2, Bot, FolderGit2 } from "lucide-react"
import { mockProjects } from "@/lib/mock"

function SpawnAgentForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const preselectedProjectId = searchParams.get("projectId")

  const [isLoading, setIsLoading] = useState(false)
  const [formData, setFormData] = useState({
    projectId: preselectedProjectId || "",
    prompt: "",
    model: "opus-4.5",
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1500))

      const mockAgentId = `agent-${Date.now()}`
      toast.success("Agent spawned successfully!")
      router.push(`/agents/${mockAgentId}`)
    } catch (error) {
      toast.error("Failed to spawn agent")
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="container mx-auto max-w-2xl p-6 space-y-6">
      {/* Back Link */}
      <Link
        href="/agents"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Agents
      </Link>

      {/* Form Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6" />
            <div>
              <CardTitle>Spawn New Agent</CardTitle>
              <CardDescription>
                Create a new AI agent to work on your project
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Project Selection */}
            <div className="space-y-2">
              <Label htmlFor="project">Project</Label>
              <Select
                value={formData.projectId}
                onValueChange={(value) => setFormData({ ...formData, projectId: value })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a project" />
                </SelectTrigger>
                <SelectContent>
                  {mockProjects.map((project) => (
                    <SelectItem key={project.id} value={project.id}>
                      <div className="flex items-center gap-2">
                        <FolderGit2 className="h-4 w-4" />
                        <span>{project.name}</span>
                        <span className="text-xs text-muted-foreground">
                          ({project.repo})
                        </span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Task Description */}
            <div className="space-y-2">
              <Label htmlFor="prompt">Task Description</Label>
              <Textarea
                id="prompt"
                placeholder="Describe what you want the agent to do..."
                value={formData.prompt}
                onChange={(e) => setFormData({ ...formData, prompt: e.target.value })}
                rows={5}
                required
              />
              <p className="text-xs text-muted-foreground">
                Be specific about what you want to build, fix, or explore.
              </p>
            </div>

            {/* Model Selection */}
            <div className="space-y-2">
              <Label htmlFor="model">Model</Label>
              <Select
                value={formData.model}
                onValueChange={(value) => setFormData({ ...formData, model: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="opus-4.5">Opus 4.5 (Most capable)</SelectItem>
                  <SelectItem value="sonnet-4">Sonnet 4 (Balanced)</SelectItem>
                  <SelectItem value="haiku-3">Haiku 3 (Fast)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4">
              <Button type="button" variant="outline" asChild>
                <Link href="/agents">Cancel</Link>
              </Button>
              <Button
                type="submit"
                disabled={isLoading || !formData.projectId || !formData.prompt}
              >
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {isLoading ? "Spawning..." : "Spawn Agent"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

export default function SpawnAgentPage() {
  return (
    <Suspense fallback={<div className="container mx-auto p-6">Loading...</div>}>
      <SpawnAgentForm />
    </Suspense>
  )
}
