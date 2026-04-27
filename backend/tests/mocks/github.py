"""Mock GitHub service for testing.

Provides in-memory GitHub operations for testing without API calls.
"""


class MockGitHubService:
    """Mock GitHub service with in-memory state tracking.

    Simulates GitHub operations (branches, PRs) in memory for testing
    without making actual API calls.
    """

    def __init__(self):
        """Initialize the mock GitHub service."""
        self.branches: dict[str, dict] = {"main": {"sha": "abc123"}}
        self.pull_requests: list[dict] = []
        self.operations: list[dict] = []

    async def create_branch(
        self, owner: str, repo: str, branch_name: str, source_sha: str
    ) -> dict:
        """Create a branch in memory.

        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: Name for the new branch
            source_sha: Source commit SHA

        Returns:
            Branch info dict
        """
        branch_info = {
            "name": branch_name,
            "sha": source_sha,
            "owner": owner,
            "repo": repo,
        }
        self.branches[branch_name] = branch_info
        self.operations.append(
            {
                "type": "create_branch",
                "owner": owner,
                "repo": repo,
                "branch_name": branch_name,
                "source_sha": source_sha,
            }
        )
        return branch_info

    async def delete_branch(self, owner: str, repo: str, branch_name: str) -> bool:
        """Delete a branch from memory.

        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: Name of the branch to delete

        Returns:
            True if deleted, False if not found
        """
        if branch_name in self.branches:
            del self.branches[branch_name]
            self.operations.append(
                {
                    "type": "delete_branch",
                    "owner": owner,
                    "repo": repo,
                    "branch_name": branch_name,
                }
            )
            return True
        return False

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        head: str,
        base: str,
        body: str = "",
    ) -> dict:
        """Create a PR in memory.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            head: Head branch name
            base: Base branch name
            body: PR description

        Returns:
            PR info dict
        """
        pr_number = len(self.pull_requests) + 1
        pr_info = {
            "number": pr_number,
            "title": title,
            "head": head,
            "base": base,
            "body": body,
            "owner": owner,
            "repo": repo,
            "state": "open",
        }
        self.pull_requests.append(pr_info)
        self.operations.append(
            {
                "type": "create_pull_request",
                "owner": owner,
                "repo": repo,
                "title": title,
                "head": head,
                "base": base,
            }
        )
        return pr_info

    async def get_repository(self, owner: str, repo: str) -> dict | None:
        """Return mock repository info.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Mock repository info
        """
        return {
            "owner": owner,
            "repo": repo,
            "default_branch": "main",
            "full_name": f"{owner}/{repo}",
        }

    async def get_branch(self, owner: str, repo: str, branch_name: str) -> dict | None:
        """Get branch info from memory.

        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: Name of the branch

        Returns:
            Branch info or None if not found
        """
        return self.branches.get(branch_name)

    async def list_branches(self, owner: str, repo: str) -> list[dict]:
        """List all branches in memory.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of branch info dicts
        """
        return list(self.branches.values())

    def assert_branch_created(self, branch_name: str) -> None:
        """Assert that a branch was created.

        Args:
            branch_name: Expected branch name

        Raises:
            AssertionError: If branch was not created
        """
        if branch_name not in self.branches:
            raise AssertionError(f"Branch '{branch_name}' was not created")

    def assert_pr_created(self, title: str) -> None:
        """Assert that a PR was created with a specific title.

        Args:
            title: Expected PR title

        Raises:
            AssertionError: If PR with title was not created
        """
        for pr in self.pull_requests:
            if pr["title"] == title:
                return
        raise AssertionError(f"PR with title '{title}' was not created")

    def reset(self) -> None:
        """Clear all state."""
        self.branches = {"main": {"sha": "abc123"}}
        self.pull_requests.clear()
        self.operations.clear()
