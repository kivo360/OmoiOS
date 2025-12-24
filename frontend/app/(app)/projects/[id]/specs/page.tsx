"use client"

import { use, useState } from "react"
import Link from "next/link"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { ArrowLeft, Plus, FileText, Clock, CheckCircle, AlertCircle, PlayCircle, Loader2, FolderGit2 } from "lucide-react"
import { useProjectSpecs, useCreateSpec } from "@/hooks/useSpecs"
import { useProject } from "@/hooks/useProjects"

interface SpecsPageProps {
  params: Promise<{ id: string }>
}

const statusConfig = {
  draft: { label: "Draft", icon: FileText, color: "secondary" },
  requirements: { label: "Requirements", icon: FileText, color: "secondary" },
  design: { label: "Design", icon: AlertCircle, color: "warning" },
  executing: { label: "Executing", icon: PlayCircle, color: "default" },
  completed: { label: "Completed", icon: CheckCircle, color: "success" },
}

export default function SpecsPage({ params }: SpecsPageProps) {
  const { id: projectId } = use(params)
  const router = useRouter()
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [newTitle, setNewTitle] = useState("")
  const [newDescription, setNewDescription] = useState("")

  const { data, isLoading, error } = useProjectSpecs(projectId)
  const { data: project } = useProject(projectId)
  const createMutation = useCreateSpec()

  const specs = data?.specs || []

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  const handleCreateSpec = async () => {
    if (!newTitle.trim()) {
      toast.error("Title is required")
      return
    }

    try {
      const result = await createMutation.mutateAsync({
        title: newTitle.trim(),
        description: newDescription.trim() || undefined,
        project_id: projectId,
      })
      toast.success("Spec created successfully!")
      setIsCreateOpen(false)
      setNewTitle("")
      setNewDescription("")
      router.push(`/projects/${projectId}/specs/${result.id}`)
    } catch {
      toast.error("Failed to create spec")
    }
  }

  if (isLoading) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <Skeleton className="h-4 w-32" />
        <div className="flex justify-between">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-10 w-32" />
        </div>
        {[...Array(3)].map((_, i) => (
          <Skeleton key={i} className="h-40 w-full" />
        ))}
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Project Context Breadcrumb */}
      <div className="flex items-center gap-2 text-sm">
        <Link
          href={`/projects/${projectId}`}
          className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
        >
          <FolderGit2 className="h-4 w-4" />
          <span className="font-medium text-foreground">{project?.name || "Project"}</span>
        </Link>
        <span className="text-muted-foreground">/</span>
        <span className="text-muted-foreground">Specifications</span>
      </div>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Specifications</h1>
          <p className="text-muted-foreground">
            Manage specifications and requirements for {project?.name || "this project"}
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" /> New Spec
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Specification</DialogTitle>
              <DialogDescription>
                Start by defining the title and description for your new spec.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="title">Title</Label>
                <Input
                  id="title"
                  placeholder="e.g., User Authentication System"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description (optional)</Label>
                <Textarea
                  id="description"
                  placeholder="Brief description of the specification..."
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateSpec} disabled={createMutation.isPending}>
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create Spec
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Specs List */}
      {specs.length > 0 ? (
        <div className="space-y-4">
          {specs.map((spec) => {
            const config = statusConfig[spec.status as keyof typeof statusConfig] || statusConfig.draft
            const StatusIcon = config.icon

            return (
              <Card key={spec.id} className="hover:border-primary/50 transition-colors">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-lg">
                        <Link
                          href={`/projects/${projectId}/specs/${spec.id}`}
                          className="hover:underline"
                        >
                          {spec.title}
                        </Link>
                      </CardTitle>
                      <CardDescription className="mt-1">
                        {spec.description || "No description"}
                      </CardDescription>
                    </div>
                    <Badge variant={config.color as "default" | "secondary" | "destructive" | "outline"}>
                      <StatusIcon className="mr-1 h-3 w-3" />
                      {config.label}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Progress</span>
                      <span className="font-medium">{spec.progress}%</span>
                    </div>
                    <Progress value={spec.progress} className="h-2" />
                  </div>

                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span>Phase: {spec.phase}</span>
                      <span className="flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTimeAgo(spec.updated_at)}
                      </span>
                    </div>
                    <Button variant="outline" size="sm" asChild>
                      <Link href={`/projects/${projectId}/specs/${spec.id}`}>
                        View Details
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        /* Empty State */
        <Card className="p-12 text-center">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No specifications yet</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your first specification to start defining requirements
          </p>
          <Button className="mt-4" onClick={() => setIsCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" /> Create Spec
          </Button>
        </Card>
      )}
    </div>
  )
}
