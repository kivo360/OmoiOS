"use client"

import { use, useState, useMemo, useEffect, useRef } from "react"
import Link from "next/link"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import {
  ArrowLeft,
  FileText,
  Palette,
  ListTodo,
  Play,
  MoreHorizontal,
  Download,
  History,
  Settings,
  ChevronDown,
  ChevronRight,
  Plus,
  Edit,
  Trash2,
  CheckCircle,
  Clock,
  AlertCircle,
  Bot,
  GitBranch,
  ExternalLink,
  Loader2,
  Check,
  X,
  Link as LinkIcon,
  FolderGit2,
} from "lucide-react"
import {
  useSpec,
  useProjectSpecs,
  useApproveRequirements,
  useApproveDesign,
  useAddRequirement,
  useAddTask,
  useUpdateTask,
  useDeleteTask,
  useDeleteRequirement,
  useAddCriterion,
  useSpecVersions,
  useExecuteSpecTasks,
  useExecutionStatus,
  useCriteriaStatus,
  useCreateSpecBranch,
  useCreateSpecPR,
  useSpecEvents,
  useDeleteSpec,
  useUpdateSpec,
  useLinkTickets,
  useLinkedTickets,
  useExportSpec,
} from "@/hooks/useSpecs"
import { useTickets } from "@/hooks/useTickets"
import { Checkbox } from "@/components/ui/checkbox"
import { useRouter } from "next/navigation"
import { EventTimeline, PhaseProgress, PhaseProgressInline } from "@/components/spec"
import { useProject } from "@/hooks/useProjects"
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
import { Markdown } from "@/components/ui/markdown"

interface SpecPageProps {
  params: Promise<{ id: string; specId: string }>
}

// Empty default data (no mock data - show real data or empty states)

const statusConfig = {
  pending: { label: "Pending", color: "secondary", icon: Clock },
  in_progress: { label: "In Progress", color: "warning", icon: Loader2 },
  completed: { label: "Completed", color: "success", icon: CheckCircle },
}

const priorityConfig = {
  high: { label: "High", color: "destructive" },
  medium: { label: "Medium", color: "warning" },
  low: { label: "Low", color: "secondary" },
}

export default function SpecWorkspacePage({ params }: SpecPageProps) {
  const { id: projectId, specId } = use(params)
  const [activeTab, setActiveTab] = useState("requirements")
  const [expandedRequirements, setExpandedRequirements] = useState<string[]>(["REQ-001"])

  // Dialog states
  const [addRequirementOpen, setAddRequirementOpen] = useState(false)
  const [addTaskOpen, setAddTaskOpen] = useState(false)
  const [addCriterionOpen, setAddCriterionOpen] = useState<string | null>(null) // reqId or null
  const [editTaskOpen, setEditTaskOpen] = useState(false)
  const [viewTaskOpen, setViewTaskOpen] = useState(false)
  const [selectedTask, setSelectedTask] = useState<{
    id: string
    title: string
    description: string
    phase: string
    priority: string
    status: string
    assigned_agent: string | null
  } | null>(null)

  // Settings modal state
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [editSpecTitle, setEditSpecTitle] = useState("")
  const [editSpecDescription, setEditSpecDescription] = useState("")

  // Link tickets modal state
  const [linkTicketsOpen, setLinkTicketsOpen] = useState(false)
  const [linkedTicketIds, setLinkedTicketIds] = useState<Set<string>>(new Set())

  // History modal state
  const [historyOpen, setHistoryOpen] = useState(false)

  // Form states
  const [newRequirement, setNewRequirement] = useState({ title: "", condition: "", action: "" })
  const [newTask, setNewTask] = useState({ title: "", description: "", phase: "Implementation", priority: "medium" })
  const [newCriterionText, setNewCriterionText] = useState("")
  const [editTask, setEditTask] = useState({ title: "", description: "", phase: "", priority: "", status: "" })

  // Fetch project and spec data
  const { data: project } = useProject(projectId)
  // Poll spec every 5s when executing to see real-time task status updates
  // Also refetch on window focus to ensure fresh data when user returns
  const { data: spec, isLoading: specLoading, error: specError } = useSpec(specId, {
    refetchInterval: (query) => {
      // Enable polling only when spec is executing
      const specData = query.state.data
      return specData?.status === "executing" ? 5000 : false
    },
    refetchOnWindowFocus: true,
    staleTime: 10_000, // Consider data stale after 10s for this page
  })
  const { data: allSpecs } = useProjectSpecs(projectId)
  const { data: versionsData } = useSpecVersions(specId, 10)

  // Execution status - poll every 5s when executing
  const isExecuting = spec?.status === "executing"
  const { data: executionStatus } = useExecutionStatus(specId, {
    enabled: isExecuting,
    refetchInterval: isExecuting ? 5000 : false,
  })
  const { data: criteriaStatus } = useCriteriaStatus(specId, {
    enabled: isExecuting,
    refetchInterval: isExecuting ? 5000 : false,
  })

  // Track phase changes for toast notifications
  const previousPhaseRef = useRef<string | null>(null)
  const previousStatusRef = useRef<string | null>(null)

  useEffect(() => {
    if (!spec) return

    const currentPhase = spec.phase?.toLowerCase()
    const currentStatus = spec.status

    // Phase transition notification
    if (previousPhaseRef.current && currentPhase && previousPhaseRef.current !== currentPhase) {
      const phaseLabels: Record<string, string> = {
        explore: "🔍 Explore",
        requirements: "📋 Requirements",
        design: "🎨 Design",
        tasks: "📝 Tasks",
        sync: "🔄 Sync",
        complete: "✅ Complete",
      }
      const phaseLabel = phaseLabels[currentPhase] || currentPhase
      const fromPhaseLabel = phaseLabels[previousPhaseRef.current] || previousPhaseRef.current

      toast.success(`Phase transitioned: ${fromPhaseLabel} → ${phaseLabel}`, {
        description: "Spec execution progressing",
        duration: 5000,
      })
    }

    // Status transition notification (started, completed, failed)
    if (previousStatusRef.current && currentStatus && previousStatusRef.current !== currentStatus) {
      if (currentStatus === "completed") {
        toast.success("🎉 Spec execution completed!", {
          description: "All tasks have been processed",
          duration: 8000,
        })
      } else if (currentStatus === "failed") {
        toast.error("❌ Spec execution failed", {
          description: "Check the event timeline for details",
          duration: 10000,
        })
      } else if (currentStatus === "executing" && previousStatusRef.current === "draft") {
        toast.info("🚀 Spec execution started", {
          description: "Working through phases...",
          duration: 4000,
        })
      }
    }

    previousPhaseRef.current = currentPhase || null
    previousStatusRef.current = currentStatus
  }, [spec?.phase, spec?.status])

  // Router for navigation after delete
  const router = useRouter()

  // Mutations
  const approveReqMutation = useApproveRequirements(specId)
  const approveDesignMutation = useApproveDesign(specId)
  const addRequirementMutation = useAddRequirement(specId)
  const addTaskMutation = useAddTask(specId)
  const updateTaskMutation = useUpdateTask(specId)
  const deleteTaskMutation = useDeleteTask(specId)
  const deleteRequirementMutation = useDeleteRequirement(specId)
  const addCriterionMutation = useAddCriterion(specId, addCriterionOpen || "")
  const executeTasksMutation = useExecuteSpecTasks(specId)
  const createBranchMutation = useCreateSpecBranch(specId)
  const createPRMutation = useCreateSpecPR(specId)
  const deleteSpecMutation = useDeleteSpec()
  const updateSpecMutation = useUpdateSpec(specId)
  const linkTicketsMutation = useLinkTickets(specId)
  const exportSpecMutation = useExportSpec()

  // Fetch project tickets for linking
  const { data: projectTickets } = useTickets({ project_id: projectId })
  // Fetch linked tickets
  const { data: linkedTicketsData } = useLinkedTickets(specId)

  // Derive spec display data from API response with safe defaults
  const specData = useMemo(() => ({
    id: spec?.id || specId,
    title: spec?.title || "Loading...",
    description: spec?.description || "",
    status: spec?.status || "draft",
    phase: spec?.phase || "Requirements",
    currentPhase: spec?.current_phase || "explore",  // State machine phase
    progress: spec?.progress || 0,
    testCoverage: spec?.test_coverage || 0,
    activeAgents: spec?.active_agents || 0,
    updatedAt: spec?.updated_at ? new Date(spec.updated_at) : new Date(),
    linkedTickets: spec?.linked_tickets || 0,
  }), [spec, specId])

  const toggleRequirement = (reqId: string) => {
    setExpandedRequirements((prev) =>
      prev.includes(reqId) ? prev.filter((id) => id !== reqId) : [...prev, reqId]
    )
  }

  const formatTimeAgo = (date: Date) => {
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const minutes = Math.floor(diff / (1000 * 60))
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ago`
    const days = Math.floor(hours / 24)
    return `${days}d ago`
  }

  const handleApproveRequirements = async () => {
    try {
      await approveReqMutation.mutateAsync()
      toast.success("Requirements approved!")
    } catch {
      toast.error("Failed to approve requirements")
    }
  }

  const handleApproveDesign = async () => {
    try {
      await approveDesignMutation.mutateAsync()
      toast.success("Design approved!")
    } catch {
      toast.error("Failed to approve design")
    }
  }

  const handleAddRequirement = async () => {
    if (!newRequirement.title || !newRequirement.condition || !newRequirement.action) {
      toast.error("Please fill in all required fields")
      return
    }
    try {
      await addRequirementMutation.mutateAsync(newRequirement)
      toast.success("Requirement added!")
      setAddRequirementOpen(false)
      setNewRequirement({ title: "", condition: "", action: "" })
    } catch {
      toast.error("Failed to add requirement")
    }
  }

  const handleAddTask = async () => {
    if (!newTask.title) {
      toast.error("Please enter a task title")
      return
    }
    try {
      await addTaskMutation.mutateAsync(newTask)
      toast.success("Task added!")
      setAddTaskOpen(false)
      setNewTask({ title: "", description: "", phase: "Implementation", priority: "medium" })
    } catch {
      toast.error("Failed to add task")
    }
  }

  const handleAddCriterion = async () => {
    if (!newCriterionText || !addCriterionOpen) {
      toast.error("Please enter criterion text")
      return
    }
    try {
      await addCriterionMutation.mutateAsync({ text: newCriterionText })
      toast.success("Criterion added!")
      setAddCriterionOpen(null)
      setNewCriterionText("")
    } catch {
      toast.error("Failed to add criterion")
    }
  }

  const handleDeleteRequirement = async (reqId: string) => {
    try {
      await deleteRequirementMutation.mutateAsync(reqId)
      toast.success("Requirement deleted!")
    } catch {
      toast.error("Failed to delete requirement")
    }
  }

  const handleViewTask = (task: typeof selectedTask) => {
    setSelectedTask(task)
    setViewTaskOpen(true)
  }

  const handleEditTaskOpen = (task: typeof selectedTask) => {
    if (!task) return
    setSelectedTask(task)
    setEditTask({
      title: task.title,
      description: task.description || "",
      phase: task.phase,
      priority: task.priority,
      status: task.status,
    })
    setEditTaskOpen(true)
  }

  const handleUpdateTask = async () => {
    if (!selectedTask || !editTask.title) {
      toast.error("Please enter a task title")
      return
    }
    try {
      await updateTaskMutation.mutateAsync({
        taskId: selectedTask.id,
        data: editTask,
      })
      toast.success("Task updated!")
      setEditTaskOpen(false)
      setSelectedTask(null)
      setEditTask({ title: "", description: "", phase: "", priority: "", status: "" })
    } catch {
      toast.error("Failed to update task")
    }
  }

  const handleDeleteTask = async (taskId: string) => {
    try {
      await deleteTaskMutation.mutateAsync(taskId)
      toast.success("Task deleted!")
    } catch {
      toast.error("Failed to delete task")
    }
  }

  const handleExecuteTasks = async () => {
    try {
      const result = await executeTasksMutation.mutateAsync(undefined)
      if (result.success) {
        toast.success(`Execution started! ${result.tasks_created} task(s) queued.`)
      } else {
        toast.error(result.message)
      }
    } catch {
      toast.error("Failed to execute tasks")
    }
  }

  const handleCreateBranch = async () => {
    try {
      const result = await createBranchMutation.mutateAsync()
      if (result.success) {
        toast.success(`Branch created: ${result.branch_name}`)
      } else {
        toast.error(result.error || "Failed to create branch")
      }
    } catch {
      toast.error("Failed to create branch")
    }
  }

  const handleCreatePR = async (force?: boolean) => {
    try {
      const result = await createPRMutation.mutateAsync({ force })
      if (result.success) {
        if (result.already_exists) {
          toast.info("PR already exists", {
            description: `PR #${result.pr_number}`,
          })
        } else {
          toast.success(`PR created: #${result.pr_number}`)
        }
      } else {
        if (result.incomplete_tasks && result.incomplete_tasks.length > 0) {
          toast.error(result.error || "Tasks not complete", {
            description: `${result.incomplete_tasks.length} task(s) still incomplete. Use "Force Create PR" to create anyway.`,
          })
        } else {
          toast.error(result.error || "Failed to create PR")
        }
      }
    } catch {
      toast.error("Failed to create PR")
    }
  }

  // Archive (delete) spec handler
  const handleArchiveSpec = async () => {
    if (!confirm("Are you sure you want to archive this spec? This action cannot be undone.")) {
      return
    }
    try {
      await deleteSpecMutation.mutateAsync({ specId, projectId })
      toast.success("Spec archived successfully")
      router.push(`/projects/${projectId}/specs`)
    } catch {
      toast.error("Failed to archive spec")
    }
  }

  // Settings handler - opens settings dialog
  const handleOpenSettings = () => {
    setEditSpecTitle(spec?.title || "")
    setEditSpecDescription(spec?.description || "")
    setSettingsOpen(true)
  }

  // Save spec settings
  const handleSaveSettings = async () => {
    if (!editSpecTitle.trim()) {
      toast.error("Title is required")
      return
    }
    try {
      await updateSpecMutation.mutateAsync({
        title: editSpecTitle.trim(),
        description: editSpecDescription.trim() || undefined,
      })
      toast.success("Spec updated successfully")
      setSettingsOpen(false)
    } catch {
      toast.error("Failed to update spec")
    }
  }

  // Link tickets handler - opens link tickets dialog
  const handleLinkTickets = () => {
    // Initialize with currently linked ticket IDs from the server
    const currentlyLinked = linkedTicketsData?.tickets?.map(t => t.id) || []
    setLinkedTicketIds(new Set(currentlyLinked))
    setLinkTicketsOpen(true)
  }

  // Toggle ticket link
  const toggleTicketLink = (ticketId: string) => {
    setLinkedTicketIds(prev => {
      const next = new Set(prev)
      if (next.has(ticketId)) {
        next.delete(ticketId)
      } else {
        next.add(ticketId)
      }
      return next
    })
  }

  // Save linked tickets via API
  const handleSaveLinkedTickets = async () => {
    try {
      const ticketIdsArray = Array.from(linkedTicketIds)
      const result = await linkTicketsMutation.mutateAsync(ticketIdsArray)
      toast.success("Tickets linked", {
        description: `${result.linked_count} ticket(s) newly linked${result.already_linked_count > 0 ? `, ${result.already_linked_count} already linked` : ""}.`,
      })
      setLinkTicketsOpen(false)
    } catch (error) {
      toast.error("Failed to link tickets", {
        description: error instanceof Error ? error.message : "Unknown error",
      })
    }
  }

  // Export spec handler
  const handleExport = async (format: "json" | "markdown") => {
    try {
      const data = await exportSpecMutation.mutateAsync({ specId, format })

      // Create download
      const blob = format === "markdown"
        ? new Blob([data as string], { type: "text/markdown" })
        : new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })

      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `${specData.title.replace(/[^a-z0-9]/gi, "_").toLowerCase()}.${format === "markdown" ? "md" : "json"}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)

      toast.success("Export completed", {
        description: `Spec exported as ${format === "markdown" ? "Markdown" : "JSON"}`,
      })
    } catch (error) {
      toast.error("Failed to export spec", {
        description: error instanceof Error ? error.message : "Unknown error",
      })
    }
  }

  if (specLoading) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="space-y-4 text-center">
          <Loader2 className="mx-auto h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-muted-foreground">Loading specification...</p>
        </div>
      </div>
    )
  }

  if (specError) {
    return (
      <div className="flex h-[calc(100vh-3.5rem)] items-center justify-center">
        <div className="text-center space-y-4">
          <AlertCircle className="mx-auto h-12 w-12 text-destructive" />
          <h2 className="text-xl font-semibold">Spec not found</h2>
          <p className="text-muted-foreground">The specification may have been deleted.</p>
          <Button asChild>
            <Link href={`/projects/${projectId}/specs`}>Back to Specs</Link>
          </Button>
        </div>
      </div>
    )
  }

  // Use real API data only - no mock fallbacks
  const requirements = spec?.requirements || []
  const design = spec?.design || null
  const tasks = spec?.tasks || []
  const execution = spec?.execution || null
  const id = projectId

  return (
    <div className="flex h-[calc(100vh-3.5rem)] overflow-hidden">
      {/* Left Sidebar - Spec Switcher */}
      <div className="hidden w-56 flex-shrink-0 border-r bg-muted/30 lg:block">
        <div className="flex h-full flex-col">
          <div className="border-b p-4">
            <Select value={specId}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Select spec" />
              </SelectTrigger>
              <SelectContent>
                {(allSpecs?.specs || []).map((s) => (
                  <SelectItem key={s.id} value={s.id}>
                    {s.title}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                All Specs
              </p>
              {(allSpecs?.specs || []).map((s) => (
                <Link
                  key={s.id}
                  href={`/projects/${id}/specs/${s.id}`}
                  className={`block rounded-md px-3 py-2 text-sm transition-colors ${
                    s.id === specId
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="truncate">{s.title}</span>
                    <div
                      className={`h-2 w-2 rounded-full ${
                        s.status === "executing"
                          ? "bg-primary"
                          : s.status === "design"
                          ? "bg-warning"
                          : "bg-muted-foreground"
                      }`}
                    />
                  </div>
                </Link>
              ))}
              {(!allSpecs?.specs || allSpecs.specs.length === 0) && (
                <p className="text-xs text-muted-foreground px-3 py-2">No specs yet</p>
              )}
            </div>
          </ScrollArea>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Header */}
        <div className="flex-shrink-0 border-b bg-background px-6 py-4">
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              {/* Project Context Breadcrumb */}
              <div className="flex items-center gap-2 text-sm mb-2">
                <Link
                  href={`/projects/${projectId}`}
                  className="inline-flex items-center gap-1.5 text-muted-foreground hover:text-foreground transition-colors"
                >
                  <FolderGit2 className="h-4 w-4" />
                  <span className="font-medium text-foreground">{project?.name || "Project"}</span>
                </Link>
                <span className="text-muted-foreground">/</span>
                <Link
                  href={`/projects/${projectId}/specs`}
                  className="text-muted-foreground hover:text-foreground transition-colors"
                >
                  Specifications
                </Link>
                <span className="text-muted-foreground">/</span>
                <span className="text-muted-foreground truncate max-w-[200px]">{specData.title}</span>
              </div>
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-semibold">{specData.title}</h1>
                <Badge
                  variant={
                    specData.status === "executing"
                      ? "default"
                      : "secondary"
                  }
                >
                  {specData.phase}
                </Badge>
              </div>
              <p className="text-sm text-muted-foreground">{specData.description}</p>
              {/* Phase Progress Indicator */}
              <div className="mt-3">
                <PhaseProgress
                  currentPhase={specData.phase.toLowerCase()}
                  status={specData.status}
                  size="sm"
                  showLabels={false}
                />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => setHistoryOpen(true)}>
                <History className="mr-2 h-4 w-4" />
                History
              </Button>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Download className="mr-2 h-4 w-4" />
                    Export
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => handleExport("markdown")}>
                    <FileText className="mr-2 h-4 w-4" />
                    Export as Markdown
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={() => handleExport("json")}>
                    <Download className="mr-2 h-4 w-4" />
                    Export as JSON
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="icon">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={handleOpenSettings}>
                    <Settings className="mr-2 h-4 w-4" />
                    Settings
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={handleLinkTickets}>
                    <LinkIcon className="mr-2 h-4 w-4" />
                    Link Tickets
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    className="text-destructive"
                    onClick={handleArchiveSpec}
                    disabled={deleteSpecMutation.isPending}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    {deleteSpecMutation.isPending ? "Archiving..." : "Archive"}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex flex-1 flex-col overflow-hidden">
          <div className="flex-shrink-0 border-b bg-background px-6">
            <TabsList className="h-12 w-full justify-start rounded-none border-0 bg-transparent p-0">
              <TabsTrigger
                value="requirements"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <FileText className="mr-2 h-4 w-4" />
                Requirements
              </TabsTrigger>
              <TabsTrigger
                value="design"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <Palette className="mr-2 h-4 w-4" />
                Design
              </TabsTrigger>
              <TabsTrigger
                value="tasks"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <ListTodo className="mr-2 h-4 w-4" />
                Tasks
              </TabsTrigger>
              <TabsTrigger
                value="execution"
                className="relative h-12 rounded-none border-b-2 border-transparent px-4 pb-3 pt-2 font-medium text-muted-foreground data-[state=active]:border-primary data-[state=active]:text-foreground"
              >
                <Play className="mr-2 h-4 w-4" />
                Execution
              </TabsTrigger>
            </TabsList>
          </div>

          {/* Tab Content */}
          <ScrollArea className="flex-1">
            {/* Requirements Tab */}
            <TabsContent value="requirements" className="m-0 p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Requirements</h2>
                    <p className="text-sm text-muted-foreground">
                      EARS-style structured requirements
                    </p>
                  </div>
                  <Dialog open={addRequirementOpen} onOpenChange={setAddRequirementOpen}>
                    <DialogTrigger asChild>
                      <Button>
                        <Plus className="mr-2 h-4 w-4" />
                        Add Requirement
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[500px]">
                      <DialogHeader>
                        <DialogTitle>Add Requirement</DialogTitle>
                        <DialogDescription>
                          Create a new EARS-style requirement with condition and action.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                          <Label htmlFor="req-title">Title</Label>
                          <Input
                            id="req-title"
                            placeholder="e.g., User Authentication"
                            value={newRequirement.title}
                            onChange={(e) => setNewRequirement({ ...newRequirement, title: e.target.value })}
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="req-condition">WHEN (Condition)</Label>
                          <Textarea
                            id="req-condition"
                            placeholder="e.g., a user submits login credentials"
                            value={newRequirement.condition}
                            onChange={(e) => setNewRequirement({ ...newRequirement, condition: e.target.value })}
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="req-action">THE SYSTEM SHALL (Action)</Label>
                          <Textarea
                            id="req-action"
                            placeholder="e.g., validate the credentials and create a session"
                            value={newRequirement.action}
                            onChange={(e) => setNewRequirement({ ...newRequirement, action: e.target.value })}
                          />
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setAddRequirementOpen(false)}>
                          Cancel
                        </Button>
                        <Button onClick={handleAddRequirement} disabled={addRequirementMutation.isPending}>
                          {addRequirementMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                          Add Requirement
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>

                <div className="space-y-4">
                  {requirements.length === 0 ? (
                    <Card>
                      <CardContent className="p-6 text-center text-muted-foreground">
                        <FileText className="h-12 w-12 mx-auto mb-4 opacity-50" />
                        <p>No requirements defined yet</p>
                        <p className="text-sm mt-2">Add your first requirement to start defining what the system should do.</p>
                      </CardContent>
                    </Card>
                  ) : requirements.map((req) => {
                    const isExpanded = expandedRequirements.includes(req.id)
                    const completedCriteria = req.criteria.filter((c: any) => c.completed).length
                    const config = statusConfig[req.status as keyof typeof statusConfig] || statusConfig.pending

                    return (
                      <Collapsible
                        key={req.id}
                        open={isExpanded}
                        onOpenChange={() => toggleRequirement(req.id)}
                      >
                        <Card className="overflow-hidden">
                          <CollapsibleTrigger asChild>
                            <CardHeader className="cursor-pointer hover:bg-muted/50 transition-colors">
                              <div className="flex items-start gap-4">
                                <div className="mt-1">
                                  {isExpanded ? (
                                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                  ) : (
                                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                                  )}
                                </div>
                                <div className="flex-1 space-y-1">
                                  <div className="flex items-center gap-2">
                                    <Badge variant="outline" className="font-mono text-xs">
                                      {req.id}
                                    </Badge>
                                    <CardTitle className="text-base">{req.title}</CardTitle>
                                    <Badge variant={config.color as any} className="ml-auto">
                                      {config.label}
                                    </Badge>
                                  </div>
                                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                                    <span>
                                      {completedCriteria}/{req.criteria.length} criteria met
                                    </span>
                                    {req.linked_design && (
                                      <span className="flex items-center gap-1">
                                        <LinkIcon className="h-3 w-3" />
                                        {req.linked_design}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </CardHeader>
                          </CollapsibleTrigger>
                          <CollapsibleContent>
                            <CardContent className="border-t pt-4">
                              {/* EARS Format - Improved visual hierarchy */}
                              <div className="space-y-4">
                                <div className="space-y-3">
                                  <div className="rounded-lg border bg-muted/30 p-4">
                                    <div className="flex items-start gap-3">
                                      <div className="flex-shrink-0 mt-0.5">
                                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-primary/10 text-primary">
                                          When
                                        </span>
                                      </div>
                                      <p className="text-sm leading-relaxed">{req.condition}</p>
                                    </div>
                                  </div>
                                  <div className="rounded-lg border bg-muted/30 p-4">
                                    <div className="flex items-start gap-3">
                                      <div className="flex-shrink-0 mt-0.5">
                                        <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-green-500/10 text-green-600 dark:text-green-400">
                                          Then
                                        </span>
                                      </div>
                                      <p className="text-sm leading-relaxed">{req.action}</p>
                                    </div>
                                  </div>
                                </div>

                                {/* Acceptance Criteria */}
                                <div>
                                  <div className="flex items-center justify-between mb-3">
                                    <h4 className="text-sm font-medium">Acceptance Criteria</h4>
                                    <Dialog open={addCriterionOpen === req.id} onOpenChange={(open) => {
                                      if (open) {
                                        setAddCriterionOpen(req.id)
                                      } else {
                                        setAddCriterionOpen(null)
                                        setNewCriterionText("")
                                      }
                                    }}>
                                      <DialogTrigger asChild>
                                        <Button variant="ghost" size="sm" className="h-7 text-xs">
                                          <Plus className="mr-1 h-3 w-3" />
                                          Add
                                        </Button>
                                      </DialogTrigger>
                                      <DialogContent>
                                        <DialogHeader>
                                          <DialogTitle>Add Acceptance Criterion</DialogTitle>
                                          <DialogDescription>
                                            Add a testable acceptance criterion for this requirement.
                                          </DialogDescription>
                                        </DialogHeader>
                                        <div className="grid gap-4 py-4">
                                          <div className="grid gap-2">
                                            <Label htmlFor="criterion-text">Criterion</Label>
                                            <Textarea
                                              id="criterion-text"
                                              placeholder="e.g., User receives confirmation email within 5 seconds"
                                              value={newCriterionText}
                                              onChange={(e) => setNewCriterionText(e.target.value)}
                                            />
                                          </div>
                                        </div>
                                        <DialogFooter>
                                          <Button variant="outline" onClick={() => setAddCriterionOpen(null)}>
                                            Cancel
                                          </Button>
                                          <Button onClick={handleAddCriterion} disabled={addCriterionMutation.isPending}>
                                            {addCriterionMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                                            Add Criterion
                                          </Button>
                                        </DialogFooter>
                                      </DialogContent>
                                    </Dialog>
                                  </div>
                                  {req.criteria.length === 0 ? (
                                    <p className="text-sm text-muted-foreground italic">No criteria defined yet</p>
                                  ) : (
                                    <div className="space-y-1">
                                      {req.criteria.map((criterion, idx) => (
                                        <label
                                          key={criterion.id}
                                          className={`flex items-start gap-3 rounded-md p-2 cursor-pointer transition-colors hover:bg-muted/50 ${
                                            criterion.completed ? "bg-muted/30" : ""
                                          }`}
                                        >
                                          <div className="mt-0.5 flex-shrink-0">
                                            <div
                                              className={`flex h-4 w-4 items-center justify-center rounded border ${
                                                criterion.completed
                                                  ? "bg-primary border-primary text-primary-foreground"
                                                  : "border-muted-foreground/40"
                                              }`}
                                            >
                                              {criterion.completed && <Check className="h-2.5 w-2.5" />}
                                            </div>
                                          </div>
                                          <div className="flex-1 min-w-0">
                                            <span
                                              className={`text-sm leading-tight ${
                                                criterion.completed ? "text-muted-foreground line-through" : ""
                                              }`}
                                            >
                                              {criterion.text}
                                            </span>
                                          </div>
                                          <span className="flex-shrink-0 text-[10px] text-muted-foreground/60 tabular-nums">
                                            #{idx + 1}
                                          </span>
                                        </label>
                                      ))}
                                    </div>
                                  )}
                                </div>

                                {/* Actions - Cleaner layout */}
                                <div className="flex items-center justify-between pt-3 border-t">
                                  <div className="flex items-center gap-2">
                                    <Button variant="ghost" size="sm" className="h-8">
                                      <Edit className="mr-1.5 h-3.5 w-3.5" />
                                      Edit
                                    </Button>
                                    {!req.linked_design && (
                                      <Button variant="ghost" size="sm" className="h-8">
                                        <LinkIcon className="mr-1.5 h-3.5 w-3.5" />
                                        Link Design
                                      </Button>
                                    )}
                                  </div>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    className="h-8 text-destructive hover:text-destructive hover:bg-destructive/10"
                                    onClick={() => handleDeleteRequirement(req.id)}
                                  >
                                    <Trash2 className="h-3.5 w-3.5" />
                                  </Button>
                                </div>
                              </div>
                            </CardContent>
                          </CollapsibleContent>
                        </Card>
                      </Collapsible>
                    )
                  })}
                </div>

                {/* Approval Actions */}
                <div className="flex items-center justify-end gap-2 pt-4 border-t">
                  <Button variant="outline">Request Changes</Button>
                  <Button onClick={handleApproveRequirements} disabled={approveReqMutation.isPending}>
                    {approveReqMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Approve Requirements
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* Design Tab */}
            <TabsContent value="design" className="m-0 p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Design</h2>
                    <p className="text-sm text-muted-foreground">
                      Architecture diagrams and data models
                    </p>
                  </div>
                  <Button variant="outline">
                    <Edit className="mr-2 h-4 w-4" />
                    Edit Design
                  </Button>
                </div>

                {!design ? (
                  <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                      <Palette className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No design defined yet</p>
                      <p className="text-sm mt-2">Create architecture diagrams, data models, and API specifications.</p>
                    </CardContent>
                  </Card>
                ) : (
                  <>
                    <div className="grid gap-6 lg:grid-cols-2">
                      {/* Architecture Diagram */}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">Architecture Overview</CardTitle>
                          <CardDescription>Component diagram</CardDescription>
                        </CardHeader>
                        <CardContent>
                          {design.architecture ? (
                            <div className="overflow-x-auto">
                              <Markdown content={design.architecture} />
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">No architecture diagram defined</p>
                          )}
                        </CardContent>
                      </Card>

                      {/* Data Model */}
                      <Card>
                        <CardHeader>
                          <CardTitle className="text-base">Data Model</CardTitle>
                          <CardDescription>Entity definitions</CardDescription>
                        </CardHeader>
                        <CardContent>
                          {design.data_model ? (
                            <div className="overflow-x-auto">
                              <Markdown content={design.data_model} />
                            </div>
                          ) : (
                            <p className="text-sm text-muted-foreground">No data model defined</p>
                          )}
                        </CardContent>
                      </Card>
                    </div>

                    {/* API Specification */}
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base">API Specification</CardTitle>
                        <CardDescription>Endpoint definitions</CardDescription>
                      </CardHeader>
                      <CardContent>
                        {design.api_spec && design.api_spec.length > 0 ? (
                          <div className="space-y-2">
                            {design.api_spec.map((endpoint: any, idx: number) => (
                              <div
                                key={idx}
                                className="flex items-center gap-4 rounded-md border p-3"
                              >
                                <Badge
                                  variant={
                                    endpoint.method === "GET"
                                      ? "secondary"
                                      : endpoint.method === "POST"
                                      ? "default"
                                      : "outline"
                                  }
                                  className="w-16 justify-center font-mono"
                                >
                                  {endpoint.method}
                                </Badge>
                                <code className="flex-1 font-mono text-sm">{endpoint.endpoint}</code>
                                <span className="text-sm text-muted-foreground">
                                  {endpoint.description}
                                </span>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-sm text-muted-foreground">No API endpoints defined</p>
                        )}
                      </CardContent>
                    </Card>
                  </>
                )}

                {/* Approval Actions */}
                <div className="flex items-center justify-end gap-2 pt-4 border-t">
                  <Button variant="outline">Request Changes</Button>
                  <Button onClick={handleApproveDesign} disabled={approveDesignMutation.isPending}>
                    {approveDesignMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                    Approve Design
                  </Button>
                </div>
              </div>
            </TabsContent>

            {/* Tasks Tab */}
            <TabsContent value="tasks" className="m-0 p-6">
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Task Breakdown</h2>
                    <p className="text-sm text-muted-foreground">
                      Implementation tasks with dependencies
                    </p>
                  </div>
                  <Dialog open={addTaskOpen} onOpenChange={setAddTaskOpen}>
                    <DialogTrigger asChild>
                      <Button>
                        <Plus className="mr-2 h-4 w-4" />
                        Add Task
                      </Button>
                    </DialogTrigger>
                    <DialogContent className="sm:max-w-[500px]">
                      <DialogHeader>
                        <DialogTitle>Add Task</DialogTitle>
                        <DialogDescription>
                          Create a new implementation task.
                        </DialogDescription>
                      </DialogHeader>
                      <div className="grid gap-4 py-4">
                        <div className="grid gap-2">
                          <Label htmlFor="task-title">Title</Label>
                          <Input
                            id="task-title"
                            placeholder="e.g., Implement user login API"
                            value={newTask.title}
                            onChange={(e) => setNewTask({ ...newTask, title: e.target.value })}
                          />
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="task-description">Description</Label>
                          <Textarea
                            id="task-description"
                            placeholder="Describe what this task involves..."
                            value={newTask.description}
                            onChange={(e) => setNewTask({ ...newTask, description: e.target.value })}
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="grid gap-2">
                            <Label htmlFor="task-phase">Phase</Label>
                            <Select
                              value={newTask.phase}
                              onValueChange={(value) => setNewTask({ ...newTask, phase: value })}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="Implementation">Implementation</SelectItem>
                                <SelectItem value="Testing">Testing</SelectItem>
                                <SelectItem value="Documentation">Documentation</SelectItem>
                                <SelectItem value="Review">Review</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                          <div className="grid gap-2">
                            <Label htmlFor="task-priority">Priority</Label>
                            <Select
                              value={newTask.priority}
                              onValueChange={(value) => setNewTask({ ...newTask, priority: value })}
                            >
                              <SelectTrigger>
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="high">High</SelectItem>
                                <SelectItem value="medium">Medium</SelectItem>
                                <SelectItem value="low">Low</SelectItem>
                              </SelectContent>
                            </Select>
                          </div>
                        </div>
                      </div>
                      <DialogFooter>
                        <Button variant="outline" onClick={() => setAddTaskOpen(false)}>
                          Cancel
                        </Button>
                        <Button onClick={handleAddTask} disabled={addTaskMutation.isPending}>
                          {addTaskMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                          Add Task
                        </Button>
                      </DialogFooter>
                    </DialogContent>
                  </Dialog>
                </div>

                {/* Tasks Table */}
                {tasks.length === 0 ? (
                  <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                      <ListTodo className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No tasks defined yet</p>
                      <p className="text-sm mt-2">Break down the implementation into discrete tasks with dependencies.</p>
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead>
                          <tr className="border-b bg-muted/50">
                            <th className="px-4 py-3 text-left text-sm font-medium">Task</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Phase</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Priority</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Status</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Agent</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Dependencies</th>
                            <th className="px-4 py-3 text-left text-sm font-medium">Est.</th>
                            <th className="px-4 py-3 text-right text-sm font-medium">Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {tasks.map((task) => {
                            const status = statusConfig[task.status as keyof typeof statusConfig] || statusConfig.pending
                            const priority = priorityConfig[task.priority?.toLowerCase() as keyof typeof priorityConfig] || priorityConfig.medium
                            const StatusIcon = status.icon

                            return (
                              <tr key={task.id} className="border-b last:border-0">
                                <td className="px-4 py-3">
                                  <div>
                                    <Badge variant="outline" className="font-mono text-xs mb-1">
                                      {task.id.slice(0, 8)}
                                    </Badge>
                                    <p className="font-medium">{task.title}</p>
                                    <p className="text-xs text-muted-foreground line-clamp-1">
                                      {task.description}
                                    </p>
                                  </div>
                                </td>
                                <td className="px-4 py-3">
                                  <Badge variant="outline">{task.phase}</Badge>
                                </td>
                                <td className="px-4 py-3">
                                  <Badge variant={priority.color as any}>{priority.label}</Badge>
                                </td>
                                <td className="px-4 py-3">
                                  <Badge variant={status.color as any} className="gap-1">
                                    <StatusIcon
                                      className={`h-3 w-3 ${
                                        task.status === "in_progress" ? "animate-spin" : ""
                                      }`}
                                    />
                                    {status.label}
                                  </Badge>
                                </td>
                                <td className="px-4 py-3">
                                  {task.assigned_agent ? (
                                    <div className="flex items-center gap-2">
                                      <Bot className="h-4 w-4 text-muted-foreground" />
                                      <span className="text-sm">{task.assigned_agent.slice(0, 8)}</span>
                                    </div>
                                  ) : (
                                    <span className="text-sm text-muted-foreground">Unassigned</span>
                                  )}
                                </td>
                                <td className="px-4 py-3">
                                  {task.dependencies && task.dependencies.length > 0 ? (
                                    <div className="flex flex-wrap gap-1">
                                      {task.dependencies.map((dep: string) => (
                                        <Badge key={dep} variant="outline" className="font-mono text-xs">
                                          {dep.slice(0, 8)}
                                        </Badge>
                                      ))}
                                    </div>
                                  ) : (
                                    <span className="text-sm text-muted-foreground">None</span>
                                  )}
                                </td>
                                <td className="px-4 py-3 text-sm">
                                  {task.actual_hours
                                    ? `${task.actual_hours}h / ${task.estimated_hours || 0}h`
                                    : task.estimated_hours ? `${task.estimated_hours}h` : '-'}
                                </td>
                                <td className="px-4 py-3 text-right">
                                  <DropdownMenu>
                                    <DropdownMenuTrigger asChild>
                                      <Button variant="ghost" size="icon">
                                        <MoreHorizontal className="h-4 w-4" />
                                      </Button>
                                    </DropdownMenuTrigger>
                                    <DropdownMenuContent align="end">
                                      <DropdownMenuItem onClick={() => handleViewTask({
                                        id: task.id,
                                        title: task.title,
                                        description: task.description,
                                        phase: task.phase,
                                        priority: task.priority,
                                        status: task.status,
                                        assigned_agent: task.assigned_agent,
                                      })}>
                                        View Details
                                      </DropdownMenuItem>
                                      <DropdownMenuItem onClick={() => handleEditTaskOpen({
                                        id: task.id,
                                        title: task.title,
                                        description: task.description,
                                        phase: task.phase,
                                        priority: task.priority,
                                        status: task.status,
                                        assigned_agent: task.assigned_agent,
                                      })}>
                                        Edit Task
                                      </DropdownMenuItem>
                                      <DropdownMenuItem onClick={() => handleEditTaskOpen({
                                        id: task.id,
                                        title: task.title,
                                        description: task.description,
                                        phase: task.phase,
                                        priority: task.priority,
                                        status: task.status,
                                        assigned_agent: task.assigned_agent,
                                      })}>
                                        Assign Agent
                                      </DropdownMenuItem>
                                      <DropdownMenuSeparator />
                                      <DropdownMenuItem
                                        className="text-destructive"
                                        onClick={() => handleDeleteTask(task.id)}
                                      >
                                        Delete
                                      </DropdownMenuItem>
                                    </DropdownMenuContent>
                                  </DropdownMenu>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </Card>
                )}

                {/* Approval Actions */}
                <div className="flex items-center justify-end gap-2 pt-4 border-t">
                  <Button variant="outline">Edit Tasks</Button>
                  <Button>Approve Plan</Button>
                </div>

                {/* View Task Dialog */}
                <Dialog open={viewTaskOpen} onOpenChange={setViewTaskOpen}>
                  <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                      <DialogTitle>Task Details</DialogTitle>
                      <DialogDescription>
                        View task information
                      </DialogDescription>
                    </DialogHeader>
                    {selectedTask && (
                      <div className="space-y-4 py-4">
                        <div>
                          <Label className="text-muted-foreground">ID</Label>
                          <p className="font-mono text-sm">{selectedTask.id}</p>
                        </div>
                        <div>
                          <Label className="text-muted-foreground">Title</Label>
                          <p className="font-medium">{selectedTask.title}</p>
                        </div>
                        <div>
                          <Label className="text-muted-foreground">Description</Label>
                          <p className="text-sm">{selectedTask.description || "No description"}</p>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label className="text-muted-foreground">Phase</Label>
                            <p>{selectedTask.phase}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">Priority</Label>
                            <p className="capitalize">{selectedTask.priority}</p>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div>
                            <Label className="text-muted-foreground">Status</Label>
                            <p className="capitalize">{selectedTask.status?.replace("_", " ")}</p>
                          </div>
                          <div>
                            <Label className="text-muted-foreground">Assigned Agent</Label>
                            <p>{selectedTask.assigned_agent || "Unassigned"}</p>
                          </div>
                        </div>
                      </div>
                    )}
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setViewTaskOpen(false)}>
                        Close
                      </Button>
                      <Button onClick={() => {
                        setViewTaskOpen(false)
                        handleEditTaskOpen(selectedTask)
                      }}>
                        Edit Task
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>

                {/* Edit Task Dialog */}
                <Dialog open={editTaskOpen} onOpenChange={setEditTaskOpen}>
                  <DialogContent className="sm:max-w-[500px]">
                    <DialogHeader>
                      <DialogTitle>Edit Task</DialogTitle>
                      <DialogDescription>
                        Update task details
                      </DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div className="grid gap-2">
                        <Label htmlFor="edit-task-title">Title</Label>
                        <Input
                          id="edit-task-title"
                          placeholder="Task title"
                          value={editTask.title}
                          onChange={(e) => setEditTask({ ...editTask, title: e.target.value })}
                        />
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="edit-task-description">Description</Label>
                        <Textarea
                          id="edit-task-description"
                          placeholder="Task description"
                          value={editTask.description}
                          onChange={(e) => setEditTask({ ...editTask, description: e.target.value })}
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="grid gap-2">
                          <Label htmlFor="edit-task-phase">Phase</Label>
                          <Select
                            value={editTask.phase}
                            onValueChange={(value) => setEditTask({ ...editTask, phase: value })}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Implementation">Implementation</SelectItem>
                              <SelectItem value="Testing">Testing</SelectItem>
                              <SelectItem value="Documentation">Documentation</SelectItem>
                              <SelectItem value="Review">Review</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="grid gap-2">
                          <Label htmlFor="edit-task-priority">Priority</Label>
                          <Select
                            value={editTask.priority}
                            onValueChange={(value) => setEditTask({ ...editTask, priority: value })}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="high">High</SelectItem>
                              <SelectItem value="medium">Medium</SelectItem>
                              <SelectItem value="low">Low</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                      </div>
                      <div className="grid gap-2">
                        <Label htmlFor="edit-task-status">Status</Label>
                        <Select
                          value={editTask.status}
                          onValueChange={(value) => setEditTask({ ...editTask, status: value })}
                        >
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="pending">Pending</SelectItem>
                            <SelectItem value="in_progress">In Progress</SelectItem>
                            <SelectItem value="completed">Completed</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setEditTaskOpen(false)}>
                        Cancel
                      </Button>
                      <Button onClick={handleUpdateTask} disabled={updateTaskMutation.isPending}>
                        {updateTaskMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                        Save Changes
                      </Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </TabsContent>

            {/* Execution Tab */}
            <TabsContent value="execution" className="m-0 p-6">
              <div className="space-y-6">
                <div className="flex items-start justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">Execution Progress</h2>
                    <p className="text-sm text-muted-foreground">
                      Real-time execution status and metrics
                    </p>
                  </div>
                  {/* Execute Tasks Button - Only enabled after design is approved */}
                  <Button
                    onClick={handleExecuteTasks}
                    disabled={executeTasksMutation.isPending || isExecuting || tasks.length === 0}
                  >
                    {executeTasksMutation.isPending ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Starting...
                      </>
                    ) : isExecuting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Executing...
                      </>
                    ) : (
                      <>
                        <Play className="mr-2 h-4 w-4" />
                        Execute Tasks
                      </>
                    )}
                  </Button>
                </div>

                {/* Progress Overview - Always show when we have execution status */}
                {(executionStatus || execution) && (
                  <div className="grid gap-4 md:grid-cols-4">
                    <Card>
                      <CardContent className="p-4">
                        <div className="space-y-2">
                          <p className="text-sm text-muted-foreground">Task Progress</p>
                          <p className="text-2xl font-bold">
                            {executionStatus?.progress ?? execution?.overall_progress ?? 0}%
                          </p>
                          <Progress value={executionStatus?.progress ?? execution?.overall_progress ?? 0} />
                          {executionStatus && (
                            <p className="text-xs text-muted-foreground">
                              {executionStatus.total_tasks} total tasks
                            </p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <div className="space-y-2">
                          <p className="text-sm text-muted-foreground">Criteria Met</p>
                          <p className="text-2xl font-bold">
                            {criteriaStatus?.completion_percentage?.toFixed(0) ?? execution?.test_coverage ?? 0}%
                          </p>
                          {criteriaStatus && (
                            <p className="text-xs text-muted-foreground">
                              {criteriaStatus.completed_criteria}/{criteriaStatus.total_criteria} criteria
                            </p>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <div className="space-y-2">
                          <p className="text-sm text-muted-foreground">Active Agents</p>
                          <p className="text-2xl font-bold">{execution?.active_agents ?? 0}</p>
                          <p className="text-xs text-muted-foreground">
                            {execution?.commits ?? 0} commits
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                    <Card>
                      <CardContent className="p-4">
                        <div className="space-y-2">
                          <p className="text-sm text-muted-foreground">Lines Changed</p>
                          <p className="text-2xl font-bold font-mono">
                            <span className="text-green-600">+{execution?.lines_added ?? 0}</span>
                            {" / "}
                            <span className="text-red-600">-{execution?.lines_removed ?? 0}</span>
                          </p>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )}

                {/* Task Status Breakdown */}
                {executionStatus && executionStatus.status_counts && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Task Status</CardTitle>
                      <CardDescription>Breakdown by execution status</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid gap-3 md:grid-cols-4">
                        {Object.entries(executionStatus.status_counts).map(([status, count]) => {
                          const statusInfo = statusConfig[status as keyof typeof statusConfig] || statusConfig.pending
                          const StatusIcon = statusInfo.icon
                          return (
                            <div key={status} className="flex items-center gap-2 p-2 rounded-md bg-muted/50">
                              <StatusIcon className={`h-4 w-4 ${status === "in_progress" ? "animate-spin" : ""}`} />
                              <span className="capitalize text-sm">{status.replace("_", " ")}</span>
                              <Badge variant="outline" className="ml-auto">{count}</Badge>
                            </div>
                          )
                        })}
                      </div>
                      {executionStatus.is_complete && (
                        <div className="mt-4 p-3 rounded-md bg-green-500/10 border border-green-500/20">
                          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                            <CheckCircle className="h-4 w-4" />
                            <span className="font-medium">All tasks completed!</span>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* Acceptance Criteria Progress */}
                {criteriaStatus && criteriaStatus.by_requirement && Object.keys(criteriaStatus.by_requirement).length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base">Acceptance Criteria</CardTitle>
                      <CardDescription>
                        {criteriaStatus.completed_criteria}/{criteriaStatus.total_criteria} criteria validated
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {Object.entries(criteriaStatus.by_requirement).map(([reqId, reqData]) => (
                          <div key={reqId} className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium">{reqData.requirement_title}</span>
                              <span className="text-xs text-muted-foreground">
                                {reqData.completed}/{reqData.total}
                              </span>
                            </div>
                            <Progress value={(reqData.completed / reqData.total) * 100} className="h-1.5" />
                            <div className="space-y-1">
                              {reqData.criteria.map((c) => (
                                <div key={c.id} className="flex items-center gap-2 text-xs">
                                  <div className={`h-3 w-3 rounded-full flex items-center justify-center ${
                                    c.completed ? "bg-green-500" : "bg-muted"
                                  }`}>
                                    {c.completed && <Check className="h-2 w-2 text-white" />}
                                  </div>
                                  <span className={c.completed ? "text-muted-foreground line-through" : ""}>
                                    {c.text}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                      {criteriaStatus.all_complete && (
                        <div className="mt-4 p-3 rounded-md bg-green-500/10 border border-green-500/20">
                          <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
                            <CheckCircle className="h-4 w-4" />
                            <span className="font-medium">All acceptance criteria met!</span>
                          </div>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                )}

                {/* GitHub/PR Section - Show when execution is complete */}
                {executionStatus?.is_complete && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <GitBranch className="h-4 w-4" />
                        GitHub Integration
                      </CardTitle>
                      <CardDescription>
                        Create a pull request to merge your changes
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {/* Branch Status */}
                      {spec?.branch_name ? (
                        <div className="flex items-center gap-2 p-2 rounded-md bg-muted/50">
                          <GitBranch className="h-4 w-4 text-muted-foreground" />
                          <code className="text-sm font-mono flex-1 truncate">{spec.branch_name}</code>
                          <Badge variant="outline" className="text-xs">Active</Badge>
                        </div>
                      ) : (
                        <Button
                          onClick={handleCreateBranch}
                          disabled={createBranchMutation.isPending}
                          className="w-full"
                          variant="outline"
                        >
                          {createBranchMutation.isPending ? (
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          ) : (
                            <GitBranch className="mr-2 h-4 w-4" />
                          )}
                          Create Branch
                        </Button>
                      )}

                      {/* PR Status */}
                      {spec?.pull_request_url ? (
                        <a
                          href={spec.pull_request_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex items-center gap-3 p-3 rounded-md bg-green-500/10 border border-green-500/30 hover:bg-green-500/20 transition-colors"
                        >
                          <CheckCircle className="h-5 w-5 text-green-600" />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-green-600">Pull Request #{spec.pull_request_number}</p>
                            <p className="text-xs text-green-600/80">Ready for review</p>
                          </div>
                          <ExternalLink className="h-4 w-4 text-green-600" />
                        </a>
                      ) : spec?.branch_name ? (
                        <div className="space-y-2">
                          <Button
                            onClick={() => handleCreatePR(false)}
                            disabled={createPRMutation.isPending}
                            className="w-full"
                          >
                            {createPRMutation.isPending ? (
                              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <ExternalLink className="mr-2 h-4 w-4" />
                            )}
                            Create Pull Request
                          </Button>
                          <p className="text-xs text-muted-foreground text-center">
                            This will create a PR with all completed tasks
                          </p>
                        </div>
                      ) : null}
                    </CardContent>
                  </Card>
                )}

                {/* Event Timeline - Real-time event feed */}
                <EventTimeline
                  specId={specId}
                  isExecuting={isExecuting}
                  maxHeight="400px"
                />

                {/* Empty State */}
                {!execution && !executionStatus && (
                  <Card>
                    <CardContent className="p-6 text-center text-muted-foreground">
                      <Play className="h-12 w-12 mx-auto mb-4 opacity-50" />
                      <p>No execution data yet</p>
                      <p className="text-sm mt-2">
                        {tasks.length === 0
                          ? "Add tasks to the spec before executing."
                          : "Click \"Execute Tasks\" to start running tasks in sandbox environments."
                        }
                      </p>
                    </CardContent>
                  </Card>
                )}

                {/* Quick Actions */}
                <div className="flex items-center gap-2 pt-4 border-t">
                  <Button variant="outline" asChild>
                    <Link href={`/board/${id}`}>View Board</Link>
                  </Button>
                  <Button variant="outline" asChild>
                    <Link href={`/graph/${id}`}>View Graph</Link>
                  </Button>
                </div>
              </div>
            </TabsContent>
          </ScrollArea>
        </Tabs>
      </div>

      {/* Right Sidebar - Metadata */}
      <div className="hidden w-64 flex-shrink-0 border-l bg-muted/30 xl:block">
        <ScrollArea className="h-full">
          <div className="p-4 space-y-5">
            {/* Quick Stats Cards */}
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-lg bg-background border p-3 text-center">
                <p className="text-2xl font-bold text-primary">{specData.progress}%</p>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Progress</p>
              </div>
              <div className="rounded-lg bg-background border p-3 text-center">
                <p className="text-2xl font-bold">{requirements.length}</p>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Requirements</p>
              </div>
              <div className="rounded-lg bg-background border p-3 text-center">
                <p className="text-2xl font-bold">{tasks.length}</p>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Tasks</p>
              </div>
              <div className="rounded-lg bg-background border p-3 text-center">
                <p className="text-2xl font-bold">{specData.activeAgents}</p>
                <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Agents</p>
              </div>
            </div>

            <Separator />

            {/* Spec Details */}
            <div>
              <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">Details</h3>
              <div className="space-y-2.5 text-sm">
                {/* Phase Progress Inline - uses current_phase from state machine */}
                <div className="rounded-md border bg-muted/30 p-2">
                  <PhaseProgressInline
                    currentPhase={specData.currentPhase}
                    status={specData.status}
                  />
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Phase</span>
                  <Badge variant="outline" className="font-normal capitalize">{specData.currentPhase}</Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Status</span>
                  <Badge
                    variant={specData.status === "executing" ? "default" : specData.status === "completed" ? "default" : "secondary"}
                    className={`font-normal capitalize ${specData.status === "completed" ? "bg-green-500/10 text-green-600 border-green-500/30" : ""}`}
                  >
                    {specData.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Linked Tickets</span>
                  <span className="font-medium">{specData.linkedTickets}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">Updated</span>
                  <span className="text-xs text-muted-foreground">{formatTimeAgo(specData.updatedAt)}</span>
                </div>
              </div>
            </div>

            <Separator />

            {/* Test Coverage */}
            <div>
              <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">Test Coverage</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Coverage</span>
                  <span className="font-medium tabular-nums">{specData.testCoverage}%</span>
                </div>
                <Progress value={specData.testCoverage} className="h-1.5" />
                {execution && (
                  <p className="text-xs text-muted-foreground">
                    {execution.tests_passing}/{execution.tests_total} tests passing
                  </p>
                )}
              </div>
            </div>

            <Separator />

            {/* GitHub Integration */}
            <div>
              <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-3">GitHub</h3>
              <div className="space-y-2">
                {/* Branch Status */}
                {spec?.branch_name ? (
                  <div className="rounded-md border bg-muted/30 p-2">
                    <div className="flex items-center gap-2">
                      <GitBranch className="h-3.5 w-3.5 text-muted-foreground" />
                      <span className="text-xs font-mono truncate flex-1">{spec.branch_name}</span>
                    </div>
                  </div>
                ) : (
                  <Button
                    variant="outline"
                    size="sm"
                    className="w-full justify-start h-8 text-xs"
                    onClick={handleCreateBranch}
                    disabled={createBranchMutation.isPending}
                  >
                    {createBranchMutation.isPending ? (
                      <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <GitBranch className="mr-2 h-3.5 w-3.5" />
                    )}
                    Create Branch
                  </Button>
                )}

                {/* PR Status */}
                {spec?.pull_request_url ? (
                  <a
                    href={spec.pull_request_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-2 rounded-md border bg-green-500/10 border-green-500/30 p-2 hover:bg-green-500/20 transition-colors"
                  >
                    <CheckCircle className="h-3.5 w-3.5 text-green-600" />
                    <span className="text-xs font-medium text-green-600">PR #{spec.pull_request_number}</span>
                    <ExternalLink className="h-3 w-3 text-green-600 ml-auto" />
                  </a>
                ) : spec?.branch_name ? (
                  <div className="space-y-1">
                    <Button
                      variant="outline"
                      size="sm"
                      className="w-full justify-start h-8 text-xs"
                      onClick={() => handleCreatePR(false)}
                      disabled={createPRMutation.isPending}
                    >
                      {createPRMutation.isPending ? (
                        <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                      ) : (
                        <ExternalLink className="mr-2 h-3.5 w-3.5" />
                      )}
                      Create Pull Request
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="w-full justify-start h-7 text-[10px] text-muted-foreground"
                      onClick={() => handleCreatePR(true)}
                      disabled={createPRMutation.isPending}
                    >
                      Force Create PR (skip task check)
                    </Button>
                  </div>
                ) : null}
              </div>
            </div>

            <Separator />

            {/* Version History */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Activity</h3>
                {versionsData?.versions && versionsData.versions.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 text-[10px] px-2"
                    onClick={() => setHistoryOpen(true)}
                  >
                    View All
                  </Button>
                )}
              </div>
              {versionsData?.versions && versionsData.versions.length > 0 ? (
                <div className="relative">
                  {/* Timeline line */}
                  <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border" />
                  <div className="space-y-3">
                    {versionsData.versions.slice(0, 5).map((version, idx) => (
                      <div
                        key={version.id}
                        className="relative pl-6"
                      >
                        {/* Timeline dot */}
                        <div className={`absolute left-0 top-1.5 w-[15px] h-[15px] rounded-full border-2 ${
                          idx === 0 ? "bg-primary border-primary" : "bg-background border-muted-foreground/30"
                        }`}>
                          {idx === 0 && <div className="absolute inset-1 rounded-full bg-primary-foreground" />}
                        </div>
                        <div>
                          <p className="text-xs font-medium capitalize">
                            {version.change_type.replace(/_/g, " ")}
                          </p>
                          <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">
                            {version.change_summary}
                          </p>
                          <p className="text-[10px] text-muted-foreground/70 mt-1">
                            {formatTimeAgo(new Date(version.created_at))}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="text-center py-4">
                  <History className="h-8 w-8 mx-auto text-muted-foreground/30 mb-2" />
                  <p className="text-xs text-muted-foreground">
                    No activity yet
                  </p>
                </div>
              )}
            </div>
          </div>
        </ScrollArea>
      </div>

      {/* Settings Dialog */}
      <Dialog open={settingsOpen} onOpenChange={setSettingsOpen}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Spec Settings</DialogTitle>
            <DialogDescription>
              Edit the title and description for this specification.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <div className="grid gap-2">
              <Label htmlFor="spec-title">Title</Label>
              <Input
                id="spec-title"
                placeholder="Specification title"
                value={editSpecTitle}
                onChange={(e) => setEditSpecTitle(e.target.value)}
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="spec-description">Description</Label>
              <Textarea
                id="spec-description"
                placeholder="Brief description of the specification..."
                value={editSpecDescription}
                onChange={(e) => setEditSpecDescription(e.target.value)}
                rows={4}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSettingsOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSaveSettings} disabled={updateSpecMutation.isPending}>
              {updateSpecMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Link Tickets Dialog */}
      <Dialog open={linkTicketsOpen} onOpenChange={setLinkTicketsOpen}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Link Tickets</DialogTitle>
            <DialogDescription>
              Select tickets from this project to link with this specification.
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            {projectTickets?.tickets && projectTickets.tickets.length > 0 ? (
              <ScrollArea className="h-[300px] pr-4">
                <div className="space-y-2">
                  {projectTickets.tickets.map((ticket) => (
                    <div
                      key={ticket.id}
                      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors cursor-pointer ${
                        linkedTicketIds.has(ticket.id)
                          ? "border-primary bg-primary/5"
                          : "hover:bg-muted/50"
                      }`}
                      onClick={() => toggleTicketLink(ticket.id)}
                    >
                      <Checkbox
                        checked={linkedTicketIds.has(ticket.id)}
                        onCheckedChange={() => toggleTicketLink(ticket.id)}
                        className="mt-0.5"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm truncate">{ticket.title}</span>
                          <Badge variant="outline" className="text-[10px] shrink-0">
                            {ticket.status}
                          </Badge>
                        </div>
                        {ticket.description && (
                          <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                            {ticket.description}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            ) : (
              <div className="text-center py-8">
                <FileText className="h-12 w-12 mx-auto text-muted-foreground/30 mb-3" />
                <p className="text-sm text-muted-foreground">No tickets in this project yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Create tickets from the command page or board to link them here.
                </p>
              </div>
            )}
          </div>
          <DialogFooter>
            <div className="flex items-center justify-between w-full">
              <span className="text-sm text-muted-foreground">
                {linkedTicketIds.size} ticket{linkedTicketIds.size !== 1 ? "s" : ""} selected
              </span>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setLinkTicketsOpen(false)}>
                  Cancel
                </Button>
                <Button onClick={handleSaveLinkedTickets}>
                  Save Links
                </Button>
              </div>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* History Dialog */}
      <Dialog open={historyOpen} onOpenChange={setHistoryOpen}>
        <DialogContent className="sm:max-w-[600px] max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Version History</DialogTitle>
            <DialogDescription>
              View the complete change history for this specification.
            </DialogDescription>
          </DialogHeader>
          <ScrollArea className="h-[400px] pr-4">
            {versionsData?.versions && versionsData.versions.length > 0 ? (
              <div className="relative py-2">
                {/* Timeline line */}
                <div className="absolute left-[9px] top-4 bottom-4 w-px bg-border" />
                <div className="space-y-4">
                  {versionsData.versions.map((version, idx) => (
                    <div
                      key={version.id}
                      className="relative pl-8"
                    >
                      {/* Timeline dot */}
                      <div className={`absolute left-0 top-1.5 w-[19px] h-[19px] rounded-full border-2 flex items-center justify-center ${
                        idx === 0
                          ? "bg-primary border-primary"
                          : "bg-background border-muted-foreground/30"
                      }`}>
                        {idx === 0 && <div className="w-2 h-2 rounded-full bg-primary-foreground" />}
                      </div>
                      <div className="bg-muted/30 rounded-lg p-3 border">
                        <div className="flex items-center justify-between gap-2 mb-1">
                          <Badge variant={idx === 0 ? "default" : "outline"} className="text-[10px] capitalize">
                            {version.change_type.replace(/_/g, " ")}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">
                            v{version.version_number}
                          </span>
                        </div>
                        <p className="text-sm">
                          {version.change_summary}
                        </p>
                        <p className="text-[11px] text-muted-foreground mt-2">
                          {new Date(version.created_at).toLocaleString()}
                        </p>
                        {version.change_details && Object.keys(version.change_details).length > 0 && (
                          <div className="mt-2 pt-2 border-t border-border/50">
                            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-1">
                              Changes
                            </p>
                            <div className="space-y-1">
                              {Object.entries(version.change_details).map(([field, changes]) => (
                                <div key={field} className="text-[11px]">
                                  <span className="text-muted-foreground">{field}:</span>{" "}
                                  <span className="text-red-500/70 line-through">
                                    {String((changes as { old: unknown; new: unknown }).old || "empty")}
                                  </span>
                                  {" → "}
                                  <span className="text-green-500/70">
                                    {String((changes as { old: unknown; new: unknown }).new || "empty")}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <History className="h-12 w-12 mx-auto text-muted-foreground/30 mb-3" />
                <p className="text-sm text-muted-foreground">No version history yet</p>
                <p className="text-xs text-muted-foreground mt-1">
                  Changes to this specification will be tracked here.
                </p>
              </div>
            )}
          </ScrollArea>
          <DialogFooter>
            <Button variant="outline" onClick={() => setHistoryOpen(false)}>
              Close
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
