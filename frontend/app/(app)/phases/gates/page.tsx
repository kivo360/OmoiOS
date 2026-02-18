"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
  Check,
  X,
  Eye,
  Info,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useTickets } from "@/hooks/useTickets";
import { useValidateGate } from "@/hooks/usePhases";
import { getPhaseById } from "@/lib/phases-config";

// Type for approval items derived from tickets
interface ApprovalItem {
  id: string;
  ticketId: string;
  ticketTitle: string;
  currentPhase: string;
  requestedPhase: string;
  status: string;
  priority: string;
  createdAt: string | null;
}

export default function PhaseGatesPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState("all");
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [rejectComment, setRejectComment] = useState("");

  // Fetch tickets that could need gate validation
  const { data: ticketsData, isLoading } = useTickets();
  const validateGateMutation = useValidateGate();

  // Build list of tickets that are in intermediate phases (not done/blocked)
  const pendingApprovals = useMemo(() => {
    if (!ticketsData?.tickets) return [];

    return ticketsData.tickets
      .filter((ticket) => {
        // Only show tickets that could transition
        const phase = getPhaseById(ticket.phase_id);
        return (
          phase && !phase.isTerminal && ticket.phase_id !== "PHASE_BLOCKED"
        );
      })
      .map((ticket): ApprovalItem => {
        const phase = getPhaseById(ticket.phase_id);
        const nextPhase = phase?.transitions[0] || "PHASE_DONE";

        return {
          id: ticket.id,
          ticketId: ticket.id.slice(0, 8).toUpperCase(),
          ticketTitle: ticket.title,
          currentPhase: ticket.phase_id,
          requestedPhase: nextPhase,
          status: ticket.status,
          priority: ticket.priority,
          createdAt: ticket.created_at,
        };
      });
  }, [ticketsData]);

  const filteredApprovals = pendingApprovals.filter((approval) => {
    const matchesSearch =
      approval.ticketTitle.toLowerCase().includes(searchQuery.toLowerCase()) ||
      approval.ticketId.toLowerCase().includes(searchQuery.toLowerCase());

    if (filterStatus === "all") return matchesSearch;
    if (filterStatus === "in_progress")
      return matchesSearch && approval.status === "in_progress";
    if (filterStatus === "pending")
      return matchesSearch && approval.status === "pending";
    return matchesSearch;
  });

  const selectedApproval = pendingApprovals.find(
    (a) => a.id === selectedTicketId,
  );

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
      case "passed":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "failed":
      case "blocked":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "in_progress":
        return <Clock className="h-4 w-4 text-blue-500" />;
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
    }
  };

  const formatTimeAgo = (dateStr: string | null | undefined) => {
    if (!dateStr) return "N/A";
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const minutes = Math.floor(diff / (1000 * 60));
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  };

  const handleValidateGate = (ticketId: string, phaseId: string) => {
    validateGateMutation.mutate({ ticketId, phaseId });
  };

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
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">
                    {pendingApprovals.length}
                  </p>
                )}
                <p className="text-sm text-muted-foreground">
                  Tickets in Workflow
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-500/10">
                <Clock className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">
                    {
                      pendingApprovals.filter((a) => a.status === "in_progress")
                        .length
                    }
                  </p>
                )}
                <p className="text-sm text-muted-foreground">In Progress</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-yellow-500/10">
                <AlertCircle className="h-5 w-5 text-yellow-600" />
              </div>
              <div>
                {isLoading ? (
                  <Skeleton className="h-8 w-12" />
                ) : (
                  <p className="text-2xl font-bold">
                    {
                      pendingApprovals.filter((a) => a.status === "pending")
                        .length
                    }
                  </p>
                )}
                <p className="text-sm text-muted-foreground">Pending</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="pending" className="space-y-4">
        <TabsList>
          <TabsTrigger value="pending">
            Tickets in Workflow
            <Badge variant="secondary" className="ml-2">
              {pendingApprovals.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="about">About Phase Gates</TabsTrigger>
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
                <SelectItem value="all">All Tickets</SelectItem>
                <SelectItem value="in_progress">In Progress</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Ticket Cards */}
          {isLoading ? (
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <Card key={i}>
                  <CardHeader className="pb-3">
                    <div className="flex items-center gap-3">
                      <Skeleton className="h-6 w-24" />
                      <Skeleton className="h-5 w-48" />
                    </div>
                  </CardHeader>
                  <CardContent>
                    <Skeleton className="h-20 w-full" />
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {filteredApprovals.map((approval) => (
                <Card key={approval.id} className="overflow-hidden">
                  <div
                    className={cn(
                      "h-1",
                      approval.status === "in_progress" && "bg-blue-500",
                      approval.status === "completed" && "bg-green-500",
                      approval.status === "blocked" && "bg-red-500",
                      approval.status === "pending" && "bg-yellow-500",
                    )}
                  />
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="font-mono">
                            {approval.ticketId}
                          </Badge>
                          <CardTitle className="text-base">
                            {approval.ticketTitle}
                          </CardTitle>
                        </div>
                        <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-4 w-4" />
                            Created {formatTimeAgo(approval.createdAt)}
                          </span>
                          <span className="flex items-center gap-1">
                            Priority: {approval.priority}
                          </span>
                        </div>
                      </div>
                      <Badge
                        variant={
                          approval.status === "in_progress"
                            ? "default"
                            : approval.status === "completed"
                              ? "secondary"
                              : "outline"
                        }
                      >
                        {approval.status}
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

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-2 pt-2">
                      <Button variant="outline" size="sm" asChild>
                        <Link href={`/board/${approval.id}/${approval.id}`}>
                          <Eye className="mr-2 h-4 w-4" />
                          View Ticket
                        </Link>
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          handleValidateGate(approval.id, approval.currentPhase)
                        }
                        disabled={validateGateMutation.isPending}
                      >
                        <Check className="mr-2 h-4 w-4" />
                        Validate Gate
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}

          {/* Empty State */}
          {!isLoading && filteredApprovals.length === 0 && (
            <Card className="py-12">
              <CardContent className="text-center">
                <CheckCircle2 className="mx-auto h-12 w-12 text-muted-foreground/50" />
                <h3 className="mt-4 font-semibold">No tickets in workflow</h3>
                <p className="text-sm text-muted-foreground">
                  {searchQuery
                    ? "Try adjusting your search criteria"
                    : "All tickets have been processed"}
                </p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="about" className="space-y-4">
          {/* About Phase Gates */}
          <Card>
            <CardHeader>
              <CardTitle>About Phase Gates</CardTitle>
              <CardDescription>
                Understanding the phase gate validation system
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="rounded-lg bg-muted p-4 space-y-3">
                <div className="flex items-start gap-3">
                  <Info className="h-5 w-5 text-primary mt-0.5" />
                  <div>
                    <p className="font-medium">What are Phase Gates?</p>
                    <p className="text-sm text-muted-foreground">
                      Phase gates are checkpoints between workflow phases that
                      validate whether tickets meet the required criteria before
                      advancing.
                    </p>
                  </div>
                </div>
              </div>

              <div className="space-y-3">
                <p className="font-medium">Gate Validation Checks:</p>
                <ul className="space-y-2 text-sm">
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span>Done criteria for the current phase are met</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span>Required artifacts (files, reports) exist</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span>All subtasks are completed</span>
                  </li>
                  <li className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    <span>No blocking issues exist</span>
                  </li>
                </ul>
              </div>

              <Separator />

              <div className="space-y-3">
                <p className="font-medium">How to Use:</p>
                <ol className="space-y-2 text-sm text-muted-foreground list-decimal list-inside">
                  <li>Browse tickets currently in the workflow</li>
                  <li>
                    Click &quot;Validate Gate&quot; to check if a ticket can
                    advance
                  </li>
                  <li>Review any blocking reasons if validation fails</li>
                  <li>
                    Ticket phases are updated via the board or ticket detail
                    pages
                  </li>
                </ol>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Review Dialog */}
      <Dialog
        open={!!selectedTicketId}
        onOpenChange={() => setSelectedTicketId(null)}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Validate Phase Gate</DialogTitle>
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
                <Badge variant="outline">{selectedApproval.status}</Badge>
              </div>

              <Separator />

              <div className="rounded-lg bg-muted p-4">
                <p className="text-sm">
                  Click &quot;Validate Gate&quot; to check if this ticket meets
                  all the requirements to transition from{" "}
                  <span className="font-mono font-medium">
                    {selectedApproval.currentPhase.replace("PHASE_", "")}
                  </span>{" "}
                  to{" "}
                  <span className="font-mono font-medium">
                    {selectedApproval.requestedPhase.replace("PHASE_", "")}
                  </span>
                  .
                </p>
              </div>

              {validateGateMutation.data && (
                <div className="rounded-lg border p-4 space-y-2">
                  <p className="font-medium">Validation Result:</p>
                  <div className="flex items-center gap-2">
                    {validateGateMutation.data.requirements_met ? (
                      <CheckCircle2 className="h-5 w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-5 w-5 text-red-500" />
                    )}
                    <span>
                      {validateGateMutation.data.requirements_met
                        ? "All requirements met - ready to advance"
                        : "Some requirements not met"}
                    </span>
                  </div>
                  {validateGateMutation.data.blocking_reasons?.length > 0 && (
                    <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                      {validateGateMutation.data.blocking_reasons.map(
                        (reason: string, i: number) => (
                          <li key={i} className="flex items-center gap-2">
                            <XCircle className="h-3 w-3 text-red-500" />
                            {reason}
                          </li>
                        ),
                      )}
                    </ul>
                  )}
                </div>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedTicketId(null)}>
              Close
            </Button>
            <Button
              onClick={() =>
                selectedApproval &&
                handleValidateGate(
                  selectedApproval.id,
                  selectedApproval.currentPhase,
                )
              }
              disabled={validateGateMutation.isPending}
            >
              <Check className="mr-2 h-4 w-4" />
              Validate Gate
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
