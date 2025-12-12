# Branch Management & Merge Architecture (Musubi)

**Created**: 2025-12-12  
**Status**: Planning Document  
**Purpose**: Architecture for managing branches, merging, and conflict resolution with AI agents
**Codename**: Musubi (結び) - "binding together"

> **Note**: "Musubi" is the documentation name for this subsystem. Code uses standard, descriptive names.

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [What We Already Have](#what-we-already-have)
3. [What We Need](#what-we-need)
4. [Branch Management Workflow](#branch-management-workflow)
5. [Merge & Conflict Resolution](#merge--conflict-resolution)
6. [Implementation Plan](#implementation-plan)
7. [Code Examples](#code-examples)

---

## Executive Summary

### ✅ What Exists (Solid Foundation!)

We have a **comprehensive GitHub integration** including:
- `GitHubAPIService` - Full API wrapper (repos, branches, files, commits, PRs)
- `GitHubIntegrationService` - Webhook handling, project connection
- `GitHubTools` - Agent-friendly tools for GitHub operations
- `Project` model with `github_owner`, `github_repo` fields
- OAuth token management per user
- Frontend hooks for all operations

### ❌ What's Missing (For Full Workflow)

1. **Merge PR** - No method to merge a pull request
2. **Compare Branches** - No diff/comparison endpoint
3. **PR Merge Status** - Need `mergeable`, `conflicts` info
4. **Delete Branch** - Clean up after merge
5. **Clone Repo to Sandbox** - Integration with Daytona
6. **Job → Branch Mapping** - Auto-create branch per ticket/task
7. **Multi-branch Coordination** - Tree of branches for parallel work
8. **AI Conflict Resolution** - Agent-based merge conflict handling

### Estimated Effort

| Component | Effort |
|-----------|--------|
| GitHub API Extensions | 4-6 hours |
| Branch Workflow Service | 8-12 hours |
| Sandbox Git Integration | 6-8 hours |
| AI Conflict Resolution | 12-16 hours |
| **Total** | **30-42 hours** |

---

## What We Already Have

### 1. GitHubAPIService ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                EXISTING: GitHubAPIService (github_api.py)                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Repository Operations:                                                     │
│  ├─ list_user_repos(user_id, visibility, sort, per_page, fetch_all_pages)  │
│  ├─ get_repo(user_id, owner, repo)                                         │
│  └─ OAuth token per user (stored in user.attributes)                       │
│                                                                             │
│  Branch Operations:                                                         │
│  ├─ list_branches(user_id, owner, repo)                                    │
│  └─ create_branch(user_id, owner, repo, branch_name, from_sha)             │
│                                                                             │
│  File Operations:                                                           │
│  ├─ get_file_content(user_id, owner, repo, path, ref)                      │
│  ├─ create_or_update_file(user_id, owner, repo, path, content, msg, sha)   │
│  ├─ list_directory(user_id, owner, repo, path, ref)                        │
│  └─ get_tree(user_id, owner, repo, tree_sha, recursive)                    │
│                                                                             │
│  Commit Operations:                                                         │
│  └─ list_commits(user_id, owner, repo, sha, path, per_page)                │
│                                                                             │
│  Pull Request Operations:                                                   │
│  ├─ list_pull_requests(user_id, owner, repo, state, per_page)              │
│  └─ create_pull_request(user_id, owner, repo, title, head, base, body)     │
│                                                                             │
│  Pydantic Models:                                                           │
│  ├─ GitHubRepo, GitHubBranch, GitHubFile                                   │
│  ├─ GitHubCommit, GitHubPullRequest                                        │
│  ├─ DirectoryItem, TreeItem                                                │
│  ├─ FileOperationResult, BranchCreateResult                                │
│  └─ PullRequestCreateResult                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. GitHubTools (Agent Interface) ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 EXISTING: GitHubTools (github_tools.py)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Agent-friendly wrappers:                                                   │
│  ├─ list_repos(visibility, limit)                                          │
│  ├─ read_file(owner, repo, path, branch)                                   │
│  ├─ write_file(owner, repo, path, content, message, branch)                │
│  ├─ list_files(owner, repo, path, branch)                                  │
│  ├─ get_repo_tree(owner, repo, branch)                                     │
│  ├─ create_branch(owner, repo, branch_name, from_branch)                   │
│  ├─ create_pull_request(owner, repo, title, head, base, body)              │
│  ├─ get_repo_info(owner, repo)                                             │
│  └─ list_branches(owner, repo)                                             │
│                                                                             │
│  Factory: create_github_tools(db, user_id) -> GitHubTools                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. Project-GitHub Connection ✅

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXISTING: Project Model (project.py)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  class Project:                                                             │
│      github_owner: Optional[str]                                           │
│      github_repo: Optional[str]                                            │
│      github_webhook_secret: Optional[str]                                  │
│      github_connected: bool                                                │
│                                                                             │
│  GitHubIntegrationService:                                                  │
│  ├─ connect_repository(project_id, owner, repo, webhook_secret)            │
│  ├─ handle_webhook(event_type, payload, signature, secret)                 │
│  ├─ _handle_push_event() - links commits to tickets                        │
│  ├─ _handle_pull_request_event()                                           │
│  └─ _extract_ticket_id_from_message()                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## What We Need

### Gap 1: Merge PR & PR Status ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        NEEDED: Merge Operations                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  New Methods for GitHubAPIService:                                          │
│                                                                             │
│  async def get_pull_request(                                                │
│      user_id, owner, repo, pr_number                                       │
│  ) -> GitHubPullRequest:                                                    │
│      """Get PR details including mergeable status."""                       │
│      # Returns: number, title, state, mergeable, mergeable_state,          │
│      #          merge_commit_sha, conflicts, head, base                    │
│                                                                             │
│  async def merge_pull_request(                                              │
│      user_id, owner, repo, pr_number,                                      │
│      merge_method="merge",  # "merge", "squash", "rebase"                  │
│      commit_title=None, commit_message=None                                │
│  ) -> MergeResult:                                                          │
│      """Merge a pull request."""                                            │
│      # POST /repos/{owner}/{repo}/pulls/{pr_number}/merge                  │
│                                                                             │
│  async def delete_branch(                                                   │
│      user_id, owner, repo, branch_name                                     │
│  ) -> DeleteBranchResult:                                                   │
│      """Delete a branch after merge."""                                     │
│      # DELETE /repos/{owner}/{repo}/git/refs/heads/{branch_name}           │
│                                                                             │
│  Effort: ~2-3 hours                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 2: Compare Branches ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       NEEDED: Branch Comparison                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  async def compare_branches(                                                │
│      user_id, owner, repo, base, head                                      │
│  ) -> BranchComparison:                                                     │
│      """Compare two branches and get diff."""                               │
│      # GET /repos/{owner}/{repo}/compare/{base}...{head}                   │
│      # Returns: status, ahead_by, behind_by, total_commits,                │
│      #          files (with patches), commits                              │
│                                                                             │
│  class BranchComparison(BaseModel):                                         │
│      status: str  # "ahead", "behind", "diverged", "identical"             │
│      ahead_by: int                                                         │
│      behind_by: int                                                        │
│      total_commits: int                                                    │
│      files: list[FileDiff]                                                 │
│      commits: list[GitHubCommit]                                           │
│      mergeable: bool                                                       │
│      has_conflicts: bool                                                   │
│                                                                             │
│  class FileDiff(BaseModel):                                                 │
│      filename: str                                                         │
│      status: str  # "added", "modified", "removed", "renamed"              │
│      additions: int                                                        │
│      deletions: int                                                        │
│      changes: int                                                          │
│      patch: Optional[str]  # Unified diff                                  │
│                                                                             │
│  Effort: ~2-3 hours                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 3: Clone Repo to Sandbox ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEEDED: Sandbox Git Integration                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Current Flow (via GitHub API):                                             │
│  ├─ Agent reads files via API                                              │
│  ├─ Agent writes files via API (creates commit per file)                   │
│  └─ Not efficient for large changes                                        │
│                                                                             │
│  Needed Flow (Git in Sandbox):                                              │
│  ├─ Clone repo into Daytona sandbox                                        │
│  ├─ Agent works on local files                                             │
│  ├─ Agent commits multiple changes in one commit                           │
│  ├─ Push to remote branch                                                  │
│  └─ Create PR via API                                                      │
│                                                                             │
│  Implementation:                                                            │
│                                                                             │
│  1. Worker script clones repo on startup:                                   │
│     git clone https://x-access-token:{TOKEN}@github.com/{owner}/{repo}     │
│     git checkout -b {task_branch_name}                                     │
│                                                                             │
│  2. Agent tools work on local filesystem (already have bash tool)          │
│                                                                             │
│  3. New sandbox tools:                                                      │
│     - git_commit(files, message)                                           │
│     - git_push()                                                           │
│     - git_status()                                                         │
│     - git_diff()                                                           │
│                                                                             │
│  4. On task completion:                                                     │
│     git push -u origin {task_branch_name}                                  │
│     Create PR via API                                                      │
│                                                                             │
│  Effort: ~6-8 hours                                                         │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 4: Job → Branch Mapping ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       NEEDED: BranchWorkflowService                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Purpose: Manage branch lifecycle for tickets with AI-generated names       │
│                                                                             │
│  class BranchWorkflowService:                                               │
│                                                                             │
│      async def start_work_on_ticket(                                        │
│          ticket_id: str,                                                   │
│          user_id: UUID                                                     │
│      ) -> WorkflowBranch:                                                   │
│          """                                                                │
│          1. Get ticket and project                                         │
│          2. Create branch: omoios/ticket-{ticket_id}                       │
│          3. Store branch name in ticket/task                               │
│          4. Return branch info                                             │
│          """                                                                │
│                                                                             │
│      async def finish_work_on_ticket(                                       │
│          ticket_id: str,                                                   │
│          user_id: UUID                                                     │
│      ) -> WorkflowResult:                                                   │
│          """                                                                │
│          1. Create PR from ticket branch to main                           │
│          2. Add ticket link to PR description                              │
│          3. Request merge or await review                                  │
│          4. Update ticket status                                           │
│          """                                                                │
│                                                                             │
│      async def merge_ticket_work(                                           │
│          ticket_id: str,                                                   │
│          user_id: UUID                                                     │
│      ) -> MergeResult:                                                      │
│          """                                                                │
│          1. Get PR for ticket                                              │
│          2. Check if mergeable                                             │
│          3. If conflicts, trigger AI resolution                            │
│          4. Merge PR                                                       │
│          5. Delete branch                                                  │
│          6. Update ticket status                                           │
│          """                                                                │
│                                                                             │
│  Database: Add fields to Task/Ticket model                                  │
│  ├─ branch_name: Optional[str]                                             │
│  ├─ pr_number: Optional[int]                                               │
│  └─ pr_url: Optional[str]                                                  │
│                                                                             │
│  Effort: ~8-12 hours                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 5: Multi-Branch Coordination ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   NEEDED: Multi-Branch Coordination                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Scenario: Multiple agents working on related tickets in parallel           │
│                                                                             │
│                     main                                                    │
│                       │                                                     │
│                       ├─── omoios/ticket-123 (Agent A)                     │
│                       │         │                                           │
│                       │         └─── omoios/ticket-456 (Agent B, depends)  │
│                       │                                                     │
│                       └─── omoios/ticket-789 (Agent C, independent)        │
│                                                                             │
│  Challenges:                                                                │
│  ├─ Dependency ordering: Agent B needs Agent A's changes                   │
│  ├─ Merge conflicts between parallel branches                              │
│  └─ Integration testing before final merge                                 │
│                                                                             │
│  Solution: BranchCoordinationService                                        │
│                                                                             │
│  async def coordinate_parallel_work(                                        │
│      ticket_ids: list[str]                                                 │
│  ) -> CoordinationPlan:                                                     │
│      """                                                                    │
│      1. Analyze ticket dependencies                                        │
│      2. Create DAG of branch dependencies                                  │
│      3. Determine merge order                                              │
│      4. Return coordination plan                                           │
│      """                                                                    │
│                                                                             │
│  async def merge_in_order(                                                  │
│      coordination_plan: CoordinationPlan                                   │
│  ) -> list[MergeResult]:                                                    │
│      """                                                                    │
│      1. Merge in dependency order                                          │
│      2. Rebase dependent branches after each merge                         │
│      3. Handle conflicts at each step                                      │
│      4. Rollback if critical failure                                       │
│      """                                                                    │
│                                                                             │
│  Effort: ~8-12 hours                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Gap 6: AI Conflict Resolution ❌

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEEDED: AI Conflict Resolution                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  When merge conflicts occur, an AI agent resolves them:                     │
│                                                                             │
│  Flow:                                                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  1. Detect conflict during merge attempt                            │   │
│  │              │                                                      │   │
│  │              ▼                                                      │   │
│  │  2. Fetch conflicting files with diff markers                       │   │
│  │              │                                                      │   │
│  │              ▼                                                      │   │
│  │  3. Spawn merge agent in sandbox                                    │   │
│  │     - Clone repo                                                    │   │
│  │     - Checkout base branch                                          │   │
│  │     - Attempt merge (will fail with conflicts)                      │   │
│  │              │                                                      │   │
│  │              ▼                                                      │   │
│  │  4. Agent analyzes conflicts                                        │   │
│  │     - Read original file from base branch                           │   │
│  │     - Read modified file from head branch                           │   │
│  │     - Understand intent of both changes                             │   │
│  │              │                                                      │   │
│  │              ▼                                                      │   │
│  │  5. Agent resolves conflicts                                        │   │
│  │     - Edit files to resolve markers                                 │   │
│  │     - Ensure code compiles/tests pass                               │   │
│  │     - git add resolved files                                        │   │
│  │              │                                                      │   │
│  │              ▼                                                      │   │
│  │  6. Create merge commit                                             │   │
│  │     git commit -m "Resolve merge conflicts"                         │   │
│  │              │                                                      │   │
│  │              ▼                                                      │   │
│  │  7. Push and complete PR merge                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  class ConflictResolutionService:                                           │
│                                                                             │
│      async def resolve_conflicts(                                           │
│          owner: str, repo: str, pr_number: int, user_id: UUID              │
│      ) -> ResolutionResult:                                                 │
│          """                                                                │
│          1. Get PR with conflict details                                   │
│          2. Spawn sandbox with repo cloned                                 │
│          3. Agent resolves conflicts                                       │
│          4. Push resolution                                                │
│          5. Return result                                                  │
│          """                                                                │
│                                                                             │
│      async def _get_conflict_files(                                         │
│          owner: str, repo: str, pr_number: int                             │
│      ) -> list[ConflictFile]:                                               │
│          """Get files with conflicts and their content."""                  │
│                                                                             │
│      async def _spawn_merge_agent(                                          │
│          task_context: MergeTaskContext                                    │
│      ) -> SandboxResult:                                                    │
│          """Spawn agent to resolve conflicts."""                           │
│                                                                             │
│  Effort: ~12-16 hours                                                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Branch Management Workflow

### Complete Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    COMPLETE BRANCH MANAGEMENT WORKFLOW                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  USER                OMOIOS                    GITHUB              SANDBOX  │
│    │                   │                         │                    │     │
│    │  Create Ticket    │                         │                    │     │
│    │──────────────────>│                         │                    │     │
│    │                   │                         │                    │     │
│    │                   │  Create Branch          │                    │     │
│    │                   │  omoios/ticket-{id}     │                    │     │
│    │                   │────────────────────────>│                    │     │
│    │                   │                         │                    │     │
│    │  Assign to Agent  │                         │                    │     │
│    │──────────────────>│                         │                    │     │
│    │                   │                         │                    │     │
│    │                   │  Spawn Sandbox          │                    │     │
│    │                   │  (Daytona)              │                    │     │
│    │                   │─────────────────────────┼───────────────────>│     │
│    │                   │                         │                    │     │
│    │                   │                         │  Clone + Checkout  │     │
│    │                   │                         │<───────────────────│     │
│    │                   │                         │                    │     │
│    │                   │               Agent Works Locally            │     │
│    │                   │                         │<───────────────────│     │
│    │                   │                         │  Edit Files        │     │
│    │                   │                         │  Run Tests         │     │
│    │                   │                         │  Commit            │     │
│    │                   │                         │                    │     │
│    │                   │                         │  Push Branch       │     │
│    │                   │                         │<───────────────────│     │
│    │                   │                         │                    │     │
│    │                   │  Create PR              │                    │     │
│    │                   │────────────────────────>│                    │     │
│    │                   │                         │                    │     │
│    │  Review PR        │                         │                    │     │
│    │<──────────────────│                         │                    │     │
│    │                   │                         │                    │     │
│    │  Approve Merge    │                         │                    │     │
│    │──────────────────>│                         │                    │     │
│    │                   │                         │                    │     │
│    │                   │  Check Conflicts?       │                    │     │
│    │                   │────────────────────────>│                    │     │
│    │                   │                         │                    │     │
│    │                   │  [No Conflicts]         │                    │     │
│    │                   │  Merge PR               │                    │     │
│    │                   │────────────────────────>│                    │     │
│    │                   │                         │                    │     │
│    │                   │  [Has Conflicts]        │                    │     │
│    │                   │  Spawn Merge Agent      │                    │     │
│    │                   │─────────────────────────┼───────────────────>│     │
│    │                   │                         │<───────────────────│     │
│    │                   │                         │  Resolve Conflicts │     │
│    │                   │                         │  Push Resolution   │     │
│    │                   │                         │                    │     │
│    │                   │  Merge PR               │                    │     │
│    │                   │────────────────────────>│                    │     │
│    │                   │                         │                    │     │
│    │                   │  Delete Branch          │                    │     │
│    │                   │────────────────────────>│                    │     │
│    │                   │                         │                    │     │
│    │                   │  Update Ticket Status   │                    │     │
│    │<──────────────────│                         │                    │     │
│    │                   │                         │                    │     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Branch Naming Convention (Standard GitFlow + AI Description)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   BRANCH NAMING CONVENTION                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Pattern: {type}/{ticket-id}-{ai-generated-description}                     │
│                                                                             │
│  Uses standard GitFlow prefixes + ticket ID for traceability.               │
│  AI generates ONLY the descriptive suffix.                                  │
│                                                                             │
│  Input: Ticket                          Output: Branch Name                 │
│  ┌────────────────────────────────┐    ┌────────────────────────────────┐  │
│  │ ID: TICKET-123                 │    │                                │  │
│  │ Title: Fix button alignment    │    │ fix/TICKET-123-login-btn-align │  │
│  │        on login page           │ => │                                │  │
│  │ Type: bug                      │    │                                │  │
│  └────────────────────────────────┘    └────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────────────┐    ┌────────────────────────────────┐  │
│  │ ID: TICKET-456                 │    │                                │  │
│  │ Title: Add dark mode support   │    │ feature/TICKET-456-dark-mode   │  │
│  │        with user preference    │ => │                                │  │
│  │ Type: feature                  │    │                                │  │
│  └────────────────────────────────┘    └────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────────────┐    ┌────────────────────────────────┐  │
│  │ ID: TICKET-789                 │    │                                │  │
│  │ Title: Refactor database       │    │ refactor/TICKET-789-db-pool    │  │
│  │        connection pooling      │ => │                                │  │
│  │ Type: refactor                 │    │                                │  │
│  └────────────────────────────────┘    └────────────────────────────────┘  │
│                                                                             │
│  ┌────────────────────────────────┐    ┌────────────────────────────────┐  │
│  │ ID: TICKET-999                 │    │                                │  │
│  │ Title: URGENT: Payment webhook │    │ hotfix/TICKET-999-stripe-retry │  │
│  │        failing                 │ => │                                │  │
│  │ Type: bug, priority: critical  │    │                                │  │
│  └────────────────────────────────┘    └────────────────────────────────┘  │
│                                                                             │
│  Type Prefixes (Standard GitFlow):                                          │
│  ├─ feature/  New functionality                                            │
│  ├─ fix/      Bug fixes                                                    │
│  ├─ hotfix/   Critical/urgent fixes                                        │
│  ├─ refactor/ Code improvements                                            │
│  ├─ docs/     Documentation changes                                        │
│  ├─ test/     Test additions/fixes                                         │
│  └─ chore/    Maintenance tasks                                            │
│                                                                             │
│  AI generates ONLY the description suffix:                                  │
│  ├─ Max 25 characters                                                      │
│  ├─ Lowercase, hyphen-separated                                            │
│  ├─ Captures essence of the change                                         │
│  └─ Examples: "dark-mode", "login-btn-align", "stripe-retry"               │
│                                                                             │
│  Benefits:                                                                  │
│  ├─ Standard GitFlow (familiar to all devs)                                │
│  ├─ Traceable via ticket ID                                                │
│  ├─ Human-readable descriptions                                            │
│  ├─ Easy to filter: git branch | grep feature/                             │
│  └─ Easy to find: git branch | grep TICKET-123                             │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Branch Name Generation Service

```python
# backend/omoi_os/services/branch_naming.py

from typing import Optional
from pydantic import BaseModel
import instructor
from anthropic import Anthropic


class BranchNameRequest(BaseModel):
    """Input for AI branch description generation."""
    ticket_id: str                    # e.g., "TICKET-123"
    ticket_title: str
    ticket_description: Optional[str] = None
    ticket_type: str = "feature"      # feature, bug, refactor, docs, test, chore
    priority: Optional[str] = None    # low, medium, high, critical


class BranchNameResult(BaseModel):
    """Generated branch name."""
    branch_name: str      # Full: feature/TICKET-123-dark-mode
    description: str      # Just the AI part: dark-mode
    type_prefix: str      # feature, fix, hotfix, etc.


async def generate_branch_name(
    request: BranchNameRequest,
    existing_branches: list[str] = [],
) -> BranchNameResult:
    """
    Generate a branch name with AI-created description.
    
    Format: {type}/{ticket-id}-{ai-description}
    Example: feature/TICKET-123-dark-mode-toggle
    
    Args:
        request: Ticket information
        existing_branches: Existing branch names (for collision avoidance)
    
    Returns:
        Generated branch name
    """
    client = instructor.from_anthropic(Anthropic())
    
    # Map ticket type to standard GitFlow prefix
    type_map = {
        "feature": "feature",
        "bug": "fix",
        "refactor": "refactor",
        "docs": "docs",
        "test": "test",
        "chore": "chore",
    }
    
    # Critical bugs become hotfixes
    if request.ticket_type == "bug" and request.priority == "critical":
        prefix = "hotfix"
    else:
        prefix = type_map.get(request.ticket_type, "feature")
    
    prompt = f"""Generate a short, descriptive slug for a Git branch.

Ticket: {request.ticket_id}
Title: {request.ticket_title}
{f"Description: {request.ticket_description}" if request.ticket_description else ""}

Requirements:
- Max 25 characters
- Lowercase, hyphen-separated
- Capture the essence of the change
- Be specific but concise
- Will be used in: {prefix}/{request.ticket_id}-<YOUR_SLUG>

Good examples:
- "dark-mode" (not "add-dark-mode-feature")
- "login-btn-align" (not "fix-button-alignment-issue")
- "stripe-retry" (not "fix-stripe-webhook")
- "db-pool-perf" (not "database-refactor")

Return ONLY the slug, no prefix or ticket ID.
"""
    
    class GeneratedSlug(BaseModel):
        slug: str
    
    result = client.chat.completions.create(
        model="claude-sonnet-4-20250514",
        response_model=GeneratedSlug,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
    )
    
    # Build full branch name: feature/TICKET-123-dark-mode
    branch_name = f"{prefix}/{request.ticket_id}-{result.slug}"
    
    # Handle collisions
    if branch_name in existing_branches:
        i = 2
        while f"{branch_name}-{i}" in existing_branches:
            i += 1
        branch_name = f"{branch_name}-{i}"
        result.slug = f"{result.slug}-{i}"
    
    return BranchNameResult(
        branch_name=branch_name,
        description=result.slug,
        type_prefix=prefix,
    )
```

---

## Merge & Conflict Resolution

### Conflict Detection Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      CONFLICT DETECTION FLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. PR Created                                                              │
│         │                                                                   │
│         ▼                                                                   │
│  2. GitHub calculates mergeable status                                      │
│     GET /repos/{owner}/{repo}/pulls/{pr_number}                            │
│         │                                                                   │
│         ├── mergeable: true ──────────────> Safe to merge                  │
│         │                                                                   │
│         ├── mergeable: false ─────────────> Conflicts exist                │
│         │                                                                   │
│         └── mergeable: null ──────────────> Still calculating              │
│                                             (retry after delay)            │
│                                                                             │
│  3. If conflicts, get details:                                              │
│     GET /repos/{owner}/{repo}/compare/{base}...{head}                      │
│         │                                                                   │
│         └── files: [ { filename, status, patch } ]                         │
│                                                                             │
│  4. Conflict file patterns:                                                 │
│     <<<<<<< HEAD                                                           │
│     (changes from base branch)                                             │
│     =======                                                                │
│     (changes from head branch)                                             │
│     >>>>>>> {branch_name}                                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### AI Conflict Resolution Strategy

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   AI CONFLICT RESOLUTION STRATEGY                            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Agent Receives:                                                            │
│  ├─ Original file (from common ancestor)                                   │
│  ├─ Base version (from target branch)                                      │
│  ├─ Head version (from source branch)                                      │
│  ├─ Unified diff with conflict markers                                     │
│  ├─ Ticket context (what changes were intended)                            │
│  └─ PR description                                                         │
│                                                                             │
│  Agent Strategy:                                                            │
│                                                                             │
│  1. UNDERSTAND both changes                                                 │
│     - What was the intent of base change?                                  │
│     - What was the intent of head change?                                  │
│     - Are they logically compatible?                                       │
│                                                                             │
│  2. CATEGORIZE conflict type                                                │
│     - Same line, different changes (harder)                                │
│     - Adjacent line changes (usually mergeable)                            │
│     - Function/block level conflict (may need refactor)                    │
│     - Import/dependency conflict (usually simple)                          │
│                                                                             │
│  3. RESOLVE based on category                                               │
│     - Compatible: Include both changes                                     │
│     - Semantic conflict: Understand intent, pick best or combine           │
│     - Code structure: May need refactoring                                 │
│                                                                             │
│  4. VERIFY resolution                                                       │
│     - No remaining conflict markers                                        │
│     - Code compiles/lints                                                  │
│     - Tests pass (if available)                                            │
│     - Logic makes sense                                                    │
│                                                                             │
│  5. DOCUMENT resolution                                                     │
│     - Add comment explaining resolution strategy                           │
│     - Update PR description with resolution notes                          │
│                                                                             │
│  Edge Cases:                                                                │
│  ├─ Binary files: Cannot auto-resolve, flag for human                      │
│  ├─ Large conflicts: May spawn sub-tasks                                   │
│  └─ Semantic conflicts: Flag for review if uncertain                       │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Plan

### Phase 1: GitHub API Extensions (4-6 hours)

```
Tasks:
□ Add get_pull_request(pr_number) - includes mergeable status
□ Add merge_pull_request(pr_number, method, message)
□ Add delete_branch(branch_name)
□ Add compare_branches(base, head)
□ Add corresponding REST API endpoints
□ Add frontend hooks
□ Write tests
```

### Phase 2: Branch Workflow Service (8-12 hours)

```
Tasks:
□ Add branch_name, pr_number, pr_url fields to Task model
□ Create BranchWorkflowService class
□ Implement start_work_on_ticket()
□ Implement finish_work_on_ticket()
□ Implement merge_ticket_work()
□ Add REST API endpoints for workflow actions
□ Write tests
```

### Phase 3: Sandbox Git Integration (6-8 hours)

```
Tasks:
□ Update worker script to clone repo on startup
□ Add git_commit tool for agents
□ Add git_push tool for agents
□ Add git_status tool for agents
□ Add git_diff tool for agents
□ Test with Daytona sandbox
□ Write tests
```

### Phase 4: AI Conflict Resolution (12-16 hours)

```
Tasks:
□ Create ConflictResolutionService class
□ Implement conflict detection from PR status
□ Implement conflict file fetching
□ Create merge agent prompt/template
□ Implement spawn_merge_agent()
□ Implement resolution verification
□ Add REST API endpoints
□ Write tests
□ Create merge agent tools (resolve_conflict, verify_resolution)
```

---

## Code Examples

### Example 1: New GitHub API Methods

```python
# backend/omoi_os/services/github_api.py (additions)

class MergeResult(BaseModel):
    """Result of a PR merge."""
    success: bool
    sha: Optional[str] = None
    message: str
    error: Optional[str] = None

class BranchComparison(BaseModel):
    """Comparison between two branches."""
    status: str  # "ahead", "behind", "diverged", "identical"
    ahead_by: int
    behind_by: int
    total_commits: int
    files: list[dict]
    mergeable: bool = True
    has_conflicts: bool = False

class GitHubAPIService:
    # ... existing methods ...

    async def get_pull_request(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> Optional[GitHubPullRequest]:
        """Get PR details including mergeable status."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}",
                headers=self._headers(token),
            )

            if response.status_code != 200:
                return None

            pr = response.json()
            return GitHubPullRequest(
                number=pr["number"],
                title=pr["title"],
                state=pr["state"],
                html_url=pr["html_url"],
                head_branch=pr["head"]["ref"],
                base_branch=pr["base"]["ref"],
                body=pr.get("body"),
                merged=pr.get("merged", False),
                mergeable=pr.get("mergeable"),
                draft=pr.get("draft", False),
            )

    async def merge_pull_request(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        pr_number: int,
        merge_method: str = "merge",  # "merge", "squash", "rebase"
        commit_title: Optional[str] = None,
        commit_message: Optional[str] = None,
    ) -> MergeResult:
        """Merge a pull request."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return MergeResult(success=False, message="No token", error="No GitHub token")

        data: dict[str, Any] = {"merge_method": merge_method}
        if commit_title:
            data["commit_title"] = commit_title
        if commit_message:
            data["commit_message"] = commit_message

        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{self.BASE_URL}/repos/{owner}/{repo}/pulls/{pr_number}/merge",
                headers=self._headers(token),
                json=data,
            )

            result = response.json()

            if response.status_code == 200:
                return MergeResult(
                    success=True,
                    sha=result.get("sha"),
                    message=result.get("message", "PR merged successfully"),
                )
            elif response.status_code == 405:
                return MergeResult(
                    success=False,
                    message="PR not mergeable",
                    error=result.get("message", "Merge conflicts or other issue"),
                )
            else:
                return MergeResult(
                    success=False,
                    message="Merge failed",
                    error=result.get("message", "Unknown error"),
                )

    async def delete_branch(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        branch_name: str,
    ) -> bool:
        """Delete a branch."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return False

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/repos/{owner}/{repo}/git/refs/heads/{branch_name}",
                headers=self._headers(token),
            )

            return response.status_code == 204

    async def compare_branches(
        self,
        user_id: UUID,
        owner: str,
        repo: str,
        base: str,
        head: str,
    ) -> Optional[BranchComparison]:
        """Compare two branches."""
        token = self._get_user_token_by_id(user_id)
        if not token:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/repos/{owner}/{repo}/compare/{base}...{head}",
                headers=self._headers(token),
            )

            if response.status_code != 200:
                return None

            data = response.json()
            return BranchComparison(
                status=data["status"],
                ahead_by=data["ahead_by"],
                behind_by=data["behind_by"],
                total_commits=data["total_commits"],
                files=[
                    {
                        "filename": f["filename"],
                        "status": f["status"],
                        "additions": f["additions"],
                        "deletions": f["deletions"],
                        "patch": f.get("patch"),
                    }
                    for f in data.get("files", [])
                ],
            )
```

### Example 2: Branch Workflow Service

```python
# backend/omoi_os/services/branch_workflow.py

from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from omoi_os.services.database import DatabaseService
from omoi_os.services.github_api import GitHubAPIService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.branch_naming import generate_branch_name, BranchNameRequest
from omoi_os.models.ticket import Ticket
from omoi_os.models.project import Project


class WorkflowBranch(BaseModel):
    """Branch created for a ticket."""
    branch_name: str      # feature/TICKET-123-dark-mode
    sha: str
    ticket_id: str
    project_id: str


class WorkflowResult(BaseModel):
    """Result of a workflow operation."""
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    message: str
    error: Optional[str] = None


class BranchWorkflowService:
    """
    Branch workflow service for ticket-based development.
    
    Handles:
    - Creating branches with AI-generated descriptions
    - PR creation and management
    - Merge coordination
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: EventBusService,
    ):
        self.db = db
        self.event_bus = event_bus

    async def _generate_branch_name(
        self, 
        ticket: Ticket,
        existing_branches: list[str],
    ) -> str:
        """
        Generate branch name with AI description.
        
        Returns:
            Full branch name (e.g., feature/TICKET-123-dark-mode)
        """
        result = await generate_branch_name(
            BranchNameRequest(
                ticket_id=ticket.id,
                ticket_title=ticket.title or "Untitled task",
                ticket_description=ticket.description,
                ticket_type=ticket.ticket_type or "feature",
                priority=ticket.priority,
            ),
            existing_branches=existing_branches,
        )
        return result.branch_name

    async def start_work_on_ticket(
        self,
        ticket_id: str,
        user_id: UUID,
    ) -> WorkflowBranch:
        """Create a branch for working on a ticket (with AI-generated description)."""
        github_api = GitHubAPIService(self.db)

        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")

            project = session.get(Project, ticket.project_id)
            if not project or not project.github_owner or not project.github_repo:
                raise ValueError(f"Project {ticket.project_id} not connected to GitHub")

            # Get existing branches for collision detection
            branches = await github_api.list_branches(
                user_id=user_id,
                owner=project.github_owner,
                repo=project.github_repo,
            )
            existing_branch_names = [b.name for b in branches]

            repo_info = await github_api.get_repo(
                user_id=user_id,
                owner=project.github_owner,
                repo=project.github_repo,
            )

            default_branch = repo_info.default_branch if repo_info else "main"
            source_sha = None
            for b in branches:
                if b.name == default_branch:
                    source_sha = b.sha
                    break

            if not source_sha:
                raise ValueError(f"Default branch {default_branch} not found")

            # Generate branch name with AI description
            branch_name = await self._generate_branch_name(ticket, existing_branch_names)

            # Create branch
            result = await github_api.create_branch(
                user_id=user_id,
                owner=project.github_owner,
                repo=project.github_repo,
                branch_name=branch_name,
                from_sha=source_sha,
            )

            if not result.success:
                raise ValueError(f"Failed to create branch: {result.error}")

            # Update ticket with branch info
            ticket.attributes = ticket.attributes or {}
            ticket.attributes["branch_name"] = branch_name
            session.commit()

            # Emit event
            self.event_bus.publish(SystemEvent(
                event_type="BRANCH_CREATED",
                entity_type="ticket",
                entity_id=ticket_id,
                payload={
                    "branch_name": branch_name,
                    "sha": result.sha,
                    "project_id": project.id,
                },
            ))

            return WorkflowBranch(
                branch_name=branch_name,
                sha=result.sha or "",
                ticket_id=ticket_id,
                project_id=project.id,
            )

    async def finish_work_on_ticket(
        self,
        ticket_id: str,
        user_id: UUID,
        pr_title: Optional[str] = None,
        pr_body: Optional[str] = None,
    ) -> WorkflowResult:
        """Create a PR for completed ticket work."""
        github_api = GitHubAPIService(self.db)

        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return WorkflowResult(success=False, message="Ticket not found")

            project = session.get(Project, ticket.project_id)
            if not project or not project.github_owner:
                return WorkflowResult(success=False, message="Project not connected to GitHub")

            branch_name = (ticket.attributes or {}).get("branch_name")
            if not branch_name:
                return WorkflowResult(success=False, message="No branch associated with ticket")

            # Get default branch
            repo_info = await github_api.get_repo(
                user_id=user_id,
                owner=project.github_owner,
                repo=project.github_repo,
            )
            base_branch = repo_info.default_branch if repo_info else "main"

            # Create PR
            title = pr_title or f"[{ticket_id}] {ticket.title}"
            body = pr_body or f"Resolves #{ticket_id}\n\n{ticket.description or ''}"

            result = await github_api.create_pull_request(
                user_id=user_id,
                owner=project.github_owner,
                repo=project.github_repo,
                title=title,
                head=branch_name,
                base=base_branch,
                body=body,
            )

            if not result.success:
                return WorkflowResult(
                    success=False,
                    message="Failed to create PR",
                    error=result.error,
                )

            # Update ticket with PR info
            ticket.attributes = ticket.attributes or {}
            ticket.attributes["pr_number"] = result.number
            ticket.attributes["pr_url"] = result.html_url
            session.commit()

            # Emit event
            self.event_bus.publish(SystemEvent(
                event_type="PR_CREATED",
                entity_type="ticket",
                entity_id=ticket_id,
                payload={
                    "pr_number": result.number,
                    "pr_url": result.html_url,
                    "branch_name": branch_name,
                },
            ))

            return WorkflowResult(
                success=True,
                pr_number=result.number,
                pr_url=result.html_url,
                message="PR created successfully",
            )

    async def merge_ticket_work(
        self,
        ticket_id: str,
        user_id: UUID,
        delete_branch_after: bool = True,
    ) -> WorkflowResult:
        """Merge the PR for a ticket."""
        github_api = GitHubAPIService(self.db)

        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return WorkflowResult(success=False, message="Ticket not found")

            project = session.get(Project, ticket.project_id)
            if not project or not project.github_owner:
                return WorkflowResult(success=False, message="Project not connected")

            pr_number = (ticket.attributes or {}).get("pr_number")
            branch_name = (ticket.attributes or {}).get("branch_name")

            if not pr_number:
                return WorkflowResult(success=False, message="No PR associated with ticket")

            # Check if mergeable
            pr = await github_api.get_pull_request(
                user_id=user_id,
                owner=project.github_owner,
                repo=project.github_repo,
                pr_number=pr_number,
            )

            if not pr:
                return WorkflowResult(success=False, message="PR not found")

            if pr.mergeable is False:
                return WorkflowResult(
                    success=False,
                    message="PR has merge conflicts",
                    error="Conflicts need to be resolved before merging",
                )

            # Merge the PR
            result = await github_api.merge_pull_request(
                user_id=user_id,
                owner=project.github_owner,
                repo=project.github_repo,
                pr_number=pr_number,
                merge_method="squash",
                commit_title=f"[{ticket_id}] {ticket.title}",
            )

            if not result.success:
                return WorkflowResult(
                    success=False,
                    message="Merge failed",
                    error=result.error,
                )

            # Delete branch if requested
            if delete_branch_after and branch_name:
                await github_api.delete_branch(
                    user_id=user_id,
                    owner=project.github_owner,
                    repo=project.github_repo,
                    branch_name=branch_name,
                )

            # Update ticket
            ticket.attributes["merged"] = True
            ticket.attributes["merge_sha"] = result.sha
            session.commit()

            # Emit event
            self.event_bus.publish(SystemEvent(
                event_type="PR_MERGED",
                entity_type="ticket",
                entity_id=ticket_id,
                payload={
                    "pr_number": pr_number,
                    "merge_sha": result.sha,
                    "branch_deleted": delete_branch_after,
                },
            ))

            return WorkflowResult(
                success=True,
                pr_number=pr_number,
                message="PR merged successfully",
            )
```

### Example 3: Worker Script with Git Clone

```python
# Addition to worker script in daytona_spawner.py

WORKER_SCRIPT_WITH_GIT = '''
import os
import subprocess
import requests

# Environment variables
SANDBOX_ID = os.environ.get("SANDBOX_ID")
TASK_ID = os.environ.get("TASK_ID")
MCP_SERVER_URL = os.environ.get("MCP_SERVER_URL")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_REPO = os.environ.get("GITHUB_REPO")  # format: owner/repo
BRANCH_NAME = os.environ.get("BRANCH_NAME")

def clone_repo():
    """Clone the GitHub repo and checkout the work branch."""
    if not GITHUB_TOKEN or not GITHUB_REPO:
        print("No GitHub credentials, skipping clone")
        return False
    
    owner, repo = GITHUB_REPO.split("/")
    clone_url = f"https://x-access-token:{GITHUB_TOKEN}@github.com/{owner}/{repo}.git"
    
    # Clone the repo
    result = subprocess.run(
        ["git", "clone", clone_url, "/workspace"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Clone failed: {result.stderr}")
        return False
    
    os.chdir("/workspace")
    
    # Checkout or create the work branch
    if BRANCH_NAME:
        # Try to checkout existing branch
        result = subprocess.run(
            ["git", "checkout", BRANCH_NAME],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            # Create new branch
            result = subprocess.run(
                ["git", "checkout", "-b", BRANCH_NAME],
                capture_output=True,
                text=True
            )
    
    return True

def git_commit(files: list[str], message: str) -> dict:
    """Stage files and create a commit."""
    # Add files
    for file in files:
        subprocess.run(["git", "add", file], cwd="/workspace")
    
    # Commit
    result = subprocess.run(
        ["git", "commit", "-m", message],
        capture_output=True,
        text=True,
        cwd="/workspace"
    )
    
    if result.returncode == 0:
        # Get commit SHA
        sha_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd="/workspace"
        )
        return {"success": True, "sha": sha_result.stdout.strip()}
    else:
        return {"success": False, "error": result.stderr}

def git_push() -> dict:
    """Push commits to remote."""
    result = subprocess.run(
        ["git", "push", "-u", "origin", BRANCH_NAME],
        capture_output=True,
        text=True,
        cwd="/workspace"
    )
    
    if result.returncode == 0:
        return {"success": True}
    else:
        return {"success": False, "error": result.stderr}

def git_status() -> dict:
    """Get git status."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True,
        text=True,
        cwd="/workspace"
    )
    
    files = []
    for line in result.stdout.strip().split("\n"):
        if line:
            status = line[:2].strip()
            filename = line[3:]
            files.append({"status": status, "file": filename})
    
    return {"files": files}

# Clone repo on startup if credentials are provided
if GITHUB_TOKEN and GITHUB_REPO:
    clone_repo()
'''
```

### Example 4: Conflict Resolution Agent Prompt

```markdown
# Merge Conflict Resolution Agent

## Context
You are an AI agent specialized in resolving Git merge conflicts. You have been given:
- The conflicting files with conflict markers
- The original file (common ancestor)
- The changes from the base branch
- The changes from the head branch
- Ticket/PR context explaining the intent of changes

## Your Task
Analyze the conflicts and resolve them by:
1. Understanding the intent of both sets of changes
2. Determining if changes are compatible or incompatible
3. Creating a merged version that preserves both intents where possible
4. Making judgment calls when changes conflict semantically

## Conflict Markers
```
<<<<<<< HEAD
(code from the base branch - target of merge)
=======
(code from the head branch - your changes)
>>>>>>> branch-name
```

## Resolution Guidelines

### Compatible Changes (MERGE BOTH)
- Changes to different lines in the same function
- Additions that don't overlap
- Import statements

### Semantic Conflicts (ANALYZE INTENT)
- Same variable/function modified differently
- Logic changes that affect the same behavior
- Configuration changes

### Decision Framework
1. If both changes add functionality: Include both
2. If one refactors and one adds: Apply refactor, then add
3. If both modify same logic: Understand higher-level intent, pick best
4. If unclear: Flag for human review

## Output Format
1. Explain your understanding of each change
2. State your resolution strategy
3. Provide the resolved file content
4. Note any concerns or areas needing human review

## Tools Available
- `read_file(path)` - Read file content
- `write_file(path, content)` - Write resolved content
- `run_command(cmd)` - Run shell commands (for testing)
- `git_add(files)` - Stage resolved files
- `report_progress(message)` - Report status
```

### Example 5: REST API Endpoints

```python
# backend/omoi_os/api/routes/branch_workflow.py

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from omoi_os.api.dependencies import get_db_service, get_current_user, get_event_bus
from omoi_os.models.user import User
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.branch_workflow import BranchWorkflowService, WorkflowResult


router = APIRouter(prefix="/workflow", tags=["branch-workflow"])


class FinishWorkRequest(BaseModel):
    """Request to finish work on a ticket."""
    pr_title: Optional[str] = None
    pr_body: Optional[str] = None


class MergeWorkRequest(BaseModel):
    """Request to merge ticket work."""
    delete_branch_after: bool = True


def get_workflow_service(
    db: DatabaseService = Depends(get_db_service),
    event_bus: EventBusService = Depends(get_event_bus),
) -> BranchWorkflowService:
    return BranchWorkflowService(db, event_bus)


@router.post("/tickets/{ticket_id}/branch")
async def start_work_on_ticket(
    ticket_id: str,
    current_user: User = Depends(get_current_user),
    workflow: BranchWorkflowService = Depends(get_workflow_service),
):
    """
    Create a branch for working on a ticket.
    
    Uses AI to generate a descriptive branch name.
    Format: {type}/{ticket-id}-{description}
    Example: feature/TICKET-123-dark-mode
    """
    try:
        result = await workflow.start_work_on_ticket(
            ticket_id=ticket_id,
            user_id=current_user.id,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tickets/{ticket_id}/pr")
async def finish_work_on_ticket(
    ticket_id: str,
    request: FinishWorkRequest,
    current_user: User = Depends(get_current_user),
    workflow: BranchWorkflowService = Depends(get_workflow_service),
):
    """Create a PR for completed ticket work."""
    result = await workflow.finish_work_on_ticket(
        ticket_id=ticket_id,
        user_id=current_user.id,
        pr_title=request.pr_title,
        pr_body=request.pr_body,
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or result.message)
    
    return result


@router.post("/tickets/{ticket_id}/merge")
async def merge_ticket_work(
    ticket_id: str,
    request: MergeWorkRequest,
    current_user: User = Depends(get_current_user),
    workflow: BranchWorkflowService = Depends(get_workflow_service),
):
    """Merge the PR for a ticket."""
    result = await workflow.merge_ticket_work(
        ticket_id=ticket_id,
        user_id=current_user.id,
        delete_branch_after=request.delete_branch_after,
    )
    
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error or result.message)
    
    return result
```

---

## Summary

### What We Have ✅

| Component | Status | Location |
|-----------|--------|----------|
| GitHub OAuth | ✅ Complete | `services/github_api.py` |
| List/Get Repos | ✅ Complete | `services/github_api.py` |
| List/Create Branches | ✅ Complete | `services/github_api.py` |
| File CRUD | ✅ Complete | `services/github_api.py` |
| List Commits | ✅ Complete | `services/github_api.py` |
| List/Create PRs | ✅ Complete | `services/github_api.py` |
| Agent GitHub Tools | ✅ Complete | `tools/github_tools.py` |
| Webhook Handling | ✅ Complete | `services/github_integration.py` |
| Project-GitHub Link | ✅ Complete | `models/project.py` |
| Frontend Hooks | ✅ Complete | `hooks/useGitHubRepos.ts` |

### What We Need ❌

| Component | Status | Priority | Effort |
|-----------|--------|----------|--------|
| Merge PR | ❌ Missing | High | 2h |
| Compare Branches | ❌ Missing | High | 2h |
| Delete Branch | ❌ Missing | Medium | 1h |
| PR Merge Status | ❌ Missing | High | 1h |
| BranchWorkflowService | ❌ Missing | High | 8-12h |
| AI Branch Naming | ❌ Missing | High | 2-3h |
| Sandbox Git Clone | ❌ Missing | High | 6-8h |
| Conflict Resolution Agent | ❌ Missing | Medium | 12-16h |
| Multi-branch Coordination | ❌ Missing | Low | 8-12h |

### Recommended Implementation Order

1. **Phase 1** (4-6h): GitHub API extensions (merge, compare, delete)
2. **Phase 2** (10-15h): BranchWorkflowService + AI Branch Naming (ticket → branch → PR → merge)
3. **Phase 3** (6-8h): Sandbox Git integration (clone, commit, push in Daytona)
4. **Phase 4** (12-16h): Conflict resolution agent

---

## Existing Code References

- **GitHub API Service**: `backend/omoi_os/services/github_api.py`
- **GitHub Tools**: `backend/omoi_os/tools/github_tools.py`
- **GitHub Integration**: `backend/omoi_os/services/github_integration.py`
- **GitHub Routes**: `backend/omoi_os/api/routes/github_repos.py`
- **Project Model**: `backend/omoi_os/models/project.py`
- **Frontend Hooks**: `frontend/hooks/useGitHubRepos.ts`
- **Daytona Spawner**: `backend/omoi_os/services/daytona_spawner.py`

## New Files to Create

```
backend/omoi_os/services/
├── branch_workflow.py        # BranchWorkflowService - main workflow orchestration
├── branch_naming.py          # AI-powered branch description generation
└── conflict_resolver.py      # AI-powered merge conflict resolution

backend/omoi_os/api/routes/
└── branch_workflow.py        # REST API endpoints

frontend/hooks/
└── useBranchWorkflow.ts      # React hooks for workflow operations
```