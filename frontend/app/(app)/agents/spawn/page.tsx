"use client";

import { useState, Suspense, useMemo } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, Loader2, Bot, FolderGit2 } from "lucide-react";
import { useProjects } from "@/hooks/useProjects";
import { useRegisterAgent } from "@/hooks/useAgents";
import { PHASES, type PhaseConfig } from "@/lib/phases-config";

function SpawnAgentForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const preselectedProjectId = searchParams.get("projectId");

  const [formData, setFormData] = useState({
    projectId: preselectedProjectId || "",
    agentType: "worker",
    phaseId: "PHASE_IMPLEMENTATION",
    capabilities: "code_generation,testing,debugging",
    capacity: "3",
  });

  const { data: projectsData } = useProjects({ status: "active" });
  const registerMutation = useRegisterAgent();

  // Transform projects for dropdown
  const projects = useMemo(() => {
    if (!projectsData?.projects) return [];
    return projectsData.projects;
  }, [projectsData]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const result = await registerMutation.mutateAsync({
        agent_type: formData.agentType,
        phase_id: formData.phaseId,
        capabilities: formData.capabilities.split(",").map((c) => c.trim()),
        capacity: parseInt(formData.capacity, 10) || 3,
        tags: formData.projectId ? [`project:${formData.projectId}`] : [],
      });

      toast.success("Agent registered successfully!");
      router.push(`/agents/${result.agent_id}`);
    } catch (error) {
      toast.error("Failed to register agent");
    }
  };

  return (
    <div className="container mx-auto max-w-2xl p-6 space-y-6">
      {/* Back Link */}
      <Link
        href="/agents"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Agents
      </Link>

      {/* Form Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Bot className="h-6 w-6" />
            <div>
              <CardTitle>Spawn New Agent</CardTitle>
              <CardDescription>
                Create a new AI agent to work on your project
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Project Selection (Optional) */}
            <div className="space-y-2">
              <Label htmlFor="project">Project (Optional)</Label>
              <Select
                value={formData.projectId}
                onValueChange={(value) =>
                  setFormData({ ...formData, projectId: value })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select a project (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">No project</SelectItem>
                  {projects.map((project) => (
                    <SelectItem key={project.id} value={project.id}>
                      <div className="flex items-center gap-2">
                        <FolderGit2 className="h-4 w-4" />
                        <span>{project.name}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Associate this agent with a specific project
              </p>
            </div>

            {/* Agent Type */}
            <div className="space-y-2">
              <Label htmlFor="agentType">Agent Type</Label>
              <Select
                value={formData.agentType}
                onValueChange={(value) =>
                  setFormData({ ...formData, agentType: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="worker">
                    Worker (General purpose)
                  </SelectItem>
                  <SelectItem value="specialist">
                    Specialist (Domain expert)
                  </SelectItem>
                  <SelectItem value="coordinator">
                    Coordinator (Orchestration)
                  </SelectItem>
                  <SelectItem value="reviewer">
                    Reviewer (Code review)
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Phase Selection */}
            <div className="space-y-2">
              <Label htmlFor="phase">Starting Phase</Label>
              <Select
                value={formData.phaseId}
                onValueChange={(value) =>
                  setFormData({ ...formData, phaseId: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PHASES.map((phase: PhaseConfig) => (
                    <SelectItem key={phase.id} value={phase.id}>
                      {phase.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Capabilities */}
            <div className="space-y-2">
              <Label htmlFor="capabilities">Capabilities</Label>
              <Input
                id="capabilities"
                placeholder="code_generation, testing, debugging"
                value={formData.capabilities}
                onChange={(e) =>
                  setFormData({ ...formData, capabilities: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                Comma-separated list of agent capabilities
              </p>
            </div>

            {/* Capacity */}
            <div className="space-y-2">
              <Label htmlFor="capacity">Capacity</Label>
              <Input
                id="capacity"
                type="number"
                min="1"
                max="10"
                value={formData.capacity}
                onChange={(e) =>
                  setFormData({ ...formData, capacity: e.target.value })
                }
              />
              <p className="text-xs text-muted-foreground">
                How many concurrent tasks this agent can handle (1-10)
              </p>
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-4">
              <Button type="button" variant="outline" asChild>
                <Link href="/agents">Cancel</Link>
              </Button>
              <Button
                type="submit"
                disabled={registerMutation.isPending || !formData.agentType}
              >
                {registerMutation.isPending && (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                )}
                {registerMutation.isPending
                  ? "Registering..."
                  : "Register Agent"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function SpawnAgentPage() {
  return (
    <Suspense
      fallback={<div className="container mx-auto p-6">Loading...</div>}
    >
      <SpawnAgentForm />
    </Suspense>
  );
}
