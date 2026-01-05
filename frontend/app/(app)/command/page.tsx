"use client"

import { useState, useMemo, useEffect, useCallback, useRef } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { PromptInput, ModelSelector, RepoSelector, Project, Repository, WorkflowModeSelector, getWorkflowModeConfig, type WorkflowMode } from "@/components/command"
import { useProjects } from "@/hooks/useProjects"
import { useConnectedRepositories } from "@/hooks/useGitHub"
import { useCreateTicket } from "@/hooks/useTickets"
import { useEvents, type SystemEvent } from "@/hooks/useEvents"
import { listTasks } from "@/lib/api/tasks"
import { Loader2 } from "lucide-react"

type LaunchState =
  | { status: "idle" }
  | { status: "creating_ticket"; prompt: string }
  | { status: "waiting_for_sandbox"; ticketId: string; prompt: string }
  | { status: "redirecting"; sandboxId: string }

// All event types the backend might send for sandbox creation
const SANDBOX_EVENT_TYPES = [
  "SANDBOX_CREATED",   // Original expected type
  "SANDBOX_SPAWNED",   // Orchestrator worker sends this (uppercase)
  "sandbox.spawned",   // DaytonaSpawner sends this (lowercase with dot)
]

export default function CommandCenterPage() {
  const router = useRouter()
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [selectedBranch, setSelectedBranch] = useState("main")
  const [selectedModel, setSelectedModel] = useState("opus-4.5")
  const [selectedMode, setSelectedMode] = useState<WorkflowMode>("quick")
  const [launchState, setLaunchState] = useState<LaunchState>({ status: "idle" })

  // Get mode configuration for dynamic UI
  const modeConfig = getWorkflowModeConfig(selectedMode)

  // Fetch real data
  const { data: projectsData } = useProjects({ status: "active" })
  const { data: connectedRepos } = useConnectedRepositories()
  const createTicketMutation = useCreateTicket()

  // Transform API projects to component format
  const projects: Project[] = useMemo(() => {
    if (!projectsData?.projects) return []
    return projectsData.projects.map((p) => ({
      id: p.id,
      name: p.name,
      repo: p.github_owner && p.github_repo ? `${p.github_owner}/${p.github_repo}` : undefined,
      ticketCount: 0,
    }))
  }, [projectsData?.projects])

  // Transform connected repos to component format
  const repositories: Repository[] = useMemo(() => {
    if (!connectedRepos) return []
    return connectedRepos.map((r) => ({
      fullName: `${r.owner}/${r.repo}`,
      isPrivate: false,
    }))
  }, [connectedRepos])

  // Set default project when data loads
  useMemo(() => {
    if (projects.length > 0 && !selectedProject) {
      setSelectedProject(projects[0])
    }
  }, [projects, selectedProject])

  // Track if we've already redirected to prevent double redirects
  const hasRedirectedRef = useRef(false)

  // Helper to handle successful sandbox detection - redirect to board to watch progress
  const handleSandboxReady = useCallback((sandboxId: string) => {
    if (hasRedirectedRef.current) return // Prevent double redirect
    hasRedirectedRef.current = true
    setLaunchState({ status: "redirecting", sandboxId })
    toast.success("Agent started! Redirecting to board...")
    // Redirect to board instead of sandbox - board shows real-time progress
    // and user can click on running tasks to see agent output
    const projectId = selectedProject?.id || "all"
    router.push(`/board/${projectId}`)
  }, [router, selectedProject])

  // Handle event from WebSocket that signals sandbox is ready
  const handleEvent = useCallback((event: SystemEvent) => {
    console.log("[Command] Received event:", event.event_type, event.entity_type, event.entity_id)

    // Look for sandbox-related events (check all known event types)
    if (
      event.entity_type === "sandbox" &&
      SANDBOX_EVENT_TYPES.includes(event.event_type)
    ) {
      const sandboxId = event.entity_id || (event.payload?.sandbox_id as string)
      if (sandboxId) {
        handleSandboxReady(sandboxId)
        return
      }
    }

    // Also check for task events that include sandbox_id
    if (
      event.entity_type === "task" &&
      (event.event_type === "TASK_STARTED" || event.event_type === "TASK_SANDBOX_ASSIGNED") &&
      event.payload?.sandbox_id
    ) {
      const sandboxId = event.payload.sandbox_id as string
      handleSandboxReady(sandboxId)
      return
    }
  }, [handleSandboxReady])

  // Subscribe to events when waiting for sandbox
  const isWaitingForSandbox = launchState.status === "waiting_for_sandbox"
  useEvents({
    enabled: isWaitingForSandbox,
    filters: isWaitingForSandbox
      ? {
          entity_types: ["sandbox", "task"],
        }
      : undefined,
    onEvent: handleEvent,
  })

  // Fallback polling for sandbox_id (in case WebSocket events are missed)
  // Also includes timeout after 60 seconds
  useEffect(() => {
    if (launchState.status !== "waiting_for_sandbox") {
      // Reset redirect flag when going back to idle
      if (launchState.status === "idle") {
        hasRedirectedRef.current = false
      }
      return
    }

    const ticketId = launchState.ticketId
    let pollCount = 0
    const maxPolls = 20 // 20 polls * 3s = 60s timeout

    // Poll for tasks with sandbox_id every 3 seconds
    const pollInterval = setInterval(async () => {
      pollCount++
      console.log(`[Command] Polling for sandbox (attempt ${pollCount}/${maxPolls})...`)

      try {
        // Fetch recent tasks and look for one matching our ticket
        const tasks = await listTasks({ limit: 20 })
        const matchingTask = tasks.find(
          (task) => task.ticket_id === ticketId && task.sandbox_id
        )

        if (matchingTask?.sandbox_id) {
          console.log("[Command] Found sandbox via polling:", matchingTask.sandbox_id)
          clearInterval(pollInterval)
          handleSandboxReady(matchingTask.sandbox_id)
          return
        }
      } catch (error) {
        console.error("[Command] Polling error:", error)
      }

      // Timeout after max polls
      if (pollCount >= maxPolls) {
        clearInterval(pollInterval)
        toast.error("Sandbox creation timed out. Please try again.")
        setLaunchState({ status: "idle" })
      }
    }, 3000)

    return () => clearInterval(pollInterval)
  }, [launchState, handleSandboxReady])

  const handleSubmit = async (prompt: string) => {
    try {
      setLaunchState({ status: "creating_ticket", prompt })

      // Build payload based on selected mode
      const basePayload = {
        title: prompt.slice(0, 100) + (prompt.length > 100 ? "..." : ""),
        description: prompt,
        priority: "MEDIUM" as const,
        check_duplicates: false, // Don't check for dups on command prompts
        force_create: true,
        project_id: selectedProject?.id,
      }

      // Mode-specific parameters
      const modePayload = selectedMode === "quick"
        ? {
            phase_id: "PHASE_IMPLEMENTATION",
            workflow_mode: "quick" as const,
            auto_spawn_sandbox: true,
          }
        : {
            phase_id: "PHASE_REQUIREMENTS",
            workflow_mode: "spec_driven" as const,
            generate_spec: true,
            auto_spawn_sandbox: false,
          }

      const result = await createTicketMutation.mutateAsync({
        ...basePayload,
        ...modePayload,
      })

      // Check if we got a duplicate response instead of a ticket
      if ("is_duplicate" in result) {
        toast.error("This looks like a duplicate request.")
        setLaunchState({ status: "idle" })
        return
      }

      // Handle navigation based on mode
      if (selectedMode === "quick") {
        // Ticket created, now wait for the orchestrator to spawn a sandbox
        toast.info("Launching sandbox...")
        setLaunchState({ status: "waiting_for_sandbox", ticketId: result.id, prompt })
      } else {
        // Spec-driven: redirect to spec workspace
        toast.info("Creating spec...")
        // For now, redirect to tickets page until spec workspace is built
        // TODO: Update to /specs/:id when spec workspace is implemented
        router.push(`/tickets/${result.id}`)
      }

    } catch (error) {
      toast.error("Failed to create task. Please try again.")
      setLaunchState({ status: "idle" })
    }
  }

  const handleProjectSelect = (project: Project) => {
    setSelectedProject(project)
    setSelectedRepo(null)
  }

  const handleRepoSelect = (repo: string) => {
    setSelectedProject(null)
    setSelectedRepo(repo)
  }

  const isLoading = launchState.status !== "idle"

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-[700px] space-y-6">
        {/* Prompt Area */}
        <div className="text-center">
          <h1 className="mb-2 text-2xl font-semibold text-foreground">
            What would you like to build?
          </h1>
          <p className="text-muted-foreground">
            {modeConfig.helperText}
          </p>
        </div>

        {/* Main Input */}
        <PromptInput
          onSubmit={handleSubmit}
          isLoading={isLoading}
          placeholder={modeConfig.placeholder}
          submitLabel={modeConfig.submitLabel}
        />

        {/* Launch Status */}
        {launchState.status !== "idle" && (
          <div className="flex items-center justify-center gap-3 rounded-lg border border-border bg-muted/50 p-4">
            <Loader2 className="h-5 w-5 animate-spin text-primary" />
            <div className="text-sm">
              {launchState.status === "creating_ticket" && (
                <span>Creating task...</span>
              )}
              {launchState.status === "waiting_for_sandbox" && (
                <span>Launching sandbox environment...</span>
              )}
              {launchState.status === "redirecting" && (
                <span>Redirecting to sandbox...</span>
              )}
            </div>
          </div>
        )}

        {/* Controls Row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <WorkflowModeSelector
              value={selectedMode}
              onValueChange={setSelectedMode}
            />
            <RepoSelector
              projects={projects}
              repositories={repositories}
              selectedProject={selectedProject}
              selectedRepo={selectedRepo}
              selectedBranch={selectedBranch}
              onProjectSelect={handleProjectSelect}
              onRepoSelect={handleRepoSelect}
              onBranchChange={setSelectedBranch}
            />
          </div>
          <ModelSelector
            value={selectedModel}
            onValueChange={setSelectedModel}
          />
        </div>

        {/* Context Indicator */}
        {(selectedProject || selectedRepo) && launchState.status === "idle" && (
          <div className="rounded-lg border border-border bg-card p-3">
            {selectedProject ? (
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-success">✓</span>
                <span>
                  Connected to:{" "}
                  <span className="font-medium">{selectedProject.name}</span>
                </span>
                <span className="text-muted-foreground">
                  • {selectedProject.ticketCount} tickets
                </span>
              </div>
            ) : selectedRepo ? (
              <div className="flex items-center gap-2 text-sm">
                <span className="font-medium text-info">ℹ</span>
                <span>
                  New project will be created from:{" "}
                  <span className="font-medium">{selectedRepo}</span>
                </span>
              </div>
            ) : null}
          </div>
        )}
      </div>
    </div>
  )
}
