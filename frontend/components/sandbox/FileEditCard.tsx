"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { FileCode, ChevronDown, ChevronRight, Plus, Minus } from "lucide-react";
import { Button } from "@/components/ui/button";

interface FileEditCardProps {
  filePath: string;
  linesAdded: number;
  linesRemoved: number;
  diff?: string;
  changeType?: "created" | "modified" | "deleted";
  timestamp?: string;
  className?: string;
}

export function FileEditCard({
  filePath,
  linesAdded,
  linesRemoved,
  diff,
  changeType = "modified",
  timestamp,
  className,
}: FileEditCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const fileName = filePath.split("/").pop() || filePath;

  return (
    <div className={cn("rounded-lg border bg-card overflow-hidden", className)}>
      {/* Header */}
      <div className="flex items-center gap-3 p-3">
        <FileCode className="h-4 w-4 text-blue-500 shrink-0" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium truncate">{fileName}</span>
            <span className="text-xs text-muted-foreground truncate hidden sm:inline">
              {filePath !== fileName && filePath}
            </span>
          </div>
        </div>

        {/* Line changes badge */}
        <div className="flex items-center gap-2 text-xs shrink-0">
          {linesAdded > 0 && (
            <span className="flex items-center text-green-600">
              <Plus className="h-3 w-3" />
              {linesAdded}
            </span>
          )}
          {linesRemoved > 0 && (
            <span className="flex items-center text-red-600">
              <Minus className="h-3 w-3" />
              {linesRemoved}
            </span>
          )}
          {timestamp && (
            <span className="text-muted-foreground">{timestamp}</span>
          )}
        </div>

        {/* Expand button */}
        {diff && (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2"
            onClick={() => setIsExpanded(!isExpanded)}
          >
            {isExpanded ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronRight className="h-4 w-4" />
            )}
            <span className="ml-1 text-xs">{isExpanded ? "Hide" : "View"}</span>
          </Button>
        )}
      </div>

      {/* Diff view */}
      {isExpanded && diff && (
        <div className="border-t bg-muted/30">
          <pre className="p-3 text-xs overflow-x-auto font-mono">
            {diff.split("\n").map((line, i) => (
              <div
                key={i}
                className={cn(
                  "px-2 -mx-2",
                  line.startsWith("+") &&
                    !line.startsWith("+++") &&
                    "bg-green-500/10 text-green-700 dark:text-green-400",
                  line.startsWith("-") &&
                    !line.startsWith("---") &&
                    "bg-red-500/10 text-red-700 dark:text-red-400",
                  line.startsWith("@@") &&
                    "text-blue-600 dark:text-blue-400 font-semibold mt-2",
                )}
              >
                {line}
              </div>
            ))}
          </pre>
        </div>
      )}
    </div>
  );
}
