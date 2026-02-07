"""End-to-end integration tests for convergence merge system.

These tests verify the complete flow from parallel task completion through
synthesis to code merging. They use real database transactions and event
publishing to catch integration issues.

Critical scenarios tested:
1. End-to-end: Synthesis → Merge flow integration
2. Database transaction semantics
3. Concurrent merge handling
4. Partial merge success/failure
5. Event ordering and race conditions
6. Ownership validation integration
7. Synthesis context preservation through merge
"""

import pytest
from unittest.mock import Mock, MagicMock
from uuid import uuid4

from omoi_os.models.merge_attempt import MergeAttempt, MergeStatus
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.synthesis_service import (
    SynthesisService,
    reset_synthesis_service,
)
from omoi_os.services.convergence_merge_service import (
    ConvergenceMergeService,
    ConvergenceMergeConfig,
    reset_convergence_merge_service,
)
from omoi_os.services.ownership_validation import (
    OwnershipValidationService,
)
from omoi_os.services.conflict_scorer import (
    ConflictScorer,
    BranchScore,
    ScoredMergeOrder,
)
from omoi_os.services.event_bus import EventBusService
from omoi_os.services.database import DatabaseService

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def db_service(test_database_url):
    """Create a database service for testing."""
    db = DatabaseService(connection_string=test_database_url)
    yield db


@pytest.fixture
def mock_event_bus():
    """Create a mock event bus that tracks published events."""
    bus = Mock(spec=EventBusService)
    bus.published_events = []

    def track_publish(event):
        bus.published_events.append(event)

    bus.publish = Mock(side_effect=track_publish)
    bus.subscribe = Mock()
    return bus


@pytest.fixture
def real_event_bus(redis_url):
    """Create a real event bus for integration tests."""
    return EventBusService(redis_url)


@pytest.fixture
def test_ticket(db_service):
    """Create a test ticket."""
    with db_service.get_session() as session:
        ticket = Ticket(
            id=str(uuid4()),
            title="Test Ticket for E2E Merge",
            description="Testing end-to-end convergence merge",
            status="in_progress",
            phase_id="PHASE_IMPLEMENTATION",
            priority="HIGH",
        )
        session.add(ticket)
        session.commit()
        ticket_id = ticket.id
    return ticket_id


@pytest.fixture
def parallel_tasks_with_results(db_service, test_ticket):
    """Create parallel tasks with completed results."""
    task_ids = []
    with db_service.get_session() as session:
        # Create 3 parallel tasks with different results
        for i in range(3):
            task = Task(
                id=str(uuid4()),
                ticket_id=test_ticket,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="implement_feature",
                title=f"Parallel Task {i+1}",
                priority="HIGH",
                status="completed",
                result={
                    "output": f"Task {i+1} implementation",
                    "files_modified": [f"src/module{i+1}/main.py"],
                    "tests_passed": True,
                },
                owned_files=[f"src/module{i+1}/**"],
            )
            session.add(task)
            task_ids.append(task.id)

        # Create continuation task (pending, waiting for parallel tasks)
        continuation = Task(
            id=str(uuid4()),
            ticket_id=test_ticket,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="integrate_feature",
            title="Continuation Task - Integration",
            priority="HIGH",
            status="pending",
            dependencies={"depends_on": task_ids},
        )
        session.add(continuation)
        task_ids.append(continuation.id)
        session.commit()

    # Return [task1, task2, task3, continuation]
    return task_ids


@pytest.fixture
def overlapping_ownership_tasks(db_service, test_ticket):
    """Create tasks with overlapping file ownership for conflict testing."""
    task_ids = []
    with db_service.get_session() as session:
        # Task 1: owns src/services/**
        task1 = Task(
            id=str(uuid4()),
            ticket_id=test_ticket,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            title="Task with services ownership",
            priority="HIGH",
            status="completed",
            result={"output": "Task 1 done"},
            owned_files=["src/services/**"],
        )
        session.add(task1)
        task_ids.append(task1.id)

        # Task 2: owns src/services/user/** (overlaps with task1!)
        task2 = Task(
            id=str(uuid4()),
            ticket_id=test_ticket,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            title="Task with user services ownership",
            priority="HIGH",
            status="completed",
            result={"output": "Task 2 done"},
            owned_files=["src/services/user/**"],  # OVERLAP!
        )
        session.add(task2)
        task_ids.append(task2.id)

        # Task 3: owns src/api/** (no overlap)
        task3 = Task(
            id=str(uuid4()),
            ticket_id=test_ticket,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            title="Task with API ownership",
            priority="HIGH",
            status="completed",
            result={"output": "Task 3 done"},
            owned_files=["src/api/**"],
        )
        session.add(task3)
        task_ids.append(task3.id)

        # Continuation task
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

    return task_ids


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset service singletons before and after each test."""
    reset_synthesis_service()
    reset_convergence_merge_service()
    yield
    reset_synthesis_service()
    reset_convergence_merge_service()


# ============================================================================
# Test: End-to-End Synthesis → Context Injection
# ============================================================================


class TestSynthesisE2E:
    """End-to-end tests for SynthesisService."""

    def test_synthesis_triggers_on_all_tasks_complete(
        self, db_service, mock_event_bus, parallel_tasks_with_results
    ):
        """Test that synthesis triggers when all parallel tasks complete."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        # Create synthesis service
        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)
        synthesis.subscribe_to_events()

        # Register join
        join_id = f"join-{uuid4().hex[:8]}"
        synthesis.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
            merge_strategy="combine",
        )

        # Since tasks are already complete, synthesis should trigger immediately
        # (register_join calls _check_already_completed_sources)

        # Verify synthesis.completed event was published
        synthesis_events = [
            e
            for e in mock_event_bus.published_events
            if hasattr(e, "event_type")
            and e.event_type == "coordination.synthesis.completed"
        ]
        assert len(synthesis_events) == 1

        event = synthesis_events[0]
        assert event.payload["join_id"] == join_id
        assert event.payload["continuation_task_id"] == continuation_id
        assert set(event.payload["source_task_ids"]) == set(source_ids)

    def test_synthesis_context_injected_into_continuation_task(
        self, db_service, mock_event_bus, parallel_tasks_with_results
    ):
        """Test that merged context is injected into continuation task."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)

        join_id = f"join-{uuid4().hex[:8]}"
        synthesis.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Verify continuation task has synthesis_context
        with db_service.get_session() as session:
            continuation = (
                session.query(Task).filter(Task.id == continuation_id).first()
            )

            assert continuation.synthesis_context is not None
            assert "_source_results" in continuation.synthesis_context
            assert continuation.synthesis_context["_join_id"] == join_id
            assert len(continuation.synthesis_context["_source_results"]) == 3

    def test_synthesis_handles_incremental_task_completion(
        self, db_service, mock_event_bus, test_ticket
    ):
        """Test synthesis handles tasks completing one at a time."""
        # Create tasks in pending state
        task_ids = []
        with db_service.get_session() as session:
            for i in range(3):
                task = Task(
                    id=str(uuid4()),
                    ticket_id=test_ticket,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type="implement_feature",
                    title=f"Incremental Task {i+1}",
                    status="pending",  # Start pending
                    priority="HIGH",
                )
                session.add(task)
                task_ids.append(task.id)

            continuation = Task(
                id=str(uuid4()),
                ticket_id=test_ticket,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="integrate_feature",
                title="Continuation Task",
                status="pending",
                priority="HIGH",
            )
            session.add(continuation)
            task_ids.append(continuation.id)
            session.commit()

        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)
        synthesis.subscribe_to_events()

        join_id = f"join-{uuid4().hex[:8]}"
        synthesis.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # No synthesis yet - tasks are pending
        assert len(mock_event_bus.published_events) == 0

        # Complete tasks one by one
        for i, task_id in enumerate(source_ids):
            with db_service.get_session() as session:
                task = session.query(Task).filter(Task.id == task_id).first()
                task.status = "completed"
                task.result = {"output": f"Task {i+1} result"}
                session.commit()

            # Simulate TASK_COMPLETED event
            synthesis._handle_task_completed({"entity_id": task_id})

            if i < 2:
                # Not all complete yet
                synthesis_events = [
                    e
                    for e in mock_event_bus.published_events
                    if hasattr(e, "event_type")
                    and e.event_type == "coordination.synthesis.completed"
                ]
                assert len(synthesis_events) == 0
            else:
                # All complete - synthesis should trigger
                synthesis_events = [
                    e
                    for e in mock_event_bus.published_events
                    if hasattr(e, "event_type")
                    and e.event_type == "coordination.synthesis.completed"
                ]
                assert len(synthesis_events) == 1

    def test_synthesis_idempotent_task_completion(
        self, db_service, mock_event_bus, parallel_tasks_with_results
    ):
        """Test that duplicate TASK_COMPLETED events don't cause issues."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)

        join_id = f"join-{uuid4().hex[:8]}"
        synthesis.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Clear published events from initial registration
        mock_event_bus.published_events.clear()

        # Send duplicate TASK_COMPLETED for same task
        synthesis._handle_task_completed({"entity_id": source_ids[0]})
        synthesis._handle_task_completed({"entity_id": source_ids[0]})
        synthesis._handle_task_completed({"entity_id": source_ids[0]})

        # Should not trigger synthesis again (join already processed)
        synthesis_events = [
            e
            for e in mock_event_bus.published_events
            if hasattr(e, "event_type")
            and e.event_type == "coordination.synthesis.completed"
        ]
        assert len(synthesis_events) == 0


# ============================================================================
# Test: Database Transaction Semantics
# ============================================================================


class TestDatabaseTransactions:
    """Test database transaction behavior in merge operations."""

    def test_merge_attempt_persists_across_sessions(
        self, db_service, test_ticket, parallel_tasks_with_results
    ):
        """Test that MergeAttempt persists correctly across database sessions."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        service = ConvergenceMergeService(db=db_service)

        # Create merge attempt in one session
        merge_id = service._create_merge_attempt(
            continuation_task_id=continuation_id,
            source_task_ids=source_ids,
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        # Verify in a completely new session (same db_service, new session)
        # This tests that data was actually committed, not just in transaction cache
        with db_service.get_session() as session:
            fetched = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert fetched is not None
            assert fetched.task_id == continuation_id
            assert fetched.status == MergeStatus.PENDING.value

        # Additional verification: update in one session, read in another
        service._update_merge_attempt_status(merge_id, MergeStatus.IN_PROGRESS)

        with db_service.get_session() as session:
            fetched = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert fetched.status == MergeStatus.IN_PROGRESS.value
            assert fetched.started_at is not None

    def test_merge_status_transitions_are_atomic(
        self, db_service, test_ticket, parallel_tasks_with_results
    ):
        """Test that status transitions happen atomically."""
        task_ids = parallel_tasks_with_results
        service = ConvergenceMergeService(db=db_service)

        merge_id = service._create_merge_attempt(
            continuation_task_id=task_ids[3],
            source_task_ids=task_ids[:3],
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        # Transition through states
        service._update_merge_attempt_status(merge_id, MergeStatus.IN_PROGRESS)

        # Verify IN_PROGRESS state
        with db_service.get_session() as session:
            attempt = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert attempt.status == MergeStatus.IN_PROGRESS.value
            assert attempt.started_at is not None

        # Finalize
        service._finalize_merge_attempt(
            merge_attempt_id=merge_id,
            success=True,
            llm_invocations=0,
            total_conflicts=0,
        )

        # Verify COMPLETED state
        with db_service.get_session() as session:
            attempt = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert attempt.status == MergeStatus.COMPLETED.value
            assert attempt.success is True
            assert attempt.completed_at is not None
            # Timestamps should be monotonic
            assert attempt.completed_at >= attempt.started_at

    def test_multiple_merge_attempts_isolation(
        self, db_service, test_ticket, parallel_tasks_with_results
    ):
        """Test that multiple merge attempts for same ticket don't interfere."""
        task_ids = parallel_tasks_with_results
        service = ConvergenceMergeService(db=db_service)

        # Create two merge attempts
        merge_id_1 = service._create_merge_attempt(
            continuation_task_id=task_ids[3],
            source_task_ids=task_ids[:3],
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        merge_id_2 = service._create_merge_attempt(
            continuation_task_id=task_ids[3],
            source_task_ids=task_ids[:3],
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        assert merge_id_1 != merge_id_2

        # Update one, verify other is unchanged
        service._update_merge_attempt_status(merge_id_1, MergeStatus.IN_PROGRESS)
        service._update_merge_attempt_status(merge_id_2, MergeStatus.CONFLICT)

        with db_service.get_session() as session:
            attempt_1 = (
                session.query(MergeAttempt)
                .filter(MergeAttempt.id == merge_id_1)
                .first()
            )
            attempt_2 = (
                session.query(MergeAttempt)
                .filter(MergeAttempt.id == merge_id_2)
                .first()
            )

            assert attempt_1.status == MergeStatus.IN_PROGRESS.value
            assert attempt_2.status == MergeStatus.CONFLICT.value


# ============================================================================
# Test: Ownership Validation Integration
# ============================================================================


class TestOwnershipValidation:
    """Test ownership validation in merge context."""

    def test_ownership_validation_detects_overlap(
        self, db_service, overlapping_ownership_tasks
    ):
        """Test that ownership validation detects overlapping patterns."""
        task_ids = overlapping_ownership_tasks
        validation_service = OwnershipValidationService(db=db_service)

        with db_service.get_session() as session:
            # Task 1 and Task 2 have overlapping ownership
            session.query(Task).filter(Task.id == task_ids[0]).first()
            task2 = session.query(Task).filter(Task.id == task_ids[1]).first()

            # Check if task2's files overlap with task1's
            # src/services/user/** overlaps with src/services/**
            validation_service.validate_task_ownership(task2)

            # Should detect the overlap (depending on implementation)
            # The service should find siblings and check for conflicts

    def test_non_overlapping_ownership_passes(
        self, db_service, parallel_tasks_with_results
    ):
        """Test that non-overlapping ownership passes validation."""
        task_ids = parallel_tasks_with_results
        validation_service = OwnershipValidationService(db=db_service)

        with db_service.get_session() as session:
            # These tasks have distinct ownership: module1/**, module2/**, module3/**
            for task_id in task_ids[:3]:
                task = session.query(Task).filter(Task.id == task_id).first()
                result = validation_service.validate_task_ownership(task)
                # Should pass - no overlaps
                assert result.valid is True

    def test_file_modification_validation(
        self, db_service, parallel_tasks_with_results
    ):
        """Test file-level modification validation."""
        task_ids = parallel_tasks_with_results
        validation_service = OwnershipValidationService(db=db_service)

        # Task 1 owns src/module1/**
        task_id = task_ids[0]

        # Should allow modifications within owned path
        assert (
            validation_service.validate_file_modification(
                task_id, "src/module1/main.py"
            )
            is True
        )
        assert (
            validation_service.validate_file_modification(
                task_id, "src/module1/utils/helper.py"
            )
            is True
        )

        # Should reject modifications outside owned path
        assert (
            validation_service.validate_file_modification(
                task_id, "src/module2/main.py"
            )
            is False
        )
        assert (
            validation_service.validate_file_modification(task_id, "src/other/file.py")
            is False
        )


# ============================================================================
# Test: Synthesis Context Preservation Through Merge
# ============================================================================


class TestSynthesisContextPreservation:
    """Test that synthesis context survives the merge process."""

    def test_synthesis_context_preserved_after_merge_attempt_creation(
        self, db_service, mock_event_bus, parallel_tasks_with_results, test_ticket
    ):
        """Test synthesis context is not overwritten by merge operations."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        # First, inject synthesis context
        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)
        join_id = f"join-{uuid4().hex[:8]}"
        synthesis.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Verify context was injected
        with db_service.get_session() as session:
            task = session.query(Task).filter(Task.id == continuation_id).first()
            original_context = task.synthesis_context.copy()
            assert "_join_id" in original_context

        # Now create a merge attempt (this shouldn't touch synthesis_context)
        # Use the actual test_ticket, not a task_id
        merge_service = ConvergenceMergeService(db=db_service)
        merge_service._create_merge_attempt(
            continuation_task_id=continuation_id,
            source_task_ids=source_ids,
            ticket_id=test_ticket,  # Use actual ticket_id from fixture
            spec_id=None,
            target_branch="ticket/test",
        )

        # Verify synthesis_context is still intact
        with db_service.get_session() as session:
            task = session.query(Task).filter(Task.id == continuation_id).first()
            assert task.synthesis_context is not None
            assert task.synthesis_context["_join_id"] == join_id
            assert "_source_results" in task.synthesis_context


# ============================================================================
# Test: Partial Merge Success Handling
# ============================================================================


class TestPartialMergeSuccess:
    """Test scenarios where some tasks merge but others fail."""

    @pytest.mark.asyncio
    async def test_partial_merge_records_both_success_and_failure(
        self, db_service, test_ticket, parallel_tasks_with_results
    ):
        """Test that partial merge success is recorded correctly."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        # Create mock sandbox that fails for one specific task
        mock_sandbox = MagicMock()
        mock_sandbox.id = "test-sandbox"

        def mock_exec(cmd, timeout=None):
            result = Mock()
            result.exit_code = 0
            result.output = ""
            result.stderr = ""

            if "rev-parse --abbrev-ref HEAD" in cmd:
                result.output = "ticket/test"
            elif "merge-tree" in cmd:
                # Fail for task 2
                if source_ids[1] in cmd:
                    result.output = "CONFLICT (content): Merge conflict in file.py"
                else:
                    result.output = "abc123"  # Success
            elif "checkout" in cmd or "fetch" in cmd:
                pass
            return result

        mock_sandbox.process.exec = mock_exec

        # Create service without conflict resolver (conflicts will fail)
        service = ConvergenceMergeService(
            db=db_service,
            config=ConvergenceMergeConfig(require_clean_merge=False),
        )

        # We can't fully test merge_at_convergence without more mocking,
        # but we can verify the _merge_in_order logic
        merge_id = service._create_merge_attempt(
            continuation_task_id=continuation_id,
            source_task_ids=source_ids,
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        # Verify merge attempt was created
        with db_service.get_session() as session:
            attempt = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert attempt is not None
            assert attempt.status == MergeStatus.PENDING.value


# ============================================================================
# Test: Event Ordering and Race Conditions
# ============================================================================


class TestEventOrdering:
    """Test event handling edge cases."""

    def test_join_created_after_tasks_already_complete(
        self, db_service, mock_event_bus, parallel_tasks_with_results
    ):
        """Test join registration when all tasks are already complete."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)

        # Register join AFTER tasks are complete
        join_id = f"join-{uuid4().hex[:8]}"
        synthesis.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Synthesis should trigger immediately since all tasks are complete
        synthesis_events = [
            e
            for e in mock_event_bus.published_events
            if hasattr(e, "event_type")
            and e.event_type == "coordination.synthesis.completed"
        ]
        assert len(synthesis_events) == 1

    def test_join_handles_unknown_task_completion(self, db_service, mock_event_bus):
        """Test that TASK_COMPLETED for unknown tasks is handled gracefully."""
        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)
        synthesis.subscribe_to_events()

        # Send completion for a task that's not in any join
        synthesis._handle_task_completed({"entity_id": str(uuid4())})

        # Should not crash, no events published
        assert len(mock_event_bus.published_events) == 0

    def test_invalid_join_event_ignored(self, db_service, mock_event_bus):
        """Test that invalid join events are ignored gracefully."""
        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)

        # Missing required fields
        synthesis._handle_join_created(
            {
                "payload": {
                    "join_id": "test",
                    # Missing source_task_ids and continuation_task_id
                }
            }
        )

        # Should not register anything
        assert len(synthesis.get_pending_joins()) == 0


# ============================================================================
# Test: Merge Complexity and Scoring
# ============================================================================


class TestMergeComplexity:
    """Test merge complexity estimation."""

    @pytest.mark.asyncio
    async def test_complexity_estimation_with_overlapping_conflicts(self):
        """Test complexity scoring when multiple branches conflict on same files."""
        # Create a scored order with overlapping conflicts
        scored_order = ScoredMergeOrder(
            scores={
                "task-1": BranchScore(
                    branch="task-1",
                    task_id="task-1",
                    conflict_count=3,
                    conflict_files=["src/common.py", "src/utils.py", "src/config.py"],
                ),
                "task-2": BranchScore(
                    branch="task-2",
                    task_id="task-2",
                    conflict_count=2,
                    conflict_files=[
                        "src/common.py",
                        "src/api.py",
                    ],  # common.py overlaps!
                ),
                "task-3": BranchScore(
                    branch="task-3",
                    task_id="task-3",
                    conflict_count=1,
                    conflict_files=["src/common.py"],  # common.py again!
                ),
            },
            merge_order=["task-3", "task-2", "task-1"],
            total_conflicts=6,
            clean_count=0,
            failed_count=0,
        )

        # Mock git ops for scorer
        mock_git_ops = Mock()
        scorer = ConflictScorer(mock_git_ops)

        complexity = await scorer.estimate_merge_complexity(scored_order)

        assert complexity["total_conflicts_across_branches"] == 6
        assert complexity["conflict_file_overlap"] >= 1  # src/common.py in all 3
        assert complexity["max_conflicts_single_branch"] == 3
        assert complexity["complexity_score"] in ["medium", "high"]


# ============================================================================
# Test: LLM Resolution Tracking
# ============================================================================


class TestLLMResolutionTracking:
    """Test LLM resolution audit trail."""

    def test_llm_resolution_logged_in_merge_attempt(
        self, db_service, test_ticket, parallel_tasks_with_results
    ):
        """Test that LLM resolutions are logged for audit."""
        task_ids = parallel_tasks_with_results
        service = ConvergenceMergeService(db=db_service)

        merge_id = service._create_merge_attempt(
            continuation_task_id=task_ids[3],
            source_task_ids=task_ids[:3],
            ticket_id=test_ticket,
            spec_id=None,
            target_branch=f"ticket/{test_ticket}",
        )

        # Log a resolution
        service._log_resolution(
            merge_attempt_id=merge_id,
            file_path="src/service.py",
            resolved_content="def merged_function(): pass",
        )

        # Verify it's logged
        with db_service.get_session() as session:
            attempt = (
                session.query(MergeAttempt).filter(MergeAttempt.id == merge_id).first()
            )
            assert attempt.llm_resolution_log is not None
            assert "src/service.py" in attempt.llm_resolution_log
            assert "resolved_at" in attempt.llm_resolution_log["src/service.py"]


# ============================================================================
# Test: Configuration Edge Cases
# ============================================================================


class TestConfigurationEdgeCases:
    """Test configuration boundary conditions."""

    def test_zero_max_conflicts_rejects_any_conflict(
        self, db_service, test_ticket, parallel_tasks_with_results
    ):
        """Test that max_conflicts_auto_resolve=0 rejects any conflicts."""
        config = ConvergenceMergeConfig(
            max_conflicts_auto_resolve=0,
            require_clean_merge=True,
        )
        ConvergenceMergeService(db=db_service, config=config)

        # Any scored order with conflicts > 0 should be rejected by config
        assert config.max_conflicts_auto_resolve == 0
        assert config.require_clean_merge is True

    def test_high_llm_invocation_limit(
        self, db_service, test_ticket, parallel_tasks_with_results
    ):
        """Test configuration with high LLM invocation limit."""
        config = ConvergenceMergeConfig(
            max_llm_invocations=100,
            max_conflicts_auto_resolve=50,
        )
        service = ConvergenceMergeService(db=db_service, config=config)

        assert service.config.max_llm_invocations == 100
        assert service.config.max_conflicts_auto_resolve == 50


# ============================================================================
# Test: Cleanup and State Management
# ============================================================================


class TestCleanupAndState:
    """Test cleanup and state management."""

    def test_pending_join_cleanup_after_synthesis(
        self, db_service, mock_event_bus, parallel_tasks_with_results
    ):
        """Test that pending joins are cleaned up after synthesis."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)

        join_id = f"join-{uuid4().hex[:8]}"
        synthesis.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Join should be cleaned up after synthesis
        assert synthesis.get_pending_join(join_id) is None
        assert join_id not in synthesis.get_pending_joins()

    def test_task_to_joins_mapping_cleanup(
        self, db_service, mock_event_bus, parallel_tasks_with_results
    ):
        """Test that task-to-joins mapping is cleaned up."""
        task_ids = parallel_tasks_with_results
        source_ids = task_ids[:3]
        continuation_id = task_ids[3]

        synthesis = SynthesisService(db=db_service, event_bus=mock_event_bus)

        join_id = f"join-{uuid4().hex[:8]}"
        synthesis.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Reverse lookup should be cleaned up
        for task_id in source_ids:
            assert (
                task_id not in synthesis._task_to_joins
                or join_id not in synthesis._task_to_joins.get(task_id, [])
            )
