"use client"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"
import { Zap, FileText } from "lucide-react"

export type WorkflowMode = "quick" | "spec_driven"

export interface WorkflowModeOption {
  id: WorkflowMode
  name: string
  description: string
  icon: React.ComponentType<{ className?: string }>
  placeholder: string
  helperText: string
  submitLabel: string
}

export const workflowModes: WorkflowModeOption[] = [
  {
    id: "quick",
    name: "Quick",
    description: "Immediate implementation",
    icon: Zap,
    placeholder: "Describe what you want to build...",
    helperText: "Agent will immediately start implementing your request",
    submitLabel: "Launch",
  },
  {
    id: "spec_driven",
    name: "Spec-Driven",
    description: "Plan first, then build",
    icon: FileText,
    placeholder: "Describe the feature to plan...",
    helperText: "We'll generate requirements & design for your approval",
    submitLabel: "Create Spec",
  },
]

interface WorkflowModeSelectorProps {
  value?: WorkflowMode
  onValueChange?: (value: WorkflowMode) => void
  className?: string
}

export function WorkflowModeSelector({
  value = "quick",
  onValueChange,
  className,
}: WorkflowModeSelectorProps) {
  const handleChange = (newValue: string) => {
    onValueChange?.(newValue as WorkflowMode)
  }

  const selectedMode = workflowModes.find((m) => m.id === value) || workflowModes[0]

  return (
    <Select value={value} onValueChange={handleChange}>
      <SelectTrigger className={cn("w-[160px] h-8 text-sm", className)}>
        <SelectValue>
          <div className="flex items-center gap-2">
            <selectedMode.icon className="h-3.5 w-3.5" />
            <span>{selectedMode.name}</span>
          </div>
        </SelectValue>
      </SelectTrigger>
      <SelectContent>
        {workflowModes.map((mode) => {
          const Icon = mode.icon
          return (
            <SelectItem key={mode.id} value={mode.id}>
              <div className="flex items-center gap-2">
                <Icon className="h-3.5 w-3.5" />
                <span>{mode.name}</span>
                <span className="text-xs text-muted-foreground">
                  ({mode.description})
                </span>
              </div>
            </SelectItem>
          )
        })}
      </SelectContent>
    </Select>
  )
}

// Helper to get mode config
export function getWorkflowModeConfig(mode: WorkflowMode): WorkflowModeOption {
  return workflowModes.find((m) => m.id === mode) || workflowModes[0]
}
