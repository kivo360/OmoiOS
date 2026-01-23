"use client"

import Link from "next/link"
import { Button } from "@/components/ui/button"
import { ResourceMonitor } from "@/components/resource-monitor"
import { ArrowLeft } from "lucide-react"

export default function ResourceMonitorPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <Button asChild variant="ghost" size="sm">
          <Link href="/health">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Health
          </Link>
        </Button>
        <div className="text-right">
          <h1 className="text-2xl font-bold">Resource Monitor</h1>
          <p className="text-muted-foreground">
            Monitor and adjust CPU, memory, and disk allocation per worker
          </p>
        </div>
      </div>

      <ResourceMonitor />
    </div>
  )
}
