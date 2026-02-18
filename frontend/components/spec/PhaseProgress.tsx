"use client";

import { cn } from "@/lib/utils";
import {
  Search,
  FileText,
  ClipboardList,
  Palette,
  ListTodo,
  RefreshCw,
  CheckCircle,
  Loader2,
  Circle,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface PhaseProgressProps {
  currentPhase: string;
  status: string;
  className?: string;
  showLabels?: boolean;
  size?: "sm" | "md" | "lg";
}

// Spec phases in order (6 phases)
const phases = [
  {
    id: "explore",
    label: "Explore",
    icon: Search,
    description: "Exploring codebase and gathering context",
  },
  {
    id: "prd",
    label: "PRD",
    icon: ClipboardList,
    description: "Creating Product Requirements Document",
  },
  {
    id: "requirements",
    label: "Requirements",
    icon: FileText,
    description: "Defining EARS-format requirements",
  },
  {
    id: "design",
    label: "Design",
    icon: Palette,
    description: "Creating architecture and data models",
  },
  {
    id: "tasks",
    label: "Tasks",
    icon: ListTodo,
    description: "Breaking down into implementation tasks",
  },
  {
    id: "sync",
    label: "Sync",
    icon: RefreshCw,
    description: "Syncing tasks to execution system",
  },
] as const;

type PhaseId = (typeof phases)[number]["id"];

function getPhaseIndex(phaseId: string): number {
  return phases.findIndex((p) => p.id === phaseId.toLowerCase());
}

function getPhaseStatus(
  phaseId: PhaseId,
  currentPhase: string,
  specStatus: string,
): "completed" | "current" | "pending" | "failed" {
  const currentIndex = getPhaseIndex(currentPhase);
  const phaseIndex = phases.findIndex((p) => p.id === phaseId);

  // If spec failed, current phase is failed
  if (specStatus === "failed" && phaseIndex === currentIndex) {
    return "failed";
  }

  // If spec completed, all phases are done
  if (specStatus === "completed") {
    return "completed";
  }

  if (phaseIndex < currentIndex) {
    return "completed";
  } else if (phaseIndex === currentIndex) {
    return "current";
  }
  return "pending";
}

const sizeConfig = {
  sm: {
    icon: "h-4 w-4",
    circle: "w-6 h-6",
    connector: "w-6 h-0.5",
    text: "text-[10px]",
    gap: "gap-1",
  },
  md: {
    icon: "h-4 w-4",
    circle: "w-8 h-8",
    connector: "w-8 h-0.5",
    text: "text-xs",
    gap: "gap-2",
  },
  lg: {
    icon: "h-5 w-5",
    circle: "w-10 h-10",
    connector: "w-12 h-1",
    text: "text-sm",
    gap: "gap-3",
  },
};

export function PhaseProgress({
  currentPhase,
  status,
  className,
  showLabels = true,
  size = "md",
}: PhaseProgressProps) {
  const config = sizeConfig[size];

  return (
    <TooltipProvider>
      <div className={cn("flex items-center", config.gap, className)}>
        {phases.map((phase, idx) => {
          const phaseStatus = getPhaseStatus(phase.id, currentPhase, status);
          const Icon = phase.icon;
          const isLast = idx === phases.length - 1;

          return (
            <div key={phase.id} className="flex items-center">
              <Tooltip>
                <TooltipTrigger asChild>
                  <div className="flex flex-col items-center gap-1">
                    <div
                      className={cn(
                        config.circle,
                        "rounded-full flex items-center justify-center transition-all duration-300",
                        phaseStatus === "completed" &&
                          "bg-green-500 text-white",
                        phaseStatus === "current" &&
                          "bg-blue-500 text-white ring-2 ring-blue-200",
                        phaseStatus === "pending" &&
                          "bg-muted text-muted-foreground",
                        phaseStatus === "failed" && "bg-red-500 text-white",
                      )}
                    >
                      {phaseStatus === "completed" ? (
                        <CheckCircle className={config.icon} />
                      ) : phaseStatus === "current" ? (
                        <Loader2 className={cn(config.icon, "animate-spin")} />
                      ) : phaseStatus === "failed" ? (
                        <Circle className={config.icon} />
                      ) : (
                        <Icon className={config.icon} />
                      )}
                    </div>
                    {showLabels && (
                      <span
                        className={cn(
                          config.text,
                          "font-medium transition-colors",
                          phaseStatus === "completed" && "text-green-600",
                          phaseStatus === "current" && "text-blue-600",
                          phaseStatus === "pending" && "text-muted-foreground",
                          phaseStatus === "failed" && "text-red-600",
                        )}
                      >
                        {phase.label}
                      </span>
                    )}
                  </div>
                </TooltipTrigger>
                <TooltipContent side="bottom">
                  <div className="text-xs">
                    <p className="font-medium">{phase.label}</p>
                    <p className="text-muted-foreground">{phase.description}</p>
                    <p className="mt-1 capitalize text-[10px]">
                      Status: {phaseStatus}
                    </p>
                  </div>
                </TooltipContent>
              </Tooltip>

              {/* Connector line */}
              {!isLast && (
                <div
                  className={cn(
                    config.connector,
                    "transition-colors duration-300",
                    showLabels ? "mt-[-20px]" : "",
                    phaseStatus === "completed" ? "bg-green-500" : "bg-muted",
                  )}
                />
              )}
            </div>
          );
        })}
      </div>
    </TooltipProvider>
  );
}

// Compact inline version for tight spaces
export function PhaseProgressInline({
  currentPhase,
  status,
  className,
}: Omit<PhaseProgressProps, "showLabels" | "size">) {
  const currentIndex = getPhaseIndex(currentPhase);
  const totalPhases = phases.length;

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <div className="flex items-center gap-0.5">
        {phases.map((phase, idx) => {
          const phaseStatus = getPhaseStatus(phase.id, currentPhase, status);
          return (
            <div
              key={phase.id}
              className={cn(
                "w-2 h-2 rounded-full transition-colors",
                phaseStatus === "completed" && "bg-green-500",
                phaseStatus === "current" && "bg-blue-500 animate-pulse",
                phaseStatus === "pending" && "bg-muted",
                phaseStatus === "failed" && "bg-red-500",
              )}
            />
          );
        })}
      </div>
      <span className="text-xs text-muted-foreground">
        {status === "completed" ? (
          "Complete"
        ) : status === "failed" ? (
          "Failed"
        ) : (
          <>
            {currentIndex + 1}/{totalPhases} •{" "}
            <span className="capitalize">{currentPhase}</span>
          </>
        )}
      </span>
    </div>
  );
}
