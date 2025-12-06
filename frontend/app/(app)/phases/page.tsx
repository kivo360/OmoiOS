"use client"

import { useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Workflow,
  Plus,
  Search,
  Ticket,
  Bot,
  Sparkles,
  ChevronRight,
  CheckCircle2,
  Clock,
  AlertCircle,
  ArrowRight,
  Filter,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Mock phase data
const mockPhases = [
  {
    id: "PHASE_BACKLOG",
    name: "Backlog",
    description: "Initial collection point for new work items",
    order: 0,
    isTerminal: false,
    taskStats: { total: 45, done: 0, active: 0, pending: 45 },
    activeAgents: 0,
    discoveries: 0,
    transitions: ["PHASE_REQUIREMENTS", "PHASE_BLOCKED"],
    color: "#6B7280",
  },
  {
    id: "PHASE_REQUIREMENTS",
    name: "Requirements Analysis",
    description: "Gathering and documenting detailed requirements",
    order: 1,
    isTerminal: false,
    taskStats: { total: 28, done: 22, active: 2, pending: 4 },
    activeAgents: 2,
    discoveries: 3,
    transitions: ["PHASE_DESIGN", "PHASE_BLOCKED"],
    color: "#3B82F6",
  },
  {
    id: "PHASE_DESIGN",
    name: "Design",
    description: "Architecture and solution design phase",
    order: 2,
    isTerminal: false,
    taskStats: { total: 18, done: 15, active: 1, pending: 2 },
    activeAgents: 1,
    discoveries: 1,
    transitions: ["PHASE_IMPLEMENTATION", "PHASE_BLOCKED"],
    color: "#8B5CF6",
  },
  {
    id: "PHASE_IMPLEMENTATION",
    name: "Implementation",
    description: "Developing and implementing features",
    order: 3,
    isTerminal: false,
    taskStats: { total: 52, done: 38, active: 5, pending: 9 },
    activeAgents: 5,
    discoveries: 8,
    doneCriteria: ["All code files created", "Minimum 3 test cases passing"],
    expectedOutputs: ["src/**/*.py", "tests/**/*.py"],
    transitions: ["PHASE_TESTING", "PHASE_BLOCKED"],
    color: "#F59E0B",
  },
  {
    id: "PHASE_TESTING",
    name: "Testing",
    description: "Comprehensive testing and quality assurance",
    order: 4,
    isTerminal: false,
    taskStats: { total: 24, done: 20, active: 2, pending: 2 },
    activeAgents: 2,
    discoveries: 2,
    transitions: ["PHASE_DEPLOYMENT", "PHASE_IMPLEMENTATION", "PHASE_BLOCKED"],
    color: "#10B981",
  },
  {
    id: "PHASE_DEPLOYMENT",
    name: "Deployment",
    description: "Release and deployment to production",
    order: 5,
    isTerminal: false,
    taskStats: { total: 12, done: 10, active: 1, pending: 1 },
    activeAgents: 1,
    discoveries: 0,
    transitions: ["PHASE_DONE"],
    color: "#EC4899",
  },
  {
    id: "PHASE_DONE",
    name: "Done",
    description: "Completed and delivered work items",
    order: 6,
    isTerminal: true,
    taskStats: { total: 120, done: 120, active: 0, pending: 0 },
    activeAgents: 0,
    discoveries: 0,
    transitions: [],
    color: "#059669",
  },
  {
    id: "PHASE_BLOCKED",
    name: "Blocked",
    description: "Items blocked by dependencies or issues",
    order: 99,
    isTerminal: false,
    taskStats: { total: 8, done: 0, active: 0, pending: 8 },
    activeAgents: 0,
    discoveries: 0,
    transitions: ["PHASE_BACKLOG", "PHASE_REQUIREMENTS", "PHASE_DESIGN", "PHASE_IMPLEMENTATION", "PHASE_TESTING"],
    color: "#EF4444",
  },
]

export default function PhasesPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [filterStatus, setFilterStatus] = useState("all")
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  const filteredPhases = mockPhases.filter((phase) => {
    const matchesSearch = phase.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      phase.description.toLowerCase().includes(searchQuery.toLowerCase())
    
    if (filterStatus === "all") return matchesSearch
    if (filterStatus === "active") return matchesSearch && phase.activeAgents > 0
    if (filterStatus === "terminal") return matchesSearch && phase.isTerminal
    if (filterStatus === "blocked") return matchesSearch && phase.id === "PHASE_BLOCKED"
    return matchesSearch
  })

  const getCompletionPercent = (stats: typeof mockPhases[0]["taskStats"]) => {
    if (stats.total === 0) return 0
    return Math.round((stats.done / stats.total) * 100)
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Workflow Phases</h1>
          <p className="text-muted-foreground">
            Configure and manage your project workflow phases
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Custom Phase
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create Custom Phase</DialogTitle>
              <DialogDescription>
                Define a new phase for your workflow. Custom phases extend the default workflow.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="phaseId">Phase ID</Label>
                  <Input id="phaseId" placeholder="PHASE_" className="font-mono" />
                  <p className="text-xs text-muted-foreground">
                    Must start with &quot;PHASE_&quot;
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="phaseName">Display Name</Label>
                  <Input id="phaseName" placeholder="e.g., Code Review" />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="phaseDesc">Description</Label>
                <Textarea
                  id="phaseDesc"
                  placeholder="Describe what happens in this phase..."
                  rows={2}
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label htmlFor="order">Sequence Order</Label>
                  <Input id="order" type="number" min="0" defaultValue="5" />
                </div>
                <div className="flex items-center space-x-2 pt-6">
                  <Checkbox id="terminal" />
                  <Label htmlFor="terminal" className="font-normal">
                    Terminal phase (no further transitions)
                  </Label>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button onClick={() => setIsCreateOpen(false)}>Create Phase</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats Overview */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                <Workflow className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{mockPhases.length}</p>
                <p className="text-sm text-muted-foreground">Total Phases</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                <Bot className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockPhases.reduce((sum, p) => sum + p.activeAgents, 0)}
                </p>
                <p className="text-sm text-muted-foreground">Active Agents</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-500/10">
                <Sparkles className="h-5 w-5 text-purple-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockPhases.reduce((sum, p) => sum + p.discoveries, 0)}
                </p>
                <p className="text-sm text-muted-foreground">Discoveries</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10">
                <Ticket className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockPhases.reduce((sum, p) => sum + p.taskStats.total, 0)}
                </p>
                <p className="text-sm text-muted-foreground">Total Tasks</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search phases..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-[180px]">
            <Filter className="mr-2 h-4 w-4" />
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Phases</SelectItem>
            <SelectItem value="active">Active (with agents)</SelectItem>
            <SelectItem value="terminal">Terminal Only</SelectItem>
            <SelectItem value="blocked">Blocked Phase</SelectItem>
          </SelectContent>
        </Select>
        <Button variant="outline" asChild>
          <Link href="/phases/gates">
            Phase Gate Approvals
            <ChevronRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>

      {/* Phase Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {filteredPhases.map((phase) => {
          const completionPercent = getCompletionPercent(phase.taskStats)
          
          return (
            <Link key={phase.id} href={`/phases/${phase.id}`}>
              <Card className="h-full transition-all hover:shadow-md hover:border-primary/30 cursor-pointer">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className="flex h-10 w-10 items-center justify-center rounded-lg text-white font-bold text-sm"
                        style={{ backgroundColor: phase.color }}
                      >
                        {phase.order}
                      </div>
                      <div>
                        <CardTitle className="text-base">{phase.name}</CardTitle>
                        <p className="text-xs text-muted-foreground font-mono">
                          {phase.id}
                        </p>
                      </div>
                    </div>
                    {phase.isTerminal && (
                      <Badge variant="outline" className="text-xs">Terminal</Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {phase.description}
                  </p>

                  {/* Task Stats */}
                  <div className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>Tasks</span>
                      <span className="font-medium">
                        {phase.taskStats.done}/{phase.taskStats.total}
                      </span>
                    </div>
                    <Progress value={completionPercent} className="h-2" />
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-3">
                        <span className="flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3 text-green-500" />
                          {phase.taskStats.done} done
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3 text-blue-500" />
                          {phase.taskStats.active} active
                        </span>
                      </div>
                      <span>{completionPercent}%</span>
                    </div>
                  </div>

                  {/* Active Agents & Discoveries */}
                  <div className="flex items-center justify-between text-sm">
                    {phase.activeAgents > 0 ? (
                      <span className="flex items-center gap-1 text-green-600">
                        <Bot className="h-4 w-4" />
                        {phase.activeAgents} agents working
                      </span>
                    ) : (
                      <span className="text-muted-foreground">No active agents</span>
                    )}
                    {phase.discoveries > 0 && (
                      <span className="flex items-center gap-1 text-purple-600">
                        <Sparkles className="h-4 w-4" />
                        {phase.discoveries} discoveries
                      </span>
                    )}
                  </div>

                  {/* Transitions */}
                  {phase.transitions.length > 0 && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <ArrowRight className="h-3 w-3" />
                      <span className="truncate">
                        {phase.transitions.slice(0, 2).map(t => t.replace("PHASE_", "")).join(", ")}
                        {phase.transitions.length > 2 && ` +${phase.transitions.length - 2}`}
                      </span>
                    </div>
                  )}
                </CardContent>
              </Card>
            </Link>
          )
        })}
      </div>

      {/* Empty State */}
      {filteredPhases.length === 0 && (
        <Card className="py-12">
          <CardContent className="text-center">
            <Workflow className="mx-auto h-12 w-12 text-muted-foreground/50" />
            <h3 className="mt-4 font-semibold">No phases found</h3>
            <p className="text-sm text-muted-foreground">
              {searchQuery ? "Try adjusting your search criteria" : "Create a custom phase to get started"}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
