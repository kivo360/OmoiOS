"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  useResourceSummary,
  useWorkerResources,
  useSetWorkerResourceLimits,
  useResetWorkerResourceLimits,
} from "@/hooks/useResources"
import type { ResourceLimits, WorkerResourceStatus } from "@/lib/api/types"
import { Cpu, HardDrive, MemoryStick, AlertTriangle, Check, RefreshCw } from "lucide-react"
import { cn } from "@/lib/utils"

interface ResourceSliderProps {
  label: string
  icon: React.ReactNode
  value: number[]
  onChange: (value: number[]) => void
  currentUsage: number
  unit?: string
  description?: string
}

function ResourceSlider({
  label,
  icon,
  value,
  onChange,
  currentUsage,
  unit = "%",
  description,
}: ResourceSliderProps) {
  const usageColor = currentUsage > 90 ? "text-destructive" : currentUsage > 70 ? "text-warning" : "text-success"
  const progressColor = currentUsage > 90 ? "bg-destructive" : currentUsage > 70 ? "bg-warning" : "bg-success"

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {icon}
          <Label className="text-sm font-medium">{label}</Label>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("text-sm font-mono", usageColor)}>
            {currentUsage.toFixed(1)}{unit}
          </span>
          <span className="text-xs text-muted-foreground">used</span>
        </div>
      </div>

      <div className="space-y-2">
        <Progress
          value={currentUsage}
          className={cn("h-2", progressColor)}
        />

        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground w-12">Limit:</span>
          <Slider
            value={value}
            onValueChange={onChange}
            min={10}
            max={100}
            step={5}
            className="flex-1"
          />
          <span className="text-sm font-mono w-12 text-right">{value[0]}{unit}</span>
        </div>
      </div>

      {description && (
        <p className="text-xs text-muted-foreground">{description}</p>
      )}
    </div>
  )
}

interface WorkerResourceCardProps {
  worker: WorkerResourceStatus
  onSave?: (workerId: string, limits: ResourceLimits) => void
  onReset?: (workerId: string) => void
  isSaving?: boolean
}

export function WorkerResourceCard({ worker, onSave, onReset, isSaving }: WorkerResourceCardProps) {
  const [cpuLimit, setCpuLimit] = useState([worker.limits.cpu_limit_percent])
  const [memoryLimit, setMemoryLimit] = useState([worker.limits.memory_limit_percent])
  const [diskLimit, setDiskLimit] = useState([worker.limits.disk_limit_percent])
  const [hasChanges, setHasChanges] = useState(false)

  useEffect(() => {
    const changed =
      cpuLimit[0] !== worker.limits.cpu_limit_percent ||
      memoryLimit[0] !== worker.limits.memory_limit_percent ||
      diskLimit[0] !== worker.limits.disk_limit_percent
    setHasChanges(changed)
  }, [cpuLimit, memoryLimit, diskLimit, worker.limits])

  useEffect(() => {
    setCpuLimit([worker.limits.cpu_limit_percent])
    setMemoryLimit([worker.limits.memory_limit_percent])
    setDiskLimit([worker.limits.disk_limit_percent])
  }, [worker.limits])

  const handleSave = () => {
    if (onSave) {
      onSave(worker.worker_id, {
        cpu_limit_percent: cpuLimit[0],
        memory_limit_percent: memoryLimit[0],
        disk_limit_percent: diskLimit[0],
      })
    }
  }

  const handleReset = () => {
    if (onReset) {
      onReset(worker.worker_id)
    }
  }

  const statusColor = {
    healthy: "bg-success text-success-foreground",
    warning: "bg-warning text-warning-foreground",
    critical: "bg-destructive text-destructive-foreground",
  }[worker.status] || "bg-muted"

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-base">{worker.worker_id}</CardTitle>
            <CardDescription className="text-xs">
              Last updated: {new Date(worker.metrics.timestamp).toLocaleTimeString()}
            </CardDescription>
          </div>
          <Badge className={statusColor}>
            {worker.status === "healthy" && <Check className="h-3 w-3 mr-1" />}
            {worker.status === "warning" && <AlertTriangle className="h-3 w-3 mr-1" />}
            {worker.status === "critical" && <AlertTriangle className="h-3 w-3 mr-1" />}
            {worker.status}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <ResourceSlider
          label="CPU"
          icon={<Cpu className="h-4 w-4 text-muted-foreground" />}
          value={cpuLimit}
          onChange={setCpuLimit}
          currentUsage={worker.metrics.cpu_percent}
          description="Limit CPU usage for this worker"
        />

        <Separator />

        <ResourceSlider
          label="Memory"
          icon={<MemoryStick className="h-4 w-4 text-muted-foreground" />}
          value={memoryLimit}
          onChange={setMemoryLimit}
          currentUsage={worker.metrics.memory_percent}
          description={`${worker.metrics.memory_used_mb.toFixed(0)} MB / ${worker.metrics.memory_total_mb.toFixed(0)} MB`}
        />

        <Separator />

        <ResourceSlider
          label="Disk"
          icon={<HardDrive className="h-4 w-4 text-muted-foreground" />}
          value={diskLimit}
          onChange={setDiskLimit}
          currentUsage={worker.metrics.disk_percent}
          description={`${worker.metrics.disk_used_gb.toFixed(1)} GB / ${worker.metrics.disk_total_gb.toFixed(0)} GB`}
        />

        {worker.alerts.length > 0 && (
          <>
            <Separator />
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Active Alerts</Label>
              {worker.alerts.map((alert, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-destructive">
                  <AlertTriangle className="h-3 w-3" />
                  {alert}
                </div>
              ))}
            </div>
          </>
        )}

        <Separator />

        <div className="flex items-center justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={isSaving}
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Reset
          </Button>
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
          >
            {isSaving ? "Saving..." : "Apply Limits"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

interface ResourceMonitorProps {
  workerId?: string
}

export function ResourceMonitor({ workerId }: ResourceMonitorProps) {
  const { data: summary, isLoading: summaryLoading } = useResourceSummary()
  const { data: workerData, isLoading: workerLoading } = useWorkerResources(workerId || "")
  const setLimitsMutation = useSetWorkerResourceLimits()
  const resetLimitsMutation = useResetWorkerResourceLimits()

  const handleSave = (wid: string, limits: ResourceLimits) => {
    setLimitsMutation.mutate({ workerId: wid, limits })
  }

  const handleReset = (wid: string) => {
    resetLimitsMutation.mutate(wid)
  }

  // If a specific worker is requested, show just that worker
  if (workerId) {
    if (workerLoading) {
      return (
        <div className="flex items-center justify-center p-8">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
        </div>
      )
    }

    if (!workerData) {
      return (
        <div className="text-center p-8 text-muted-foreground">
          Worker not found
        </div>
      )
    }

    return (
      <WorkerResourceCard
        worker={workerData}
        onSave={handleSave}
        onReset={handleReset}
        isSaving={setLimitsMutation.isPending || resetLimitsMutation.isPending}
      />
    )
  }

  // Show all workers
  if (summaryLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!summary) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        No resource data available
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{summary.total_workers}</div>
            <div className="text-xs text-muted-foreground">Total Workers</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-success">{summary.healthy_count}</div>
            <div className="text-xs text-muted-foreground">Healthy</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-warning">{summary.warning_count}</div>
            <div className="text-xs text-muted-foreground">Warning</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold text-destructive">{summary.critical_count}</div>
            <div className="text-xs text-muted-foreground">Critical</div>
          </CardContent>
        </Card>
      </div>

      {/* Average Usage */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Average Resource Usage</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-3">
            <Cpu className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm w-16">CPU</span>
            <Progress value={summary.avg_cpu_percent} className="flex-1" />
            <span className="text-sm font-mono w-12 text-right">{summary.avg_cpu_percent.toFixed(1)}%</span>
          </div>
          <div className="flex items-center gap-3">
            <MemoryStick className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm w-16">Memory</span>
            <Progress value={summary.avg_memory_percent} className="flex-1" />
            <span className="text-sm font-mono w-12 text-right">{summary.avg_memory_percent.toFixed(1)}%</span>
          </div>
          <div className="flex items-center gap-3">
            <HardDrive className="h-4 w-4 text-muted-foreground" />
            <span className="text-sm w-16">Disk</span>
            <Progress value={summary.avg_disk_percent} className="flex-1" />
            <span className="text-sm font-mono w-12 text-right">{summary.avg_disk_percent.toFixed(1)}%</span>
          </div>
        </CardContent>
      </Card>

      {/* Worker Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {summary.workers.map((worker) => (
          <WorkerResourceCard
            key={worker.worker_id}
            worker={worker}
            onSave={handleSave}
            onReset={handleReset}
            isSaving={setLimitsMutation.isPending || resetLimitsMutation.isPending}
          />
        ))}
      </div>
    </div>
  )
}

export default ResourceMonitor
