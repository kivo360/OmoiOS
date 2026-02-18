"use client";

import { useState } from "react";
import {
  Activity,
  Search,
  ChevronDown,
  GitCommit,
  Brain,
  MessageSquare,
  CheckCircle2,
  XCircle,
  FileCode,
  Ticket,
  Bot,
  User,
  Cpu,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

interface FilterSectionProps {
  title: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}

function FilterSection({
  title,
  children,
  defaultOpen = true,
}: FilterSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <Collapsible open={isOpen} onOpenChange={setIsOpen}>
      <CollapsibleTrigger className="flex w-full items-center justify-between py-2 text-sm font-medium text-foreground hover:text-foreground/80">
        {title}
        <ChevronDown
          className={cn(
            "h-4 w-4 text-muted-foreground transition-transform",
            isOpen && "rotate-180",
          )}
        />
      </CollapsibleTrigger>
      <CollapsibleContent className="space-y-2 pb-3">
        {children}
      </CollapsibleContent>
    </Collapsible>
  );
}

export function ActivityFiltersPanel() {
  const [activityTypes, setActivityTypes] = useState({
    commit: true,
    decision: true,
    comment: true,
    taskComplete: true,
    error: true,
    prOpened: true,
    ticketStatus: true,
    tasksGenerated: true,
  });

  const [actorFilter, setActorFilter] = useState("all");
  const [projectFilter, setProjectFilter] = useState("all");
  const [timeRange, setTimeRange] = useState("all");

  const toggleActivityType = (type: keyof typeof activityTypes) => {
    setActivityTypes((prev) => ({ ...prev, [type]: !prev[type] }));
  };

  const clearFilters = () => {
    setActivityTypes({
      commit: true,
      decision: true,
      comment: true,
      taskComplete: true,
      error: true,
      prOpened: true,
      ticketStatus: true,
      tasksGenerated: true,
    });
    setActorFilter("all");
    setProjectFilter("all");
    setTimeRange("all");
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center gap-2 mb-3">
          <Activity className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Activity Filters</h2>
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search activities..." className="pl-8 h-9" />
        </div>
      </div>

      {/* Filters */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-1">
          {/* Activity Types */}
          <FilterSection title="Activity Type">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="commit"
                  checked={activityTypes.commit}
                  onCheckedChange={() => toggleActivityType("commit")}
                />
                <Label
                  htmlFor="commit"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <GitCommit className="h-3.5 w-3.5 text-blue-500" />
                  Commits
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="decision"
                  checked={activityTypes.decision}
                  onCheckedChange={() => toggleActivityType("decision")}
                />
                <Label
                  htmlFor="decision"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <Brain className="h-3.5 w-3.5 text-purple-500" />
                  Decisions
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="comment"
                  checked={activityTypes.comment}
                  onCheckedChange={() => toggleActivityType("comment")}
                />
                <Label
                  htmlFor="comment"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <MessageSquare className="h-3.5 w-3.5 text-gray-500" />
                  Comments
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="taskComplete"
                  checked={activityTypes.taskComplete}
                  onCheckedChange={() => toggleActivityType("taskComplete")}
                />
                <Label
                  htmlFor="taskComplete"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                  Task Completions
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="error"
                  checked={activityTypes.error}
                  onCheckedChange={() => toggleActivityType("error")}
                />
                <Label
                  htmlFor="error"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <XCircle className="h-3.5 w-3.5 text-red-500" />
                  Errors
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="prOpened"
                  checked={activityTypes.prOpened}
                  onCheckedChange={() => toggleActivityType("prOpened")}
                />
                <Label
                  htmlFor="prOpened"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <FileCode className="h-3.5 w-3.5 text-orange-500" />
                  Pull Requests
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="ticketStatus"
                  checked={activityTypes.ticketStatus}
                  onCheckedChange={() => toggleActivityType("ticketStatus")}
                />
                <Label
                  htmlFor="ticketStatus"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <Ticket className="h-3.5 w-3.5 text-yellow-500" />
                  Ticket Updates
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="tasksGenerated"
                  checked={activityTypes.tasksGenerated}
                  onCheckedChange={() => toggleActivityType("tasksGenerated")}
                />
                <Label
                  htmlFor="tasksGenerated"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <Cpu className="h-3.5 w-3.5 text-indigo-500" />
                  Tasks Generated
                </Label>
              </div>
            </div>
          </FilterSection>

          {/* Actor Filter */}
          <FilterSection title="Actor">
            <Select value={actorFilter} onValueChange={setActorFilter}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="All Actors" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Actors</SelectItem>
                <SelectItem value="agents">
                  <span className="flex items-center gap-2">
                    <Bot className="h-3.5 w-3.5" />
                    Agents Only
                  </span>
                </SelectItem>
                <SelectItem value="users">
                  <span className="flex items-center gap-2">
                    <User className="h-3.5 w-3.5" />
                    Users Only
                  </span>
                </SelectItem>
                <SelectItem value="system">
                  <span className="flex items-center gap-2">
                    <Cpu className="h-3.5 w-3.5" />
                    System Only
                  </span>
                </SelectItem>
              </SelectContent>
            </Select>
          </FilterSection>

          {/* Project Filter */}
          <FilterSection title="Project">
            <Select value={projectFilter} onValueChange={setProjectFilter}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="All Projects" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Projects</SelectItem>
                <SelectItem value="senseii-games">senseii-games</SelectItem>
                <SelectItem value="api-service">api-service</SelectItem>
                <SelectItem value="auth-system">auth-system</SelectItem>
                <SelectItem value="gaming-service">gaming-service</SelectItem>
              </SelectContent>
            </Select>
          </FilterSection>

          {/* Time Range */}
          <FilterSection title="Time Range">
            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="All Time" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Time</SelectItem>
                <SelectItem value="1h">Last Hour</SelectItem>
                <SelectItem value="24h">Last 24 Hours</SelectItem>
                <SelectItem value="7d">Last 7 Days</SelectItem>
                <SelectItem value="30d">Last 30 Days</SelectItem>
              </SelectContent>
            </Select>
          </FilterSection>
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t p-3">
        <Button
          variant="ghost"
          size="sm"
          className="w-full text-muted-foreground"
          onClick={clearFilters}
        >
          Clear all filters
        </Button>
      </div>
    </div>
  );
}
