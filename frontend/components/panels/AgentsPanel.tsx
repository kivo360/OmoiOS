"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Filter, SortAsc, Plus, AlertCircle } from "lucide-react";
import { AgentCard, TimeGroupHeader } from "@/components/custom";
import { useAgents } from "@/hooks/useAgents";

// Map API agent status to component status
type AgentCardStatus = "running" | "completed" | "failed" | "blocked";

function mapAgentStatus(status: string): AgentCardStatus {
  switch (status.toLowerCase()) {
    case "active":
    case "running":
      return "running";
    case "completed":
    case "done":
      return "completed";
    case "failed":
    case "error":
      return "failed";
    case "blocked":
    case "stalled":
      return "blocked";
    default:
      return "completed";
  }
}

function formatTimeAgo(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 7) return `${diffDays}d`;
  return `${Math.floor(diffDays / 7)}w`;
}

export function AgentsPanel() {
  const [searchQuery, setSearchQuery] = useState("");
  const { data: agents, isLoading, error } = useAgents();

  const filteredAgents = useMemo(() => {
    if (!agents) return [];
    return agents.filter(
      (agent) =>
        agent.agent_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.agent_id.toLowerCase().includes(searchQuery.toLowerCase()),
    );
  }, [agents, searchQuery]);

  const todayAgents = filteredAgents.filter(
    (a) => mapAgentStatus(a.status) === "running",
  );
  const weekAgents = filteredAgents.filter(
    (a) => mapAgentStatus(a.status) === "completed",
  );
  const erroredAgents = filteredAgents.filter((a) => {
    const status = mapAgentStatus(a.status);
    return status === "failed" || status === "blocked";
  });

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-3 space-y-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-9 pl-8 text-sm"
            />
          </div>
          <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0">
            <Filter className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0">
            <SortAsc className="h-4 w-4" />
          </Button>
        </div>
        <Button className="w-full" size="sm" asChild>
          <Link href="/agents/spawn">
            <Plus className="mr-2 h-4 w-4" /> New Agent
          </Link>
        </Button>
      </div>

      {/* Agent List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          ) : error ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              Failed to load agents
            </div>
          ) : (
            <>
              {todayAgents.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Running</TimeGroupHeader>
                  {todayAgents.map((agent) => (
                    <AgentCard
                      key={agent.agent_id}
                      id={agent.agent_id}
                      taskName={agent.agent_type}
                      status={mapAgentStatus(agent.status)}
                      timeAgo={
                        agent.created_at
                          ? formatTimeAgo(agent.created_at)
                          : "N/A"
                      }
                    />
                  ))}
                </div>
              )}

              {weekAgents.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Completed</TimeGroupHeader>
                  {weekAgents.map((agent) => (
                    <AgentCard
                      key={agent.agent_id}
                      id={agent.agent_id}
                      taskName={agent.agent_type}
                      status={mapAgentStatus(agent.status)}
                      timeAgo={
                        agent.created_at
                          ? formatTimeAgo(agent.created_at)
                          : "N/A"
                      }
                    />
                  ))}
                </div>
              )}

              {erroredAgents.length > 0 && (
                <div className="space-y-1">
                  <TimeGroupHeader>Errored</TimeGroupHeader>
                  {erroredAgents.map((agent) => (
                    <AgentCard
                      key={agent.agent_id}
                      id={agent.agent_id}
                      taskName={agent.agent_type}
                      status={mapAgentStatus(agent.status)}
                      timeAgo={
                        agent.created_at
                          ? formatTimeAgo(agent.created_at)
                          : "N/A"
                      }
                    />
                  ))}
                </div>
              )}

              {filteredAgents.length === 0 && (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No agents found
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
