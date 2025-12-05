"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { toast } from "sonner"
import { PromptInput, ModelSelector, RepoSelector, Project, Repository } from "@/components/command"

// Mock data (will be replaced with real API calls)
const mockProjects: Project[] = [
  { id: "1", name: "Auth System", repo: "kivo360/auth-system", ticketCount: 12 },
  { id: "2", name: "Payment Gateway", repo: "kivo360/payment-gateway", ticketCount: 8 },
  { id: "3", name: "API Service", repo: "kivo360/api-service", ticketCount: 3 },
]

const mockRepositories: Repository[] = [
  { fullName: "kivo360/frontend-app", isPrivate: false },
  { fullName: "kivo360/mobile-app", isPrivate: true },
  { fullName: "kivo360/senseii-games", isPrivate: false },
]

export default function CommandCenterPage() {
  const router = useRouter()
  const [selectedProject, setSelectedProject] = useState<Project | null>(mockProjects[0])
  const [selectedRepo, setSelectedRepo] = useState<string | null>(null)
  const [selectedModel, setSelectedModel] = useState("opus-4.5")
  const [isSubmitting, setIsSubmitting] = useState(false)

  const handleSubmit = async (prompt: string) => {
    setIsSubmitting(true)
    
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1500))
      
      // Mock creating an agent
      const mockAgentId = `agent-${Date.now()}`
      
      toast.success("Agent spawned successfully!")
      router.push(`/agents/${mockAgentId}`)
    } catch (error) {
      toast.error("Failed to spawn agent. Please try again.")
    } finally {
      setIsSubmitting(false)
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
          isLoading={isSubmitting}
          placeholder="Ask Cursor to build, fix bugs, explore"
        />

        {/* Controls Row */}
        <div className="flex items-center justify-between">
          <RepoSelector
            projects={mockProjects}
            repositories={mockRepositories}
            selectedProject={selectedProject}
            selectedRepo={selectedRepo}
            onProjectSelect={handleProjectSelect}
            onRepoSelect={handleRepoSelect}
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
