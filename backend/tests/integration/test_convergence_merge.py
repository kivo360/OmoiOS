"""Integration tests for convergence merge services.

Tests the DAG Merge Executor foundation:
- MergeAttempt model and database operations
- ConflictScorer ordering logic
- ConvergenceMergeService database integration
- AgentConflictResolver fallback resolution
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from omoi_os.models.merge_attempt import MergeAttempt, MergeStatus
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.conflict_scorer import (
    ConflictScorer,
    BranchScore,
    ScoredMergeOrder,
)
from omoi_os.services.convergence_merge_service import (
    ConvergenceMergeService,
    reset_convergence_merge_service,
)
from omoi_os.services.agent_conflict_resolver import (
    AgentConflictResolver,
    ResolutionContext,
)
from omoi_os.services.sandbox_git_operations import (
    SandboxGitOperations,
    MergeResultStatus,
)
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_service(test_database_url):
    """Create a database service for testing."""
    db = DatabaseService(connection_string=test_database_url)
    yield db


@pytest.fixture
def test_ticket(db_service):
    """Create a test ticket."""
    with db_service.get_session() as session:
        ticket = Ticket(
            id=str(uuid4()),
            title="Test Ticket for Merge",
            description="Testing convergence merge",
            status="in_progress",
            phase_id="PHASE_IMPLEMENTATION",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id
    return ticket_id


@pytest.fixture
def test_tasks(db_service, test_ticket):
    """Create test tasks for merge testing."""
    task_ids = []
    with db_service.get_session() as session:
        # Create 3 parallel tasks
        for i in range(3):
            task = Task(
                id=str(uuid4()),
                ticket_id=test_ticket,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="implement_feature",
                title=f"Parallel Task {i + 1}",
                priority="HIGH",
                status="completed",
                result={"output": f"Task {i + 1} completed"},
                owned_files=[f"src/module{i + 1}/**"],
            )
            session.add(task)
            task_ids.append(task.id)

        # Create continuation task
        continuation = Task(
            id=str(uuid4()),
            ticket_id=test_ticket,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="integrate_feature",
            title="Continuation Task",
            priority="HIGH",
            status="pending",
            dependencies={"depends_on": task_ids},
        )
        session.add(continuation)
        task_ids.append(continuation.id)
        session.commit()

    return task_ids  # [task1, task2, task3, continuation]


@pytest.fixture
def mock_sandbox():
    """Create a mock Daytona sandbox."""
    sandbox = Mock()
    sandbox.id = "test-sandbox-123"
    sandbox.process = Mock()

    def mock_exec(cmd, timeout=None):
        """Mock process.exec that returns reasonable git output."""
        result = Mock()
        result.output = ""
        result.stderr = ""
        result.exit_code = 0

        if "rev-parse --abbrev-ref HEAD" in cmd:
            result.output = "ticket/test-ticket"
        elif "rev-parse HEAD" in cmd:
            result.output = "abc123def456"
        elif "merge-tree" in cmd:
            # No conflicts by default
            result.output = "abc123def456789"
        elif "git merge" in cmd:
            result.output = "Merge successful"
        elif "git diff --name-only --diff-filter=U" in cmd:
            result.output = ""  # No conflicts
        elif "git fetch" in cmd:
            result.output = ""
        elif "git checkout" in cmd:
            result.output = "Switched to branch"

        return result

    sandbox.process.exec = mock_exec
    return sandbox


@pytest.fixture
def mock_git_ops(mock_sandbox):
    """Create SandboxGitOperations with mock sandbox."""
    return SandboxGitOperations(
        sandbox=mock_sandbox,
        workspace_path="/workspace",
    )


# ============================================================================
# MergeAttempt Model Tests
# ============================================================================


class TestMergeAttemptModel:
    """Test MergeAttempt database operations."""

    def test_create_merge_attempt(self, db_service, test_ticket, test_tasks):
        """Test creating a MergeAttempt record."""
        with db_service.get_session() as session:
            merge_attempt = MergeAttempt(
                id=str(uuid4()),
                task_id=test_tasks[3],  # continuation task
                ticket_id=test_ticket,
                source_task_ids=test_tasks[:3],
                target_branch=f"ticket/{test_ticket}",
                status=MergeStatus.PENDING.value,
            )
            session.add(merge_attempt)
            session.commit()

            # Verify it was created
            fetched = (
                session.query(MergeAttempt)
                .filter(MergeAttempt.id == merge_attempt.id)
                .first()
            )

            assert fetched is not None
            assert fetched.task_id == test_tasks[3]
            assert fetched.source_task_ids == test_tasks[:3]
            assert fetched.status == MergeStatus.PENDING.value

    def test_merge_attempt_status_transitions(
        self, db_service, test_ticket, test_tasks
    ):
        """Test MergeAttempt status transitions."""
        merge_id = str(uuid4())

        with db_service.get_session() as session:
            merge_attempt = MergeAttempt(
                id=merge_id,
                task_id=test_tasks[3],
                ticket_id=test_ticket,
                source_task_ids=test_tasks[:3],
                target_branch=f"ticket/{test_ticket}",
                status=MergeStatus.PENDING.value,
            )
            session.add(merge_attempt)
            session.commit()

        # Transition to IN_PROGRESS
        with db_service.get_session() as session:
            attempt = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            attempt.status = MergeStatus.IN_PROGRESS.value
            attempt.started_at = utc_now()
            session.commit()

        # Transition to COMPLETED
        with db_service.get_session() as session:
            attempt = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            attempt.status = MergeStatus.COMPLETED.value
            attempt.success = True
            attempt.completed_at = utc_now()
            session.commit()

        # Verify final state
        with db_service.get_session() as session:
            attempt = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert attempt.status == MergeStatus.COMPLETED.value
            assert attempt.success is True
            assert attempt.started_at is not None
            assert attempt.completed_at is not None

    def test_merge_attempt_with_conflicts(self, db_service, test_ticket, test_tasks):
        """Test MergeAttempt with conflict tracking."""
        with db_service.get_session() as session:
            merge_attempt = MergeAttempt(
                id=str(uuid4()),
                task_id=test_tasks[3],
                ticket_id=test_ticket,
                source_task_ids=test_tasks[:3],
                target_branch=f"ticket/{test_ticket}",
                status=MergeStatus.CONFLICT.value,
                total_conflicts=5,
                conflict_scores={
                    test_tasks[0]: {"count": 2, "files": ["src/a.py", "src/b.py"]},
                    test_tasks[1]: {
                        "count": 3,
                        "files": ["src/c.py", "src/d.py", "src/e.py"],
                    },
                    test_tasks[2]: {"count": 0, "files": []},
                },
                merge_order=[test_tasks[2], test_tasks[0], test_tasks[1]],
            )
            session.add(merge_attempt)
            session.commit()

            # Verify conflict data
            fetched = (
                session.query(MergeAttempt)
                .filter(MergeAttempt.id == merge_attempt.id)
                .first()
            )

            assert fetched.total_conflicts == 5
            assert fetched.has_conflicts is True
            assert fetched.merge_order[0] == test_tasks[2]  # Least conflicts first

    def test_merge_attempt_llm_resolution_log(
        self, db_service, test_ticket, test_tasks
    ):
        """Test MergeAttempt LLM resolution logging."""
        merge_id = str(uuid4())

        with db_service.get_session() as session:
            merge_attempt = MergeAttempt(
                id=merge_id,
                task_id=test_tasks[3],
                ticket_id=test_ticket,
                source_task_ids=test_tasks[:3],
                target_branch=f"ticket/{test_ticket}",
                status=MergeStatus.RESOLVING.value,
                llm_invocations=3,
                llm_resolution_log={
                    "src/service.py": {
                        "resolved_at": utc_now().isoformat(),
                        "content_length": 150,
                    },
                    "src/model.py": {
                        "resolved_at": utc_now().isoformat(),
                        "content_length": 200,
                    },
                },
                llm_tokens_used=5000,
            )
            session.add(merge_attempt)
            session.commit()

        with db_service.get_session() as session:
            fetched = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )

            assert fetched.required_llm_resolution is True
            assert fetched.llm_invocations == 3
            assert "src/service.py" in fetched.llm_resolution_log


# ============================================================================
# ConflictScorer Tests
# ============================================================================


class TestConflictScorer:
    """Test ConflictScorer ordering logic."""

    @pytest.mark.asyncio
    async def test_score_branch_clean(self, mock_git_ops):
        """Test scoring a branch with no conflicts."""
        scorer = ConflictScorer(mock_git_ops)

        score = await scorer.score_branch("feature-branch", task_id="task-001")

        assert score.branch == "feature-branch"
        assert score.task_id == "task-001"
        assert score.conflict_count == 0
        assert score.is_clean is True

    @pytest.mark.asyncio
    async def test_score_branch_with_conflicts(self, mock_sandbox):
        """Test scoring a branch with conflicts."""

        # Mock sandbox to return conflicts
        def mock_exec_with_conflicts(cmd, timeout=None):
            result = Mock()
            result.output = ""
            result.stderr = ""
            result.exit_code = 0

            if "merge-tree" in cmd:
                result.output = """abc123
CONFLICT (content): Merge conflict in src/service.py
CONFLICT (content): Merge conflict in src/model.py
"""
            return result

        mock_sandbox.process.exec = mock_exec_with_conflicts
        git_ops = SandboxGitOperations(mock_sandbox, "/workspace")
        scorer = ConflictScorer(git_ops)

        score = await scorer.score_branch("conflict-branch")

        assert score.conflict_count == 2
        assert score.has_conflicts is True
        assert "src/service.py" in score.conflict_files
        assert "src/model.py" in score.conflict_files

    @pytest.mark.asyncio
    async def test_score_branches_ordering(self, mock_sandbox):
        """Test that branches are ordered by conflict count."""
        call_count = {"count": 0}

        def mock_exec_varying_conflicts(cmd, timeout=None):
            result = Mock()
            result.output = ""
            result.stderr = ""
            result.exit_code = 0

            if "merge-tree" in cmd:
                call_count["count"] += 1
                if "branch-a" in cmd:
                    result.output = "CONFLICT (content): Merge conflict in a.py\nCONFLICT (content): Merge conflict in b.py"
                elif "branch-b" in cmd:
                    result.output = "abc123"  # No conflicts
                elif "branch-c" in cmd:
                    result.output = "CONFLICT (content): Merge conflict in c.py"
            elif "checkout" in cmd or "fetch" in cmd:
                pass
            elif "rev-parse --abbrev-ref" in cmd:
                result.output = "main"

            return result

        mock_sandbox.process.exec = mock_exec_varying_conflicts
        git_ops = SandboxGitOperations(mock_sandbox, "/workspace")
        scorer = ConflictScorer(git_ops)

        result = await scorer.score_branches(
            base_branch="main",
            branches=["branch-a", "branch-b", "branch-c"],
        )

        # Should be ordered: branch-b (0), branch-c (1), branch-a (2)
        assert result.merge_order[0] == "branch-b"
        assert result.merge_order[1] == "branch-c"
        assert result.merge_order[2] == "branch-a"
        assert result.total_conflicts == 3
        assert result.clean_count == 1

    @pytest.mark.asyncio
    async def test_estimate_merge_complexity(self, mock_git_ops):
        """Test merge complexity estimation."""
        scorer = ConflictScorer(mock_git_ops)

        # Create a scored order with known values
        scored_order = ScoredMergeOrder(
            scores={
                "task-1": BranchScore(
                    branch="task-1",
                    task_id="task-1",
                    conflict_count=0,
                ),
                "task-2": BranchScore(
                    branch="task-2",
                    task_id="task-2",
                    conflict_count=2,
                    conflict_files=["src/a.py", "src/b.py"],
                ),
                "task-3": BranchScore(
                    branch="task-3",
                    task_id="task-3",
                    conflict_count=1,
                    conflict_files=["src/a.py"],  # Overlaps with task-2
                ),
            },
            merge_order=["task-1", "task-3", "task-2"],
            total_conflicts=3,
            clean_count=1,
            failed_count=0,
        )

        complexity = await scorer.estimate_merge_complexity(scored_order)

        assert complexity["total_conflicts_across_branches"] == 3
        assert complexity["clean_branches"] == 1
        assert complexity["conflict_file_overlap"] == 1  # src/a.py in both
        assert complexity["complexity_score"] in ["low", "medium"]


# ============================================================================
# ConvergenceMergeService Tests
# ============================================================================


class TestConvergenceMergeService:
    """Test ConvergenceMergeService integration."""

    @pytest.fixture(autouse=True)
    def reset_service(self):
        """Reset singleton before each test."""
        reset_convergence_merge_service()
        yield
        reset_convergence_merge_service()

    def test_create_merge_attempt_record(self, db_service, test_ticket, test_tasks):
        """Test that ConvergenceMergeService creates MergeAttempt records."""
        service = ConvergenceMergeService(db=db_service)

        # Call internal method directly - now returns ID string directly
        merge_id = service._create_merge_attempt(
            continuation_task_id=test_tasks[3],
            source_task_ids=test_tasks[:3],
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        # Verify it's in the database
        with db_service.get_session() as session:
            fetched = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert fetched is not None
            assert fetched.task_id == test_tasks[3]
            assert fetched.source_task_ids == test_tasks[:3]
            assert fetched.status == MergeStatus.PENDING.value

    def test_update_merge_attempt_status(self, db_service, test_ticket, test_tasks):
        """Test status update methods."""
        service = ConvergenceMergeService(db=db_service)

        # Create initial record - now returns ID string directly
        merge_id = service._create_merge_attempt(
            continuation_task_id=test_tasks[3],
            source_task_ids=test_tasks[:3],
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        # Update to IN_PROGRESS
        service._update_merge_attempt_status(merge_id, MergeStatus.IN_PROGRESS)

        with db_service.get_session() as session:
            fetched = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert fetched.status == MergeStatus.IN_PROGRESS.value
            assert fetched.started_at is not None

    def test_update_merge_attempt_scoring(self, db_service, test_ticket, test_tasks):
        """Test scoring update method."""
        service = ConvergenceMergeService(db=db_service)

        # Now returns ID string directly
        merge_id = service._create_merge_attempt(
            continuation_task_id=test_tasks[3],
            source_task_ids=test_tasks[:3],
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        scored_order = ScoredMergeOrder(
            scores={
                test_tasks[0]: BranchScore(
                    branch=test_tasks[0], conflict_count=1, conflict_files=["a.py"]
                ),
                test_tasks[1]: BranchScore(
                    branch=test_tasks[1], conflict_count=0, conflict_files=[]
                ),
                test_tasks[2]: BranchScore(
                    branch=test_tasks[2],
                    conflict_count=2,
                    conflict_files=["b.py", "c.py"],
                ),
            },
            merge_order=[test_tasks[1], test_tasks[0], test_tasks[2]],
            total_conflicts=3,
            clean_count=1,
            failed_count=0,
        )

        service._update_merge_attempt_scoring(merge_id, scored_order)

        with db_service.get_session() as session:
            fetched = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert fetched.total_conflicts == 3
            assert fetched.merge_order[0] == test_tasks[1]  # Clean one first

    def test_fail_merge_records_error(self, db_service, test_ticket, test_tasks):
        """Test that failed merges are recorded properly."""
        service = ConvergenceMergeService(db=db_service)

        # Now returns ID string directly
        merge_id = service._create_merge_attempt(
            continuation_task_id=test_tasks[3],
            source_task_ids=test_tasks[:3],
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        result = service._fail_merge(
            merge_id,
            "Test error message",
            test_tasks[:3],
        )

        assert result.success is False
        assert result.error_message == "Test error message"
        assert result.failed_tasks == test_tasks[:3]

        with db_service.get_session() as session:
            fetched = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert fetched.status == MergeStatus.FAILED.value
            assert fetched.success is False
            assert "Test error" in fetched.error_message


# ============================================================================
# AgentConflictResolver Tests
# ============================================================================


class TestAgentConflictResolver:
    """Test AgentConflictResolver fallback resolution.

    These tests force fallback mode by patching CLAUDE_SDK_AVAILABLE to False,
    testing the heuristic-based resolution without calling the actual Claude API.
    """

    @pytest.mark.asyncio
    async def test_resolve_empty_ours(self):
        """Test resolution when ours is empty."""
        # Patch to use fallback mode
        with patch(
            "omoi_os.services.agent_conflict_resolver.CLAUDE_SDK_AVAILABLE", False
        ):
            resolver = AgentConflictResolver()

            result = await resolver.resolve_conflict(
                file_path="src/service.py",
                ours_content="",
                theirs_content="def hello(): pass",
            )

            assert result.success is True
            assert result.resolved_content == "def hello(): pass"
            assert result.reasoning is not None
            assert "theirs" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_resolve_empty_theirs(self):
        """Test resolution when theirs is empty."""
        with patch(
            "omoi_os.services.agent_conflict_resolver.CLAUDE_SDK_AVAILABLE", False
        ):
            resolver = AgentConflictResolver()

            result = await resolver.resolve_conflict(
                file_path="src/service.py",
                ours_content="def hello(): pass",
                theirs_content="",
            )

            assert result.success is True
            assert result.resolved_content == "def hello(): pass"
            assert result.reasoning is not None
            assert "ours" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_resolve_identical(self):
        """Test resolution when both sides are identical."""
        with patch(
            "omoi_os.services.agent_conflict_resolver.CLAUDE_SDK_AVAILABLE", False
        ):
            resolver = AgentConflictResolver()

            result = await resolver.resolve_conflict(
                file_path="src/service.py",
                ours_content="def hello(): pass",
                theirs_content="def hello(): pass",
            )

            assert result.success is True
            assert result.resolved_content == "def hello(): pass"
            assert result.reasoning is not None
            assert "identical" in result.reasoning.lower()

    @pytest.mark.asyncio
    async def test_resolve_extension(self):
        """Test resolution when one extends the other."""
        with patch(
            "omoi_os.services.agent_conflict_resolver.CLAUDE_SDK_AVAILABLE", False
        ):
            resolver = AgentConflictResolver()

            result = await resolver.resolve_conflict(
                file_path="src/service.py",
                ours_content="def hello(): pass",
                theirs_content="def hello(): pass\ndef world(): pass",
            )

            assert result.success is True
            assert "world" in result.resolved_content

    @pytest.mark.asyncio
    async def test_merge_python_imports(self):
        """Test merging Python import statements."""
        with patch(
            "omoi_os.services.agent_conflict_resolver.CLAUDE_SDK_AVAILABLE", False
        ):
            resolver = AgentConflictResolver()

            result = await resolver.resolve_conflict(
                file_path="src/service.py",
                ours_content="import os\nimport sys",
                theirs_content="import os\nimport json",
            )

            assert result.success is True
            assert "import os" in result.resolved_content
            assert "import sys" in result.resolved_content
            assert "import json" in result.resolved_content

    @pytest.mark.asyncio
    async def test_complex_conflict_fallback_fails(self):
        """Test that complex conflicts fail in fallback mode."""
        with patch(
            "omoi_os.services.agent_conflict_resolver.CLAUDE_SDK_AVAILABLE", False
        ):
            resolver = AgentConflictResolver()

            result = await resolver.resolve_conflict(
                file_path="src/service.py",
                ours_content="def foo(x): return x + 1",
                theirs_content="def foo(y): return y * 2",
            )

            # Without SDK, complex conflicts can't be resolved
            assert result.success is False
            assert (
                "Claude Agent SDK" in result.error_message
                or "automatically" in result.error_message
            )

    def test_build_resolution_prompt(self):
        """Test prompt building."""
        resolver = AgentConflictResolver()

        context = ResolutionContext(
            file_path="src/service.py",
            ours_content="def foo(): pass",
            theirs_content="def bar(): pass",
            task_description="Implementing user service",
            related_files=["src/model.py", "src/utils.py"],
        )

        prompt = resolver._build_resolution_prompt(context)

        assert "src/service.py" in prompt
        assert "def foo(): pass" in prompt
        assert "def bar(): pass" in prompt
        assert "Implementing user service" in prompt
        assert "src/model.py" in prompt
        assert "<<<RESOLVED>>>" in prompt


# ============================================================================
# SandboxGitOperations Tests
# ============================================================================


class TestSandboxGitOperations:
    """Test SandboxGitOperations with mock sandbox."""

    @pytest.mark.asyncio
    async def test_get_current_branch(self, mock_git_ops):
        """Test getting current branch."""
        branch = await mock_git_ops.get_current_branch()
        assert branch == "ticket/test-ticket"

    @pytest.mark.asyncio
    async def test_get_current_commit(self, mock_git_ops):
        """Test getting current commit."""
        commit = await mock_git_ops.get_current_commit()
        assert commit == "abc123def456"

    @pytest.mark.asyncio
    async def test_fetch(self, mock_git_ops):
        """Test fetch operation."""
        result = await mock_git_ops.fetch()
        assert result is True

    @pytest.mark.asyncio
    async def test_count_conflicts_dry_run_clean(self, mock_git_ops):
        """Test dry-run with no conflicts."""
        result = await mock_git_ops.count_conflicts_dry_run("feature-branch")

        assert result.would_conflict is False
        assert result.conflict_count == 0

    @pytest.mark.asyncio
    async def test_merge_success(self, mock_git_ops):
        """Test successful merge."""
        result = await mock_git_ops.merge("feature-branch")

        assert result.success is True
        assert result.status == MergeResultStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_parse_conflict_markers(self, mock_git_ops):
        """Test parsing git conflict markers."""
        content = """some code before
<<<<<<< HEAD
def ours():
    pass
=======
def theirs():
    pass
>>>>>>> feature
some code after"""

        conflict_info = mock_git_ops._parse_conflict_markers("test.py", content)

        assert conflict_info.file_path == "test.py"
        assert "def ours():" in conflict_info.ours_content
        assert "def theirs():" in conflict_info.theirs_content

    @pytest.mark.asyncio
    async def test_write_file(self):
        """Test writing resolved content."""
        # Create a proper mock with MagicMock for assert_called support
        mock_sandbox = MagicMock()
        mock_sandbox.id = "test-sandbox-123"
        mock_sandbox.process.exec.return_value = Mock(output="", stderr="", exit_code=0)

        git_ops = SandboxGitOperations(mock_sandbox, "/workspace")

        result = await git_ops.write_file("test.py", "resolved content")

        assert result is True
        # Verify exec was called with cat command
        mock_sandbox.process.exec.assert_called()
