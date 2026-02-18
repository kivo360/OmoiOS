"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Brain,
  Ticket,
  ListTodo,
  ArrowLeft,
  Clock,
  User,
  GitBranch,
  Filter,
  Search,
  ChevronDown,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { cn } from "@/lib/utils";

interface DiagnosticContextPanelProps {
  entityType?: string;
  entityId?: string;
}

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

// Mock source entity data
const mockSourceEntity = {
  type: "ticket",
  id: "TICKET-042",
  title: "Infrastructure: Redis Cache Setup",
  status: "in_progress",
  priority: "critical",
  assignee: "worker-1",
  createdAt: "2024-01-15T10:00:00Z",
  phase: "Implementation",
};

export function DiagnosticContextPanel({
  entityType,
  entityId,
}: DiagnosticContextPanelProps) {
  const [eventFilters, setEventFilters] = useState({
    discovery: true,
    decision: true,
    codeChange: true,
    error: true,
    linking: true,
  });

  const toggleEventFilter = (filter: keyof typeof eventFilters) => {
    setEventFilters((prev) => ({ ...prev, [filter]: !prev[filter] }));
  };

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-4">
        <div className="flex items-center gap-2 mb-3">
          <Brain className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-semibold">Diagnostic Context</h2>
        </div>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input placeholder="Search events..." className="pl-8 h-9" />
        </div>
      </div>

      {/* Source Entity */}
      <div className="border-b p-4">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-3">
          Source Entity
        </p>
        <div className="rounded-lg border bg-card p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Ticket className="h-4 w-4 text-muted-foreground" />
            <span className="text-xs font-mono text-muted-foreground">
              {mockSourceEntity.id}
            </span>
            <Badge variant="outline" className="text-xs ml-auto">
              {mockSourceEntity.status.replace("_", " ")}
            </Badge>
          </div>
          <p className="text-sm font-medium line-clamp-2">
            {mockSourceEntity.title}
          </p>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <User className="h-3 w-3" />
              {mockSourceEntity.assignee}
            </span>
            <span className="flex items-center gap-1">
              <GitBranch className="h-3 w-3" />
              {mockSourceEntity.phase}
            </span>
          </div>
          <Button variant="outline" size="sm" className="w-full mt-2" asChild>
            <Link href={`/board/project-1/${mockSourceEntity.id}`}>
              <ArrowLeft className="h-3 w-3 mr-1" />
              View Ticket
            </Link>
          </Button>
        </div>
      </div>

      {/* Filters */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-1">
          {/* Event Type Filters */}
          <FilterSection title="Event Types">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="discovery"
                  checked={eventFilters.discovery}
                  onCheckedChange={() => toggleEventFilter("discovery")}
                />
                <Label
                  htmlFor="discovery"
                  className="text-sm font-normal cursor-pointer"
                >
                  🔍 Discoveries
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="decision"
                  checked={eventFilters.decision}
                  onCheckedChange={() => toggleEventFilter("decision")}
                />
                <Label
                  htmlFor="decision"
                  className="text-sm font-normal cursor-pointer"
                >
                  🧠 Decisions
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="codeChange"
                  checked={eventFilters.codeChange}
                  onCheckedChange={() => toggleEventFilter("codeChange")}
                />
                <Label
                  htmlFor="codeChange"
                  className="text-sm font-normal cursor-pointer"
                >
                  💻 Code Changes
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="error"
                  checked={eventFilters.error}
                  onCheckedChange={() => toggleEventFilter("error")}
                />
                <Label
                  htmlFor="error"
                  className="text-sm font-normal cursor-pointer"
                >
                  ❌ Errors
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="linking"
                  checked={eventFilters.linking}
                  onCheckedChange={() => toggleEventFilter("linking")}
                />
                <Label
                  htmlFor="linking"
                  className="text-sm font-normal cursor-pointer"
                >
                  🔗 Linking Events
                </Label>
              </div>
            </div>
          </FilterSection>

          {/* Quick Stats */}
          <FilterSection title="Reasoning Summary" defaultOpen={false}>
            <div className="grid grid-cols-2 gap-2">
              <div className="rounded-md border p-2 text-center">
                <p className="text-lg font-semibold">12</p>
                <p className="text-xs text-muted-foreground">Events</p>
              </div>
              <div className="rounded-md border p-2 text-center">
                <p className="text-lg font-semibold">3</p>
                <p className="text-xs text-muted-foreground">Discoveries</p>
              </div>
              <div className="rounded-md border p-2 text-center">
                <p className="text-lg font-semibold">5</p>
                <p className="text-xs text-muted-foreground">Decisions</p>
              </div>
              <div className="rounded-md border p-2 text-center">
                <p className="text-lg font-semibold">1</p>
                <p className="text-xs text-muted-foreground">Error</p>
              </div>
            </div>
          </FilterSection>

          {/* Related Entities */}
          <FilterSection title="Related Entities" defaultOpen={false}>
            <div className="space-y-2">
              <Link
                href="/board/project-1/TICKET-041"
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <Ticket className="h-3.5 w-3.5" />
                TICKET-041 (blocked)
              </Link>
              <Link
                href="/board/project-1/TICKET-043"
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <Ticket className="h-3.5 w-3.5" />
                TICKET-043 (blocker)
              </Link>
              <Link
                href="#"
                className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                <ListTodo className="h-3.5 w-3.5" />3 spawned tasks
              </Link>
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
          onClick={() =>
            setEventFilters({
              discovery: true,
              decision: true,
              codeChange: true,
              error: true,
              linking: true,
            })
          }
        >
          Reset filters
        </Button>
      </div>
    </div>
  );
}
