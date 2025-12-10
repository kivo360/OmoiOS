"use client"

import { use, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Checkbox } from "@/components/ui/checkbox"
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
  Plus,
  Eye,
  Pencil,
  Trash2,
  Save,
  Upload,
  ChevronRight,
  Info,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { useProject } from "@/hooks/useProjects"
import { PHASES, type PhaseConfig } from "@/lib/phases-config"

interface PhaseSettingsPageProps {
  params: Promise<{ id: string }>
}

const settingsNav = [
  { href: "", label: "General", icon: Settings },
  { href: "/board", label: "Board", icon: Columns3 },
  { href: "/phases", label: "Phases", icon: Workflow },
  { href: "/github", label: "GitHub", icon: GitBranch },
]

// Custom phases (placeholder for future API)
const initialCustomPhases: PhaseConfig[] = []

export default function PhaseSettingsPage({ params }: PhaseSettingsPageProps) {
  const { id } = use(params)
  const pathname = usePathname()
  
  const { data: project, isLoading, error } = useProject(id)
  const [customPhases, setCustomPhases] = useState(initialCustomPhases)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedPhase, setSelectedPhase] = useState<PhaseConfig | null>(null)

  if (isLoading) {
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

  if (error || !project) {
    return (
      <div className="container mx-auto p-6 text-center">
        <h1 className="text-2xl font-bold">Project not found</h1>
        <Button className="mt-4" asChild>
          <Link href="/projects">Back to Projects</Link>
        </Button>
      </div>
    )
  }

  const handleSave = () => {
    toast.success("Phase settings saved locally. Note: Custom phases are system-defined.")
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
          {/* Info Banner */}
          <div className="flex items-start gap-3 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <Info className="h-5 w-5 text-blue-600 mt-0.5" />
            <div>
              <p className="font-medium text-blue-900">Phase Configuration</p>
              <p className="text-sm text-blue-700">
                Phases are system-defined and provide a consistent workflow across all projects. Custom phase creation is planned for a future release.
              </p>
            </div>
          </div>

          {/* Default Phases */}
          <Card>
            <CardHeader>
              <CardTitle>System Phases</CardTitle>
              <CardDescription>
                System-defined phases that provide the standard workflow. These are shared across all projects.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {PHASES.map((phase: PhaseConfig, index: number) => (
                  <div
                    key={phase.id}
                    className="flex items-center gap-3 rounded-lg border p-3"
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded bg-muted text-sm font-medium">
                      {index + 1}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{phase.name}</p>
                        {phase.id === "PHASE_DONE" && (
                          <Badge variant="outline" className="text-xs">Terminal</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{phase.description}</p>
                    </div>
                    <Dialog>
                      <DialogTrigger asChild>
                        <Button variant="ghost" size="sm" onClick={() => setSelectedPhase(phase)}>
                          <Eye className="mr-2 h-3 w-3" />
                          View Details
                        </Button>
                      </DialogTrigger>
                      <DialogContent className="max-w-2xl">
                        <DialogHeader>
                          <DialogTitle>Phase: {phase.name}</DialogTitle>
                          <DialogDescription>{phase.description}</DialogDescription>
                        </DialogHeader>
                        <div className="space-y-4 py-4">
                          <div className="grid gap-4 md:grid-cols-2">
                            <div>
                              <Label className="text-muted-foreground">Phase ID</Label>
                              <p className="font-mono text-sm">{phase.id}</p>
                            </div>
                            <div>
                              <Label className="text-muted-foreground">Sequence</Label>
                              <p className="text-sm">{index + 1} of {PHASES.length}</p>
                            </div>
                          </div>
                          {phase.doneCriteria && phase.doneCriteria.length > 0 && (
                            <>
                              <Separator />
                              <div>
                                <Label className="text-muted-foreground">Done Criteria</Label>
                                <ul className="mt-2 space-y-1">
                                  {phase.doneCriteria.map((criteria: string, i: number) => (
                                    <li key={i} className="flex items-center gap-2 text-sm">
                                      <span className="text-blue-600">•</span> {criteria}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </>
                          )}
                          {phase.expectedOutputs && phase.expectedOutputs.length > 0 && (
                            <>
                              <Separator />
                              <div>
                                <Label className="text-muted-foreground">Expected Outputs</Label>
                                <div className="mt-2 space-y-1">
                                  {phase.expectedOutputs.map((output, i: number) => (
                                    <p key={i} className="font-mono text-sm text-muted-foreground">
                                      {output.pattern} ({output.type})
                                    </p>
                                  ))}
                                </div>
                              </div>
                            </>
                          )}
                        </div>
                      </DialogContent>
                    </Dialog>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Coming Soon: Custom Phases */}
          <Card className="border-dashed">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-muted-foreground">
                <Plus className="h-5 w-5" />
                Custom Phases
              </CardTitle>
              <CardDescription>
                Project-specific phases to extend the default workflow
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="py-8 text-center">
                <Workflow className="mx-auto h-12 w-12 text-muted-foreground/30" />
                <p className="mt-4 text-muted-foreground">Coming Soon</p>
                <p className="text-sm text-muted-foreground">
                  Custom phase creation will be available in a future release
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Phase Workflow Visualization */}
          <Card>
            <CardHeader>
              <CardTitle>Workflow Overview</CardTitle>
              <CardDescription>
                Visual representation of phase transitions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex items-center justify-center gap-2 overflow-x-auto py-4">
                {PHASES.map((phase: PhaseConfig, index: number, arr: PhaseConfig[]) => (
                    <div key={phase.id} className="flex items-center">
                      <div className="flex flex-col items-center">
                        <div
                          className={cn(
                            "flex h-12 w-24 items-center justify-center rounded-lg border-2 text-xs font-medium",
                            phase.id === "PHASE_DONE"
                              ? "border-green-500 bg-green-50 text-green-700"
                              : "border-border bg-card"
                          )}
                        >
                          {phase.name}
                        </div>
                        <span className="mt-1 text-xs text-muted-foreground">
                          {index + 1}
                        </span>
                      </div>
                      {index < arr.length - 1 && (
                        <ChevronRight className="mx-1 h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  ))}
              </div>
              <p className="mt-4 text-center text-xs text-muted-foreground">
                Phases follow a sequential workflow from Backlog to Done
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
