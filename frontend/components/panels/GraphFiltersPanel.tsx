"use client";

import { useState } from "react";
import {
  Search,
  Filter,
  GitBranch,
  CheckCircle2,
  Clock,
  AlertCircle,
  XCircle,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
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
import { ChevronDown } from "lucide-react";
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

export function GraphFiltersPanel() {
  const [statusFilters, setStatusFilters] = useState({
    pending: true,
    inProgress: true,
    completed: true,
    blocked: true,
  });

  const [phaseFilter, setPhaseFilter] = useState("all");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [assigneeFilter, setAssigneeFilter] = useState("all");

  const toggleStatus = (status: keyof typeof statusFilters) => {
    setStatusFilters((prev) => ({ ...prev, [status]: !prev[status] }));
  };

  const clearFilters = () => {
    setStatusFilters({
      pending: true,
      inProgress: true,
      completed: true,
      blocked: true,
    });
    setPhaseFilter("all");
    setPriorityFilter("all");
    setAssigneeFilter("all");
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Graph Filters</h2>
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search tickets..." className="pl-8 h-9" />
        </div>
      </div>

      {/* Filters */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-1">
          {/* Status Filter */}
          <FilterSection title="Status">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="pending"
                  checked={statusFilters.pending}
                  onCheckedChange={() => toggleStatus("pending")}
                />
                <Label
                  htmlFor="pending"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <Clock className="h-3.5 w-3.5 text-muted-foreground" />
                  Pending
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="inProgress"
                  checked={statusFilters.inProgress}
                  onCheckedChange={() => toggleStatus("inProgress")}
                />
                <Label
                  htmlFor="inProgress"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <AlertCircle className="h-3.5 w-3.5 text-blue-500" />
                  In Progress
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="completed"
                  checked={statusFilters.completed}
                  onCheckedChange={() => toggleStatus("completed")}
                />
                <Label
                  htmlFor="completed"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                  Completed
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="blocked"
                  checked={statusFilters.blocked}
                  onCheckedChange={() => toggleStatus("blocked")}
                />
                <Label
                  htmlFor="blocked"
                  className="flex items-center gap-2 text-sm font-normal cursor-pointer"
                >
                  <XCircle className="h-3.5 w-3.5 text-red-500" />
                  Blocked
                </Label>
              </div>
            </div>
          </FilterSection>

          {/* Phase Filter */}
          <FilterSection title="Phase">
            <Select value={phaseFilter} onValueChange={setPhaseFilter}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="All Phases" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Phases</SelectItem>
                <SelectItem value="requirements">Requirements</SelectItem>
                <SelectItem value="design">Design</SelectItem>
                <SelectItem value="implementation">Implementation</SelectItem>
                <SelectItem value="testing">Testing</SelectItem>
                <SelectItem value="review">Review</SelectItem>
              </SelectContent>
            </Select>
          </FilterSection>

          {/* Priority Filter */}
          <FilterSection title="Priority">
            <Select value={priorityFilter} onValueChange={setPriorityFilter}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="All Priorities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Priorities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="medium">Medium</SelectItem>
                <SelectItem value="low">Low</SelectItem>
              </SelectContent>
            </Select>
          </FilterSection>

          {/* Assignee Filter */}
          <FilterSection title="Assignee">
            <Select value={assigneeFilter} onValueChange={setAssigneeFilter}>
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="All Assignees" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Assignees</SelectItem>
                <SelectItem value="worker-1">worker-1</SelectItem>
                <SelectItem value="worker-2">worker-2</SelectItem>
                <SelectItem value="unassigned">Unassigned</SelectItem>
              </SelectContent>
            </Select>
          </FilterSection>

          {/* Node Types */}
          <FilterSection title="Show">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox id="showTickets" defaultChecked />
                <Label
                  htmlFor="showTickets"
                  className="text-sm font-normal cursor-pointer"
                >
                  Tickets
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox id="showTasks" defaultChecked />
                <Label
                  htmlFor="showTasks"
                  className="text-sm font-normal cursor-pointer"
                >
                  Tasks
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox id="showDiscoveries" defaultChecked />
                <Label
                  htmlFor="showDiscoveries"
                  className="text-sm font-normal cursor-pointer"
                >
                  Discoveries
                </Label>
              </div>
            </div>
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
