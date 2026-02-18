"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import {
  FileText,
  Bot,
  Ticket,
  GitCommit,
  TrendingUp,
  TrendingDown,
  ArrowRight,
} from "lucide-react";

const stats = [
  {
    label: "Active Specs",
    value: 5,
    icon: FileText,
    trend: "up",
    change: "+2",
  },
  { label: "Active Agents", value: 3, icon: Bot, trend: "up", change: "+1" },
  {
    label: "Open Tickets",
    value: 12,
    icon: Ticket,
    trend: "down",
    change: "-3",
  },
  {
    label: "Commits (7d)",
    value: 28,
    icon: GitCommit,
    trend: "up",
    change: "+12",
  },
];

const recentActivity = [
  {
    type: "agent",
    message: "Agent completed: Fix groq integration",
    time: "2h ago",
  },
  { type: "commit", message: "Merged PR #142 to main", time: "3h ago" },
  { type: "spec", message: "Spec approved: Auth System", time: "5h ago" },
  {
    type: "agent",
    message: "Agent started: Improve performance",
    time: "6h ago",
  },
];

export function AnalyticsPanel() {
  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b p-3">
        <h3 className="font-semibold">Quick Stats</h3>
        <p className="text-xs text-muted-foreground">Last 7 days</p>
      </div>

      {/* Stats */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {/* Stat Cards */}
          <div className="grid grid-cols-2 gap-2">
            {stats.map((stat) => {
              const Icon = stat.icon;
              return (
                <Card key={stat.label} className="p-3">
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <span className="text-xs text-muted-foreground">
                      {stat.label}
                    </span>
                  </div>
                  <div className="mt-1 flex items-baseline gap-2">
                    <span className="text-xl font-bold">{stat.value}</span>
                    <span
                      className={`flex items-center text-xs ${
                        stat.trend === "up"
                          ? "text-success"
                          : "text-destructive"
                      }`}
                    >
                      {stat.trend === "up" ? (
                        <TrendingUp className="mr-0.5 h-3 w-3" />
                      ) : (
                        <TrendingDown className="mr-0.5 h-3 w-3" />
                      )}
                      {stat.change}
                    </span>
                  </div>
                </Card>
              );
            })}
          </div>

          {/* Completion Progress */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-muted-foreground">Sprint Progress</span>
              <span className="font-medium">68%</span>
            </div>
            <Progress value={68} className="h-2" />
          </div>

          {/* Recent Activity */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Recent Activity</h4>
            <div className="space-y-2">
              {recentActivity.map((item, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 rounded-md p-2 text-xs hover:bg-accent transition-colors"
                >
                  <span
                    className={`mt-0.5 h-1.5 w-1.5 rounded-full shrink-0 ${
                      item.type === "agent"
                        ? "bg-primary"
                        : item.type === "commit"
                          ? "bg-success"
                          : "bg-info"
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="truncate">{item.message}</p>
                    <p className="text-muted-foreground">{item.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t p-3">
        <Link
          href="/analytics"
          className="flex items-center justify-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          View full dashboard <ArrowRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}
