"use client"

import { useMemo, useState } from "react"
import Link from "next/link"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Progress } from "@/components/ui/progress"
import { ArrowLeft, ArrowRight } from "lucide-react"

const trajectories = [
  { agent: "worker-1", project: "auth-system", alignment: 0.93, status: "aligned", lastEvent: "5m ago", note: "Stable" },
  { agent: "worker-2", project: "payment-gateway", alignment: 0.62, status: "drifting", lastEvent: "2m ago", note: "Investigating cache miss" },
  { agent: "worker-3", project: "api-service", alignment: 0.78, status: "warning", lastEvent: "11m ago", note: "High error retries" },
  { agent: "worker-4", project: "frontend-app", alignment: 0.88, status: "aligned", lastEvent: "9m ago", note: "Following spec" },
  { agent: "worker-5", project: "analytics", alignment: 0.55, status: "stuck", lastEvent: "18m ago", note: "Idle loop detected" },
]

const statusColor = (status: string) => {
  if (status === "aligned") return "bg-emerald-100 text-emerald-700"
  if (status === "warning") return "bg-amber-100 text-amber-700"
  if (status === "drifting") return "bg-orange-100 text-orange-700"
  return "bg-rose-100 text-rose-700"
}

export default function TrajectoriesPage() {
  const [filter, setFilter] = useState("all")
  const [search, setSearch] = useState("")

  const rows = useMemo(() => {
    return trajectories.filter((t) => {
      const matchesSearch =
        t.agent.toLowerCase().includes(search.toLowerCase()) ||
        t.project.toLowerCase().includes(search.toLowerCase())
      if (filter === "all") return matchesSearch
      return matchesSearch && t.status === filter
    })
  }, [filter, search])

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between gap-3">
        <Button asChild variant="ghost" size="sm">
          <Link href="/health">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Link>
        </Button>
        <div className="text-right">
          <h1 className="text-2xl font-bold">Trajectory Analysis</h1>
          <p className="text-muted-foreground">Alignment monitoring per agent</p>
        </div>
      </div>

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle>Active Trajectories</CardTitle>
            <CardDescription>Alignment score, drift, and idle detection</CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agent or project"
              className="w-[200px]"
            />
            <Select defaultValue="all" onValueChange={setFilter}>
              <SelectTrigger className="w-[150px]">
                <SelectValue placeholder="Filter status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="aligned">Aligned</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="drifting">Drifting</SelectItem>
                <SelectItem value="stuck">Stuck</SelectItem>
              </SelectContent>
            </Select>
            <Button asChild variant="outline">
              <Link href="/health/interventions">
                Interventions
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-12 items-center rounded-lg bg-muted px-4 py-2 text-sm font-medium text-muted-foreground">
            <div className="col-span-2">Agent</div>
            <div className="col-span-2">Project</div>
            <div className="col-span-3">Alignment</div>
            <div className="col-span-2">Status</div>
            <div className="col-span-2">Last Event</div>
            <div className="col-span-1 text-right">Action</div>
          </div>
          {rows.map((row) => (
            <div key={row.agent} className="grid grid-cols-12 items-center rounded-lg border px-4 py-3">
              <div className="col-span-2 font-medium">{row.agent}</div>
              <div className="col-span-2 text-muted-foreground">{row.project}</div>
              <div className="col-span-3 space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Score</span>
                  <span className="font-semibold">{Math.round(row.alignment * 100)}%</span>
                </div>
                <Progress value={row.alignment * 100} className="h-2" />
                <p className="text-xs text-muted-foreground">{row.note}</p>
              </div>
              <div className="col-span-2">
                <Badge className={statusColor(row.status)} variant="outline">
                  {row.status}
                </Badge>
              </div>
              <div className="col-span-2 text-sm text-muted-foreground">{row.lastEvent}</div>
              <div className="col-span-1 flex justify-end">
                <Button size="sm" variant="outline" asChild>
                  <Link href={`/agents/${row.agent}`}>Open</Link>
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

