"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { CardTitle, CardDescription } from "@/components/ui/card"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Label } from "@/components/ui/label"
import { Skeleton } from "@/components/ui/skeleton"
import {
  ArrowRight,
  Search,
  Folder,
  Star,
  Clock,
  Loader2,
  AlertCircle,
} from "lucide-react"
import { useOnboarding } from "@/hooks/useOnboarding"
import { api } from "@/lib/api/client"

interface GitHubRepo {
  id: number
  full_name: string
  name: string
  owner: {
    login: string
  }
  description: string | null
  language: string | null
  stargazers_count: number
  updated_at: string
  private: boolean
}

export function RepoSelectStep() {
  const { data, updateData, nextStep, isLoading: onboardingLoading } = useOnboarding()

  const [repos, setRepos] = useState<GitHubRepo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedRepoFullName, setSelectedRepoFullName] = useState<string | null>(
    data.selectedRepo?.fullName || null
  )

  // Fetch repos on mount
  useEffect(() => {
    fetchRepos()
  }, [])

  const fetchRepos = async () => {
    setIsLoading(true)
    setError(null)

    try {
      const response = await api.get<GitHubRepo[]>("/api/v1/github/repos")
      // Sort by most recently updated
      const sorted = response.sort(
        (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      )
      setRepos(sorted)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load repositories")
    } finally {
      setIsLoading(false)
    }
  }

  const filteredRepos = repos.filter(repo =>
    repo.full_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    repo.description?.toLowerCase().includes(searchQuery.toLowerCase())
  )

  const handleSelect = (fullName: string) => {
    setSelectedRepoFullName(fullName)
    const repo = repos.find(r => r.full_name === fullName)
    if (repo) {
      updateData({
        selectedRepo: {
          owner: repo.owner.login,
          name: repo.name,
          fullName: repo.full_name,
          language: repo.language || undefined,
        },
      })
    }
  }

  const handleContinue = () => {
    if (selectedRepoFullName) {
      nextStep()
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return "Today"
    if (diffDays === 1) return "Yesterday"
    if (diffDays < 7) return `${diffDays} days ago`
    if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
    return `${Math.floor(diffDays / 30)} months ago`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <CardTitle className="text-2xl">Choose Your First Project</CardTitle>
        <CardDescription>
          Select a repository for your first feature. You can add more projects later.
        </CardDescription>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search repositories..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9"
        />
      </div>

      {/* Repository list */}
      <div className="space-y-2 max-h-[300px] overflow-y-auto">
        {isLoading ? (
          // Loading skeletons
          Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="flex items-center gap-3 p-3 border rounded-lg">
              <Skeleton className="h-4 w-4 rounded" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-48" />
                <Skeleton className="h-3 w-32" />
              </div>
            </div>
          ))
        ) : error ? (
          // Error state
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <AlertCircle className="h-10 w-10 text-destructive mb-3" />
            <p className="text-sm text-muted-foreground">{error}</p>
            <Button variant="outline" size="sm" onClick={fetchRepos} className="mt-3">
              Try Again
            </Button>
          </div>
        ) : filteredRepos.length === 0 ? (
          // Empty state
          <div className="flex flex-col items-center justify-center p-8 text-center">
            <Folder className="h-10 w-10 text-muted-foreground mb-3" />
            <p className="text-sm text-muted-foreground">
              {searchQuery ? "No repositories match your search" : "No repositories found"}
            </p>
          </div>
        ) : (
          // Repository list
          <RadioGroup value={selectedRepoFullName || ""} onValueChange={handleSelect}>
            {filteredRepos.map((repo) => (
              <div
                key={repo.id}
                className={`flex items-start gap-3 p-3 border rounded-lg cursor-pointer transition-colors hover:bg-accent ${
                  selectedRepoFullName === repo.full_name ? "border-primary bg-primary/5" : ""
                }`}
                onClick={() => handleSelect(repo.full_name)}
              >
                <RadioGroupItem value={repo.full_name} id={repo.full_name} className="mt-1" />
                <Label htmlFor={repo.full_name} className="flex-1 cursor-pointer">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{repo.full_name}</span>
                    {repo.private && (
                      <span className="text-xs bg-muted px-2 py-0.5 rounded">Private</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                    {repo.language && (
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-primary" />
                        {repo.language}
                      </span>
                    )}
                    {repo.stargazers_count > 0 && (
                      <span className="flex items-center gap-1">
                        <Star className="h-3 w-3" />
                        {repo.stargazers_count}
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDate(repo.updated_at)}
                    </span>
                  </div>
                </Label>
              </div>
            ))}
          </RadioGroup>
        )}
      </div>

      {/* Continue button */}
      <Button
        size="lg"
        onClick={handleContinue}
        disabled={!selectedRepoFullName || onboardingLoading}
        className="w-full"
      >
        {onboardingLoading ? (
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        ) : (
          <>
            Continue
            <ArrowRight className="ml-2 h-5 w-5" />
          </>
        )}
      </Button>
    </div>
  )
}
