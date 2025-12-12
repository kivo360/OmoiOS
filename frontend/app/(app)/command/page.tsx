"use client"

import { useState, useMemo } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { PromptInput, ModelSelector, RepoSelector, Project, Repository } from "@/components/command"
import { useProjects } from "@/hooks/useProjects"
import { useConnectedRepositories } from "@/hooks/useGitHub"
import { useRegisterAgent } from "@/hooks/useAgents"

export default function CommandCenterPage() {
  const router = useRouter()
  const [selectedProject, setSelectedProject] = useState<Project | null>(null)
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [selectedBranch, setSelectedBranch] = useState("main")
  const [selectedModel, setSelectedModel] = useState("opus-4.5")

  // Fetch real data
  const { data: projectsData } = useProjects({ status: "active" })
  const { data: connectedRepos } = useConnectedRepositories()
  const registerMutation = useRegisterAgent()

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

  const handleSubmit = async (prompt: string) => {
    try {
      // Register a new agent with the prompt context
      const result = await registerMutation.mutateAsync({
        agent_type: "worker",
        phase_id: "PHASE_IMPLEMENTATION",
        capabilities: ["code_generation", "testing", "debugging"],
        capacity: 3,
        tags: selectedProject ? [`project:${selectedProject.id}`, `prompt:${prompt.slice(0, 50)}`] : [],
      })
      
      toast.success("Agent spawned successfully!")
      router.push(`/agents/${result.agent_id}`)
    } catch (error) {
      toast.error("Failed to spawn agent. Please try again.")
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

  return (
    <div className="flex h-[calc(100vh-48px)] flex-col items-center justify-center bg-background px-4">
      <div className="w-full max-w-[700px] space-y-6">
        {/* Prompt Area */}
        <div className="text-center">
          <h1 className="mb-2 text-2xl font-semibold text-foreground">
            What would you like to build?
          </h1>
          <p className="text-muted-foreground">
            Ask Cursor to build, fix bugs, or explore your codebase
          </p>
        </div>

        {/* Main Input */}
        <PromptInput
          onSubmit={handleSubmit}
          isLoading={registerMutation.isPending}
          placeholder="Ask Cursor to build, fix bugs, explore"
        />

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
        {(selectedProject || selectedRepo) && (
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
