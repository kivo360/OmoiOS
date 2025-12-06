"use client"

import { useState } from "react"
import Link from "next/link"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Separator } from "@/components/ui/separator"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
} from "@/components/ui/dialog"
import {
  ArrowLeft,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ArrowRight,
  Clock,
  Bot,
  FileCode,
  GitCommit,
  ChevronRight,
  Check,
  X,
  Eye,
} from "lucide-react"
import { cn } from "@/lib/utils"

// Mock pending approvals
const mockPendingApprovals = [
  {
    id: "gate-001",
    ticketId: "TICKET-042",
    ticketTitle: "Add OAuth2 Authentication",
    currentPhase: "PHASE_IMPLEMENTATION",
    requestedPhase: "PHASE_TESTING",
    requestedBy: "worker-agent-5",
    requestedAt: "2 hours ago",
    gateCriteria: [
      { name: "All code files created", status: "passed" },
      { name: "Minimum 3 test cases passing", status: "passed" },
      { name: "All tasks completed", status: "passed" },
      { name: "Code follows style guidelines", status: "passed" },
    ],
    artifacts: [
      { name: "Source files", pattern: "src/auth/*.py", found: 3, expected: "1+", status: "passed" },
      { name: "Test files", pattern: "tests/test_auth/*.py", found: 5, expected: "3+", status: "passed" },
    ],
    overallStatus: "passed",
    comments: [],
  },
  {
    id: "gate-002",
    ticketId: "TICKET-038",
    ticketTitle: "Setup Database Schema",
    currentPhase: "PHASE_IMPLEMENTATION",
    requestedPhase: "PHASE_TESTING",
    requestedBy: "worker-agent-3",
    requestedAt: "4 hours ago",
    gateCriteria: [
      { name: "All code files created", status: "passed" },
      { name: "Minimum 3 test cases passing", status: "failed" },
      { name: "All tasks completed", status: "passed" },
      { name: "Code follows style guidelines", status: "warning" },
    ],
    artifacts: [
      { name: "Source files", pattern: "src/db/*.py", found: 2, expected: "1+", status: "passed" },
      { name: "Test files", pattern: "tests/test_db/*.py", found: 2, expected: "3+", status: "failed" },
    ],
    overallStatus: "failed",
    missing: ["Need at least 1 more passing test case"],
    comments: [],
  },
  {
    id: "gate-003",
    ticketId: "TICKET-045",
    ticketTitle: "Implement User Profile API",
    currentPhase: "PHASE_TESTING",
    requestedPhase: "PHASE_DEPLOYMENT",
    requestedBy: "worker-agent-2",
    requestedAt: "30 minutes ago",
    gateCriteria: [
      { name: "All tests passing", status: "passed" },
      { name: "Code coverage above 80%", status: "passed" },
      { name: "No critical bugs", status: "passed" },
    ],
    artifacts: [
      { name: "Coverage report", pattern: "coverage.xml", found: 1, expected: "1", status: "passed" },
    ],
    overallStatus: "passed",
    comments: [],
  },
]

// Mock recent approvals
const mockRecentApprovals = [
  {
    id: "gate-hist-001",
    ticketId: "TICKET-035",
    ticketTitle: "Add API Keys Management",
    fromPhase: "PHASE_IMPLEMENTATION",
    toPhase: "PHASE_TESTING",
    decision: "approved",
    decidedBy: "john@example.com",
    decidedAt: "Oct 30, 2025 11:30",
    comment: "All criteria met, good work!",
  },
  {
    id: "gate-hist-002",
    ticketId: "TICKET-032",
    ticketTitle: "Setup Database Connection",
    fromPhase: "PHASE_BACKLOG",
    toPhase: "PHASE_REQUIREMENTS",
    decision: "auto-approved",
    decidedBy: "system",
    decidedAt: "Oct 30, 2025 10:15",
    comment: null,
  },
  {
    id: "gate-hist-003",
    ticketId: "TICKET-028",
    ticketTitle: "Implement Session Storage",
    fromPhase: "PHASE_IMPLEMENTATION",
    toPhase: "PHASE_TESTING",
    decision: "rejected",
    decidedBy: "jane@example.com",
    decidedAt: "Oct 29, 2025 16:45",
    comment: "Insufficient test coverage, please add more unit tests",
  },
]

export default function PhaseGatesPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [filterStatus, setFilterStatus] = useState("all")
  const [selectedApproval, setSelectedApproval] = useState<typeof mockPendingApprovals[0] | null>(null)
  const [rejectComment, setRejectComment] = useState("")

  const filteredApprovals = mockPendingApprovals.filter((approval) => {
    const matchesSearch = approval.ticketTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
      approval.ticketId.toLowerCase().includes(searchQuery.toLowerCase())
    
    if (filterStatus === "all") return matchesSearch
    if (filterStatus === "passed") return matchesSearch && approval.overallStatus === "passed"
    if (filterStatus === "failed") return matchesSearch && approval.overallStatus === "failed"
    return matchesSearch
  })

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "passed":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case "failed":
        return <XCircle className="h-4 w-4 text-red-500" />
      case "warning":
        return <AlertCircle className="h-4 w-4 text-yellow-500" />
      default:
        return <Clock className="h-4 w-4 text-muted-foreground" />
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Back Link */}
      <Link
        href="/phases"
        className="inline-flex items-center text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="mr-2 h-4 w-4" />
        Back to Phases
      </Link>

      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold">Phase Gate Approvals</h1>
        <p className="text-muted-foreground">
          Review and approve phase transition requests
        </p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-500/10">
                <Clock className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{mockPendingApprovals.length}</p>
                <p className="text-sm text-muted-foreground">Pending Approvals</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-500/10">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockPendingApprovals.filter(a => a.overallStatus === "passed").length}
                </p>
                <p className="text-sm text-muted-foreground">Ready to Approve</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10">
                <XCircle className="h-5 w-5 text-red-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">
                  {mockPendingApprovals.filter(a => a.overallStatus === "failed").length}
                </p>
                <p className="text-sm text-muted-foreground">Failed Validation</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending">
            Pending Approvals
            <Badge variant="secondary" className="ml-2">
              {mockPendingApprovals.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="recent">Recent Decisions</TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="space-y-4">
          {/* Filters */}
          <div className="flex items-center gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by ticket..."
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
                <SelectItem value="all">All Pending</SelectItem>
                <SelectItem value="passed">Validation Passed</SelectItem>
                <SelectItem value="failed">Validation Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Approval Cards */}
          <div className="space-y-4">
            {filteredApprovals.map((approval) => (
              <Card key={approval.id} className="overflow-hidden">
                <div
                  className={cn(
                    "h-1",
                    approval.overallStatus === "passed" && "bg-green-500",
                    approval.overallStatus === "failed" && "bg-red-500"
                  )}
                />
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="font-mono">
                          {approval.ticketId}
                        </Badge>
                        <CardTitle className="text-base">{approval.ticketTitle}</CardTitle>
                      </div>
                      <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Bot className="h-4 w-4" />
                          {approval.requestedBy}
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-4 w-4" />
                          {approval.requestedAt}
                        </span>
                      </div>
                    </div>
                    <Badge
                      variant={approval.overallStatus === "passed" ? "default" : "destructive"}
                    >
                      {approval.overallStatus === "passed" ? "Validation Passed" : "Validation Failed"}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Phase Transition */}
                  <div className="flex items-center gap-2 text-sm">
                    <Badge variant="secondary" className="font-mono">
                      {approval.currentPhase.replace("PHASE_", "")}
                    </Badge>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                    <Badge variant="outline" className="font-mono">
                      {approval.requestedPhase.replace("PHASE_", "")}
                    </Badge>
                  </div>

                  {/* Gate Criteria */}
                  <div className="rounded-lg border p-3 space-y-2">
                    <p className="text-sm font-medium">Gate Criteria</p>
                    <div className="grid gap-1 sm:grid-cols-2">
                      {approval.gateCriteria.map((criterion, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm">
                          {getStatusIcon(criterion.status)}
                          <span className={cn(
                            criterion.status === "failed" && "text-red-600",
                            criterion.status === "warning" && "text-yellow-600"
                          )}>
                            {criterion.name}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Artifacts */}
                  <div className="rounded-lg border p-3 space-y-2">
                    <p className="text-sm font-medium">Artifacts</p>
                    <div className="space-y-1">
                      {approval.artifacts.map((artifact, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <div className="flex items-center gap-2">
                            {getStatusIcon(artifact.status)}
                            <span>{artifact.name}</span>
                            <span className="font-mono text-muted-foreground">
                              {artifact.pattern}
                            </span>
                          </div>
                          <span className={cn(
                            artifact.status === "passed" && "text-green-600",
                            artifact.status === "failed" && "text-red-600"
                          )}>
                            Found: {artifact.found} (expected: {artifact.expected})
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Missing items */}
                  {approval.missing && approval.missing.length > 0 && (
                    <div className="rounded-lg bg-red-50 border border-red-200 p-3">
                      <p className="text-sm font-medium text-red-800">Missing Requirements:</p>
                      <ul className="mt-1 space-y-1">
                        {approval.missing.map((item, i) => (
                          <li key={i} className="flex items-center gap-2 text-sm text-red-700">
                            <XCircle className="h-3 w-3" />
                            {item}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-2 pt-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedApproval(approval)}
                    >
                      <Eye className="mr-2 h-4 w-4" />
                      Review Details
                    </Button>
                    {approval.overallStatus === "failed" && (
                      <Button variant="secondary" size="sm">
                        Approve Anyway
                      </Button>
                    )}
                    <Button variant="outline" size="sm" className="text-destructive">
                      <X className="mr-2 h-4 w-4" />
                      Reject
                    </Button>
                    <Button size="sm">
                      <Check className="mr-2 h-4 w-4" />
                      Approve
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Empty State */}
          {filteredApprovals.length === 0 && (
            <Card className="py-12">
              <CardContent className="text-center">
                <CheckCircle2 className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <h3 className="mt-4 font-semibold">No pending approvals</h3>
                <p className="text-sm text-muted-foreground">
                  All phase gate requests have been processed
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="recent" className="space-y-4">
          {/* Recent Approvals */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Decisions</CardTitle>
              <CardDescription>History of phase gate approvals and rejections</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockRecentApprovals.map((approval) => (
                  <div
                    key={approval.id}
                    className="flex items-start gap-4 rounded-lg border p-4"
                  >
                    <div className={cn(
                      "mt-1 flex h-8 w-8 items-center justify-center rounded-full",
                      approval.decision === "approved" && "bg-green-100",
                      approval.decision === "auto-approved" && "bg-blue-100",
                      approval.decision === "rejected" && "bg-red-100"
                    )}>
                      {approval.decision === "rejected" ? (
                        <XCircle className="h-4 w-4 text-red-600" />
                      ) : (
                        <CheckCircle2 className={cn(
                          "h-4 w-4",
                          approval.decision === "approved" && "text-green-600",
                          approval.decision === "auto-approved" && "text-blue-600"
                        )} />
                      )}
                    </div>
                    <div className="flex-1 space-y-1">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="font-mono text-xs">
                          {approval.ticketId}
                        </Badge>
                        <span className="font-medium">{approval.ticketTitle}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Badge variant="secondary" className="font-mono text-xs">
                          {approval.fromPhase.replace("PHASE_", "")}
                        </Badge>
                        <ArrowRight className="h-3 w-3" />
                        <Badge variant="secondary" className="font-mono text-xs">
                          {approval.toPhase.replace("PHASE_", "")}
                        </Badge>
                      </div>
                      {approval.comment && (
                        <p className="text-sm text-muted-foreground italic">
                          &quot;{approval.comment}&quot;
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">
                        {approval.decision === "auto-approved" ? "Auto-approved by system" : `By ${approval.decidedBy}`}
                        {" · "}{approval.decidedAt}
                      </p>
                    </div>
                    <Badge
                      variant={
                        approval.decision === "rejected" ? "destructive" :
                        approval.decision === "auto-approved" ? "secondary" : "default"
                      }
                    >
                      {approval.decision === "auto-approved" ? "Auto" : approval.decision}
                    </Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Review Dialog */}
      <Dialog open={!!selectedApproval} onOpenChange={() => setSelectedApproval(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Review Phase Gate Request</DialogTitle>
            <DialogDescription>
              {selectedApproval?.ticketId}: {selectedApproval?.ticketTitle}
            </DialogDescription>
          </DialogHeader>
          {selectedApproval && (
            <div className="space-y-4 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Badge variant="secondary" className="font-mono">
                    {selectedApproval.currentPhase.replace("PHASE_", "")}
                  </Badge>
                  <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  <Badge variant="outline" className="font-mono">
                    {selectedApproval.requestedPhase.replace("PHASE_", "")}
                  </Badge>
                </div>
                <Badge
                  variant={selectedApproval.overallStatus === "passed" ? "default" : "destructive"}
                >
                  {selectedApproval.overallStatus === "passed" ? "Validation Passed" : "Validation Failed"}
                </Badge>
              </div>

              <Separator />

              <div className="space-y-3">
                <p className="text-sm font-medium">Gate Criteria</p>
                {selectedApproval.gateCriteria.map((criterion, i) => (
                  <div key={i} className="flex items-center gap-2 text-sm">
                    {getStatusIcon(criterion.status)}
                    <span>{criterion.name}</span>
                  </div>
                ))}
              </div>

              <Separator />

              <div className="space-y-3">
                <p className="text-sm font-medium">Artifacts</p>
                {selectedApproval.artifacts.map((artifact, i) => (
                  <div key={i} className="flex items-center justify-between text-sm rounded-lg border p-2">
                    <div className="flex items-center gap-2">
                      <FileCode className="h-4 w-4 text-muted-foreground" />
                      <span>{artifact.name}</span>
                      <span className="font-mono text-xs text-muted-foreground">
                        {artifact.pattern}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(artifact.status)}
                      <span>
                        {artifact.found}/{artifact.expected}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              <Separator />

              <div className="space-y-2">
                <p className="text-sm font-medium">Decision Comment (optional)</p>
                <Textarea
                  placeholder="Add a comment for the decision..."
                  value={rejectComment}
                  onChange={(e) => setRejectComment(e.target.value)}
                  rows={3}
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedApproval(null)}>
              Cancel
            </Button>
            <Button
              variant="outline"
              className="text-destructive"
              onClick={() => setSelectedApproval(null)}
            >
              <X className="mr-2 h-4 w-4" />
              Reject
            </Button>
            <Button onClick={() => setSelectedApproval(null)}>
              <Check className="mr-2 h-4 w-4" />
              Approve Transition
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
