"use client";

import { useState, useMemo, useCallback, Suspense } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Search,
  Filter,
  RefreshCw,
  Bot,
  User,
  GitCommit,
  GitPullRequest,
  MessageSquare,
  CheckCircle,
  AlertCircle,
  Pause,
  FileText,
  Zap,
  Lightbulb,
  AlertTriangle,
  Brain,
  Plus,
  ArrowRight,
  ExternalLink,
  Wifi,
  WifiOff,
  FileCode,
  Terminal,
  Wrench,
  Eye,
  Code,
  X,
} from "lucide-react";
import { useEvents, type SystemEvent } from "@/hooks/useEvents";
import { FileChangeCard } from "@/components/custom/FileChangeCard";

// Activity type derived from system events
interface Activity {
  id: string;
  timestamp: Date;
  type: string;
  title: string;
  description: string;
  actor: { type: string; name: string; avatar: string };
  project: string | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  metadata: Record<string, any>;
  link: string;
}

const activityTypeConfig: Record<
  string,
  { icon: typeof Plus; color: string; bg: string; label: string }
> = {
  // Commit events
  COMMIT_LINKED: {
    icon: GitCommit,
    color: "text-cyan-600",
    bg: "bg-cyan-100",
    label: "Commit",
  },
  commit: {
    icon: GitCommit,
    color: "text-cyan-600",
    bg: "bg-cyan-100",
    label: "Commit",
  },
  // Task events
  TASK_COMPLETED: {
    icon: CheckCircle,
    color: "text-emerald-600",
    bg: "bg-emerald-100",
    label: "Complete",
  },
  TASK_ASSIGNED: {
    icon: ArrowRight,
    color: "text-indigo-600",
    bg: "bg-indigo-100",
    label: "Assigned",
  },
  TASK_CREATED: {
    icon: Plus,
    color: "text-blue-600",
    bg: "bg-blue-100",
    label: "Created",
  },
  task_complete: {
    icon: CheckCircle,
    color: "text-emerald-600",
    bg: "bg-emerald-100",
    label: "Complete",
  },
  // Ticket events
  TICKET_TRANSITION: {
    icon: ArrowRight,
    color: "text-indigo-600",
    bg: "bg-indigo-100",
    label: "Status",
  },
  TICKET_BLOCKED: {
    icon: AlertTriangle,
    color: "text-orange-600",
    bg: "bg-orange-100",
    label: "Blocked",
  },
  TICKET_UNBLOCKED: {
    icon: CheckCircle,
    color: "text-green-600",
    bg: "bg-green-100",
    label: "Unblocked",
  },
  ticket_status: {
    icon: ArrowRight,
    color: "text-indigo-600",
    bg: "bg-indigo-100",
    label: "Status",
  },
  // Agent events
  AGENT_REGISTERED: {
    icon: Zap,
    color: "text-pink-600",
    bg: "bg-pink-100",
    label: "Spawned",
  },
  AGENT_HEARTBEAT: {
    icon: Wifi,
    color: "text-gray-500",
    bg: "bg-gray-100",
    label: "Heartbeat",
  },
  agent_spawned: {
    icon: Zap,
    color: "text-pink-600",
    bg: "bg-pink-100",
    label: "Spawned",
  },
  // Decision events
  decision: {
    icon: Brain,
    color: "text-green-600",
    bg: "bg-green-100",
    label: "Decision",
  },
  // Comment events
  comment: {
    icon: MessageSquare,
    color: "text-blue-600",
    bg: "bg-blue-100",
    label: "Comment",
  },
  // Error events
  error: {
    icon: AlertCircle,
    color: "text-red-600",
    bg: "bg-red-100",
    label: "Error",
  },
  ERROR: {
    icon: AlertCircle,
    color: "text-red-600",
    bg: "bg-red-100",
    label: "Error",
  },
  // PR events
  pr_opened: {
    icon: GitPullRequest,
    color: "text-purple-600",
    bg: "bg-purple-100",
    label: "PR Opened",
  },
  // Discovery events
  discovery: {
    icon: Lightbulb,
    color: "text-yellow-600",
    bg: "bg-yellow-100",
    label: "Discovery",
  },
  blocking_added: {
    icon: AlertTriangle,
    color: "text-orange-600",
    bg: "bg-orange-100",
    label: "Blocking",
  },
  tasks_generated: {
    icon: Zap,
    color: "text-violet-600",
    bg: "bg-violet-100",
    label: "Generated",
  },
  spec_approved: {
    icon: FileText,
    color: "text-teal-600",
    bg: "bg-teal-100",
    label: "Approved",
  },
  // File edit events (sandbox)
  "SANDBOX_agent.file_edited": {
    icon: FileCode,
    color: "text-blue-600",
    bg: "bg-blue-100",
    label: "File Edit",
  },
  "agent.file_edited": {
    icon: FileCode,
    color: "text-blue-600",
    bg: "bg-blue-100",
    label: "File Edit",
  },
  // Sandbox agent events
  "SANDBOX_agent.started": {
    icon: Zap,
    color: "text-green-600",
    bg: "bg-green-100",
    label: "Started",
  },
  "SANDBOX_agent.completed": {
    icon: CheckCircle,
    color: "text-emerald-600",
    bg: "bg-emerald-100",
    label: "Completed",
  },
  "SANDBOX_agent.error": {
    icon: AlertCircle,
    color: "text-red-600",
    bg: "bg-red-100",
    label: "Error",
  },
  "SANDBOX_agent.tool_use": {
    icon: Wrench,
    color: "text-purple-600",
    bg: "bg-purple-100",
    label: "Tool Use",
  },
  "SANDBOX_agent.tool_result": {
    icon: Terminal,
    color: "text-gray-600",
    bg: "bg-gray-100",
    label: "Tool Result",
  },
  "SANDBOX_agent.thinking": {
    icon: Brain,
    color: "text-amber-600",
    bg: "bg-amber-100",
    label: "Thinking",
  },
  "SANDBOX_agent.assistant_message": {
    icon: MessageSquare,
    color: "text-blue-600",
    bg: "bg-blue-100",
    label: "Message",
  },
  "SANDBOX_agent.heartbeat": {
    icon: Wifi,
    color: "text-gray-400",
    bg: "bg-gray-50",
    label: "Heartbeat",
  },
  "SANDBOX_agent.message_injected": {
    icon: MessageSquare,
    color: "text-indigo-600",
    bg: "bg-indigo-100",
    label: "Injected",
  },
  "SANDBOX_agent.subagent_invoked": {
    icon: Bot,
    color: "text-violet-600",
    bg: "bg-violet-100",
    label: "Subagent",
  },
  "SANDBOX_agent.subagent_completed": {
    icon: CheckCircle,
    color: "text-violet-600",
    bg: "bg-violet-100",
    label: "Subagent Done",
  },
  // Default for unknown types
  default: {
    icon: Zap,
    color: "text-gray-600",
    bg: "bg-gray-100",
    label: "Event",
  },
};

// Transform a SystemEvent into an Activity
function eventToActivity(event: SystemEvent, index: number): Activity {
  const payload = event.payload || {};

  // Determine actor based on entity type and payload
  let actorType = "system";
  let actorName = "System";
  let actorAvatar = "S";

  if (event.entity_type === "agent" || payload.agent_id) {
    actorType = "agent";
    actorName = (payload.agent_id as string) || event.entity_id || "Agent";
    actorAvatar = actorName.substring(0, 2).toUpperCase();
  } else if (payload.user_id) {
    actorType = "user";
    actorName = "User";
    actorAvatar = "U";
  }

  // Build description from event type and payload
  let description = event.event_type.replace(/_/g, " ").toLowerCase();

  // Special handling for file edit events
  if (
    event.event_type === "SANDBOX_agent.file_edited" ||
    payload.original_event_type === "agent.file_edited"
  ) {
    const filePath = payload.file_path as string;
    const changeType = payload.change_type as string;
    const linesAdded = payload.lines_added as number;
    const linesRemoved = payload.lines_removed as number;
    if (filePath) {
      const filename = filePath.split("/").pop() || filePath;
      description = `${changeType === "created" ? "Created" : "Modified"} ${filename} (+${linesAdded} -${linesRemoved})`;
    }
  } else if (payload.message) {
    description = payload.message as string;
  } else if (event.entity_type && event.entity_id) {
    description = `${event.event_type} on ${event.entity_type} ${event.entity_id}`;
  }

  // Extract project from payload if available
  const project =
    (payload.project_id as string) || (payload.project as string) || null;

  // Build link based on entity type
  let link = "#";
  if (event.entity_type === "ticket" && event.entity_id) {
    link = `/board/${project || "default"}/${event.entity_id}`;
  } else if (event.entity_type === "agent" && event.entity_id) {
    link = `/agents/${event.entity_id}`;
  } else if (event.entity_type === "task" && event.entity_id) {
    link = `/board/${project || "default"}`;
  }

  return {
    id: `event-${index}-${Date.now()}`,
    timestamp: new Date(),
    type: event.event_type,
    title: event.event_type.replace(/_/g, " "),
    description,
    actor: { type: actorType, name: actorName, avatar: actorAvatar },
    project,
    metadata: payload,
    link,
  };
}

function ActivityPageContent() {
  const searchParams = useSearchParams();
  const sandboxId = searchParams.get("sandbox_id");

  const [searchQuery, setSearchQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [actorFilter, setActorFilter] = useState<string>("all");
  const [projectFilter, setProjectFilter] = useState<string>("all");
  const [isLive, setIsLive] = useState(true);
  const [activities, setActivities] = useState<Activity[]>([]);

  // Handle new events from WebSocket
  const handleNewEvent = useCallback(
    (event: SystemEvent) => {
      // If filtering by sandbox, only accept events for that sandbox
      if (sandboxId && event.entity_id !== sandboxId) {
        return;
      }

      setActivities((prev) => {
        const activity = eventToActivity(event, prev.length);
        return [activity, ...prev].slice(0, 100); // Keep max 100 activities
      });
    },
    [sandboxId],
  );

  // Build WebSocket filters based on sandbox_id
  const wsFilters = useMemo(() => {
    if (sandboxId) {
      return {
        entity_types: ["sandbox"],
        entity_ids: [sandboxId],
      };
    }
    return undefined;
  }, [sandboxId]);

  // Subscribe to real-time events
  const { isConnected, isConnecting, error, clearEvents } = useEvents({
    enabled: isLive,
    filters: wsFilters,
    onEvent: handleNewEvent,
    maxEvents: 100,
  });

  const filteredActivities = useMemo(() => {
    return activities.filter((activity) => {
      const matchesSearch =
        searchQuery === "" ||
        activity.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        activity.description.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesType =
        typeFilter === "all" ||
        activity.type === typeFilter ||
        (typeFilter === "SANDBOX_agent.file_edited" &&
          (activity.type === "SANDBOX_agent.file_edited" ||
            activity.type === "agent.file_edited" ||
            activity.metadata?.original_event_type === "agent.file_edited"));
      const matchesActor =
        actorFilter === "all" || activity.actor.type === actorFilter;
      const matchesProject =
        projectFilter === "all" ||
        activity.project === projectFilter ||
        (!activity.project && projectFilter === "system");
      return matchesSearch && matchesType && matchesActor && matchesProject;
    });
  }, [activities, searchQuery, typeFilter, actorFilter, projectFilter]);

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  // Group activities by date
  const groupedActivities = useMemo(() => {
    const groups: { label: string; activities: Activity[] }[] = [];
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const todayActivities = filteredActivities.filter(
      (a) => a.timestamp.toDateString() === today.toDateString(),
    );
    const yesterdayActivities = filteredActivities.filter(
      (a) => a.timestamp.toDateString() === yesterday.toDateString(),
    );
    const olderActivities = filteredActivities.filter(
      (a) =>
        a.timestamp.toDateString() !== today.toDateString() &&
        a.timestamp.toDateString() !== yesterday.toDateString(),
    );

    if (todayActivities.length)
      groups.push({ label: "Today", activities: todayActivities });
    if (yesterdayActivities.length)
      groups.push({ label: "Yesterday", activities: yesterdayActivities });
    if (olderActivities.length)
      groups.push({ label: "Earlier", activities: olderActivities });

    return groups;
  }, [filteredActivities]);

  // Unique projects for filter
  const projects = useMemo(() => {
    const set = new Set<string>();
    activities.forEach((a) => {
      if (a.project) set.add(a.project);
    });
    return Array.from(set);
  }, [activities]);

  // Handle refresh - clear events
  const handleRefresh = () => {
    setActivities([]);
    clearEvents();
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* Header */}
      <div className="flex-shrink-0 border-b bg-background px-6 py-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-semibold">
                {sandboxId ? "Sandbox Activity" : "Activity Timeline"}
              </h1>
              {sandboxId && (
                <Badge variant="secondary" className="font-mono text-xs">
                  <Terminal className="mr-1 h-3 w-3" />
                  {sandboxId.slice(0, 8)}...
                  <Link
                    href="/activity"
                    className="ml-1 hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </Link>
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">
              {sandboxId
                ? "Real-time events from sandbox execution"
                : "Real-time feed of all system activity"}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Connection status */}
            {isConnecting && (
              <Badge variant="outline" className="text-yellow-600">
                <Wifi className="mr-1 h-3 w-3 animate-pulse" />
                Connecting...
              </Badge>
            )}
            {error && (
              <Badge variant="destructive">
                <WifiOff className="mr-1 h-3 w-3" />
                Disconnected
              </Badge>
            )}
            {isConnected && (
              <Badge variant="outline" className="text-green-600">
                <Wifi className="mr-1 h-3 w-3" />
                Connected
              </Badge>
            )}
            <Badge variant="outline">{filteredActivities.length} events</Badge>
            <Button
              variant={isLive ? "default" : "outline"}
              size="sm"
              onClick={() => setIsLive(!isLive)}
            >
              {isLive ? (
                <>
                  <span className="relative flex h-2 w-2 mr-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
                  </span>
                  Live
                </>
              ) : (
                <>
                  <Pause className="mr-2 h-3 w-3" />
                  Paused
                </>
              )}
            </Button>
            <Button variant="outline" size="icon" onClick={handleRefresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex-shrink-0 border-b bg-muted/30 px-6 py-3">
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search activity..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-8"
            />
          </div>

          {/* Type Filter */}
          <Select value={typeFilter} onValueChange={setTypeFilter}>
            <SelectTrigger className="w-[150px]">
              <Filter className="mr-2 h-4 w-4" />
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="commit">Commits</SelectItem>
              <SelectItem value="decision">Decisions</SelectItem>
              <SelectItem value="comment">Comments</SelectItem>
              <SelectItem value="task_complete">Completions</SelectItem>
              <SelectItem value="error">Errors</SelectItem>
              <SelectItem value="pr_opened">Pull Requests</SelectItem>
              <SelectItem value="discovery">Discoveries</SelectItem>
              <SelectItem value="blocking_added">Blocking</SelectItem>
              <SelectItem value="ticket_status">Status Changes</SelectItem>
              <SelectItem value="SANDBOX_agent.file_edited">
                File Edits
              </SelectItem>
            </SelectContent>
          </Select>

          {/* Actor Filter */}
          <ToggleGroup
            type="single"
            value={actorFilter}
            onValueChange={(v) => v && setActorFilter(v)}
            className="border rounded-md"
          >
            <ToggleGroupItem value="all" className="px-3">
              All
            </ToggleGroupItem>
            <ToggleGroupItem value="agent" className="px-3">
              <Bot className="mr-1 h-3 w-3" />
              Agents
            </ToggleGroupItem>
            <ToggleGroupItem value="user" className="px-3">
              <User className="mr-1 h-3 w-3" />
              You
            </ToggleGroupItem>
            <ToggleGroupItem value="system" className="px-3">
              <Zap className="mr-1 h-3 w-3" />
              System
            </ToggleGroupItem>
          </ToggleGroup>

          {/* Project Filter */}
          <Select value={projectFilter} onValueChange={setProjectFilter}>
            <SelectTrigger className="w-[160px]">
              <SelectValue placeholder="Project" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Projects</SelectItem>
              <SelectItem value="system">System Events</SelectItem>
              {projects.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Activity Feed */}
      <ScrollArea className="flex-1 px-6 py-4">
        <div className="max-w-3xl mx-auto space-y-6">
          {groupedActivities.map((group) => (
            <div key={group.label}>
              <h2 className="text-sm font-medium text-muted-foreground mb-3 sticky top-0 bg-background py-1">
                {group.label}
              </h2>
              <div className="space-y-3">
                {group.activities.map((activity) => {
                  const config =
                    activityTypeConfig[activity.type] ||
                    activityTypeConfig.default;
                  const ActivityIcon = config.icon;

                  return (
                    <Card
                      key={activity.id}
                      className="group hover:border-primary/30 transition-colors"
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start gap-4">
                          {/* Avatar */}
                          <Avatar className="h-9 w-9">
                            <AvatarFallback
                              className={
                                activity.actor.type === "user"
                                  ? "bg-primary text-primary-foreground"
                                  : activity.actor.type === "agent"
                                    ? "bg-muted"
                                    : "bg-muted"
                              }
                            >
                              {activity.actor.avatar}
                            </AvatarFallback>
                          </Avatar>

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <div className="flex items-center gap-2">
                                  <span className="font-medium">
                                    {activity.actor.name}
                                  </span>
                                  {activity.actor.type === "agent" && (
                                    <Badge
                                      variant="outline"
                                      className="text-xs"
                                    >
                                      <Bot className="mr-1 h-3 w-3" />
                                      Agent
                                    </Badge>
                                  )}
                                </div>
                                <p className="text-sm text-muted-foreground">
                                  {activity.description}
                                </p>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0">
                                <div
                                  className={`flex h-6 w-6 items-center justify-center rounded-full ${config.bg}`}
                                >
                                  <ActivityIcon
                                    className={`h-3 w-3 ${config.color}`}
                                  />
                                </div>
                                <span className="text-xs text-muted-foreground">
                                  {formatTimeAgo(activity.timestamp)}
                                </span>
                              </div>
                            </div>

                            {/* Metadata */}
                            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                              <Badge
                                variant="secondary"
                                className={`${config.bg} ${config.color} border-0`}
                              >
                                {config.label}
                              </Badge>
                              {activity.project && (
                                <Badge variant="outline">
                                  {activity.project}
                                </Badge>
                              )}

                              {/* File edit event - render FileChangeCard */}
                              {(activity.type === "SANDBOX_agent.file_edited" ||
                                activity.type === "agent.file_edited" ||
                                activity.metadata?.original_event_type ===
                                  "agent.file_edited") && (
                                <div className="mt-3 w-full">
                                  <FileChangeCard
                                    event={{
                                      event_type: activity.type as
                                        | "agent.file_edited"
                                        | "SANDBOX_agent.file_edited",
                                      event_data: {
                                        file_path:
                                          activity.metadata?.file_path || "",
                                        change_type:
                                          activity.metadata?.change_type ||
                                          "modified",
                                        lines_added:
                                          activity.metadata?.lines_added || 0,
                                        lines_removed:
                                          activity.metadata?.lines_removed || 0,
                                        diff_preview:
                                          activity.metadata?.diff_preview || "",
                                        full_diff: activity.metadata?.full_diff,
                                        full_diff_available:
                                          activity.metadata
                                            ?.full_diff_available || false,
                                        full_diff_size:
                                          activity.metadata?.full_diff_size,
                                        turn: activity.metadata?.turn,
                                        tool_use_id:
                                          activity.metadata?.tool_use_id,
                                      },
                                    }}
                                  />
                                </div>
                              )}

                              {/* Type-specific metadata */}
                              {(activity.type === "COMMIT_LINKED" ||
                                activity.type === "commit") &&
                                activity.metadata.commit_sha && (
                                  <span className="text-muted-foreground font-mono">
                                    {String(
                                      activity.metadata.commit_sha,
                                    ).substring(0, 7)}
                                  </span>
                                )}
                              {(activity.type === "TASK_COMPLETED" ||
                                activity.type === "task_complete") &&
                                activity.metadata.task_id && (
                                  <span className="text-muted-foreground">
                                    Task: {String(activity.metadata.task_id)}
                                  </span>
                                )}
                              {(activity.type === "TICKET_TRANSITION" ||
                                activity.type === "ticket_status") &&
                                activity.metadata.from_status && (
                                  <span className="text-muted-foreground">
                                    {String(activity.metadata.from_status)} →{" "}
                                    {String(activity.metadata.to_status)}
                                  </span>
                                )}
                              {activity.type === "AGENT_REGISTERED" &&
                                activity.metadata.agent_type && (
                                  <span className="text-muted-foreground">
                                    Type: {String(activity.metadata.agent_type)}
                                  </span>
                                )}
                              {(activity.type === "ERROR" ||
                                activity.type === "error") &&
                                activity.metadata.error_type && (
                                  <span className="text-red-600 font-mono">
                                    {String(activity.metadata.error_type)}
                                  </span>
                                )}
                              {activity.metadata.ticket_id && (
                                <span className="text-muted-foreground">
                                  Ticket: {String(activity.metadata.ticket_id)}
                                </span>
                              )}
                            </div>

                            {/* Message/content preview */}
                            {activity.metadata.message && (
                              <div className="mt-2 p-2 rounded bg-muted/50 text-sm">
                                {String(activity.metadata.message)}
                              </div>
                            )}

                            {/* Commit message */}
                            {(activity.type === "COMMIT_LINKED" ||
                              activity.type === "commit") &&
                              activity.metadata.commit_message && (
                                <div className="mt-2 text-xs text-muted-foreground">
                                  {String(activity.metadata.commit_message)}
                                </div>
                              )}
                          </div>

                          {/* Link */}
                          {activity.link && activity.link !== "#" && (
                            <Button
                              variant="ghost"
                              size="icon"
                              className="opacity-0 group-hover:opacity-100 transition-opacity"
                              asChild
                            >
                              <Link href={activity.link}>
                                <ExternalLink className="h-4 w-4" />
                              </Link>
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            </div>
          ))}

          {filteredActivities.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              {isConnected ? (
                <div className="space-y-2">
                  <Wifi className="h-8 w-8 mx-auto opacity-50" />
                  <p>Listening for events...</p>
                  <p className="text-xs">
                    Activities will appear here as they happen
                  </p>
                </div>
              ) : isConnecting ? (
                <div className="space-y-2">
                  <Wifi className="h-8 w-8 mx-auto opacity-50 animate-pulse" />
                  <p>Connecting to event stream...</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <WifiOff className="h-8 w-8 mx-auto opacity-50" />
                  <p>Not connected</p>
                  <p className="text-xs">Enable live mode to receive events</p>
                </div>
              )}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

function ActivityPageLoading() {
  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      <div className="flex-shrink-0 border-b bg-background px-6 py-4">
        <div className="flex items-start justify-between">
          <div className="space-y-2">
            <Skeleton className="h-6 w-48" />
            <Skeleton className="h-4 w-64" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-8 w-24" />
            <Skeleton className="h-8 w-16" />
          </div>
        </div>
      </div>
      <div className="flex-shrink-0 border-b bg-muted/30 px-6 py-3">
        <div className="flex items-center gap-3">
          <Skeleton className="h-9 w-64" />
          <Skeleton className="h-9 w-32" />
          <Skeleton className="h-9 w-48" />
        </div>
      </div>
      <div className="flex-1 px-6 py-4">
        <div className="max-w-3xl mx-auto space-y-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
      </div>
    </div>
  );
}

export default function ActivityPage() {
  return (
    <Suspense fallback={<ActivityPageLoading />}>
      <ActivityPageContent />
    </Suspense>
  );
}
