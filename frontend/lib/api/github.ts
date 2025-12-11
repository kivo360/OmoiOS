/**
 * GitHub API functions
 * Handles GitHub repository operations via OAuth
 */

import { api } from "./client"
import type {
  GitHubRepo,
  GitHubBranch,
  GitHubFile,
  GitHubCommitInfo,
  GitHubPullRequest,
  DirectoryItem,
  TreeItem,
  FileOperationResult,
  BranchCreateResult,
  PullRequestCreateResult,
  CreateFileRequest,
  CreateBranchRequest,
  CreatePullRequestRequest,
  ConnectRepositoryRequest,
  ConnectRepositoryResponse,
  RepositoryInfo,
  SyncRepositoryResponse,
} from "./types"

// ============================================================================
// Project-Repository Connection (Legacy API)
// ============================================================================

/**
 * Connect a GitHub repository to a project
 */
export async function connectRepository(
  projectId: string,
  data: ConnectRepositoryRequest
): Promise<ConnectRepositoryResponse> {
  return api.post<ConnectRepositoryResponse>(`/api/v1/projects/${projectId}/github/connect`, data)
}

/**
 * List connected repositories (across all projects)
 */
export async function listConnectedRepositories(): Promise<RepositoryInfo[]> {
  return api.get<RepositoryInfo[]>("/api/v1/github/connected")
}

/**
 * Sync repository data for a project
 */
export async function syncRepository(projectId: string): Promise<SyncRepositoryResponse> {
  return api.post<SyncRepositoryResponse>(`/api/v1/projects/${projectId}/github/sync`)
}

// ============================================================================
// Repository Operations
// ============================================================================

export interface ListReposParams {
  visibility?: "all" | "public" | "private"
  sort?: "created" | "updated" | "pushed" | "full_name"
  per_page?: number
  page?: number
}

/**
 * List repositories for the authenticated user
 */
export async function listRepos(params: ListReposParams = {}): Promise<GitHubRepo[]> {
  const searchParams = new URLSearchParams()
  if (params.visibility) searchParams.set("visibility", params.visibility)
  if (params.sort) searchParams.set("sort", params.sort)
  if (params.per_page) searchParams.set("per_page", params.per_page.toString())
  if (params.page) searchParams.set("page", params.page.toString())

  const query = searchParams.toString()
  return api.get<GitHubRepo[]>(`/api/v1/github/repos${query ? `?${query}` : ""}`)
}

/**
 * Get repository details
 */
export async function getRepo(owner: string, repo: string): Promise<GitHubRepo> {
  return api.get<GitHubRepo>(`/api/v1/github/repos/${owner}/${repo}`)
}

// ============================================================================
// Branch Operations
// ============================================================================

export interface ListBranchesParams {
  per_page?: number
  page?: number
}

/**
 * List repository branches
 */
export async function listBranches(
  owner: string,
  repo: string,
  params: ListBranchesParams = {}
): Promise<GitHubBranch[]> {
  const searchParams = new URLSearchParams()
  if (params.per_page) searchParams.set("per_page", params.per_page.toString())
  if (params.page) searchParams.set("page", params.page.toString())

  const query = searchParams.toString()
  return api.get<GitHubBranch[]>(
    `/api/v1/github/repos/${owner}/${repo}/branches${query ? `?${query}` : ""}`
  )
}

/**
 * Create a new branch
 */
export async function createBranch(
  owner: string,
  repo: string,
  data: CreateBranchRequest
): Promise<BranchCreateResult> {
  return api.post<BranchCreateResult>(`/api/v1/github/repos/${owner}/${repo}/branches`, data)
}

// ============================================================================
// File Operations
// ============================================================================

/**
 * Get file content from repository
 */
export async function getFileContent(
  owner: string,
  repo: string,
  path: string,
  ref?: string
): Promise<GitHubFile> {
  const searchParams = new URLSearchParams()
  if (ref) searchParams.set("ref", ref)

  const query = searchParams.toString()
  return api.get<GitHubFile>(
    `/api/v1/github/repos/${owner}/${repo}/contents/${path}${query ? `?${query}` : ""}`
  )
}

/**
 * Create or update a file in the repository
 */
export async function createOrUpdateFile(
  owner: string,
  repo: string,
  path: string,
  data: CreateFileRequest
): Promise<FileOperationResult> {
  return api.put<FileOperationResult>(`/api/v1/github/repos/${owner}/${repo}/contents/${path}`, data)
}

/**
 * List directory contents
 */
export async function listDirectory(
  owner: string,
  repo: string,
  path: string = "",
  ref?: string
): Promise<DirectoryItem[]> {
  const searchParams = new URLSearchParams()
  if (path) searchParams.set("path", path)
  if (ref) searchParams.set("ref", ref)

  const query = searchParams.toString()
  return api.get<DirectoryItem[]>(
    `/api/v1/github/repos/${owner}/${repo}/directory${query ? `?${query}` : ""}`
  )
}

/**
 * Get repository file tree
 */
export async function getTree(
  owner: string,
  repo: string,
  treeSha: string = "HEAD",
  recursive: boolean = true
): Promise<TreeItem[]> {
  const searchParams = new URLSearchParams()
  searchParams.set("tree_sha", treeSha)
  searchParams.set("recursive", recursive.toString())

  return api.get<TreeItem[]>(`/api/v1/github/repos/${owner}/${repo}/tree?${searchParams}`)
}

// ============================================================================
// Commit Operations
// ============================================================================

export interface ListCommitsParams {
  sha?: string
  path?: string
  per_page?: number
  page?: number
}

/**
 * List repository commits
 */
export async function listCommits(
  owner: string,
  repo: string,
  params: ListCommitsParams = {}
): Promise<GitHubCommitInfo[]> {
  const searchParams = new URLSearchParams()
  if (params.sha) searchParams.set("sha", params.sha)
  if (params.path) searchParams.set("path", params.path)
  if (params.per_page) searchParams.set("per_page", params.per_page.toString())
  if (params.page) searchParams.set("page", params.page.toString())

  const query = searchParams.toString()
  return api.get<GitHubCommitInfo[]>(
    `/api/v1/github/repos/${owner}/${repo}/commits${query ? `?${query}` : ""}`
  )
}

// ============================================================================
// Pull Request Operations
// ============================================================================

export interface ListPullRequestsParams {
  state?: "open" | "closed" | "all"
  per_page?: number
  page?: number
}

/**
 * List repository pull requests
 */
export async function listPullRequests(
  owner: string,
  repo: string,
  params: ListPullRequestsParams = {}
): Promise<GitHubPullRequest[]> {
  const searchParams = new URLSearchParams()
  if (params.state) searchParams.set("state", params.state)
  if (params.per_page) searchParams.set("per_page", params.per_page.toString())
  if (params.page) searchParams.set("page", params.page.toString())

  const query = searchParams.toString()
  return api.get<GitHubPullRequest[]>(
    `/api/v1/github/repos/${owner}/${repo}/pulls${query ? `?${query}` : ""}`
  )
}

/**
 * Create a pull request
 */
export async function createPullRequest(
  owner: string,
  repo: string,
  data: CreatePullRequestRequest
): Promise<PullRequestCreateResult> {
  return api.post<PullRequestCreateResult>(`/api/v1/github/repos/${owner}/${repo}/pulls`, data)
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Parse a GitHub URL to extract owner and repo
 */
export function parseGitHubUrl(url: string): { owner: string; repo: string } | null {
  // Handle various GitHub URL formats
  const patterns = [
    /github\.com[/:]([^/]+)\/([^/.]+)(?:\.git)?/,
    /^([^/]+)\/([^/]+)$/,
  ]

  for (const pattern of patterns) {
    const match = url.match(pattern)
    if (match) {
      return { owner: match[1], repo: match[2] }
    }
  }

  return null
}

/**
 * Get the raw content URL for a file
 */
export function getRawContentUrl(owner: string, repo: string, branch: string, path: string): string {
  return `https://raw.githubusercontent.com/${owner}/${repo}/${branch}/${path}`
}

/**
 * Get the GitHub web URL for a file
 */
export function getFileUrl(owner: string, repo: string, branch: string, path: string): string {
  return `https://github.com/${owner}/${repo}/blob/${branch}/${path}`
}

/**
 * Get the GitHub web URL for a repository
 */
export function getRepoUrl(owner: string, repo: string): string {
  return `https://github.com/${owner}/${repo}`
}

/**
 * Get file extension from path
 */
export function getFileExtension(path: string): string {
  const parts = path.split(".")
  return parts.length > 1 ? parts[parts.length - 1] : ""
}

/**
 * Get language from file extension for syntax highlighting
 */
export function getLanguageFromExtension(ext: string): string {
  const languageMap: Record<string, string> = {
    ts: "typescript",
    tsx: "typescript",
    js: "javascript",
    jsx: "javascript",
    py: "python",
    rb: "ruby",
    rs: "rust",
    go: "go",
    java: "java",
    kt: "kotlin",
    swift: "swift",
    c: "c",
    cpp: "cpp",
    h: "c",
    hpp: "cpp",
    cs: "csharp",
    php: "php",
    sql: "sql",
    sh: "bash",
    bash: "bash",
    zsh: "bash",
    yml: "yaml",
    yaml: "yaml",
    json: "json",
    xml: "xml",
    html: "html",
    css: "css",
    scss: "scss",
    sass: "sass",
    less: "less",
    md: "markdown",
    mdx: "markdown",
    dockerfile: "dockerfile",
    makefile: "makefile",
    toml: "toml",
    ini: "ini",
    env: "bash",
  }

  return languageMap[ext.toLowerCase()] || "plaintext"
}
