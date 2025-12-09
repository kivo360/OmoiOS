"use client"

import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Separator } from "@/components/ui/separator"

const shortcuts = [
  { label: "Overview", href: "/health" },
  { label: "Trajectories", href: "/health/trajectories" },
  { label: "Interventions", href: "/health/interventions" },
  { label: "Settings", href: "/health/settings" },
]

const mockSummary = {
  alignment: "86%",
  activeAgents: 7,
  openAlerts: 3,
  interventions24h: 12,
}

export function HealthPanel() {
  return (
    <div className="flex h-full flex-col">
      <div className="p-4 pb-2">
        <h2 className="text-sm font-semibold">System Health</h2>
        <p className="text-xs text-muted-foreground">Guardian, trajectories, interventions</p>
      </div>

      <div className="px-4 pb-3">
        <Card>
          <CardContent className="p-3 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Avg alignment</span>
              <Badge variant="secondary">{mockSummary.alignment}</Badge>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Active agents</span>
              <span className="font-medium">{mockSummary.activeAgents}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Interventions (24h)</span>
              <span className="font-medium">{mockSummary.interventions24h}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-muted-foreground">Open alerts</span>
              <Badge variant="destructive">{mockSummary.openAlerts}</Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      <Separator />

      <div className="flex-1 overflow-auto px-2 py-3 space-y-1.5">
        {shortcuts.map((item) => (
          <Button key={item.href} variant="ghost" className="w-full justify-start" asChild>
            <Link href={item.href}>{item.label}</Link>
          </Button>
        ))}
      </div>
    </div>
  )
}

