"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Moon,
  ExternalLink,
  CheckCircle2,
  Clock,
  GitPullRequest,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableRow } from "@/components/ui/table";

interface LogEntry {
  id: string;
  timestamp: string;
  agentId: string;
  ticketId: string;
  action: string;
  status: "completed" | "in_progress" | "pr_opened";
  testCount?: number;
  prNumber?: number;
}

const mockLogEntries: LogEntry[] = [
  {
    id: "1",
    timestamp: "02:47 AM",
    agentId: "Agent-Architect",
    ticketId: "FEAT-147",
    action: "Decomposed into 5 tasks",
    status: "completed",
  },
  {
    id: "2",
    timestamp: "03:12 AM",
    agentId: "Agent-Dev-1",
    ticketId: "TASK-301",
    action: "Completed",
    status: "completed",
    testCount: 8,
  },
  {
    id: "3",
    timestamp: "03:34 AM",
    agentId: "Agent-Dev-2",
    ticketId: "TASK-302",
    action: "Completed",
    status: "completed",
    testCount: 12,
  },
  {
    id: "4",
    timestamp: "04:01 AM",
    agentId: "Agent-Dev-3",
    ticketId: "TASK-303",
    action: "In Progress",
    status: "in_progress",
  },
  {
    id: "5",
    timestamp: "04:22 AM",
    agentId: "Agent-Dev-1",
    ticketId: "TASK-304",
    action: "Completed",
    status: "completed",
    testCount: 6,
  },
  {
    id: "6",
    timestamp: "05:15 AM",
    agentId: "Agent-Orchestrator",
    ticketId: "FEAT-147",
    action: "PR Opened",
    status: "pr_opened",
    prNumber: 147,
  },
];

interface NightShiftLogProps {
  className?: string;
  autoPlay?: boolean;
}

export function NightShiftLog({
  className,
  autoPlay = true,
}: NightShiftLogProps) {
  const [visibleEntries, setVisibleEntries] = useState<number>(
    autoPlay ? 0 : mockLogEntries.length,
  );

  useEffect(() => {
    if (!autoPlay) return;

    const timer = setInterval(() => {
      setVisibleEntries((prev) => {
        if (prev >= mockLogEntries.length) {
          return prev;
        }
        return prev + 1;
      });
    }, 1500);

    return () => clearInterval(timer);
  }, [autoPlay]);

  const getStatusBadge = (entry: LogEntry) => {
    switch (entry.status) {
      case "completed":
        return (
          <Badge variant="outline" className="border-success text-success">
            <CheckCircle2 className="mr-1 h-3 w-3" />
            {entry.action}
          </Badge>
        );
      case "in_progress":
        return (
          <Badge variant="secondary">
            <div className="mr-1 h-3 w-3 animate-spin rounded-full border-2 border-warning border-t-transparent" />
            {entry.action}
          </Badge>
        );
      case "pr_opened":
        return (
          <Badge variant="outline" className="border-primary text-primary">
            <GitPullRequest className="mr-1 h-3 w-3" />
            {entry.action}
          </Badge>
        );
    }
  };

  return (
    <div
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-card",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <Moon className="h-4 w-4 text-primary" />
          <span className="font-semibold text-foreground">Night Shift</span>
          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs text-primary">
            While you slept
          </span>
        </div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>02:47 AM - 05:15 AM</span>
        </div>
      </div>

      {/* Log Entries */}
      <div className="max-h-80 overflow-y-auto">
        <Table>
          <TableBody>
            <AnimatePresence mode="popLayout">
              {mockLogEntries.slice(0, visibleEntries).map((entry) => (
                <motion.tr
                  key={entry.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3 }}
                  className="border-b transition-colors hover:bg-muted/50"
                >
                  {/* Timestamp */}
                  <TableCell className="w-20 font-mono text-xs text-muted-foreground">
                    {entry.timestamp}
                  </TableCell>

                  {/* Agent */}
                  <TableCell className="w-36">
                    <Badge variant="secondary" className="text-xs">
                      {entry.agentId}
                    </Badge>
                  </TableCell>

                  {/* Ticket */}
                  <TableCell className="w-24">
                    <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs text-foreground">
                      {entry.ticketId}
                    </span>
                  </TableCell>

                  {/* Status & Action */}
                  <TableCell>
                    <div className="flex items-center gap-2">
                      {getStatusBadge(entry)}
                      {entry.testCount && (
                        <span className="text-xs text-muted-foreground">
                          Tests: {entry.testCount}/{entry.testCount}
                        </span>
                      )}
                      {entry.prNumber && (
                        <span className="inline-flex items-center gap-1 text-xs text-primary">
                          #{entry.prNumber}
                          <ExternalLink className="h-3 w-3" />
                        </span>
                      )}
                    </div>
                  </TableCell>
                </motion.tr>
              ))}
            </AnimatePresence>
          </TableBody>
        </Table>

        {/* Loading indicator */}
        {autoPlay && visibleEntries < mockLogEntries.length && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex items-center justify-center py-4"
          >
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <div className="h-2 w-2 animate-pulse rounded-full bg-success" />
              Processing...
            </div>
          </motion.div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="border-t border-border px-4 py-3">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center gap-4">
            <span className="text-muted-foreground">
              <span className="text-success">5</span> tasks completed
            </span>
            <span className="text-muted-foreground">
              <span className="text-success">26</span> tests passing
            </span>
          </div>
          <span className="text-success">1 PR ready for review</span>
        </div>
      </div>
    </div>
  );
}
