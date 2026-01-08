"""Branch workflow service for ticket-based development.

Phase 5: BranchWorkflowService

This service handles the Git branch lifecycle for tickets:
- Creating feature branches when tasks start
- Creating PRs when tasks complete
- Managing the branch lifecycle (Musubi workflow)

Follows standard GitFlow naming conventions:
- feature/{ticket-id}-{description} for features
- fix/{ticket-id}-{description} for bug fixes
- hotfix/{ticket-id}-{description} for critical bugs
- refactor/{ticket-id}-{description} for refactoring
- docs/{ticket-id}-{description} for documentation
- test/{ticket-id}-{description} for test additions
- chore/{ticket-id}-{description} for maintenance
"""

import asyncio
import re
from typing import Any, Optional

from omoi_os.logging import get_logger
from omoi_os.services.github_api import GitHubAPIService

logger = get_logger(__name__)


# Type prefix mapping from ticket type to branch prefix
TYPE_PREFIX_MAP = {
    "feature": "feature",
    "bug": "fix",
    "refactor": "refactor",
    "docs": "docs",
    "test": "test",
    "chore": "chore",
}


class BranchWorkflowService:
    """
    Branch workflow service for ticket-based development.
    
    Handles:
    - Creating branches with descriptive names
    - PR creation and management
    - Merge coordination
    - Rollback and recovery
    
    Example:
        >>> service = BranchWorkflowService(github_service=github_api)
        >>> result = await service.start_work_on_ticket(
        ...     ticket_id="123",
        ...     ticket_title="Add user authentication",
        ...     repo_owner="myorg",
        ...     repo_name="myapp",
        ...     user_id="user-uuid-123"
        ... )
        >>> print(result["branch_name"])  # "feature/123-user-auth"
    """

    def __init__(
        self,
        github_service: GitHubAPIService,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        """
        Initialize the BranchWorkflowService.
        
        Args:
            github_service: GitHubAPIService instance for GitHub operations
            max_retries: Maximum number of retries for transient failures
            retry_delay: Base delay between retries (with exponential backoff)
        """
        self.github_service = github_service
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    def _generate_branch_name_sync(
        self,
        ticket_id: str,
        ticket_title: str,
        ticket_type: str = "feature",
        priority: Optional[str] = None,
        existing_branches: Optional[list[str]] = None,
    ) -> str:
        """
        Generate a branch name following GitFlow conventions.
        
        Format: {type}/{ticket-id}-{description}
        
        Args:
            ticket_id: Unique ticket identifier
            ticket_title: Human-readable ticket title
            ticket_type: Type of ticket (feature, bug, refactor, etc.)
            priority: Priority level (critical makes bugs into hotfixes)
            existing_branches: List of existing branch names to avoid collisions
            
        Returns:
            Generated branch name
        """
        existing_branches = existing_branches or []
        
        # Determine prefix from type
        if ticket_type == "bug" and priority == "critical":
            prefix = "hotfix"
        else:
            prefix = TYPE_PREFIX_MAP.get(ticket_type, "feature")
        
        # Generate description slug from title
        # Remove special characters, lowercase, replace spaces with hyphens
        slug = re.sub(r"[^a-zA-Z0-9\s-]", "", ticket_title.lower())
        slug = re.sub(r"\s+", "-", slug.strip())
        # Limit slug length
        slug = slug[:25].rstrip("-")
        
        # Build branch name
        branch_name = f"{prefix}/{ticket_id}-{slug}"
        
        # Handle collisions
        if branch_name in existing_branches:
            i = 2
            while f"{branch_name}-{i}" in existing_branches:
                i += 1
            branch_name = f"{branch_name}-{i}"
        
        return branch_name

    async def _retry_operation(
        self,
        operation,
        operation_name: str,
        *args,
        **kwargs,
    ) -> Any:
        """
        Retry an async operation with exponential backoff.
        
        Args:
            operation: Async function to retry
            operation_name: Human-readable name for logging
            *args, **kwargs: Arguments to pass to operation
            
        Returns:
            Result from operation
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                return await operation(*args, **kwargs)
            except Exception as e:
                last_exception = e
                delay = self.retry_delay * (2 ** attempt)
                logger.warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{self.max_retries}): {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
        
        raise last_exception  # type: ignore

    async def start_work_on_ticket(
        self,
        ticket_id: str,
        ticket_title: str,
        repo_owner: str,
        repo_name: str,
        user_id: str,
        ticket_type: str = "feature",
        priority: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a branch for working on a ticket.
        
        This is the first step in the workflow when an agent starts working
        on a ticket. It creates a new feature branch from the default branch.
        
        Args:
            ticket_id: Unique ticket identifier
            ticket_title: Human-readable ticket title
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            user_id: User ID for authentication
            ticket_type: Type of ticket (feature, bug, refactor, etc.)
            priority: Priority level (critical bugs become hotfixes)
            
        Returns:
            Dict with keys:
            - success: bool
            - branch_name: str (if successful)
            - sha: str (branch SHA, if successful)
            - error: str (if failed)
        """
        try:
            # Get repository info for default branch
            repo_info = await self.github_service.get_repo(user_id, repo_owner, repo_name)
            default_branch = None
            if repo_info and repo_info.default_branch:
                default_branch = repo_info.default_branch

            # Get existing branches for collision detection and to find default branch SHA
            branches = await self.github_service.list_branches(user_id, repo_owner, repo_name)
            existing_branch_names = [b.name for b in branches]

            if not branches:
                logger.error(
                    f"No branches found for {repo_owner}/{repo_name}. "
                    "Repository may be empty or inaccessible."
                )
                return {
                    "success": False,
                    "error": f"No branches found in {repo_owner}/{repo_name}. Repository may be empty.",
                }

            # Find SHA of default branch with fallback logic
            source_sha = None

            # First, try the default branch from repo info
            if default_branch:
                for branch in branches:
                    if branch.name == default_branch:
                        source_sha = branch.sha
                        break

            # If not found, try common default branch names
            if not source_sha:
                common_defaults = ["main", "master", "develop", "trunk"]
                for fallback_name in common_defaults:
                    for branch in branches:
                        if branch.name == fallback_name:
                            logger.warning(
                                f"Default branch '{default_branch}' not found, "
                                f"falling back to '{fallback_name}'"
                            )
                            default_branch = fallback_name
                            source_sha = branch.sha
                            break
                    if source_sha:
                        break

            # Last resort: use the first branch we find
            if not source_sha and branches:
                first_branch = branches[0]
                logger.warning(
                    f"No common default branch found, using first available: '{first_branch.name}'"
                )
                default_branch = first_branch.name
                source_sha = first_branch.sha

            if not source_sha:
                return {
                    "success": False,
                    "error": f"Could not find any branch to create from in {repo_owner}/{repo_name}",
                }
            
            # Generate branch name
            branch_name = self._generate_branch_name_sync(
                ticket_id=ticket_id,
                ticket_title=ticket_title,
                ticket_type=ticket_type,
                priority=priority,
                existing_branches=existing_branch_names,
            )
            
            # Create branch with retry
            async def create_branch():
                return await self.github_service.create_branch(
                    user_id=user_id,
                    owner=repo_owner,
                    repo=repo_name,
                    branch_name=branch_name,
                    from_sha=source_sha,
                )
            
            result = await self._retry_operation(
                create_branch,
                f"Create branch {branch_name}",
            )
            
            if not result.success:
                return {
                    "success": False,
                    "error": result.error or "Failed to create branch",
                }
            
            logger.info(f"Created branch {branch_name} for ticket {ticket_id}")
            
            return {
                "success": True,
                "branch_name": branch_name,
                "sha": result.sha,
            }
            
        except Exception as e:
            logger.error(f"Failed to start work on ticket {ticket_id}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def finish_work_on_ticket(
        self,
        ticket_id: str,
        ticket_title: str,
        branch_name: str,
        repo_owner: str,
        repo_name: str,
        user_id: str,
        pr_body: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a pull request for completed ticket work.
        
        This is called when an agent finishes working on a ticket and is
        ready to submit a PR for review.
        
        Args:
            ticket_id: Unique ticket identifier
            ticket_title: Human-readable ticket title
            branch_name: Feature branch name
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            user_id: User ID for authentication
            pr_body: Optional custom PR body (defaults to ticket reference)
            
        Returns:
            Dict with keys:
            - success: bool
            - pr_number: int (if successful)
            - pr_url: str (if successful)
            - error: str (if failed)
        """
        try:
            # Get default branch
            repo_info = await self.github_service.get_repo(user_id, repo_owner, repo_name)
            base_branch = repo_info.default_branch if repo_info else "main"
            
            # Build PR title and body
            pr_title = f"[{ticket_id}] {ticket_title}"
            if not pr_body:
                pr_body = f"Resolves #{ticket_id}\n\nAutomated PR for ticket {ticket_id}."
            
            # Create PR with retry
            async def create_pr():
                return await self.github_service.create_pull_request(
                    user_id=user_id,
                    owner=repo_owner,
                    repo=repo_name,
                    title=pr_title,
                    head=branch_name,
                    base=base_branch,
                    body=pr_body,
                )
            
            result = await self._retry_operation(
                create_pr,
                f"Create PR for ticket {ticket_id}",
            )
            
            if not result.success:
                return {
                    "success": False,
                    "error": result.error or "Failed to create PR",
                }
            
            logger.info(f"Created PR #{result.number} for ticket {ticket_id}")
            
            return {
                "success": True,
                "pr_number": result.number,
                "pr_url": result.html_url,
            }
            
        except Exception as e:
            logger.error(f"Failed to finish work on ticket {ticket_id}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def merge_ticket_work(
        self,
        ticket_id: str,
        pr_number: int,
        repo_owner: str,
        repo_name: str,
        user_id: str,
        delete_branch_after: bool = True,
        merge_method: str = "squash",
    ) -> dict[str, Any]:
        """
        Merge the PR for a ticket.
        
        This is called when a PR is approved and ready to be merged.
        It checks for merge conflicts before attempting to merge.
        
        Args:
            ticket_id: Unique ticket identifier
            pr_number: Pull request number
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            user_id: User ID for authentication
            delete_branch_after: Whether to delete the branch after merge
            merge_method: How to merge ("merge", "squash", "rebase")
            
        Returns:
            Dict with keys:
            - success: bool
            - merge_sha: str (if successful)
            - has_conflicts: bool (True if merge blocked by conflicts)
            - error: str (if failed)
        """
        try:
            # Get PR details to check if mergeable
            pr = await self.github_service.get_pull_request(
                user_id=user_id,
                owner=repo_owner,
                repo=repo_name,
                pr_number=pr_number,
            )
            
            if not pr:
                return {
                    "success": False,
                    "error": f"PR #{pr_number} not found",
                }
            
            # Check if PR has conflicts
            if pr.mergeable is False:
                logger.warning(f"PR #{pr_number} has merge conflicts")
                return {
                    "success": False,
                    "has_conflicts": True,
                    "error": "PR has merge conflicts and cannot be merged",
                }
            
            # Merge the PR
            merge_result = await self.github_service.merge_pull_request(
                user_id=user_id,
                owner=repo_owner,
                repo=repo_name,
                pr_number=pr_number,
                merge_method=merge_method,
                commit_title=f"[{ticket_id}] Merge PR #{pr_number}",
            )
            
            if not merge_result.success:
                return {
                    "success": False,
                    "error": merge_result.error or "Merge failed",
                }
            
            logger.info(f"Merged PR #{pr_number} for ticket {ticket_id}")
            
            # Delete branch if requested
            if delete_branch_after and pr.head_branch:
                try:
                    await self.github_service.delete_branch(
                        user_id=user_id,
                        owner=repo_owner,
                        repo=repo_name,
                        branch_name=pr.head_branch,
                    )
                    logger.info(f"Deleted branch {pr.head_branch}")
                except Exception as e:
                    logger.warning(f"Failed to delete branch {pr.head_branch}: {e}")
            
            return {
                "success": True,
                "merge_sha": merge_result.sha,
            }
            
        except Exception as e:
            logger.error(f"Failed to merge PR #{pr_number} for ticket {ticket_id}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def handle_agent_failure(
        self,
        ticket_id: str,
        branch_name: str,
        repo_owner: str,
        repo_name: str,
        user_id: str,
        failure_reason: str,
    ) -> dict[str, Any]:
        """
        Handle agent failure during ticket work.
        
        IMPORTANT: Agent crashes should NOT delete the branch.
        This preserves any uncommitted work and allows for recovery.
        
        Args:
            ticket_id: Unique ticket identifier
            branch_name: Feature branch name
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            user_id: User ID for authentication
            failure_reason: Reason for failure (e.g., "agent_crash", "timeout")
            
        Returns:
            Dict with handling result
        """
        logger.warning(
            f"Agent failure for ticket {ticket_id} on branch {branch_name}: {failure_reason}"
        )
        
        # DO NOT delete the branch - preserve work for manual recovery
        # The branch can be checked out manually to recover any committed work
        
        return {
            "success": True,
            "action": "preserved",
            "message": f"Branch {branch_name} preserved for manual recovery",
            "branch_name": branch_name,
        }

    async def get_branch_status(
        self,
        branch_name: str,
        repo_owner: str,
        repo_name: str,
        user_id: str,
    ) -> dict[str, Any]:
        """
        Get the status of a branch compared to main.
        
        Args:
            branch_name: Feature branch name
            repo_owner: GitHub repository owner
            repo_name: GitHub repository name
            user_id: User ID for authentication
            
        Returns:
            Dict with branch status including ahead/behind counts
        """
        try:
            repo_info = await self.github_service.get_repo(user_id, repo_owner, repo_name)
            base_branch = repo_info.default_branch if repo_info else "main"
            
            comparison = await self.github_service.compare_branches(
                user_id=user_id,
                owner=repo_owner,
                repo=repo_name,
                base=base_branch,
                head=branch_name,
            )
            
            if not comparison:
                return {
                    "success": False,
                    "error": "Could not compare branches",
                }
            
            return {
                "success": True,
                "branch_name": branch_name,
                "base_branch": base_branch,
                "status": comparison.status,
                "ahead_by": comparison.ahead_by,
                "behind_by": comparison.behind_by,
                "total_commits": comparison.total_commits,
                "files_changed": len(comparison.files),
            }
            
        except Exception as e:
            logger.error(f"Failed to get branch status for {branch_name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }
