"use client"

import { useState, useEffect } from "react"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
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
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb"
import {
  File,
  Folder,
  ChevronRight,
  Loader2,
  ExternalLink,
  Home,
  GitBranch,
} from "lucide-react"
import { listDirectory, listBranches, getFileContent, getFileUrl } from "@/lib/api/github"
import type { DirectoryItem, GitHubBranch, GitHubFile } from "@/lib/api/types"

interface FileBrowserProps {
  owner: string
  repo: string
  defaultBranch?: string
  onFileSelect?: (file: GitHubFile) => void
}

export function FileBrowser({ owner, repo, defaultBranch = "main", onFileSelect }: FileBrowserProps) {
  const [currentPath, setCurrentPath] = useState("")
  const [items, setItems] = useState<DirectoryItem[]>([])
  const [branches, setBranches] = useState<GitHubBranch[]>([])
  const [selectedBranch, setSelectedBranch] = useState(defaultBranch)
  const [loading, setLoading] = useState(true)
  const [loadingBranches, setLoadingBranches] = useState(true)
  const [selectedFile, setSelectedFile] = useState<GitHubFile | null>(null)
  const [loadingFile, setLoadingFile] = useState(false)

  useEffect(() => {
    fetchBranches()
  }, [owner, repo])

  useEffect(() => {
    fetchDirectory()
  }, [owner, repo, currentPath, selectedBranch])

  const fetchBranches = async () => {
    try {
      setLoadingBranches(true)
      const data = await listBranches(owner, repo, { per_page: 100 })
      setBranches(data)
      // Set default branch if it exists
      if (data.some((b) => b.name === defaultBranch)) {
        setSelectedBranch(defaultBranch)
      } else if (data.length > 0) {
        setSelectedBranch(data[0].name)
      }
    } catch (error) {
      console.error("Failed to fetch branches:", error)
    } finally {
      setLoadingBranches(false)
    }
  }

  const fetchDirectory = async () => {
    try {
      setLoading(true)
      const data = await listDirectory(owner, repo, currentPath, selectedBranch)
      // Sort: directories first, then files, both alphabetically
      const sorted = [...data].sort((a, b) => {
        if (a.type === "dir" && b.type !== "dir") return -1
        if (a.type !== "dir" && b.type === "dir") return 1
        return a.name.localeCompare(b.name)
      })
      setItems(sorted)
    } catch (error) {
      console.error("Failed to fetch directory:", error)
      toast.error("Failed to load directory contents")
    } finally {
      setLoading(false)
    }
  }

  const handleItemClick = async (item: DirectoryItem) => {
    if (item.type === "dir") {
      setCurrentPath(item.path)
      setSelectedFile(null)
    } else {
      // Fetch file content
      setLoadingFile(true)
      try {
        const file = await getFileContent(owner, repo, item.path, selectedBranch)
        setSelectedFile(file)
        onFileSelect?.(file)
      } catch (error) {
        console.error("Failed to fetch file:", error)
        toast.error("Failed to load file content")
      } finally {
        setLoadingFile(false)
      }
    }
  }

  const navigateToPath = (path: string) => {
    setCurrentPath(path)
    setSelectedFile(null)
  }

  const pathParts = currentPath ? currentPath.split("/") : []

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  }

  const getFileIcon = (name: string, type: string) => {
    if (type === "dir") {
      return <Folder className="h-4 w-4 text-blue-500" />
    }
    return <File className="h-4 w-4 text-muted-foreground" />
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg">
              {owner}/{repo}
            </CardTitle>
            <CardDescription>Browse repository files</CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <GitBranch className="h-4 w-4 text-muted-foreground" />
            <Select
              value={selectedBranch}
              onValueChange={setSelectedBranch}
              disabled={loadingBranches}
            >
              <SelectTrigger className="w-40">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {branches.map((branch) => (
                  <SelectItem key={branch.name} value={branch.name}>
                    {branch.name}
                    {branch.protected && (
                      <Badge variant="outline" className="ml-2 text-xs">
                        protected
                      </Badge>
                    )}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Breadcrumb */}
        <Breadcrumb className="mt-2">
          <BreadcrumbList>
            <BreadcrumbItem>
              <BreadcrumbLink
                onClick={() => navigateToPath("")}
                className="cursor-pointer flex items-center gap-1"
              >
                <Home className="h-3.5 w-3.5" />
                root
              </BreadcrumbLink>
            </BreadcrumbItem>
            {pathParts.map((part, index) => {
              const fullPath = pathParts.slice(0, index + 1).join("/")
              return (
                <BreadcrumbItem key={fullPath}>
                  <BreadcrumbSeparator>
                    <ChevronRight className="h-3.5 w-3.5" />
                  </BreadcrumbSeparator>
                  <BreadcrumbLink
                    onClick={() => navigateToPath(fullPath)}
                    className="cursor-pointer"
                  >
                    {part}
                  </BreadcrumbLink>
                </BreadcrumbItem>
              )
            })}
          </BreadcrumbList>
        </Breadcrumb>
      </CardHeader>

      <CardContent>
        <ScrollArea className="h-[400px]">
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-3 p-2">
                  <Skeleton className="h-4 w-4" />
                  <Skeleton className="h-4 w-48" />
                </div>
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-8 text-center">
              <Folder className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground">This directory is empty</p>
            </div>
          ) : (
            <div className="space-y-1">
              {/* Go up directory */}
              {currentPath && (
                <div
                  className="flex items-center gap-3 p-2 rounded-md cursor-pointer hover:bg-muted"
                  onClick={() => {
                    const parts = currentPath.split("/")
                    parts.pop()
                    navigateToPath(parts.join("/"))
                  }}
                >
                  <Folder className="h-4 w-4 text-blue-500" />
                  <span className="text-sm">..</span>
                </div>
              )}

              {items.map((item) => (
                <div
                  key={item.sha}
                  className={`flex items-center justify-between gap-3 p-2 rounded-md cursor-pointer hover:bg-muted ${
                    selectedFile?.path === item.path ? "bg-muted" : ""
                  }`}
                  onClick={() => handleItemClick(item)}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {getFileIcon(item.name, item.type)}
                    <span className="text-sm truncate">{item.name}</span>
                    {loadingFile && selectedFile?.path === item.path && (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    )}
                  </div>
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    {item.type === "file" && item.size > 0 && (
                      <span>{formatFileSize(item.size)}</span>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6"
                      asChild
                      onClick={(e) => e.stopPropagation()}
                    >
                      <a
                        href={getFileUrl(owner, repo, selectedBranch, item.path)}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ScrollArea>
      </CardContent>
    </Card>
  )
}
