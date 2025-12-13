"""Test BranchWorkflowService for Git branch lifecycle management.

Phase 5: Branch Workflow Service

Tests Requirements:
- Branch creation for tickets (start_work_on_ticket)
- PR creation when work completes (finish_work_on_ticket)
- PR merge and branch cleanup (merge_ticket_work)
- Rollback and recovery strategies
"""

from omoi_os.services.branch_workflow import BranchWorkflowService
import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.mark.asyncio
@pytest.mark.unit
async def test_start_work_creates_branch():
    """
    SPEC: start_work_on_ticket should create a new branch.

    Given a ticket ID and repository info,
    When start_work_on_ticket is called,
    Then a new feature branch should be created via GitHub API.
    """

    # Arrange: Mock GitHub service
    mock_github = MagicMock()
    mock_github.create_branch = AsyncMock(
        return_value=MagicMock(
            success=True, ref="refs/heads/feature/123-add-auth", sha="abc123"
        )
    )
    # Include default branch in list_branches response
    # Note: MagicMock(name="main") sets mock's internal name, not .name attribute
    main_branch = MagicMock()
    main_branch.name = "main"
    main_branch.sha = "def456"
    mock_github.list_branches = AsyncMock(return_value=[main_branch])
    mock_github.get_repo = AsyncMock(return_value=MagicMock(default_branch="main"))

    service = BranchWorkflowService(github_service=mock_github)

    # Act
    result = await service.start_work_on_ticket(
        ticket_id="123",
        ticket_title="Add authentication",
        repo_owner="myorg",
        repo_name="myapp",
        user_id="user-uuid-123",
    )

    # Assert
    assert result["success"] is True, f"Expected success but got: {result}"
    assert "feature/" in result["branch_name"]
    mock_github.create_branch.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_start_work_generates_branch_name():
    """
    SPEC: Branch names should follow the convention {type}/{ticket-id}-{description}.

    Given a ticket with type "bug",
    When start_work_on_ticket is called,
    Then branch name should be like "fix/456-descriptive-name".
    """

    mock_github = MagicMock()
    mock_github.create_branch = AsyncMock(
        return_value=MagicMock(
            success=True, ref="refs/heads/fix/456-btn-align", sha="abc123"
        )
    )
    # Include default branch in list_branches response
    main_branch = MagicMock()
    main_branch.name = "main"
    main_branch.sha = "def456"
    mock_github.list_branches = AsyncMock(return_value=[main_branch])
    mock_github.get_repo = AsyncMock(return_value=MagicMock(default_branch="main"))

    service = BranchWorkflowService(github_service=mock_github)

    result = await service.start_work_on_ticket(
        ticket_id="456",
        ticket_title="Fix button alignment on login page",
        ticket_type="bug",
        repo_owner="myorg",
        repo_name="myapp",
        user_id="user-uuid-123",
    )

    assert result["success"] is True, f"Expected success but got: {result}"
    # Bug type should produce fix/ prefix
    assert result["branch_name"].startswith("fix/") and "456" in result["branch_name"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_finish_work_creates_pr():
    """
    SPEC: finish_work_on_ticket should create a pull request.

    Given a completed ticket with a branch,
    When finish_work_on_ticket is called,
    Then a PR should be created from the feature branch to main.
    """

    mock_github = MagicMock()
    mock_github.create_pull_request = AsyncMock(
        return_value=MagicMock(
            success=True,
            number=42,
            html_url="https://github.com/myorg/myapp/pull/42",
        )
    )
    mock_github.get_repo = AsyncMock(return_value=MagicMock(default_branch="main"))

    service = BranchWorkflowService(github_service=mock_github)

    result = await service.finish_work_on_ticket(
        ticket_id="123",
        ticket_title="Add authentication",
        branch_name="feature/123-add-auth",
        repo_owner="myorg",
        repo_name="myapp",
        user_id="user-uuid-123",
    )

    assert result["success"] is True
    assert result["pr_number"] == 42
    assert "pull/42" in result["pr_url"]
    mock_github.create_pull_request.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_finish_work_pr_body_includes_ticket_reference():
    """
    SPEC: PR body should reference the ticket.

    When a PR is created for a ticket,
    Then the PR body should include a reference to the ticket.
    """

    mock_github = MagicMock()
    mock_github.create_pull_request = AsyncMock(
        return_value=MagicMock(
            success=True, number=42, html_url="https://github.com/myorg/myapp/pull/42"
        )
    )
    mock_github.get_repo = AsyncMock(return_value=MagicMock(default_branch="main"))

    service = BranchWorkflowService(github_service=mock_github)

    await service.finish_work_on_ticket(
        ticket_id="123",
        ticket_title="Add authentication",
        branch_name="feature/123-add-auth",
        repo_owner="myorg",
        repo_name="myapp",
        user_id="user-uuid-123",
    )

    # Verify PR was created with ticket reference in title or body
    call_kwargs = mock_github.create_pull_request.call_args
    pr_title = call_kwargs.kwargs.get("title", "")
    pr_body = call_kwargs.kwargs.get("body", "")

    assert "123" in pr_title or "123" in pr_body


@pytest.mark.asyncio
@pytest.mark.unit
async def test_merge_work_completes_pr():
    """
    SPEC: merge_ticket_work should merge PR and cleanup branch.

    Given a mergeable PR,
    When merge_ticket_work is called,
    Then the PR should be merged and the branch deleted.
    """

    mock_github = MagicMock()
    mock_github.get_pull_request = AsyncMock(
        return_value=MagicMock(
            number=42, mergeable=True, state="open", head_branch="feature/123-add-auth"
        )
    )
    mock_github.merge_pull_request = AsyncMock(
        return_value=MagicMock(success=True, sha="merge123")
    )
    mock_github.delete_branch = AsyncMock(return_value=True)

    service = BranchWorkflowService(github_service=mock_github)

    result = await service.merge_ticket_work(
        ticket_id="123",
        pr_number=42,
        repo_owner="myorg",
        repo_name="myapp",
        user_id="user-uuid-123",
    )

    assert result["success"] is True
    mock_github.merge_pull_request.assert_called_once()
    mock_github.delete_branch.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_merge_work_skip_branch_delete():
    """
    SPEC: Branch deletion can be optionally skipped.

    When merge_ticket_work is called with delete_branch_after=False,
    Then the branch should NOT be deleted.
    """

    mock_github = MagicMock()
    mock_github.get_pull_request = AsyncMock(
        return_value=MagicMock(
            number=42, mergeable=True, state="open", head_branch="feature/123-add-auth"
        )
    )
    mock_github.merge_pull_request = AsyncMock(
        return_value=MagicMock(success=True, sha="merge123")
    )
    mock_github.delete_branch = AsyncMock(return_value=True)

    service = BranchWorkflowService(github_service=mock_github)

    result = await service.merge_ticket_work(
        ticket_id="123",
        pr_number=42,
        repo_owner="myorg",
        repo_name="myapp",
        user_id="user-uuid-123",
        delete_branch_after=False,
    )

    assert result["success"] is True
    mock_github.merge_pull_request.assert_called_once()
    mock_github.delete_branch.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_pr_conflict_does_not_auto_merge():
    """
    SPEC: PR with conflicts should NOT be auto-merged.

    Given a PR with merge conflicts,
    When merge_ticket_work is called,
    Then it should return failure with has_conflicts=True.
    """

    mock_github = MagicMock()
    mock_github.get_pull_request = AsyncMock(
        return_value=MagicMock(
            number=42,
            mergeable=False,
            state="open",
            head_branch="feature/123-add-auth",
        )
    )

    service: BranchWorkflowService = BranchWorkflowService(github_service=mock_github)

    result = await service.merge_ticket_work(
        ticket_id="123",
        pr_number=42,
        repo_owner="myorg",
        repo_name="myapp",
        user_id="user-uuid-123",
    )

    # VERIFY: Did NOT attempt to merge
    assert result["success"] is False
    assert result.get("has_conflicts") is True
    mock_github.merge_pull_request.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_branch_creation_retry_on_transient_failure():
    """
    SPEC: Branch creation should retry on GitHub API failures.

    Given transient GitHub API failures,
    When start_work_on_ticket is called,
    Then it should retry up to 3 times before failing.
    """

    mock_github = MagicMock()
    # First two calls fail, third succeeds
    mock_github.create_branch = AsyncMock(
        side_effect=[
            Exception("GitHub API rate limited"),
            Exception("GitHub API timeout"),
            MagicMock(success=True, ref="refs/heads/feature/123", sha="abc123"),
        ]
    )
    # Include default branch in list_branches response
    main_branch = MagicMock()
    main_branch.name = "main"
    main_branch.sha = "def456"
    mock_github.list_branches = AsyncMock(return_value=[main_branch])
    mock_github.get_repo = AsyncMock(return_value=MagicMock(default_branch="main"))

    # Use shorter retry delay for test
    service = BranchWorkflowService(github_service=mock_github, retry_delay=0.01)

    result = await service.start_work_on_ticket(
        ticket_id="123",
        ticket_title="Test",
        repo_owner="org",
        repo_name="repo",
        user_id="user-uuid-123",
    )

    # VERIFY: Succeeded after retries
    assert result["success"] is True, f"Expected success but got: {result}"
    assert mock_github.create_branch.call_count == 3


@pytest.mark.asyncio
@pytest.mark.unit
async def test_branch_creation_fails_after_max_retries():
    """
    SPEC: Branch creation should fail after exhausting retries.

    Given persistent GitHub API failures,
    When start_work_on_ticket exhausts all retries,
    Then it should return failure.
    """

    mock_github = MagicMock()
    mock_github.create_branch = AsyncMock(
        side_effect=Exception("Persistent GitHub API failure")
    )
    # Include default branch in list_branches response
    main_branch = MagicMock()
    main_branch.name = "main"
    main_branch.sha = "def456"
    mock_github.list_branches = AsyncMock(return_value=[main_branch])
    mock_github.get_repo = AsyncMock(return_value=MagicMock(default_branch="main"))

    # Use shorter retry delay for test
    service = BranchWorkflowService(github_service=mock_github, retry_delay=0.01)

    result = await service.start_work_on_ticket(
        ticket_id="123",
        ticket_title="Test",
        repo_owner="org",
        repo_name="repo",
        user_id="user-uuid-123",
    )

    assert result["success"] is False
    assert "error" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_agent_crash_preserves_branch():
    """
    SPEC: Agent crash should NOT delete the branch (preserves work).

    When handle_agent_failure is called after an agent crash,
    Then the branch should NOT be deleted.
    """

    mock_github = MagicMock()
    mock_github.delete_branch = AsyncMock(return_value=True)

    service = BranchWorkflowService(github_service=mock_github)

    # Simulate agent crash cleanup
    await service.handle_agent_failure(
        ticket_id="123",
        branch_name="feature/123-add-auth",
        repo_owner="myorg",
        repo_name="myapp",
        user_id="user-uuid-123",
        failure_reason="agent_crash",
    )

    # VERIFY: Branch was NOT deleted (preserves work)
    mock_github.delete_branch.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_branch_name_basic():
    """
    SPEC: Branch name generation should produce valid names.

    Given ticket information,
    When _generate_branch_name is called,
    Then it should produce a valid branch name following the pattern {type}/{ticket-id}-{description}.
    """

    mock_github = MagicMock()
    service = BranchWorkflowService(github_service=mock_github)

    branch_name = service._generate_branch_name_sync(
        ticket_id="123",
        ticket_title="Add user authentication",
        ticket_type="feature",
    )

    # Should start with feature/ and contain ticket ID
    assert branch_name.startswith("feature/")
    assert "123" in branch_name
    # Should be lowercase with hyphens
    assert branch_name.islower() or "-" in branch_name


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_branch_name_bug_type():
    """
    SPEC: Bug tickets should generate fix/ prefix.

    Given a bug ticket,
    When _generate_branch_name is called,
    Then branch should have fix/ prefix.
    """

    mock_github = MagicMock()
    service = BranchWorkflowService(github_service=mock_github)

    branch_name = service._generate_branch_name_sync(
        ticket_id="456",
        ticket_title="Fix login button alignment",
        ticket_type="bug",
    )

    assert branch_name.startswith("fix/")
    assert "456" in branch_name


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_branch_name_critical_bug_is_hotfix():
    """
    SPEC: Critical bugs should generate hotfix/ prefix.

    Given a critical bug ticket,
    When _generate_branch_name is called,
    Then branch should have hotfix/ prefix.
    """

    mock_github = MagicMock()
    service = BranchWorkflowService(github_service=mock_github)

    branch_name = service._generate_branch_name_sync(
        ticket_id="999",
        ticket_title="URGENT: Payment webhook failing",
        ticket_type="bug",
        priority="critical",
    )

    assert branch_name.startswith("hotfix/")
    assert "999" in branch_name


@pytest.mark.asyncio
@pytest.mark.unit
async def test_generate_branch_name_collision_handling():
    """
    SPEC: Branch names should handle collisions by appending suffix.

    Given existing branches with the same name,
    When _generate_branch_name is called,
    Then it should append a numeric suffix to avoid collision.
    """

    mock_github = MagicMock()
    service = BranchWorkflowService(github_service=mock_github)

    existing_branches = ["feature/123-auth", "feature/123-auth-2"]

    branch_name = service._generate_branch_name_sync(
        ticket_id="123",
        ticket_title="Auth",
        ticket_type="feature",
        existing_branches=existing_branches,
    )

    # Should have suffix to avoid collision
    assert branch_name not in existing_branches


# ============================================================================
# Integration Tests (with Database/Real Service dependencies)
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sandbox
async def test_branch_workflow_service_imports():
    """
    SPEC: BranchWorkflowService should be importable.

    Verify that the service module exists and can be imported.
    """
    try:
        from omoi_os.services.branch_workflow import BranchWorkflowService

        assert BranchWorkflowService is not None
    except ImportError as e:
        pytest.skip(f"BranchWorkflowService not yet implemented: {e}")


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.sandbox
async def test_github_api_has_required_methods():
    """
    SPEC: GitHubAPIService should have required methods for Phase 5.

    Verify that GitHubAPIService has:
    - get_pull_request
    - merge_pull_request
    - delete_branch
    - compare_branches (optional)
    """
    from omoi_os.services.github_api import GitHubAPIService

    # These methods should exist
    assert hasattr(GitHubAPIService, "get_pull_request"), (
        "Missing get_pull_request method"
    )
    assert hasattr(GitHubAPIService, "merge_pull_request"), (
        "Missing merge_pull_request method"
    )
    assert hasattr(GitHubAPIService, "delete_branch"), "Missing delete_branch method"

    # compare_branches is optional for MVP
    # assert hasattr(GitHubAPIService, "compare_branches"), "Missing compare_branches method"
