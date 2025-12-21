"use client"

import { useState, useMemo, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { PromptInput, ModelSelector, RepoSelector, Project, Repository } from "@/components/command"
import { useProjects } from "@/hooks/useProjects"
import { useConnectedRepositories } from "@/hooks/useGitHub"
import { useCreateTicket } from "@/hooks/useTickets"
import { useEvents, type SystemEvent } from "@/hooks/useEvents"
import { Loader2 } from "lucide-react"

type LaunchState = 
  | { status: "idle" }
  | { status: "creating_ticket"; prompt: string }
  | { status: "waiting_for_sandbox"; ticketId: string; prompt: string }
  | { status: "redirecting"; sandboxId: string }

export default function CommandCenterPage() {
  const router = useRouter()
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [selectedBranch, setSelectedBranch] = useState("main")
  const [selectedModel, setSelectedModel] = useState("opus-4.5")
  const [launchState, setLaunchState] = useState<LaunchState>({ status: "idle" })

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

  // Handle event from WebSocket that signals sandbox is ready
  const handleEvent = useCallback((event: SystemEvent) => {
    // Look for sandbox-related events
    if (
      event.entity_type === "sandbox" &&
      event.event_type === "SANDBOX_CREATED"
    ) {
      const sandboxId = event.entity_id
      if (sandboxId) {
        setLaunchState({ status: "redirecting", sandboxId })
        toast.success("Sandbox launched!")
        router.push(`/sandbox/${sandboxId}`)
      }
    }
    // Also check for task events that include sandbox_id
    if (
      event.entity_type === "task" &&
      (event.event_type === "TASK_STARTED" || event.event_type === "TASK_SANDBOX_ASSIGNED") &&
      event.payload?.sandbox_id
    ) {
      const sandboxId = event.payload.sandbox_id as string
      setLaunchState({ status: "redirecting", sandboxId })
      toast.success("Sandbox launched!")
      router.push(`/sandbox/${sandboxId}`)
    }
  }, [router])

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

  // Timeout for sandbox creation (60 seconds)
  useEffect(() => {
    if (launchState.status !== "waiting_for_sandbox") return

    const timeout = setTimeout(() => {
      toast.error("Sandbox creation timed out. Please try again.")
      setLaunchState({ status: "idle" })
    }, 60000)

    return () => clearTimeout(timeout)
  }, [launchState])

  const handleSubmit = async (prompt: string) => {
    try {
      setLaunchState({ status: "creating_ticket", prompt })

      // Create a ticket with the prompt as title/description
      const result = await createTicketMutation.mutateAsync({
        title: prompt.slice(0, 100) + (prompt.length > 100 ? "..." : ""),
        description: prompt,
        phase_id: "PHASE_IMPLEMENTATION",
        priority: "MEDIUM",
        check_duplicates: false, // Don't check for dups on command prompts
        force_create: true,
      })

      // Check if we got a duplicate response instead of a ticket
      if ("is_duplicate" in result) {
        toast.error("This looks like a duplicate request.")
        setLaunchState({ status: "idle" })
        return
      }

      // Ticket created, now wait for the orchestrator to spawn a sandbox
      toast.info("Launching sandbox...")
      setLaunchState({ status: "waiting_for_sandbox", ticketId: result.id, prompt })

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
            Describe what you want, and we'll spawn an AI agent to build it
          </p>
        </div>

        {/* Main Input */}
        <PromptInput
          onSubmit={handleSubmit}
          isLoading={isLoading}
          placeholder="Describe what you want to build..."
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
