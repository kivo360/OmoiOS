"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import { Input } from "@/components/ui/input"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Badge } from "@/components/ui/badge"
import { cn } from "@/lib/utils"
import {
  FolderGit2,
  GitBranch,
  ChevronDown,
  Search,
  Plus,
  Check,
  Lock,
  Globe,
} from "lucide-react"

export interface Project {
  id: string
  name: string
  repo: string
  ticketCount: number
}

export interface Repository {
  fullName: string
  isPrivate: boolean
}

interface RepoSelectorProps {
  projects?: Project[]
  repositories?: Repository[]
  selectedProject?: Project | null
  selectedRepo?: string | null
  selectedBranch?: string
  onProjectSelect?: (project: Project) => void
  onRepoSelect?: (repo: string) => void
  onBranchChange?: (branch: string) => void
  className?: string
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
  const [open, setOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")

  const displayName = selectedProject?.repo || selectedRepo || "Select repository"

  const filteredProjects = projects.filter(
    (p) =>
      p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      p.repo.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const filteredRepos = repositories.filter((r) =>
    r.fullName.toLowerCase().includes(searchQuery.toLowerCase())
  )

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
                        onProjectSelect?.(project)
                        setOpen(false)
                      }}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left hover:bg-accent",
                        selectedProject?.id === project.id && "bg-accent"
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
                        onRepoSelect?.(repo.fullName)
                        setOpen(false)
                      }}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-md px-2 py-2 text-left hover:bg-accent",
                        selectedRepo === repo.fullName && "bg-accent"
                      )}
                    >
                      <Plus className="h-4 w-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm">{repo.fullName}</p>
                      </div>
                      <Badge variant="outline" className="shrink-0 gap-1 text-xs">
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
              <button className="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left hover:bg-accent">
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
      <Button
        variant="ghost"
        size="sm"
        className="h-8 gap-1.5 text-muted-foreground hover:text-foreground"
      >
        <GitBranch className="h-4 w-4" />
        <span>{selectedBranch}</span>
        <ChevronDown className="h-3 w-3" />
      </Button>
    </div>
  )
}
