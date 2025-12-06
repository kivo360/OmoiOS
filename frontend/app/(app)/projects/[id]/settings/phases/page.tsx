"use client"

import { use, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Checkbox } from "@/components/ui/checkbox"
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
} from "lucide-react"
import { cn } from "@/lib/utils"
import { mockProjects } from "@/lib/mock"

interface PhaseSettingsPageProps {
  params: Promise<{ id: string }>
}

const settingsNav = [
  { href: "", label: "General", icon: Settings },
  { href: "/board", label: "Board", icon: Columns3 },
  { href: "/phases", label: "Phases", icon: Workflow },
  { href: "/github", label: "GitHub", icon: GitBranch },
]

// Default phases (read-only)
const defaultPhases = [
  {
    id: "PHASE_BACKLOG",
    name: "Backlog",
    description: "Initial phase for new tickets",
    order: 0,
    isTerminal: false,
    transitions: ["PHASE_REQUIREMENTS", "PHASE_BLOCKED"],
  },
  {
    id: "PHASE_REQUIREMENTS",
    name: "Requirements",
    description: "Gathering and documenting requirements",
    order: 1,
    isTerminal: false,
    transitions: ["PHASE_DESIGN", "PHASE_BLOCKED"],
  },
  {
    id: "PHASE_DESIGN",
    name: "Design",
    description: "Designing the solution architecture",
    order: 2,
    isTerminal: false,
    transitions: ["PHASE_IMPLEMENTATION", "PHASE_BLOCKED"],
  },
  {
    id: "PHASE_IMPLEMENTATION",
    name: "Implementation",
    description: "Developing and implementing the solution",
    order: 3,
    isTerminal: false,
    transitions: ["PHASE_TESTING", "PHASE_BLOCKED"],
    doneCriteria: ["All code files created", "Minimum 3 test cases passing"],
    expectedOutputs: ["src/**/*.py", "tests/**/*.py"],
  },
  {
    id: "PHASE_TESTING",
    name: "Testing",
    description: "Testing and quality assurance",
    order: 4,
    isTerminal: false,
    transitions: ["PHASE_DEPLOYMENT", "PHASE_BLOCKED"],
  },
  {
    id: "PHASE_DEPLOYMENT",
    name: "Deployment",
    description: "Deploying to production",
    order: 5,
    isTerminal: false,
    transitions: ["PHASE_DONE"],
  },
  {
    id: "PHASE_DONE",
    name: "Done",
    description: "Completed and delivered",
    order: 6,
    isTerminal: true,
    transitions: [],
  },
  {
    id: "PHASE_BLOCKED",
    name: "Blocked",
    description: "Blocked by dependencies or issues",
    order: 99,
    isTerminal: false,
    transitions: ["PHASE_BACKLOG", "PHASE_REQUIREMENTS", "PHASE_DESIGN", "PHASE_IMPLEMENTATION", "PHASE_TESTING"],
  },
]

// Custom phases (editable)
const initialCustomPhases = [
  {
    id: "PHASE_CODE_REVIEW",
    name: "Code Review",
    description: "Peer review of code changes",
    order: 4,
    isTerminal: false,
    transitions: ["PHASE_TESTING", "PHASE_IMPLEMENTATION"],
  },
]

export default function PhaseSettingsPage({ params }: PhaseSettingsPageProps) {
  const { id } = use(params)
  const pathname = usePathname()
  const project = mockProjects.find((p) => p.id === id)
  const [customPhases, setCustomPhases] = useState(initialCustomPhases)
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [selectedPhase, setSelectedPhase] = useState<typeof defaultPhases[0] | null>(null)

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
          {/* Default Phases */}
          <Card>
            <CardHeader>
              <CardTitle>Default Phases</CardTitle>
              <CardDescription>
                System-defined phases that provide the standard workflow. These cannot be deleted.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {defaultPhases.map((phase) => (
                  <div
                    key={phase.id}
                    className="flex items-center gap-3 rounded-lg border p-3"
                  >
                    <div className="flex h-8 w-8 items-center justify-center rounded bg-muted text-sm font-medium">
                      {phase.order}
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="font-medium">{phase.name}</p>
                        {phase.isTerminal && (
                          <Badge variant="outline" className="text-xs">Terminal</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">{phase.description}</p>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      {phase.transitions.length > 0 && (
                        <>
                          <span>→</span>
                          <span>{phase.transitions.length} transitions</span>
                        </>
                      )}
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
                              <Label className="text-muted-foreground">Sequence Order</Label>
                              <p className="text-sm">{phase.order}</p>
                            </div>
                          </div>
                          <Separator />
                          <div>
                            <Label className="text-muted-foreground">Allowed Transitions</Label>
                            <div className="mt-2 flex flex-wrap gap-2">
                              {phase.transitions.length > 0 ? (
                                phase.transitions.map((t) => (
                                  <Badge key={t} variant="secondary">
                                    {t.replace("PHASE_", "")}
                                  </Badge>
                                ))
                              ) : (
                                <p className="text-sm text-muted-foreground">No transitions (terminal phase)</p>
                              )}
                            </div>
                          </div>
                          {phase.doneCriteria && (
                            <>
                              <Separator />
                              <div>
                                <Label className="text-muted-foreground">Done Criteria</Label>
                                <ul className="mt-2 space-y-1">
                                  {phase.doneCriteria.map((c, i) => (
                                    <li key={i} className="flex items-center gap-2 text-sm">
                                      <span className="text-green-600">✓</span> {c}
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            </>
                          )}
                          {phase.expectedOutputs && (
                            <>
                              <Separator />
                              <div>
                                <Label className="text-muted-foreground">Expected Outputs</Label>
                                <div className="mt-2 space-y-1">
                                  {phase.expectedOutputs.map((o, i) => (
                                    <p key={i} className="font-mono text-sm text-muted-foreground">{o}</p>
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

          {/* Custom Phases */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Custom Phases</CardTitle>
                <CardDescription>
                  Project-specific phases that extend the default workflow
                </CardDescription>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" size="sm">
                  <Upload className="mr-2 h-4 w-4" />
                  Import YAML
                </Button>
                <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
                  <DialogTrigger asChild>
                    <Button size="sm">
                      <Plus className="mr-2 h-4 w-4" />
                      Create Custom Phase
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="max-w-2xl">
                    <DialogHeader>
                      <DialogTitle>Create Custom Phase</DialogTitle>
                      <DialogDescription>
                        Define a new phase for your project workflow
                      </DialogDescription>
                    </DialogHeader>
                    <div className="space-y-4 py-4">
                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                          <Label htmlFor="phaseId">Phase ID</Label>
                          <Input
                            id="phaseId"
                            placeholder="PHASE_"
                            className="font-mono"
                          />
                          <p className="text-xs text-muted-foreground">
                            Must start with &quot;PHASE_&quot; (e.g., PHASE_CODE_REVIEW)
                          </p>
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="phaseName">Display Name</Label>
                          <Input id="phaseName" placeholder="e.g., Code Review" />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="phaseDesc">Description</Label>
                        <Textarea
                          id="phaseDesc"
                          placeholder="Describe what happens in this phase..."
                          rows={2}
                        />
                      </div>
                      <div className="grid gap-4 md:grid-cols-2">
                        <div className="space-y-2">
                          <Label htmlFor="phaseOrder">Sequence Order</Label>
                          <Input id="phaseOrder" type="number" min="0" defaultValue="5" />
                        </div>
                        <div className="flex items-center space-x-2 pt-6">
                          <Checkbox id="isTerminal" />
                          <Label htmlFor="isTerminal" className="font-normal">
                            Terminal phase (no further transitions)
                          </Label>
                        </div>
                      </div>
                      <Separator />
                      <div className="space-y-2">
                        <Label>Allowed Transitions</Label>
                        <div className="grid gap-2 sm:grid-cols-3">
                          {defaultPhases.filter(p => !p.isTerminal || p.id === "PHASE_DONE").map((phase) => (
                            <div key={phase.id} className="flex items-center space-x-2">
                              <Checkbox id={`trans-${phase.id}`} />
                              <Label htmlFor={`trans-${phase.id}`} className="font-normal text-sm">
                                {phase.name}
                              </Label>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                        Cancel
                      </Button>
                      <Button onClick={() => setIsCreateOpen(false)}>Create Phase</Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </CardHeader>
            <CardContent>
              {customPhases.length === 0 ? (
                <div className="py-8 text-center">
                  <Workflow className="mx-auto h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-4 text-muted-foreground">No custom phases defined</p>
                  <p className="text-sm text-muted-foreground">
                    Create custom phases to extend your workflow
                  </p>
                </div>
              ) : (
                <div className="space-y-2">
                  {customPhases.map((phase) => (
                    <div
                      key={phase.id}
                      className="flex items-center gap-3 rounded-lg border p-3"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded bg-primary/10 text-sm font-medium text-primary">
                        {phase.order}
                      </div>
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{phase.name}</p>
                          <Badge variant="outline" className="text-xs">Custom</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground">{phase.description}</p>
                      </div>
                      <div className="flex items-center gap-1 text-xs text-muted-foreground">
                        <span>→</span>
                        <span>{phase.transitions.length} transitions</span>
                      </div>
                      <Button variant="ghost" size="icon" className="h-8 w-8">
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <AlertDialog>
                        <AlertDialogTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>Delete Phase?</AlertDialogTitle>
                            <AlertDialogDescription>
                              This will delete the custom phase &quot;{phase.name}&quot;. Tickets in this
                              phase will be moved to the Backlog. This action cannot be undone.
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>Cancel</AlertDialogCancel>
                            <AlertDialogAction className="bg-destructive text-destructive-foreground hover:bg-destructive/90">
                              Delete Phase
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  ))}
                </div>
              )}
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
                {defaultPhases
                  .filter((p) => p.id !== "PHASE_BLOCKED")
                  .sort((a, b) => a.order - b.order)
                  .map((phase, index, arr) => (
                    <div key={phase.id} className="flex items-center">
                      <div className="flex flex-col items-center">
                        <div
                          className={cn(
                            "flex h-12 w-24 items-center justify-center rounded-lg border-2 text-xs font-medium",
                            phase.isTerminal
                              ? "border-green-500 bg-green-50 text-green-700"
                              : "border-border bg-card"
                          )}
                        >
                          {phase.name}
                        </div>
                        <span className="mt-1 text-xs text-muted-foreground">
                          {phase.order}
                        </span>
                      </div>
                      {index < arr.length - 1 && (
                        <ChevronRight className="mx-1 h-4 w-4 text-muted-foreground" />
                      )}
                    </div>
                  ))}
              </div>
              <p className="mt-4 text-center text-xs text-muted-foreground">
                Blocked phase can transition to any non-terminal phase
              </p>
            </CardContent>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button>
              <Save className="mr-2 h-4 w-4" />
              Save Changes
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
