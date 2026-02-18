"use client";

import { cn } from "@/lib/utils";
import {
  FileText,
  Terminal,
  Search,
  FolderOpen,
  Edit,
  Wrench,
  Globe,
  GitBranch,
} from "lucide-react";

interface ToolUseCardProps {
  tool: string;
  input: Record<string, unknown>;
  timestamp?: string;
  className?: string;
}

const toolConfig: Record<
  string,
  { icon: typeof Wrench; label: string; color: string }
> = {
  Read: { icon: FileText, label: "Read File", color: "text-blue-500" },
  Write: { icon: Edit, label: "Write File", color: "text-green-500" },
  Edit: { icon: Edit, label: "Edit File", color: "text-amber-500" },
  Bash: { icon: Terminal, label: "Run Command", color: "text-purple-500" },
  Glob: { icon: FolderOpen, label: "Search Files", color: "text-cyan-500" },
  Grep: { icon: Search, label: "Search Content", color: "text-orange-500" },
  WebFetch: { icon: Globe, label: "Fetch URL", color: "text-indigo-500" },
  Task: { icon: GitBranch, label: "Spawn Task", color: "text-pink-500" },
  default: { icon: Wrench, label: "Tool", color: "text-muted-foreground" },
};

export function ToolUseCard({
  tool,
  input,
  timestamp,
  className,
}: ToolUseCardProps) {
  const config = toolConfig[tool] || toolConfig.default;
  const Icon = config.icon;

  // Helper to get string value from input
  const getString = (key: string): string => {
    const value = input[key];
    return typeof value === "string" ? value : "";
  };

  // Get a summary of the input
  const getSummary = (): string => {
    if (tool === "Read" || tool === "Write" || tool === "Edit") {
      return (
        getString("filePath") ||
        getString("file_path") ||
        getString("path") ||
        "file"
      );
    }
    if (tool === "Bash") {
      const cmd = getString("command");
      return cmd.length > 60 ? cmd.slice(0, 60) + "..." : cmd;
    }
    if (tool === "Glob") {
      return getString("pattern") || "pattern";
    }
    if (tool === "Grep") {
      return getString("pattern") || "search";
    }
    if (tool === "WebFetch") {
      return getString("url") || "url";
    }
    if (tool === "Task") {
      return getString("description") || "task";
    }
    return Object.keys(input).length > 0
      ? JSON.stringify(input).slice(0, 50)
      : "";
  };

  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border bg-card p-3",
        className,
      )}
    >
      <div className={cn("mt-0.5", config.color)}>
        <Icon className="h-4 w-4" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">{config.label}</span>
          {timestamp && (
            <span className="text-xs text-muted-foreground">{timestamp}</span>
          )}
        </div>
        <p className="text-sm text-muted-foreground truncate mt-0.5">
          {getSummary()}
        </p>
      </div>
    </div>
  );
}
