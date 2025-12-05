"use client"

import { useState } from "react"
import Link from "next/link"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Search, Plus, FolderGit2, Star, Clock } from "lucide-react"
import { mockProjects } from "@/lib/mock"

export function ProjectsPanel() {
  const [searchQuery, setSearchQuery] = useState("")

  const filteredProjects = mockProjects.filter((project) =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const activeProjects = filteredProjects.filter((p) => p.status === "active")
  const pausedProjects = filteredProjects.filter((p) => p.status === "paused")

  return (
    <div className="flex h-full flex-col">
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
          {/* Favorites Section */}
          <div className="space-y-1">
            <div className="flex items-center gap-2 px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
              <Star className="h-3 w-3" />
              Favorites
            </div>
            {activeProjects.slice(0, 2).map((project) => (
              <Link
                key={project.id}
                href={`/projects/${project.id}`}
                className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent transition-colors"
              >
                <FolderGit2 className="h-4 w-4 text-muted-foreground" />
                <span className="flex-1 truncate">{project.name}</span>
                <Badge variant="secondary" className="text-[10px] h-5">
                  {project.ticketCount}
                </Badge>
              </Link>
            ))}
          </div>

          {/* Active Projects */}
          {activeProjects.length > 0 && (
            <div className="space-y-1">
              <div className="flex items-center gap-2 px-2 py-1 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                <Clock className="h-3 w-3" />
                Active
              </div>
              {activeProjects.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-accent transition-colors"
                >
                  <FolderGit2 className="h-4 w-4 text-muted-foreground" />
                  <span className="flex-1 truncate">{project.name}</span>
                  {project.activeAgents > 0 && (
                    <span className="flex h-2 w-2 rounded-full bg-success" />
                  )}
                </Link>
              ))}
            </div>
          )}

          {/* Paused Projects */}
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
  )
}
