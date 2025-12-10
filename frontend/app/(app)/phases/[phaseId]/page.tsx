"use client"

import { use, useMemo, useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Separator } from "@/components/ui/separator"
import { Switch } from "@/components/ui/switch"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
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
  Save,
  Trash2,
  Plus,
  Pencil,
  FileCode,
  CheckCircle2,
  Clock,
  Bot,
  AlertCircle,
  ArrowRight,
  X,
  Info,
} from "lucide-react"
import { cn } from "@/lib/utils"
import { getPhaseById, ALL_PHASE_IDS, type PhaseConfig } from "@/lib/phases-config"
import { useTasks } from "@/hooks/useTasks"
import { useAgents } from "@/hooks/useAgents"

interface PhaseDetailPageProps {
  params: Promise<{ phaseId: string }>
}

export default function PhaseDetailPage({ params }: PhaseDetailPageProps) {
  const { phaseId } = use(params)
  const phase = getPhaseById(phaseId)
  
  // Fetch real data
  const { data: tasks, isLoading: tasksLoading } = useTasks()
  const { data: agents, isLoading: agentsLoading } = useAgents()
  
  const isLoading = tasksLoading || agentsLoading

  // Compute task stats for this phase
  const taskStats = useMemo(() => {
    const stats = { total: 0, done: 0, active: 0, pending: 0 }
    
    tasks?.forEach((task) => {
      if (task.phase_id === phaseId) {
        stats.total++
        if (task.status === "completed") {
          stats.done++
        } else if (task.status === "in_progress") {
          stats.active++
        } else {
          stats.pending++
        }
      }
    })

    return stats
  }, [tasks, phaseId])

  // Count active agents (simplified)
  const activeAgents = useMemo(() => {
    return agents?.filter((a) => a.status === "active" || a.status === "busy").length ?? 0
  }, [agents])
  
  const [isEditing, setIsEditing] = useState(false)
  const [name, setName] = useState(phase?.name ?? "")
  const [description, setDescription] = useState(phase?.description ?? "")
  const [order, setOrder] = useState(phase?.order ?? 0)
  const [isTerminal, setIsTerminal] = useState(phase?.isTerminal ?? false)
  const [transitions, setTransitions] = useState<string[]>(phase?.transitions ?? [])
  const [phasePrompt, setPhasePrompt] = useState(phase?.phasePrompt ?? "")

  const handleToggleTransition = (phaseTransition: string) => {
    if (transitions.includes(phaseTransition)) {
      setTransitions(transitions.filter(t => t !== phaseTransition))
    } else {
      setTransitions([...transitions, phaseTransition])
    }
  }

  // Handle unknown phase
  if (!phase) {
    return (
      <div className="container mx-auto p-6 space-y-6">
        <Link
          href="/phases"
          className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Phases
        </Link>
        <Card className="py-12">
          <CardContent className="text-center">
            <AlertCircle className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 font-semibold">Phase Not Found</h3>
            <p className="text-sm text-muted-foreground">
              The phase &quot;{phaseId}&quot; does not exist.
            </p>
            <Button asChild className="mt-4">
              <Link href="/phases">View All Phases</Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Back Link */}
      <Link
        href="/phases"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Phases
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-4">
          <div
            className="flex h-14 w-14 items-center justify-center rounded-lg text-white font-bold text-xl"
            style={{ backgroundColor: phase.color }}
          >
            {phase.order}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold">{phase.name}</h1>
              {phase.isTerminal && (
                <Badge variant="outline">Terminal</Badge>
              )}
              {phase.isSystem && (
                <Badge variant="secondary">System</Badge>
              )}
            </div>
            <p className="font-mono text-sm text-muted-foreground">{phase.id}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="secondary" className="text-xs">
            <Info className="h-3 w-3 mr-1" />
            System Phase
          </Badge>
          {!isEditing ? (
            <Button variant="outline" onClick={() => setIsEditing(true)}>
              <Pencil className="mr-2 h-4 w-4" />
              View Config
            </Button>
          ) : (
            <Button variant="outline" onClick={() => setIsEditing(false)}>
              Done
            </Button>
          )}
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-green-500" />
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">{taskStats.done}</p>
                )}
                <p className="text-sm text-muted-foreground">Completed</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Clock className="h-5 w-5 text-blue-500" />
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">{taskStats.active}</p>
                )}
                <p className="text-sm text-muted-foreground">Active</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-orange-500" />
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">{taskStats.pending}</p>
                )}
                <p className="text-sm text-muted-foreground">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <Bot className="h-5 w-5 text-primary" />
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">{activeAgents}</p>
                )}
                <p className="text-sm text-muted-foreground">Active Agents</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="basic" className="space-y-4">
        <TabsList>
          <TabsTrigger value="basic">Basic Info</TabsTrigger>
          <TabsTrigger value="criteria">Done Criteria</TabsTrigger>
          <TabsTrigger value="outputs">Expected Outputs</TabsTrigger>
          <TabsTrigger value="prompt">Phase Prompt</TabsTrigger>
          <TabsTrigger value="transitions">Transitions</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        {/* Basic Info Tab */}
        <TabsContent value="basic" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Basic Information</CardTitle>
              <CardDescription>Core phase settings and metadata</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="phaseId">Phase ID</Label>
                  <Input
                    id="phaseId"
                    value={phase.id}
                    disabled
                    className="font-mono bg-muted"
                  />
                  <p className="text-xs text-muted-foreground">
                    System identifier (read-only)
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phaseName">Display Name</Label>
                  <Input
                    id="phaseName"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    disabled={!isEditing}
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="phaseDesc">Description</Label>
                <Textarea
                  id="phaseDesc"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  disabled={!isEditing}
                  rows={3}
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="order">Sequence Order</Label>
                  <Input
                    id="order"
                    type="number"
                    min="0"
                    value={order}
                    onChange={(e) => setOrder(parseInt(e.target.value))}
                    disabled={!isEditing}
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <Label>Terminal Phase</Label>
                    <p className="text-sm text-muted-foreground">
                      No further transitions allowed
                    </p>
                  </div>
                  <Switch
                    checked={isTerminal}
                    onCheckedChange={setIsTerminal}
                    disabled={!isEditing}
                  />
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Done Criteria Tab */}
        <TabsContent value="criteria" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Done Definitions</CardTitle>
                <CardDescription>Criteria that must be met to complete this phase</CardDescription>
              </div>
              {isEditing && (
                <Button size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Criterion
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {phase.doneCriteria.length === 0 ? (
                <div className="py-8 text-center">
                  <CheckCircle2 className="mx-auto h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-4 text-muted-foreground">No done criteria defined</p>
                  {isEditing && (
                    <Button variant="outline" className="mt-4">
                      <Plus className="mr-2 h-4 w-4" />
                      Add First Criterion
                    </Button>
                  )}
                </div>
              ) : (
                <div className="space-y-2">
                  {phase.doneCriteria.map((criterion, i) => (
                    <div
                      key={i}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="flex items-center gap-3">
                        <CheckCircle2 className="h-4 w-4 text-green-500" />
                        <span>{criterion}</span>
                      </div>
                      {isEditing && (
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" className="h-8 w-8">
                            <Pencil className="h-3 w-3" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8 text-destructive"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Expected Outputs Tab */}
        <TabsContent value="outputs" className="space-y-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>Expected Outputs</CardTitle>
                <CardDescription>Files and artifacts expected from this phase</CardDescription>
              </div>
              {isEditing && (
                <Button size="sm">
                  <Plus className="mr-2 h-4 w-4" />
                  Add Output
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {phase.expectedOutputs.length === 0 ? (
                <div className="py-8 text-center">
                  <FileCode className="mx-auto h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-4 text-muted-foreground">No expected outputs defined</p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>Pattern</TableHead>
                      <TableHead>Required</TableHead>
                      {isEditing && <TableHead className="w-24">Actions</TableHead>}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {phase.expectedOutputs.map((output, i) => (
                      <TableRow key={i}>
                        <TableCell>
                          <Badge variant="secondary">{output.type}</Badge>
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {output.pattern}
                        </TableCell>
                        <TableCell>
                          {output.required ? (
                            <Badge variant="default">Required</Badge>
                          ) : (
                            <Badge variant="outline">Optional</Badge>
                          )}
                        </TableCell>
                        {isEditing && (
                          <TableCell>
                            <div className="flex items-center gap-1">
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <Pencil className="h-3 w-3" />
                              </Button>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 text-destructive"
                              >
                                <Trash2 className="h-3 w-3" />
                              </Button>
                            </div>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Phase Prompt Tab */}
        <TabsContent value="prompt" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Phase Prompt</CardTitle>
              <CardDescription>
                Instructions given to agents working in this phase
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Textarea
                value={phasePrompt}
                onChange={(e) => setPhasePrompt(e.target.value)}
                disabled={!isEditing}
                rows={10}
                className="font-mono text-sm"
                placeholder="Enter instructions for agents..."
              />
              <p className="mt-2 text-xs text-muted-foreground">
                Supports Markdown formatting. These instructions are provided to agents
                when they enter this phase.
              </p>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Transitions Tab */}
        <TabsContent value="transitions" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Allowed Transitions</CardTitle>
              <CardDescription>
                Select which phases can be transitioned to from this phase
              </CardDescription>
            </CardHeader>
            <CardContent>
              {phase.isTerminal ? (
                <div className="py-8 text-center">
                  <ArrowRight className="mx-auto h-12 w-12 text-muted-foreground/50" />
                  <p className="mt-4 text-muted-foreground">
                    Terminal phases have no outgoing transitions
                  </p>
                </div>
              ) : (
                <div className="grid gap-2 sm:grid-cols-2">
                  {ALL_PHASE_IDS.filter(p => p !== phase.id).map((phaseOption) => (
                    <div
                      key={phaseOption}
                      className={cn(
                        "flex items-center space-x-3 rounded-lg border p-3 transition-colors",
                        transitions.includes(phaseOption) && "border-primary/50 bg-primary/5"
                      )}
                    >
                      <Checkbox
                        id={phaseOption}
                        checked={transitions.includes(phaseOption)}
                        onCheckedChange={() => isEditing && handleToggleTransition(phaseOption)}
                        disabled={!isEditing}
                      />
                      <Label
                        htmlFor={phaseOption}
                        className="flex-1 cursor-pointer font-mono text-sm"
                      >
                        {phaseOption.replace("PHASE_", "")}
                      </Label>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Configuration Tab */}
        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Phase Configuration</CardTitle>
              <CardDescription>Advanced settings for phase behavior</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="timeout">Timeout (seconds)</Label>
                  <Input
                    id="timeout"
                    type="number"
                    min="0"
                    defaultValue={phase.config.timeout}
                    disabled={!isEditing}
                  />
                  <p className="text-xs text-muted-foreground">
                    0 = no timeout
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="maxRetries">Max Retries</Label>
                  <Input
                    id="maxRetries"
                    type="number"
                    min="0"
                    defaultValue={phase.config.maxRetries}
                    disabled={!isEditing}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="retryStrategy">Retry Strategy</Label>
                  <Select defaultValue={phase.config.retryStrategy} disabled={!isEditing}>
                    <SelectTrigger id="retryStrategy">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">None</SelectItem>
                      <SelectItem value="linear">Linear</SelectItem>
                      <SelectItem value="exponential">Exponential Backoff</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="wipLimit">WIP Limit</Label>
                  <Input
                    id="wipLimit"
                    type="number"
                    min="0"
                    defaultValue={phase.config.wipLimit}
                    disabled={!isEditing}
                  />
                  <p className="text-xs text-muted-foreground">
                    0 = unlimited
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Danger Zone */}
      {!phase.isSystem && (
        <Card className="border-destructive/50">
          <CardHeader>
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
            <CardDescription>Irreversible actions for this phase</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <p className="font-medium">Delete Phase</p>
                <p className="text-sm text-muted-foreground">
                  Permanently delete this custom phase
                </p>
              </div>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive">
                    <Trash2 className="mr-2 h-4 w-4" />
                    Delete Phase
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>Delete Phase?</AlertDialogTitle>
                    <AlertDialogDescription>
                      This will permanently delete the phase &quot;{phase.name}&quot;.
                      Tasks in this phase will be moved to PHASE_BACKLOG.
                      This action cannot be undone.
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
          </CardContent>
        </Card>
      )}
    </div>
  )
}
