"use client"

import { use } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { ArrowLeft, Plus, FileText, Clock, CheckCircle, AlertCircle, PlayCircle } from "lucide-react"

interface SpecsPageProps {
  params: Promise<{ id: string }>
}

// Mock specs data
const mockSpecs = [
  {
    id: "spec-001",
    title: "User Authentication",
    description: "Implement secure user authentication with OAuth2 and JWT",
    status: "executing",
    progress: 75,
    phase: "Implementation",
    updatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000),
  },
  {
    id: "spec-002",
    title: "Payment Processing",
    description: "Integrate Stripe for payment processing",
    status: "design",
    progress: 40,
    phase: "Design",
    updatedAt: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000),
  },
  {
    id: "spec-003",
    title: "API Rate Limiting",
    description: "Add rate limiting to prevent API abuse",
    status: "requirements",
    progress: 20,
    phase: "Requirements",
    updatedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
  },
]

const statusConfig = {
  draft: { label: "Draft", icon: FileText, color: "secondary" },
  requirements: { label: "Requirements", icon: FileText, color: "secondary" },
  design: { label: "Design", icon: AlertCircle, color: "warning" },
  executing: { label: "Executing", icon: PlayCircle, color: "default" },
  completed: { label: "Completed", icon: CheckCircle, color: "success" },
}

export default function SpecsPage({ params }: SpecsPageProps) {
  const { id } = use(params)

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Back Link */}
      <Link
        href={`/projects/${id}`}
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Project
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Specifications</h1>
          <p className="text-muted-foreground">
            Manage project specifications and requirements
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" /> New Spec
        </Button>
      </div>

      {/* Specs List */}
      <div className="space-y-4">
        {mockSpecs.map((spec) => {
          const config = statusConfig[spec.status as keyof typeof statusConfig]
          const StatusIcon = config.icon

          return (
            <Card key={spec.id} className="hover:border-primary/50 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">
                      <Link
                        href={`/projects/${id}/specs/${spec.id}`}
                        className="hover:underline"
                      >
                        {spec.title}
                      </Link>
                    </CardTitle>
                    <CardDescription className="mt-1">
                      {spec.description}
                    </CardDescription>
                  </div>
                  <Badge variant={config.color as any}>
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
                      {formatTimeAgo(spec.updatedAt)}
                    </span>
                  </div>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={`/projects/${id}/specs/${spec.id}`}>
                      View Details
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Empty State */}
      {mockSpecs.length === 0 && (
        <Card className="p-12 text-center">
          <FileText className="mx-auto h-12 w-12 text-muted-foreground" />
          <h3 className="mt-4 text-lg font-semibold">No specifications yet</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Create your first specification to start defining requirements
          </p>
          <Button className="mt-4">
            <Plus className="mr-2 h-4 w-4" /> Create Spec
          </Button>
        </Card>
      )}
    </div>
  )
}
