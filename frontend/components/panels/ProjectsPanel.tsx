"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Search,
  Plus,
  FolderGit2,
  Star,
  Clock,
  AlertCircle,
  ChevronRight,
} from "lucide-react";
import { useProjects } from "@/hooks/useProjects";

// Extract project ID from various route patterns
function extractProjectIdFromPath(pathname: string): string | null {
  // /projects/[id]/... pattern
  const projectMatch = pathname.match(/^\/projects\/([^/]+)/);
  if (projectMatch) return projectMatch[1];

  // /board/[projectId]/... pattern
  const boardMatch = pathname.match(/^\/board\/([^/]+)/);
  if (boardMatch && boardMatch[1] !== "all") return boardMatch[1];

  // /graph/[projectId]/... pattern
  const graphMatch = pathname.match(/^\/graph\/([^/]+)/);
  if (graphMatch) return graphMatch[1];

  return null;
}

export function ProjectsPanel() {
  const pathname = usePathname();
  const [searchQuery, setSearchQuery] = useState("");
  const { data: projects, isLoading, error } = useProjects();

  // Extract current project ID from URL
  const currentProjectId = extractProjectIdFromPath(pathname);

  const filteredProjects = useMemo(() => {
    const projectList = projects?.projects ?? [];
    return projectList.filter((project) =>
      project.name.toLowerCase().includes(searchQuery.toLowerCase()),
    );
  }, [projects, searchQuery]);

  const activeProjects = filteredProjects.filter((p) => p.status === "active");
  const pausedProjects = filteredProjects.filter(
    (p) => p.status === "paused" || p.status === "archived",
  );

  // Find the current project for display
  const currentProject = useMemo(() => {
    if (!currentProjectId) return null;
    const allProjects = projects?.projects ?? [];
    return allProjects.find((p) => p.id === currentProjectId);
  }, [currentProjectId, projects]);

  return (
    <div className="flex h-full flex-col">
      {/* Current Project Indicator */}
      {currentProject && (
        <div className="border-b bg-primary/5 p-3">
          <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
            Current Project
          </div>
          <Link
            href={`/projects/${currentProject.id}`}
            className="flex items-center gap-2 rounded-md bg-primary/10 border border-primary/20 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/15 transition-colors"
          >
            <FolderGit2 className="h-4 w-4" />
            <span className="flex-1 truncate">{currentProject.name}</span>
            <ChevronRight className="h-4 w-4 opacity-50" />
          </Link>
          {/* Quick navigation links for current project */}
          <div className="mt-2 flex flex-wrap gap-1">
            <Link
              href={`/board/${currentProject.id}`}
              className={cn(
                "text-xs px-2 py-1 rounded hover:bg-accent transition-colors",
                pathname.startsWith(`/board/${currentProject.id}`) &&
                  "bg-accent font-medium",
              )}
            >
              Board
            </Link>
            <Link
              href={`/projects/${currentProject.id}/specs`}
              className={cn(
                "text-xs px-2 py-1 rounded hover:bg-accent transition-colors",
                pathname.includes(`/projects/${currentProject.id}/specs`) &&
                  "bg-accent font-medium",
              )}
            >
              Specs
            </Link>
            <Link
              href={`/graph/${currentProject.id}`}
              className={cn(
                "text-xs px-2 py-1 rounded hover:bg-accent transition-colors",
                pathname.startsWith(`/graph/${currentProject.id}`) &&
                  "bg-accent font-medium",
              )}
            >
              Graph
            </Link>
            <Link
              href={`/projects/${currentProject.id}/settings`}
              className={cn(
                "text-xs px-2 py-1 rounded hover:bg-accent transition-colors",
                pathname.includes(`/projects/${currentProject.id}/settings`) &&
                  "bg-accent font-medium",
              )}
            >
              Settings
            </Link>
          </div>
        </div>
      )}

      {/* Header */}
      <div className="border-b p-3 space-y-3">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search projects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-9 pl-8 text-sm"
          />
        </div>
        <Button className="w-full" size="sm" asChild>
          <Link href="/projects/new">
            <Plus className="mr-2 h-4 w-4" /> New Project
          </Link>
        </Button>
      </div>

      {/* Project List */}
      <ScrollArea className="flex-1">
        <div className="p-3 space-y-4">
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-8 w-full rounded-md" />
              ))}
            </div>
          ) : error ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              <AlertCircle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              Failed to load projects
            </div>
          ) : (
            <>
              {/* Favorites Section - show first 2 active */}
              {activeProjects.length > 0 && (
                <div className="space-y-1">
                  <div className="flex items-center gap-2 px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    <Star className="h-3 w-3" />
                    Favorites
                  </div>
                  {activeProjects.slice(0, 2).map((project) => {
                    const isCurrentProject = project.id === currentProjectId;
                    return (
                      <Link
                        key={project.id}
                        href={`/projects/${project.id}`}
                        className={cn(
                          "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                          isCurrentProject
                            ? "bg-primary/10 text-primary font-medium border border-primary/20"
                            : "hover:bg-accent",
                        )}
                      >
                        <FolderGit2
                          className={cn(
                            "h-4 w-4",
                            isCurrentProject
                              ? "text-primary"
                              : "text-muted-foreground",
                          )}
                        />
                        <span className="flex-1 truncate">{project.name}</span>
                        {isCurrentProject && (
                          <ChevronRight className="h-4 w-4 text-primary opacity-50" />
                        )}
                      </Link>
                    );
                  })}
                </div>
              )}

              {/* Active Projects */}
              {activeProjects.length > 0 && (
                <div className="space-y-1">
                  <div className="flex items-center gap-2 px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    <Clock className="h-3 w-3" />
                    Active
                  </div>
                  {activeProjects.map((project) => {
                    const isCurrentProject = project.id === currentProjectId;
                    return (
                      <Link
                        key={project.id}
                        href={`/projects/${project.id}`}
                        className={cn(
                          "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                          isCurrentProject
                            ? "bg-primary/10 text-primary font-medium border border-primary/20"
                            : "hover:bg-accent",
                        )}
                      >
                        <FolderGit2
                          className={cn(
                            "h-4 w-4",
                            isCurrentProject
                              ? "text-primary"
                              : "text-muted-foreground",
                          )}
                        />
                        <span className="flex-1 truncate">{project.name}</span>
                        {project.status === "active" && !isCurrentProject && (
                          <span className="flex h-2 w-2 rounded-full bg-success" />
                        )}
                        {isCurrentProject && (
                          <ChevronRight className="h-4 w-4 text-primary opacity-50" />
                        )}
                      </Link>
                    );
                  })}
                </div>
              )}

              {/* Paused/Archived Projects */}
              {pausedProjects.length > 0 && (
                <div className="space-y-1">
                  <div className="px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                    Paused
                  </div>
                  {pausedProjects.map((project) => (
                    <Link
                      key={project.id}
                      href={`/projects/${project.id}`}
                      className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-accent hover:text-foreground transition-colors"
                    >
                      <FolderGit2 className="h-4 w-4" />
                      <span className="flex-1 truncate">{project.name}</span>
                    </Link>
                  ))}
                </div>
              )}

              {filteredProjects.length === 0 && (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  No projects found
                </div>
              )}
            </>
          )}
        </div>
      </ScrollArea>

      {/* Footer */}
      <div className="border-t p-3">
        <Link
          href="/projects"
          className="block text-center text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          View all projects →
        </Link>
      </div>
    </div>
  );
}
