"use client"

import { useState, useEffect } from "react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { ScrollArea } from "@/components/ui/scroll-area"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Github,
  Search,
  Star,
  GitFork,
  Lock,
  Globe,
  Loader2,
  ExternalLink,
  RefreshCw,
  FolderOpen,
} from "lucide-react"
import { listRepos } from "@/lib/api/github"
import { isProviderConnected } from "@/lib/api/oauth"
import type { GitHubRepo } from "@/lib/api/types"

interface RepositoryBrowserProps {
  onSelectRepo?: (repo: GitHubRepo) => void
  selectedRepoId?: number
}

export function RepositoryBrowser({ onSelectRepo, selectedRepoId }: RepositoryBrowserProps) {
  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [loading, setLoading] = useState(true)
  const [connected, setConnected] = useState(false)
  const [search, setSearch] = useState("")
  const [visibility, setVisibility] = useState<"all" | "public" | "private">("all")
  const [sort, setSort] = useState<"updated" | "created" | "pushed" | "full_name">("updated")

  useEffect(() => {
    checkConnection()
  }, [])

  useEffect(() => {
    if (connected) {
      fetchRepos()
    }
  }, [connected, visibility, sort])

  const checkConnection = async () => {
    const isConnected = await isProviderConnected("github")
    setConnected(isConnected)
    if (!isConnected) {
      setLoading(false)
    }
  }

  const fetchRepos = async () => {
    try {
      setLoading(true)
      const data = await listRepos({ visibility, sort, per_page: 100 })
      setRepos(data)
      if (data.length === 0) {
        console.warn("No repositories returned from GitHub API")
      }
    } catch (error: any) {
      console.error("Failed to fetch repos:", error)
      if (error.status === 400) {
        const errorMessage = error.message || "GitHub not connected"
        console.error("GitHub connection error:", errorMessage)
        setConnected(false)
        toast.error(errorMessage)
      } else if (error.status === 401 || error.status === 403) {
        toast.error("GitHub authentication failed. Please reconnect your GitHub account.")
        setConnected(false)
      } else {
        toast.error(`Failed to load repositories: ${error.message || "Unknown error"}`)
      }
    } finally {
      setLoading(false)
    }
  }

  const filteredRepos = repos.filter((repo) => {
    if (!search) return true
    const searchLower = search.toLowerCase()
    return (
      repo.name.toLowerCase().includes(searchLower) ||
      repo.full_name.toLowerCase().includes(searchLower) ||
      repo.description?.toLowerCase().includes(searchLower)
    )
  })

  const getLanguageColor = (language: string | null): string => {
    const colors: Record<string, string> = {
      TypeScript: "#3178c6",
      JavaScript: "#f1e05a",
      Python: "#3572A5",
      Go: "#00ADD8",
      Rust: "#dea584",
      Java: "#b07219",
      Ruby: "#701516",
      PHP: "#4F5D95",
      C: "#555555",
      "C++": "#f34b7d",
      "C#": "#178600",
      Swift: "#ffac45",
      Kotlin: "#A97BFF",
      Scala: "#c22d40",
    }
    return colors[language || ""] || "#858585"
  }

  if (!connected) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Github className="h-5 w-5" />
            GitHub Repositories
          </CardTitle>
          <CardDescription>Connect your GitHub account to browse repositories</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Github className="h-12 w-12 text-muted-foreground mb-4" />
            <p className="text-muted-foreground mb-4">
              GitHub is not connected. Please connect your GitHub account in settings to browse your
              repositories.
            </p>
            <Button asChild>
              <a href="/settings/integrations">Connect GitHub</a>
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Github className="h-5 w-5" />
              GitHub Repositories
            </CardTitle>
            <CardDescription>Select a repository to work with</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={fetchRepos} disabled={loading}>
            <RefreshCw className={`h-4 w-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Filters */}
        <div className="flex gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search repositories..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={visibility} onValueChange={(v) => setVisibility(v as any)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="public">Public</SelectItem>
              <SelectItem value="private">Private</SelectItem>
            </SelectContent>
          </Select>
          <Select value={sort} onValueChange={(v) => setSort(v as any)}>
            <SelectTrigger className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="updated">Updated</SelectItem>
              <SelectItem value="created">Created</SelectItem>
              <SelectItem value="pushed">Pushed</SelectItem>
              <SelectItem value="full_name">Name</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Repository List */}
        <ScrollArea className="h-[400px]">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="p-4 border rounded-lg">
                  <div className="flex items-center justify-between">
                    <div className="space-y-2">
                      <Skeleton className="h-5 w-48" />
                      <Skeleton className="h-4 w-64" />
                    </div>
                    <Skeleton className="h-8 w-20" />
                  </div>
                </div>
              ))}
            </div>
          ) : filteredRepos.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">
                {search ? "No repositories match your search" : "No repositories found"}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredRepos.map((repo) => (
                <div
                  key={repo.id}
                  className={`p-4 border rounded-lg cursor-pointer transition-all hover:border-primary/50 ${
                    selectedRepoId === repo.id ? "border-primary bg-primary/5" : ""
                  }`}
                  onClick={() => onSelectRepo?.(repo)}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium truncate">{repo.full_name}</span>
                        {repo.private ? (
                          <Lock className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                        ) : (
                          <Globe className="h-3.5 w-3.5 text-muted-foreground flex-shrink-0" />
                        )}
                      </div>
                      {repo.description && (
                        <p className="text-sm text-muted-foreground truncate mt-1">
                          {repo.description}
                        </p>
                      )}
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        {repo.language && (
                          <span className="flex items-center gap-1">
                            <span
                              className="w-2.5 h-2.5 rounded-full"
                              style={{ backgroundColor: getLanguageColor(repo.language) }}
                            />
                            {repo.language}
                          </span>
                        )}
                        <span className="flex items-center gap-1">
                          <Star className="h-3.5 w-3.5" />
                          {repo.stargazers_count.toLocaleString()}
                        </span>
                        <span className="flex items-center gap-1">
                          <GitFork className="h-3.5 w-3.5" />
                          {repo.forks_count.toLocaleString()}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {repo.default_branch}
                        </Badge>
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="flex-shrink-0"
                      asChild
                      onClick={(e) => e.stopPropagation()}
                    >
                      <a href={repo.html_url} target="_blank" rel="noopener noreferrer">
                        <ExternalLink className="h-4 w-4" />
                      </a>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        {/* Footer */}
        {!loading && filteredRepos.length > 0 && (
          <div className="text-xs text-muted-foreground text-center">
            Showing {filteredRepos.length} of {repos.length} repositories
          </div>
        )}
      </CardContent>
    </Card>
  )
}
