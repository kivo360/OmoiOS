/**
 * React Query hooks for GitHub Repository API (OAuth-based)
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  listRepos,
  getRepo,
  listBranches,
  getFileContent,
  listDirectory,
  getTree,
  listCommits,
  listPullRequests,
  createBranch,
  createOrUpdateFile,
  createPullRequest,
  type ListReposParams,
  type ListBranchesParams,
  type ListCommitsParams,
  type ListPullRequestsParams,
} from "@/lib/api/github"
import type {
  GitHubRepo,
  GitHubBranch,
  GitHubFile,
  DirectoryItem,
  TreeItem,
  GitHubCommitInfo,
  GitHubPullRequest,
  BranchCreateResult,
  FileOperationResult,
  PullRequestCreateResult,
  CreateBranchRequest,
  CreateFileRequest,
  CreatePullRequestRequest,
} from "@/lib/api/types"

// Query keys
export const githubRepoKeys = {
  all: ["github-repos"] as const,
  repos: (params?: ListReposParams) => [...githubRepoKeys.all, "list", params] as const,
  repo: (owner: string, repo: string) => [...githubRepoKeys.all, "detail", owner, repo] as const,
  branches: (owner: string, repo: string, params?: ListBranchesParams) =>
    [...githubRepoKeys.all, "branches", owner, repo, params] as const,
  file: (owner: string, repo: string, path: string, ref?: string) =>
    [...githubRepoKeys.all, "file", owner, repo, path, ref] as const,
  directory: (owner: string, repo: string, path: string, ref?: string) =>
    [...githubRepoKeys.all, "directory", owner, repo, path, ref] as const,
  tree: (owner: string, repo: string, sha: string, recursive?: boolean) =>
    [...githubRepoKeys.all, "tree", owner, repo, sha, recursive] as const,
  commits: (owner: string, repo: string, params?: ListCommitsParams) =>
    [...githubRepoKeys.all, "commits", owner, repo, params] as const,
  pullRequests: (owner: string, repo: string, params?: ListPullRequestsParams) =>
    [...githubRepoKeys.all, "pulls", owner, repo, params] as const,
}

// ============================================================================
// Repository Hooks
// ============================================================================

/**
 * Hook to list repositories for authenticated user
 * @param params - Query parameters for listing repos
 * @param enabled - Whether the query should run (default: true)
 */
export function useGitHubRepos(params?: ListReposParams, enabled: boolean = true) {
  return useQuery<GitHubRepo[]>({
    queryKey: githubRepoKeys.repos(params),
    queryFn: () => listRepos(params),
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: 1, // Only retry once on failure
  })
}

/**
 * Hook to get repository details
 */
export function useGitHubRepo(owner: string, repo: string) {
  return useQuery<GitHubRepo>({
    queryKey: githubRepoKeys.repo(owner, repo),
    queryFn: () => getRepo(owner, repo),
    enabled: !!owner && !!repo,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })
}

// ============================================================================
// Branch Hooks
// ============================================================================

/**
 * Hook to list repository branches
 */
export function useGitHubBranches(owner: string, repo: string, params?: ListBranchesParams) {
  return useQuery<GitHubBranch[]>({
    queryKey: githubRepoKeys.branches(owner, repo, params),
    queryFn: () => listBranches(owner, repo, params),
    enabled: !!owner && !!repo,
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

/**
 * Hook to create a new branch
 */
export function useCreateBranch(owner: string, repo: string) {
  const queryClient = useQueryClient()

  return useMutation<BranchCreateResult, Error, CreateBranchRequest>({
    mutationFn: (data) => createBranch(owner, repo, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: githubRepoKeys.branches(owner, repo) })
    },
  })
}

// ============================================================================
// File Hooks
// ============================================================================

/**
 * Hook to get file content
 */
export function useGitHubFile(owner: string, repo: string, path: string, ref?: string) {
  return useQuery<GitHubFile>({
    queryKey: githubRepoKeys.file(owner, repo, path, ref),
    queryFn: () => getFileContent(owner, repo, path, ref),
    enabled: !!owner && !!repo && !!path,
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Hook to list directory contents
 */
export function useGitHubDirectory(owner: string, repo: string, path: string = "", ref?: string) {
  return useQuery<DirectoryItem[]>({
    queryKey: githubRepoKeys.directory(owner, repo, path, ref),
    queryFn: () => listDirectory(owner, repo, path, ref),
    enabled: !!owner && !!repo,
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Hook to get repository file tree
 */
export function useGitHubTree(
  owner: string,
  repo: string,
  sha: string = "HEAD",
  recursive: boolean = true
) {
  return useQuery<TreeItem[]>({
    queryKey: githubRepoKeys.tree(owner, repo, sha, recursive),
    queryFn: () => getTree(owner, repo, sha, recursive),
    enabled: !!owner && !!repo,
    staleTime: 1 * 60 * 1000, // 1 minute
  })
}

/**
 * Hook to create or update a file
 */
export function useCreateOrUpdateFile(owner: string, repo: string) {
  const queryClient = useQueryClient()

  return useMutation<
    FileOperationResult,
    Error,
    { path: string; data: CreateFileRequest }
  >({
    mutationFn: ({ path, data }) => createOrUpdateFile(owner, repo, path, data),
    onSuccess: (_, { path, data }) => {
      // Invalidate file and directory queries
      queryClient.invalidateQueries({ queryKey: githubRepoKeys.file(owner, repo, path) })
      const dirPath = path.split("/").slice(0, -1).join("/")
      queryClient.invalidateQueries({
        queryKey: githubRepoKeys.directory(owner, repo, dirPath, data.branch),
      })
      queryClient.invalidateQueries({ queryKey: githubRepoKeys.tree(owner, repo, "HEAD") })
      queryClient.invalidateQueries({ queryKey: githubRepoKeys.commits(owner, repo) })
    },
  })
}

// ============================================================================
// Commit Hooks
// ============================================================================

/**
 * Hook to list repository commits
 */
export function useGitHubCommits(owner: string, repo: string, params?: ListCommitsParams) {
  return useQuery<GitHubCommitInfo[]>({
    queryKey: githubRepoKeys.commits(owner, repo, params),
    queryFn: () => listCommits(owner, repo, params),
    enabled: !!owner && !!repo,
    staleTime: 30 * 1000, // 30 seconds
  })
}

// ============================================================================
// Pull Request Hooks
// ============================================================================

/**
 * Hook to list repository pull requests
 */
export function useGitHubPullRequests(
  owner: string,
  repo: string,
  params?: ListPullRequestsParams
) {
  return useQuery<GitHubPullRequest[]>({
    queryKey: githubRepoKeys.pullRequests(owner, repo, params),
    queryFn: () => listPullRequests(owner, repo, params),
    enabled: !!owner && !!repo,
    staleTime: 30 * 1000, // 30 seconds
  })
}

/**
 * Hook to create a pull request
 */
export function useCreatePullRequest(owner: string, repo: string) {
  const queryClient = useQueryClient()

  return useMutation<PullRequestCreateResult, Error, CreatePullRequestRequest>({
    mutationFn: (data) => createPullRequest(owner, repo, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: githubRepoKeys.pullRequests(owner, repo) })
    },
  })
}
