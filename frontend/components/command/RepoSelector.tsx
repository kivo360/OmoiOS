"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  FolderGit2,
  GitBranch,
  ChevronDown,
  Search,
  Plus,
  Check,
  Lock,
  Globe,
} from "lucide-react";
import { useGitHubRepos, useGitHubBranches } from "@/hooks/useGitHubRepos";
import { useIsProviderConnected } from "@/hooks/useOAuth";

export interface Project {
  id: string;
  name: string;
  repo?: string;
  ticketCount: number;
}

export interface Repository {
  fullName: string;
  isPrivate: boolean;
}

interface RepoSelectorProps {
  projects?: Project[];
  repositories?: Repository[];
  selectedProject?: Project | null;
  selectedRepo?: string | null;
  selectedBranch?: string;
  onProjectSelect?: (project: Project) => void;
  onRepoSelect?: (repo: string) => void;
  onBranchChange?: (branch: string) => void;
  className?: string;
}

export function RepoSelector({
  projects = [],
  repositories = [],
  selectedProject,
  selectedRepo,
  selectedBranch = "main",
  onProjectSelect,
  onRepoSelect,
  onBranchChange,
  className,
}: RepoSelectorProps) {
  const [open, setOpen] = useState(false);
  const [branchOpen, setBranchOpen] = useState(false);
  const [connectDialogOpen, setConnectDialogOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [branchSearchQuery, setBranchSearchQuery] = useState("");
  const [connectSearchQuery, setConnectSearchQuery] = useState("");

  // Check GitHub connection status
  const { isConnected: isGitHubConnected, isLoading: isCheckingConnection } =
    useIsProviderConnected("github");

  // Parse owner/repo from selectedRepo (format: "owner/repo")
  const repoFullName = selectedProject?.repo || selectedRepo;
  const [repoOwner, repoName] = repoFullName?.split("/") ?? [null, null];

  // Fetch all GitHub repositories for the connect dialog (only if connected)
  const {
    data: allRepos,
    isLoading: reposLoading,
    error: reposError,
  } = useGitHubRepos(
    {
      sort: "updated",
      per_page: 100,
    },
    isGitHubConnected && !isCheckingConnection, // Only fetch if GitHub is connected
  );

  // Fetch branches for the selected repository
  const { data: branches, isLoading: branchesLoading } = useGitHubBranches(
    repoOwner ?? "",
    repoName ?? "",
  );

  // Filter branches based on search
  const filteredBranches =
    branches?.filter((b) =>
      b.name.toLowerCase().includes(branchSearchQuery.toLowerCase()),
    ) ?? [];

  const displayName =
    selectedProject?.repo || selectedRepo || "Select repository";

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (p.repo?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false),
  );

  const filteredRepos = repositories.filter((r) =>
    r.fullName.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  // Filter all GitHub repos for the connect dialog
  const filteredAllRepos =
    allRepos?.filter((r) =>
      r.full_name.toLowerCase().includes(connectSearchQuery.toLowerCase()),
    ) || [];

  // Get repos that aren't already in the repositories list
  const availableToConnect = filteredAllRepos.filter(
    (r) => !repositories.some((existing) => existing.fullName === r.full_name),
  );

  // Debug logging (only in development, after all variables are defined)
  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      process.env.NODE_ENV === "development"
    ) {
      console.log("RepoSelector Debug:", {
        isGitHubConnected,
        isCheckingConnection,
        reposLoading,
        reposError: reposError ? String(reposError) : null,
        allReposCount: allRepos?.length ?? 0,
        repositoriesCount: repositories.length,
        filteredAllReposCount: filteredAllRepos.length,
        availableToConnectCount: availableToConnect.length,
        repositoriesList: repositories.map((r) => r.fullName),
      });
    }
  }, [
    isGitHubConnected,
    isCheckingConnection,
    reposLoading,
    reposError,
    allRepos,
    repositories,
    filteredAllRepos,
    availableToConnect,
  ]);

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-muted-foreground hover:text-foreground"
          >
            <FolderGit2 className="h-4 w-4" />
            <span className="max-w-[200px] truncate">{displayName}</span>
            <ChevronDown className="h-3 w-3" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[350px] p-0" align="start">
          <div className="p-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search projects & repos..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="h-9 pl-8"
              />
            </div>
          </div>

          <ScrollArea className="h-[300px]">
            {/* Projects Section */}
            {filteredProjects.length > 0 && (
              <div className="px-2 pb-2">
                <p className="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Projects
                </p>
                <div className="space-y-0.5">
                  {filteredProjects.map((project) => (
                    <button
                      key={project.id}
                      onClick={() => {
                        onProjectSelect?.(project);
                        setOpen(false);
                      }}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left hover:bg-accent",
                        selectedProject?.id === project.id && "bg-accent",
                      )}
                    >
                      <FolderGit2 className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {project.name}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          {project.repo} • {project.ticketCount} tickets
                        </p>
                      </div>
                      {selectedProject?.id === project.id && (
                        <Check className="h-4 w-4 shrink-0 text-success" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {filteredProjects.length > 0 && filteredRepos.length > 0 && (
              <Separator className="my-2" />
            )}

            {/* Available Repositories Section */}
            {filteredRepos.length > 0 && (
              <div className="px-2 pb-2">
                <p className="px-2 py-1.5 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">
                  Available Repositories
                </p>
                <div className="space-y-0.5">
                  {filteredRepos.map((repo) => (
                    <button
                      key={repo.fullName}
                      onClick={() => {
                        onRepoSelect?.(repo.fullName);
                        setOpen(false);
                      }}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left hover:bg-accent",
                        selectedRepo === repo.fullName && "bg-accent",
                      )}
                    >
                      <Plus className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm">{repo.fullName}</p>
                      </div>
                      <Badge
                        variant="outline"
                        className="shrink-0 gap-1 text-xs"
                      >
                        {repo.isPrivate ? (
                          <>
                            <Lock className="h-3 w-3" /> Private
                          </>
                        ) : (
                          <>
                            <Globe className="h-3 w-3" /> Public
                          </>
                        )}
                      </Badge>
                    </button>
                  ))}
                </div>
              </div>
            )}

            <Separator className="my-2" />

            {/* Connect New Repository */}
            <div className="px-2 pb-2">
              <button
                onClick={() => {
                  setOpen(false);
                  setConnectDialogOpen(true);
                }}
                className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left hover:bg-accent"
              >
                <Plus className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-sm">Connect New Repository</p>
                  <p className="text-xs text-muted-foreground">
                    Add a repo not listed here
                  </p>
                </div>
              </button>
            </div>
          </ScrollArea>
        </PopoverContent>
      </Popover>

      {/* Branch Selector */}
      <Popover open={branchOpen} onOpenChange={setBranchOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="h-8 gap-1.5 text-muted-foreground hover:text-foreground"
            disabled={!repoFullName}
          >
            <GitBranch className="h-4 w-4" />
            <span>{selectedBranch}</span>
            <ChevronDown className="h-3 w-3" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[250px] p-0" align="start">
          <div className="p-3">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search branches..."
                value={branchSearchQuery}
                onChange={(e) => setBranchSearchQuery(e.target.value)}
                className="h-9 pl-8"
              />
            </div>
          </div>
          <ScrollArea className="h-[200px]">
            {!repoFullName ? (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                Select a repository first
              </div>
            ) : branchesLoading ? (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                Loading branches...
              </div>
            ) : filteredBranches.length === 0 ? (
              <div className="px-4 py-6 text-center text-sm text-muted-foreground">
                {branchSearchQuery
                  ? "No branches match your search"
                  : "No branches found"}
              </div>
            ) : (
              <div className="px-2 pb-2">
                {filteredBranches.map((branch) => (
                  <button
                    key={branch.name}
                    onClick={() => {
                      onBranchChange?.(branch.name);
                      setBranchOpen(false);
                      setBranchSearchQuery("");
                    }}
                    className={cn(
                      "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left hover:bg-accent",
                      selectedBranch === branch.name && "bg-accent",
                    )}
                  >
                    <GitBranch className="h-4 w-4 shrink-0 text-muted-foreground" />
                    <span className="truncate text-sm">{branch.name}</span>
                    {selectedBranch === branch.name && (
                      <Check className="ml-auto h-4 w-4 shrink-0 text-success" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </ScrollArea>
        </PopoverContent>
      </Popover>

      {/* Connect Repository Dialog */}
      <Dialog open={connectDialogOpen} onOpenChange={setConnectDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh]">
          <DialogHeader>
            <DialogTitle>Connect GitHub Repository</DialogTitle>
            <DialogDescription>
              Select a repository from your GitHub account to connect
            </DialogDescription>
          </DialogHeader>

          {!isGitHubConnected ? (
            <div className="py-8 text-center">
              <p className="text-sm text-muted-foreground mb-4">
                Please connect your GitHub account first to view repositories.
              </p>
              <Button onClick={() => (window.location.href = "/settings")}>
                Go to Settings
              </Button>
            </div>
          ) : (
            <>
              <div className="relative mb-4">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search repositories..."
                  value={connectSearchQuery}
                  onChange={(e) => setConnectSearchQuery(e.target.value)}
                  className="h-9 pl-8"
                />
              </div>

              <ScrollArea className="h-[400px]">
                {reposLoading || isCheckingConnection ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">
                    Loading repositories...
                  </div>
                ) : reposError ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">
                    <p className="text-destructive mb-2">
                      Failed to load repositories
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {(reposError as any)?.message ||
                        "Please try again or reconnect your GitHub account"}
                    </p>
                  </div>
                ) : !allRepos || allRepos.length === 0 ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">
                    <p>No repositories found in your GitHub account</p>
                    <p className="text-xs mt-2">
                      Make sure you have repositories on GitHub
                    </p>
                  </div>
                ) : availableToConnect.length === 0 ? (
                  <div className="py-8 text-center text-sm text-muted-foreground">
                    {connectSearchQuery
                      ? "No repositories match your search"
                      : filteredAllRepos.length === 0
                        ? "No repositories match your search"
                        : `All ${filteredAllRepos.length} repository${filteredAllRepos.length === 1 ? "" : "ies"} are already connected`}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {availableToConnect.map((repo) => (
                      <button
                        key={repo.id}
                        onClick={() => {
                          onRepoSelect?.(repo.full_name);
                          setConnectDialogOpen(false);
                        }}
                        className="flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-left hover:bg-accent"
                      >
                        <FolderGit2 className="h-5 w-5 shrink-0 text-muted-foreground" />
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">
                            {repo.full_name}
                          </p>
                          {repo.description && (
                            <p className="truncate text-xs text-muted-foreground">
                              {repo.description}
                            </p>
                          )}
                        </div>
                        <Badge
                          variant="outline"
                          className="shrink-0 gap-1 text-xs"
                        >
                          {repo.private ? (
                            <>
                              <Lock className="h-3 w-3" /> Private
                            </>
                          ) : (
                            <>
                              <Globe className="h-3 w-3" /> Public
                            </>
                          )}
                        </Badge>
                      </button>
                    ))}
                  </div>
                )}
              </ScrollArea>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
