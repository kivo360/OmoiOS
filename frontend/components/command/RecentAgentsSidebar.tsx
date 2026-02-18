"use client";

import { useState } from "react";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarSeparator,
} from "@/components/ui/sidebar";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { AgentCard, AgentStatus } from "@/components/custom";
import { TimeGroupHeader } from "@/components/custom";
import {
  Search,
  Plus,
  Settings,
  HelpCircle,
  Filter,
  SlidersHorizontal,
} from "lucide-react";

export interface RecentAgent {
  id: string;
  taskName: string;
  status: AgentStatus;
  timeAgo: string;
  additions?: number;
  deletions?: number;
  repoName?: string;
  createdAt: Date;
}

interface RecentAgentsSidebarProps {
  agents?: RecentAgent[];
  onNewAgent?: () => void;
}

function groupAgentsByTime(agents: RecentAgent[]) {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const thisWeek = new Date(today);
  thisWeek.setDate(thisWeek.getDate() - 7);
  const thisMonth = new Date(today);
  thisMonth.setDate(thisMonth.getDate() - 30);

  const groups = {
    today: [] as RecentAgent[],
    thisWeek: [] as RecentAgent[],
    thisMonth: [] as RecentAgent[],
    older: [] as RecentAgent[],
    errored: [] as RecentAgent[],
  };

  agents.forEach((agent) => {
    if (agent.status === "failed") {
      groups.errored.push(agent);
      return;
    }

    const agentDate = new Date(agent.createdAt);
    if (agentDate >= today) {
      groups.today.push(agent);
    } else if (agentDate >= thisWeek) {
      groups.thisWeek.push(agent);
    } else if (agentDate >= thisMonth) {
      groups.thisMonth.push(agent);
    } else {
      groups.older.push(agent);
    }
  });

  return groups;
}

export function RecentAgentsSidebar({
  agents = [],
  onNewAgent,
}: RecentAgentsSidebarProps) {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredAgents = agents.filter((agent) =>
    agent.taskName.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  const groupedAgents = groupAgentsByTime(filteredAgents);

  return (
    <Sidebar variant="sidebar" className="border-r border-sidebar-border">
      <SidebarHeader className="p-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search agents..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-9 pl-8 bg-background"
            />
          </div>
          <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0">
            <Filter className="h-4 w-4" />
            <span className="sr-only">Filter</span>
          </Button>
          <Button variant="ghost" size="icon" className="h-9 w-9 shrink-0">
            <SlidersHorizontal className="h-4 w-4" />
            <span className="sr-only">Sort</span>
          </Button>
        </div>
        <Button onClick={onNewAgent} className="mt-3 w-full gap-2" size="sm">
          <Plus className="h-4 w-4" />
          New Agent
        </Button>
      </SidebarHeader>

      <SidebarContent>
        <ScrollArea className="h-full">
          {/* Today */}
          {groupedAgents.today.length > 0 && (
            <SidebarGroup>
              <TimeGroupHeader>Today</TimeGroupHeader>
              <SidebarGroupContent className="px-2 space-y-0.5">
                {groupedAgents.today.map((agent) => (
                  <AgentCard key={agent.id} {...agent} />
                ))}
              </SidebarGroupContent>
            </SidebarGroup>
          )}

          {/* This Week */}
          {groupedAgents.thisWeek.length > 0 && (
            <>
              <SidebarSeparator />
              <SidebarGroup>
                <TimeGroupHeader>This Week</TimeGroupHeader>
                <SidebarGroupContent className="px-2 space-y-0.5">
                  {groupedAgents.thisWeek.map((agent) => (
                    <AgentCard key={agent.id} {...agent} />
                  ))}
                </SidebarGroupContent>
              </SidebarGroup>
            </>
          )}

          {/* This Month */}
          {groupedAgents.thisMonth.length > 0 && (
            <>
              <SidebarSeparator />
              <SidebarGroup>
                <TimeGroupHeader>This Month</TimeGroupHeader>
                <SidebarGroupContent className="px-2 space-y-0.5">
                  {groupedAgents.thisMonth.map((agent) => (
                    <AgentCard key={agent.id} {...agent} />
                  ))}
                </SidebarGroupContent>
              </SidebarGroup>
            </>
          )}

          {/* Errored */}
          {groupedAgents.errored.length > 0 && (
            <>
              <SidebarSeparator />
              <SidebarGroup>
                <TimeGroupHeader>Errored</TimeGroupHeader>
                <SidebarGroupContent className="px-2 space-y-0.5">
                  {groupedAgents.errored.map((agent) => (
                    <AgentCard key={agent.id} {...agent} />
                  ))}
                </SidebarGroupContent>
              </SidebarGroup>
            </>
          )}

          {/* Empty state */}
          {filteredAgents.length === 0 && (
            <div className="flex flex-col items-center justify-center px-4 py-8 text-center">
              <p className="text-sm text-muted-foreground">No agents found</p>
              <Button
                variant="link"
                size="sm"
                onClick={onNewAgent}
                className="mt-2"
              >
                Create your first agent
              </Button>
            </div>
          )}
        </ScrollArea>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <a href="/settings">
              <Settings className="h-4 w-4" />
              <span className="sr-only">Settings</span>
            </a>
          </Button>
          <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
            <a href="/help">
              <HelpCircle className="h-4 w-4" />
              <span className="sr-only">Help</span>
            </a>
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
