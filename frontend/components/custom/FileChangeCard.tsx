"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { FileCode, ChevronDown, ChevronUp, Download } from "lucide-react";
import { LineChanges } from "./LineChanges";
import { cn } from "@/lib/utils";

interface FileEditedEvent {
  event_type: "agent.file_edited" | "SANDBOX_agent.file_edited";
  event_data: {
    turn?: number;
    tool_use_id?: string;
    file_path: string;
    change_type: "created" | "modified";
    lines_added: number;
    lines_removed: number;
    diff_preview: string;
    full_diff?: string;
    full_diff_available?: boolean;
    full_diff_size?: number;
  };
}

interface FileChangeCardProps {
  event: FileEditedEvent;
  className?: string;
}

export function FileChangeCard({ event, className }: FileChangeCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [loadingFullDiff, setLoadingFullDiff] = useState(false);
  const [fullDiff, setFullDiff] = useState<string | null>(
    event.event_data.full_diff || null,
  );

  const {
    file_path,
    change_type,
    lines_added,
    lines_removed,
    diff_preview,
    full_diff_available,
    full_diff_size,
  } = event.event_data;

  const needsFullDiff = full_diff_available && !fullDiff && !loadingFullDiff;
  const displayDiff = expanded && fullDiff ? fullDiff : diff_preview;

  const loadFullDiff = async () => {
    if (needsFullDiff && event.event_data.tool_use_id) {
      setLoadingFullDiff(true);
      try {
        // TODO: Implement API endpoint for fetching full diff
        // For now, we'll use the preview if full diff isn't available
        // const response = await fetch(
        //   `/api/v1/sandboxes/${sandboxId}/file-diffs/${event.event_data.tool_use_id}`
        // )
        // const data = await response.json()
        // setFullDiff(data.diff)
        setLoadingFullDiff(false);
      } catch (error) {
        console.error("Failed to load full diff:", error);
        setLoadingFullDiff(false);
      }
    }
  };

  const handleExpand = () => {
    if (!expanded) {
      setExpanded(true);
      if (needsFullDiff) {
        loadFullDiff();
      }
    } else {
      setExpanded(false);
    }
  };

  // Extract filename from path
  const filename = file_path.split("/").pop() || file_path;
  const fileExtension = filename.split(".").pop() || "";

  return (
    <Card className={cn("w-full", className)}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <FileCode className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="font-mono text-sm truncate" title={file_path}>
              {filename}
            </span>
            <Badge
              variant={change_type === "created" ? "default" : "secondary"}
              className="shrink-0"
            >
              {change_type === "created" ? "New" : "Modified"}
            </Badge>
            <LineChanges
              additions={lines_added}
              deletions={lines_removed}
              className="shrink-0"
            />
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {full_diff_available && full_diff_size && (
              <span className="text-xs text-muted-foreground">
                {full_diff_size > 1024
                  ? `${(full_diff_size / 1024).toFixed(1)}KB`
                  : `${full_diff_size}B`}
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleExpand}
              className="h-7 px-2"
            >
              {expanded ? (
                <>
                  <ChevronUp className="h-3 w-3 mr-1" />
                  Collapse
                </>
              ) : (
                <>
                  <ChevronDown className="h-3 w-3 mr-1" />
                  Expand
                </>
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      {expanded && (
        <CardContent className="pt-0">
          <ScrollArea className="max-h-[600px] w-full rounded-md border bg-muted/30">
            <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-words">
              <code>{displayDiff}</code>
            </pre>
          </ScrollArea>
          {loadingFullDiff && (
            <div className="mt-2 text-xs text-muted-foreground text-center">
              Loading full diff...
            </div>
          )}
        </CardContent>
      )}
    </Card>
  );
}
