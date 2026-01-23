"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"
import { Slider } from "@/components/ui/slider"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  useSandboxResources,
  useResourceSummary,
  useUpdateSandboxAllocation,
} from "@/hooks/useResources"
import { Cpu, HardDrive, MemoryStick, ChevronDown, ChevronRight, RefreshCw } from "lucide-react"

interface ResourceSliderProps {
  label: string
  icon: React.ReactNode
  value: number
  onChange: (value: number) => void
  min: number
  max: number
  step: number
  unit: string
  currentUsage?: number
  currentUsageLabel?: string
}

function ResourceSlider({
  label,
  icon,
  value,
  onChange,
  min,
  max,
  step,
  unit,
  currentUsage,
  currentUsageLabel,
}: ResourceSliderProps) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="flex items-center gap-2 text-sm">
          {icon}
          {label}
        </Label>
        <span className="text-sm font-medium">
          {value} {unit}
        </span>
      </div>
      <Slider
        value={[value]}
        onValueChange={(v) => onChange(v[0])}
        min={min}
        max={max}
        step={step}
        className="w-full"
      />
      {currentUsage !== undefined && (
        <div className="space-y-1">
          <Progress value={currentUsage} className="h-1.5" />
          <p className="text-xs text-muted-foreground">
            {currentUsageLabel || `${currentUsage.toFixed(1)}% used`}
          </p>
        </div>
      )}
    </div>
  )
}

interface SandboxResourceCardProps {
  sandbox: {
    sandbox_id: string
    task_id: string | null
    agent_id: string | null
    allocation: {
      cpu_cores: number
      memory_gb: number
      disk_gb: number
    }
    usage: {
      cpu_usage_percent: number
      memory_usage_percent: number
      memory_used_mb: number
      disk_usage_percent: number
      disk_used_gb: number
    }
    status: string
    last_updated: string
  }
}

function SandboxResourceCard({ sandbox }: SandboxResourceCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [cpuCores, setCpuCores] = useState(sandbox.allocation.cpu_cores)
  const [memoryGb, setMemoryGb] = useState(sandbox.allocation.memory_gb)
  const [diskGb, setDiskGb] = useState(sandbox.allocation.disk_gb)
  const [hasChanges, setHasChanges] = useState(false)

  const updateAllocation = useUpdateSandboxAllocation()

  const handleCpuChange = (value: number) => {
    setCpuCores(value)
    setHasChanges(value !== sandbox.allocation.cpu_cores || memoryGb !== sandbox.allocation.memory_gb || diskGb !== sandbox.allocation.disk_gb)
  }

  const handleMemoryChange = (value: number) => {
    setMemoryGb(value)
    setHasChanges(cpuCores !== sandbox.allocation.cpu_cores || value !== sandbox.allocation.memory_gb || diskGb !== sandbox.allocation.disk_gb)
  }

  const handleDiskChange = (value: number) => {
    setDiskGb(value)
    setHasChanges(cpuCores !== sandbox.allocation.cpu_cores || memoryGb !== sandbox.allocation.memory_gb || value !== sandbox.allocation.disk_gb)
  }

  const handleApplyChanges = async () => {
    try {
      await updateAllocation.mutateAsync({
        sandboxId: sandbox.sandbox_id,
        allocation: {
          cpu_cores: cpuCores,
          memory_gb: memoryGb,
          disk_gb: diskGb,
        },
      })
      setHasChanges(false)
    } catch (error) {
      console.error("Failed to update allocation:", error)
    }
  }

  const handleReset = () => {
    setCpuCores(sandbox.allocation.cpu_cores)
    setMemoryGb(sandbox.allocation.memory_gb)
    setDiskGb(sandbox.allocation.disk_gb)
    setHasChanges(false)
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "running":
        return "bg-green-500"
      case "creating":
        return "bg-yellow-500"
      case "completed":
        return "bg-blue-500"
      case "failed":
      case "terminated":
        return "bg-red-500"
      default:
        return "bg-gray-500"
    }
  }

  const getUsageColor = (percent: number) => {
    if (percent >= 90) return "destructive"
    if (percent >= 70) return "secondary"
    return "default"
  }

  return (
    <Card className="mb-3">
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer py-3 px-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {isOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
                <div>
                  <CardTitle className="text-sm font-medium">
                    {sandbox.sandbox_id.slice(0, 12)}...
                  </CardTitle>
                  <CardDescription className="text-xs">
                    {sandbox.task_id ? `Task: ${sandbox.task_id.slice(0, 8)}...` : "No task"}
                  </CardDescription>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant={getUsageColor(sandbox.usage.cpu_usage_percent)} className="text-xs">
                  CPU {sandbox.usage.cpu_usage_percent.toFixed(0)}%
                </Badge>
                <Badge variant={getUsageColor(sandbox.usage.memory_usage_percent)} className="text-xs">
                  MEM {sandbox.usage.memory_usage_percent.toFixed(0)}%
                </Badge>
                <div className={`h-2 w-2 rounded-full ${getStatusColor(sandbox.status)}`} />
              </div>
            </div>
          </CardHeader>
        </CollapsibleTrigger>
        <CollapsibleContent>
          <CardContent className="pt-0 px-4 pb-4 space-y-4">
            <div className="grid grid-cols-3 gap-4 text-xs text-muted-foreground">
              <div>
                <span className="block font-medium text-foreground">Status</span>
                <span className="capitalize">{sandbox.status}</span>
              </div>
              <div>
                <span className="block font-medium text-foreground">Agent</span>
                <span>{sandbox.agent_id?.slice(0, 8) || "None"}...</span>
              </div>
              <div>
                <span className="block font-medium text-foreground">Updated</span>
                <span>{new Date(sandbox.last_updated).toLocaleTimeString()}</span>
              </div>
            </div>

            <Separator />

            <div className="space-y-4">
              <h4 className="text-sm font-medium">Resource Allocation</h4>

              <ResourceSlider
                label="CPU Cores"
                icon={<Cpu className="h-4 w-4" />}
                value={cpuCores}
                onChange={handleCpuChange}
                min={1}
                max={4}
                step={1}
                unit="cores"
                currentUsage={sandbox.usage.cpu_usage_percent}
              />

              <ResourceSlider
                label="Memory"
                icon={<MemoryStick className="h-4 w-4" />}
                value={memoryGb}
                onChange={handleMemoryChange}
                min={1}
                max={8}
                step={1}
                unit="GB"
                currentUsage={sandbox.usage.memory_usage_percent}
                currentUsageLabel={`${sandbox.usage.memory_used_mb.toFixed(0)} MB used (${sandbox.usage.memory_usage_percent.toFixed(1)}%)`}
              />

              <ResourceSlider
                label="Disk"
                icon={<HardDrive className="h-4 w-4" />}
                value={diskGb}
                onChange={handleDiskChange}
                min={1}
                max={10}
                step={1}
                unit="GB"
                currentUsage={sandbox.usage.disk_usage_percent}
                currentUsageLabel={`${sandbox.usage.disk_used_gb.toFixed(1)} GB used (${sandbox.usage.disk_usage_percent.toFixed(1)}%)`}
              />
            </div>

            {hasChanges && (
              <div className="flex gap-2 pt-2">
                <Button
                  size="sm"
                  onClick={handleApplyChanges}
                  disabled={updateAllocation.isPending}
                >
                  {updateAllocation.isPending ? (
                    <>
                      <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                      Applying...
                    </>
                  ) : (
                    "Apply Changes"
                  )}
                </Button>
                <Button size="sm" variant="outline" onClick={handleReset}>
                  Reset
                </Button>
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}

export function ResourceMonitorPanel() {
  const { data: sandboxes, isLoading: sandboxesLoading, refetch } = useSandboxResources()
  const { data: summary, isLoading: summaryLoading } = useResourceSummary()

  const isLoading = sandboxesLoading || summaryLoading

  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-20 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="p-4 pb-2">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold">Resource Monitor</h2>
            <p className="text-xs text-muted-foreground">CPU, Memory, Disk per sandbox</p>
          </div>
          <Button variant="ghost" size="sm" onClick={() => refetch()}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {/* Summary Card */}
      <div className="px-4 pb-3">
        <Card>
          <CardContent className="p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Active Sandboxes</span>
              <span className="font-medium">{summary?.total_sandboxes ?? 0}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Total CPU Allocated</span>
              <span className="font-medium">{summary?.total_cpu_allocated ?? 0} cores</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Avg CPU Usage</span>
              <Badge variant={summary && summary.avg_cpu_usage_percent > 80 ? "destructive" : "secondary"}>
                {summary?.avg_cpu_usage_percent.toFixed(1) ?? 0}%
              </Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Total Memory</span>
              <span className="font-medium">{summary?.total_memory_allocated_gb ?? 0} GB</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Avg Memory Usage</span>
              <Badge variant={summary && summary.avg_memory_usage_percent > 80 ? "destructive" : "secondary"}>
                {summary?.avg_memory_usage_percent.toFixed(1) ?? 0}%
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Separator />

      {/* Sandbox List */}
      <div className="flex-1 overflow-auto px-4 py-3">
        {!sandboxes || sandboxes.length === 0 ? (
          <div className="text-center py-8 text-sm text-muted-foreground">
            No active sandboxes
          </div>
        ) : (
          sandboxes.map((sandbox) => (
            <SandboxResourceCard key={sandbox.sandbox_id} sandbox={sandbox} />
          ))
        )}
      </div>
    </div>
  )
}
