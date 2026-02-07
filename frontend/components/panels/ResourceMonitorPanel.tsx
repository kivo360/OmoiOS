"use client"

import { useState } from "react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import { Slider } from "@/components/ui/slider"
import { Separator } from "@/components/ui/separator"
import {
  useResources,
  useResourceSummary,
  useResourceLimits,
  useUpdateAllocation,
} from "@/hooks/useResources"
import type { ResourceStatus, UpdateAllocationRequest } from "@/lib/api/resources"

// Progress bar component for resource usage
function UsageBar({
  value,
  max,
  label,
  unit,
  warningThreshold = 70,
  criticalThreshold = 90,
}: {
  value: number
  max: number
  label: string
  unit: string
  warningThreshold?: number
  criticalThreshold?: number
}) {
  const percentage = max > 0 ? (value / max) * 100 : 0
  const getColor = () => {
    if (percentage >= criticalThreshold) return "bg-red-500"
    if (percentage >= warningThreshold) return "bg-yellow-500"
    return "bg-green-500"
  }

  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {value.toFixed(1)} / {max} {unit}
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
        <div
          className={`h-full transition-all duration-300 ${getColor()}`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
    </div>
  )
}

// Allocation slider component
function AllocationSlider({
  label,
  value,
  max,
  min,
  step,
  unit,
  onChange,
  disabled,
}: {
  label: string
  value: number
  max: number
  min: number
  step: number
  unit: string
  onChange: (value: number) => void
  disabled?: boolean
}) {
  return (
    <div className="space-y-2">
      <div className="flex justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium">
          {value} {unit}
        </span>
      </div>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={([v]) => onChange(v)}
        disabled={disabled}
        className="cursor-pointer"
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>
          {min} {unit}
        </span>
        <span>
          {max} {unit}
        </span>
      </div>
    </div>
  )
}

// Individual resource card for a sandbox
function ResourceCard({
  resource,
  limits,
  onUpdateAllocation,
  isUpdating,
}: {
  resource: ResourceStatus
  limits: { max_cpu_cores: number; max_memory_mb: number; max_disk_gb: number }
  onUpdateAllocation: (sandboxId: string, allocation: UpdateAllocationRequest) => void
  isUpdating: boolean
}) {
  const [localAllocation, setLocalAllocation] = useState({
    cpu_cores: resource.allocation.cpu_cores,
    memory_mb: resource.allocation.memory_mb,
    disk_gb: resource.allocation.disk_gb,
  })

  const hasChanges =
    localAllocation.cpu_cores !== resource.allocation.cpu_cores ||
    localAllocation.memory_mb !== resource.allocation.memory_mb ||
    localAllocation.disk_gb !== resource.allocation.disk_gb

  const handleApply = () => {
    const changes: UpdateAllocationRequest = {}
    if (localAllocation.cpu_cores !== resource.allocation.cpu_cores) {
      changes.cpu_cores = localAllocation.cpu_cores
    }
    if (localAllocation.memory_mb !== resource.allocation.memory_mb) {
      changes.memory_mb = localAllocation.memory_mb
    }
    if (localAllocation.disk_gb !== resource.allocation.disk_gb) {
      changes.disk_gb = localAllocation.disk_gb
    }
    onUpdateAllocation(resource.sandbox_id, changes)
  }

  const handleReset = () => {
    setLocalAllocation({
      cpu_cores: resource.allocation.cpu_cores,
      memory_mb: resource.allocation.memory_mb,
      disk_gb: resource.allocation.disk_gb,
    })
  }

  return (
    <Card className="mb-3">
      <CardHeader className="p-3 pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium truncate">
            {resource.sandbox_id}
          </CardTitle>
          <Badge
            variant={resource.status === "active" ? "secondary" : "outline"}
            className="capitalize text-xs"
          >
            {resource.status}
          </Badge>
        </div>
        {resource.task_id && (
          <p className="text-xs text-muted-foreground truncate">
            Task: {resource.task_id}
          </p>
        )}
      </CardHeader>
      <CardContent className="p-3 pt-0 space-y-4">
        {/* Current Usage */}
        <div className="space-y-2">
          <h4 className="text-xs font-medium text-muted-foreground">Usage</h4>
          <UsageBar
            label="CPU"
            value={resource.usage.cpu_percent}
            max={100}
            unit="%"
          />
          <UsageBar
            label="Memory"
            value={resource.usage.memory_mb}
            max={resource.allocation.memory_mb}
            unit="MB"
          />
          <UsageBar
            label="Disk"
            value={resource.usage.disk_gb}
            max={resource.allocation.disk_gb}
            unit="GB"
          />
        </div>

        <Separator />

        {/* Allocation Sliders */}
        <div className="space-y-3">
          <h4 className="text-xs font-medium text-muted-foreground">
            Allocation
          </h4>
          <AllocationSlider
            label="CPU Cores"
            value={localAllocation.cpu_cores}
            min={0.5}
            max={limits.max_cpu_cores}
            step={0.5}
            unit="cores"
            onChange={(v) =>
              setLocalAllocation((prev) => ({ ...prev, cpu_cores: v }))
            }
            disabled={resource.status !== "active"}
          />
          <AllocationSlider
            label="Memory"
            value={localAllocation.memory_mb}
            min={512}
            max={limits.max_memory_mb}
            step={512}
            unit="MB"
            onChange={(v) =>
              setLocalAllocation((prev) => ({ ...prev, memory_mb: v }))
            }
            disabled={resource.status !== "active"}
          />
          <AllocationSlider
            label="Disk"
            value={localAllocation.disk_gb}
            min={1}
            max={limits.max_disk_gb}
            step={1}
            unit="GB"
            onChange={(v) =>
              setLocalAllocation((prev) => ({ ...prev, disk_gb: v }))
            }
            disabled={resource.status !== "active"}
          />
        </div>

        {/* Apply/Reset buttons */}
        {hasChanges && (
          <div className="flex gap-2 pt-2">
            <Button
              size="sm"
              className="flex-1"
              onClick={handleApply}
              disabled={isUpdating || resource.status !== "active"}
            >
              {isUpdating ? "Applying..." : "Apply"}
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={handleReset}
              disabled={isUpdating}
            >
              Reset
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Summary stats component
function SummaryStats() {
  const { data: summary, isLoading } = useResourceSummary()

  if (isLoading) {
    return (
      <Card className="mb-4">
        <CardContent className="p-3">
          <div className="space-y-2">
            <Skeleton className="h-4 w-full" />
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!summary || summary.total_sandboxes === 0) {
    return (
      <Card className="mb-4">
        <CardContent className="p-3">
          <p className="text-sm text-muted-foreground text-center">
            No active sandboxes
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="mb-4">
      <CardContent className="p-3 space-y-2">
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Active Sandboxes</span>
          <span className="font-medium">{summary.total_sandboxes}</span>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Avg CPU Usage</span>
          <Badge
            variant={summary.avg_cpu_usage_percent > 80 ? "destructive" : "secondary"}
          >
            {summary.avg_cpu_usage_percent.toFixed(1)}%
          </Badge>
        </div>
        <div className="flex justify-between text-xs">
          <span className="text-muted-foreground">Avg Memory Usage</span>
          <Badge
            variant={
              summary.avg_memory_usage_percent > 80 ? "destructive" : "secondary"
            }
          >
            {summary.avg_memory_usage_percent.toFixed(1)}%
          </Badge>
        </div>
        {summary.high_cpu_count > 0 && (
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">High CPU Sandboxes</span>
            <Badge variant="destructive">{summary.high_cpu_count}</Badge>
          </div>
        )}
        {summary.high_memory_count > 0 && (
          <div className="flex justify-between text-xs">
            <span className="text-muted-foreground">High Memory Sandboxes</span>
            <Badge variant="destructive">{summary.high_memory_count}</Badge>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Main panel component
export function ResourceMonitorPanel() {
  const { data: resources, isLoading: resourcesLoading } = useResources("active")
  const { data: limits, isLoading: limitsLoading } = useResourceLimits()
  const updateAllocation = useUpdateAllocation()

  const isLoading = resourcesLoading || limitsLoading

  const handleUpdateAllocation = (
    sandboxId: string,
    allocation: UpdateAllocationRequest
  ) => {
    updateAllocation.mutate({ sandboxId, allocation })
  }

  return (
    <div className="flex h-full flex-col">
      <div className="p-4 pb-2">
        <h2 className="text-sm font-semibold">Resource Monitor</h2>
        <p className="text-xs text-muted-foreground">
          CPU, memory, disk per worker
        </p>
      </div>

      <div className="flex-1 overflow-auto px-4 pb-4">
        {/* Summary */}
        <SummaryStats />

        {/* Resource cards */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <Card key={i}>
                <CardContent className="p-3">
                  <div className="space-y-2">
                    <Skeleton className="h-4 w-3/4" />
                    <Skeleton className="h-2 w-full" />
                    <Skeleton className="h-2 w-full" />
                    <Skeleton className="h-2 w-full" />
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : resources && resources.length > 0 ? (
          resources.map((resource) => (
            <ResourceCard
              key={resource.sandbox_id}
              resource={resource}
              limits={
                limits || { max_cpu_cores: 4, max_memory_mb: 8192, max_disk_gb: 10 }
              }
              onUpdateAllocation={handleUpdateAllocation}
              isUpdating={updateAllocation.isPending}
            />
          ))
        ) : (
          <Card>
            <CardContent className="p-6 text-center">
              <p className="text-sm text-muted-foreground">
                No active sandboxes to monitor
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Resource metrics will appear when sandboxes are running
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
