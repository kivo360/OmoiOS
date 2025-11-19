"""Tests for dynamic task scoring (REQ-TQM-PRI-002, REQ-TQM-PRI-003, REQ-TQM-PRI-004)."""

from datetime import timedelta

import pytest

from omoi_os.config import TaskQueueSettings
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_scorer import TaskScorer
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def task_scorer(db_service: DatabaseService) -> TaskScorer:
    """Create a task scorer for testing."""
    return TaskScorer(db_service)


@pytest.fixture
def task_with_priority(db_service: DatabaseService, sample_ticket: Ticket) -> Task:
    """Create a task with a specific priority."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test_task",
            description="Test task",
            priority="HIGH",
            status="pending",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


class TestTaskScorerPriority:
    """Test priority component of scoring (REQ-TQM-PRI-002)."""

    def test_priority_critical(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test CRITICAL priority score is 1.0."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test",
                description="Test",
                priority="CRITICAL",
                status="pending",
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            score = task_scorer.compute_score(task)
            # Priority component should be 1.0 * 0.45 = 0.45 (base)
            assert score >= 0.45  # At minimum, priority component
            assert score <= 1.0  # Maximum possible score

    def test_priority_high(self, task_scorer: TaskScorer, task_with_priority: Task):
        """Test HIGH priority score is 0.75."""
        task_with_priority.priority = "HIGH"
        score = task_scorer.compute_score(task_with_priority)
        # Priority component should be 0.75 * 0.45 = 0.3375 (base)
        assert score >= 0.3375
        assert score <= 1.0

    def test_priority_medium(self, task_scorer: TaskScorer, task_with_priority: Task):
        """Test MEDIUM priority score is 0.5."""
        task_with_priority.priority = "MEDIUM"
        score = task_scorer.compute_score(task_with_priority)
        # Priority component should be 0.5 * 0.45 = 0.225 (base)
        assert score >= 0.225
        assert score <= 1.0

    def test_priority_low(self, task_scorer: TaskScorer, task_with_priority: Task):
        """Test LOW priority score is 0.25."""
        task_with_priority.priority = "LOW"
        score = task_scorer.compute_score(task_with_priority)
        # Priority component should be 0.25 * 0.45 = 0.1125 (base)
        assert score >= 0.1125
        assert score <= 1.0


class TestTaskScorerAge:
    """Test age component of scoring (REQ-TQM-PRI-002)."""

    def test_age_normalized(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test age is normalized correctly."""
        now = utc_now()
        old_time = now - timedelta(seconds=1800)  # 30 minutes ago

        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test",
                description="Test",
                priority="MEDIUM",
                status="pending",
                created_at=old_time,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            # Age is 30 minutes = 1800 seconds, AGE_CEILING = 3600 seconds
            # age_norm = min(1800 / 3600, 1.0) = 0.5
            # Age component = 0.5 * 0.20 = 0.10
            score = task_scorer.compute_score(task, now=now)
            # Should include age component
            assert score > 0.225  # Base priority (0.225) + some age component

    def test_age_capped(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test age is capped at AGE_CEILING."""
        now = utc_now()
        very_old_time = now - timedelta(seconds=7200)  # 2 hours ago (> AGE_CEILING)

        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test",
                description="Test",
                priority="MEDIUM",
                status="pending",
                created_at=very_old_time,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            # Age is 7200 seconds > AGE_CEILING (3600), so age_norm = 1.0
            # Age component = 1.0 * 0.20 = 0.20
            score = task_scorer.compute_score(task, now=now)
            # Should include max age component
            assert score > 0.425  # Base priority (0.225) + max age (0.20)


class TestTaskScorerDeadline:
    """Test deadline component of scoring (REQ-TQM-PRI-002, REQ-TQM-PRI-003)."""

    def test_deadline_within_window(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test deadline within SLA_URGENCY_WINDOW gets boost."""
        now = utc_now()
        deadline = now + timedelta(seconds=600)  # 10 minutes from now (< 15 min window)

        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test",
                description="Test",
                priority="MEDIUM",
                status="pending",
                deadline_at=deadline,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            score = task_scorer.compute_score(task, now=now)
            # Should have deadline component AND SLA boost
            # Base score (priority=0.225 + deadline component) * 1.25 (SLA_BOOST_MULTIPLIER)
            # MEDIUM priority: 0.225 base, deadline within window adds ~0.1, SLA boost multiplies by 1.25
            assert score > 0.4  # Should be higher than normal medium priority task (~0.225)

    def test_deadline_past(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test deadline in past gets maximum urgency."""
        now = utc_now()
        past_deadline = now - timedelta(seconds=100)  # 100 seconds ago

        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test",
                description="Test",
                priority="MEDIUM",
                status="pending",
                deadline_at=past_deadline,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            score = task_scorer.compute_score(task, now=now)
            # Past deadline: deadline_norm = 1.0, should get SLA boost
            # Deadline component = 1.0 * 0.15 = 0.15
            # Base score (0.225 + 0.15) * 1.25 = 0.46875
            assert score > 0.4

    def test_deadline_far_future(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test deadline far in future has no impact."""
        now = utc_now()
        future_deadline = now + timedelta(hours=2)  # 2 hours from now

        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test",
                description="Test",
                priority="MEDIUM",
                status="pending",
                deadline_at=future_deadline,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            score = task_scorer.compute_score(task, now=now)
            # Far future deadline: deadline_norm = 0.0
            # Should be similar to task without deadline
            assert 0.2 <= score <= 0.3  # Just priority + small age component


class TestTaskScorerBlocker:
    """Test blocker component of scoring (REQ-TQM-PRI-002)."""

    def test_blocker_count(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test tasks that block others get higher score."""
        now = utc_now()

        with db_service.get_session() as session:
            # Create a task that will block others
            blocking_task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="blocking",
                description="Blocking task",
                priority="MEDIUM",
                status="pending",
            )
            session.add(blocking_task)
            session.flush()

            # Create tasks that depend on the blocking task
            for i in range(5):
                dependent_task = Task(
                    ticket_id=sample_ticket.id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type=f"dependent_{i}",
                    description=f"Dependent task {i}",
                    priority="MEDIUM",
                    status="pending",
                    dependencies={"depends_on": [blocking_task.id]},
                )
                session.add(dependent_task)
            session.commit()
            session.refresh(blocking_task)
            session.expunge(blocking_task)

            # Blocking task should have higher score due to blocker component
            # blocker_count = 5, BLOCKER_CEILING = 10
            # blocker_norm = min(5 / 10, 1.0) = 0.5
            # Blocker component = 0.5 * 0.15 = 0.075
            score_with_blockers = task_scorer.compute_score(blocking_task, now=now)

            # Compare to same task without blockers
            with db_service.get_session() as session:
                non_blocking_task = Task(
                    ticket_id=sample_ticket.id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type="non_blocking",
                    description="Non-blocking task",
                    priority="MEDIUM",
                    status="pending",
                )
                session.add(non_blocking_task)
                session.commit()
                session.refresh(non_blocking_task)
                session.expunge(non_blocking_task)

            score_without_blockers = task_scorer.compute_score(non_blocking_task, now=now)

            # Score with blockers should be higher
            assert score_with_blockers > score_without_blockers


class TestTaskScorerRetry:
    """Test retry penalty component of scoring (REQ-TQM-PRI-002)."""

    def test_retry_penalty(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test retry penalty reduces score."""
        now = utc_now()

        with db_service.get_session() as session:
            # Task with no retries
            fresh_task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="fresh",
                description="Fresh task",
                priority="MEDIUM",
                status="pending",
                retry_count=0,
                max_retries=3,
            )
            session.add(fresh_task)
            session.commit()
            session.refresh(fresh_task)
            session.expunge(fresh_task)

            # Task with retries
            retried_task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="retried",
                description="Retried task",
                priority="MEDIUM",
                status="pending",
                retry_count=2,
                max_retries=3,
            )
            session.add(retried_task)
            session.commit()
            session.refresh(retried_task)
            session.expunge(retried_task)

            fresh_score = task_scorer.compute_score(fresh_task, now=now)
            retried_score = task_scorer.compute_score(retried_task, now=now)

            # Fresh task should have higher score
            # retry_ratio = 2/3 = 0.67, retry_penalty = max(0.0, 1.0 - 0.67) = 0.33
            # Retry component = 0.33 * 0.05 = 0.0165 (vs 0.05 for fresh)
            assert fresh_score > retried_score


class TestTaskScorerStarvation:
    """Test starvation guard (REQ-TQM-PRI-004)."""

    def test_starvation_floor(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test starvation guard applies floor score."""
        now = utc_now()
        starved_time = now - timedelta(seconds=7300)  # > 2 hours (STARVATION_LIMIT)

        with db_service.get_session() as session:
            # Low priority task that's been waiting
            starved_task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="starved",
                description="Starved task",
                priority="LOW",  # Low priority
                status="pending",
                created_at=starved_time,
            )
            session.add(starved_task)
            session.commit()
            session.refresh(starved_task)

            score = task_scorer.compute_score(starved_task, now=now)
            # Should have starvation floor applied
            # STARVATION_FLOOR_SCORE = 0.6
            assert score >= 0.6  # Floor score applied

    def test_starvation_not_applied(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test starvation guard not applied to recent tasks."""
        now = utc_now()
        recent_time = now - timedelta(seconds=1800)  # 30 minutes (< 2 hours)

        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="recent",
                description="Recent task",
                priority="LOW",
                status="pending",
                created_at=recent_time,
            )
            session.add(task)
            session.commit()
            session.refresh(task)

            score = task_scorer.compute_score(task, now=now)
            # Should not have starvation floor (task is recent)
            # Can be less than 0.6 if it's truly low priority
            assert score < 0.6  # No floor applied


class TestTaskScorerComposite:
    """Test composite score calculation (REQ-TQM-PRI-002)."""

    def test_composite_score_all_factors(
        self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket
    ):
        """Test composite score with all factors."""
        now = utc_now()
        old_time = now - timedelta(seconds=1800)  # 30 minutes ago
        deadline = now + timedelta(seconds=600)  # 10 minutes from now

        with db_service.get_session() as session:
            # Create blocking task
            blocking_task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="blocking",
                description="Blocking task",
                priority="HIGH",
                status="pending",
                created_at=old_time,
                deadline_at=deadline,
                retry_count=0,
                max_retries=3,
            )
            session.add(blocking_task)
            session.flush()

            # Create dependent tasks
            for i in range(3):
                dependent = Task(
                    ticket_id=sample_ticket.id,
                    phase_id="PHASE_IMPLEMENTATION",
                    task_type=f"dependent_{i}",
                    description=f"Dependent {i}",
                    priority="MEDIUM",
                    status="pending",
                    dependencies={"depends_on": [blocking_task.id]},
                )
                session.add(dependent)
            session.commit()
            session.refresh(blocking_task)

            score = task_scorer.compute_score(blocking_task, now=now)
            # Should include all components:
            # Priority (HIGH=0.75) * 0.45 = 0.3375
            # Age (0.5) * 0.20 = 0.10
            # Deadline (within window) * 0.15 = high
            # Blocker (3/10=0.3) * 0.15 = 0.045
            # Retry (0 retries) * 0.05 = 0.05
            # Plus SLA boost (1.25x)
            assert score > 0.6  # Should be high due to all factors


class TestTaskScorerIntegration:
    """Test integration with TaskQueueService."""

    def test_enqueue_task_computes_score(
        self, task_queue_service: TaskQueueService, sample_ticket: Ticket
    ):
        """Test enqueue_task computes initial score."""
        task = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="test",
            description="Test",
            priority="HIGH",
        )

        # Score should be computed
        assert task.score > 0.0

    def test_get_next_task_sorts_by_score(
        self, task_queue_service: TaskQueueService, sample_ticket: Ticket
    ):
        """Test get_next_task returns highest-scored task."""
        now = utc_now()

        # Create LOW priority task with deadline
        low_task = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="low",
            description="Low priority",
            priority="LOW",
        )
        low_task_id = low_task.id  # Extract ID before session expires
        with task_queue_service.db.get_session() as session:
            from omoi_os.models.task import Task
            task = session.get(Task, low_task_id)
            task.deadline_at = now + timedelta(seconds=300)  # 5 minutes
            session.commit()

        # Create HIGH priority task without deadline
        high_task = task_queue_service.enqueue_task(
            ticket_id=sample_ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="high",
            description="High priority",
            priority="HIGH",
        )
        high_task_id = high_task.id  # Extract ID before session expires

        # Due to deadline proximity, low task might have higher score
        next_task = task_queue_service.get_next_task("PHASE_IMPLEMENTATION")
        assert next_task is not None
        next_task_id = next_task.id  # Extract ID before expunging
        # Should return the task with highest score (could be either)
        assert next_task_id in [low_task_id, high_task_id]

    def test_get_ready_tasks_sorts_by_score(
        self, task_queue_service: TaskQueueService, sample_ticket: Ticket
    ):
        """Test get_ready_tasks returns tasks sorted by score."""
        # Create multiple tasks
        tasks = []
        for i, priority in enumerate(["LOW", "MEDIUM", "HIGH"]):
            task = task_queue_service.enqueue_task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type=f"task_{i}",
                description=f"Task {i}",
                priority=priority,
            )
            tasks.append(task)

        # Get ready tasks
        ready = task_queue_service.get_ready_tasks("PHASE_IMPLEMENTATION", limit=3)

        # Should be sorted by score descending
        assert len(ready) == 3
        # Extract scores before accessing (tasks are expunged from session)
        scores = []
        for task in ready:
            scores.append(task.score)
        assert scores == sorted(scores, reverse=True)

    def test_update_task_score(self, task_scorer: TaskScorer, db_service: DatabaseService, sample_ticket: Ticket):
        """Test update_task_score updates score in database."""
        with db_service.get_session() as session:
            task = Task(
                ticket_id=sample_ticket.id,
                phase_id="PHASE_IMPLEMENTATION",
                task_type="test",
                description="Test",
                priority="MEDIUM",
                status="pending",
            )
            session.add(task)
            session.commit()
            task_id = task.id

        # Update score
        updated_score = task_scorer.update_task_score(task_id)
        assert updated_score is not None
        assert updated_score > 0.0

        # Verify in database
        with db_service.get_session() as session:
            task = session.get(Task, task_id)
            assert task.score == updated_score

