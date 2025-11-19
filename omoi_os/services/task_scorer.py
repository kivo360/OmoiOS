"""Task scoring service for dynamic task prioritization (REQ-TQM-PRI-002, REQ-TQM-PRI-003, REQ-TQM-PRI-004)."""

from datetime import datetime
from typing import Optional

from omoi_os.config import TaskQueueSettings
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


class TaskScorer:
    """
    Computes dynamic task scores per REQ-TQM-PRI-002.

    Composite score formula:
    score = w_p * P(priority) + w_a * A(age) + w_d * D(deadline) + w_b * B(blocker) + w_r * R(retry)

    Also applies SLA boost (REQ-TQM-PRI-003) and starvation guard (REQ-TQM-PRI-004).
    """

    def __init__(self, db: DatabaseService, config: Optional[TaskQueueSettings] = None):
        """
        Initialize task scorer.

        Args:
            db: Database service for querying blocker counts
            config: Task queue configuration (defaults to TaskQueueSettings())
        """
        self.db = db
        self.config = config or TaskQueueSettings()

        # Priority mapping per REQ-TQM-PRI-002
        self.priority_map = {
            "CRITICAL": 1.0,
            "HIGH": 0.75,
            "MEDIUM": 0.5,
            "LOW": 0.25,
        }

    def compute_score(self, task: Task, now: Optional[datetime] = None) -> float:
        """
        Compute dynamic score for a task per REQ-TQM-PRI-002.

        Args:
            task: Task to score
            now: Current time (defaults to utc_now())

        Returns:
            Computed score (0.0-1.0+)
        """
        if now is None:
            now = utc_now()

        # P(priority): discrete mapping (REQ-TQM-PRI-002)
        priority_score = self.priority_map.get(task.priority, 0.25)

        # A(age_seconds): normalized 0.0-1.0 with cap at AGE_CEILING (REQ-TQM-PRI-002)
        age_seconds = (now - task.created_at).total_seconds()
        age_norm = min(age_seconds / self.config.age_ceiling, 1.0)

        # D(deadline_slack): higher when closer to deadline (REQ-TQM-PRI-002)
        deadline_norm = 0.0
        if task.deadline_at:
            slack_seconds = (task.deadline_at - now).total_seconds()
            if slack_seconds <= 0:
                # Past deadline - maximum urgency
                deadline_norm = 1.0
            else:
                # Normalize: closer to deadline = higher score
                # At 0 seconds before deadline: 1.0, at SLA_URGENCY_WINDOW: 0.0
                deadline_norm = max(
                    0.0, 1.0 - (slack_seconds / self.config.sla_urgency_window)
                )
                # Cap at 1.0 if within urgency window
                if slack_seconds <= self.config.sla_urgency_window:
                    deadline_norm = min(1.0, deadline_norm)

        # B(blocker_count): increases urgency when this task unblocks others (REQ-TQM-PRI-002)
        blocker_count = self._get_blocker_count(task.id)
        blocker_norm = min(blocker_count / self.config.blocker_ceiling, 1.0)

        # R(retry_penalty): reduces score as retries accumulate (REQ-TQM-PRI-002)
        retry_ratio = task.retry_count / max(task.max_retries, 1)
        retry_penalty = max(0.0, 1.0 - retry_ratio)

        # Composite score (REQ-TQM-PRI-002)
        base_score = (
            self.config.w_p * priority_score
            + self.config.w_a * age_norm
            + self.config.w_d * deadline_norm
            + self.config.w_b * blocker_norm
            + self.config.w_r * retry_penalty
        )

        # SLA boost when deadline_at within SLA_URGENCY_WINDOW (REQ-TQM-PRI-003)
        if task.deadline_at:
            slack_seconds = (task.deadline_at - now).total_seconds()
            if 0 <= slack_seconds <= self.config.sla_urgency_window:
                base_score *= self.config.sla_boost_multiplier

        # Starvation guard: floor score after STARVATION_LIMIT (REQ-TQM-PRI-004)
        wait_seconds = (now - task.created_at).total_seconds()
        if wait_seconds >= self.config.starvation_limit:
            base_score = max(base_score, self.config.starvation_floor_score)

        return base_score

    def _get_blocker_count(self, task_id: str) -> int:
        """
        Get count of tasks blocked by this task (i.e., tasks that depend on this task).

        Args:
            task_id: Task ID to check

        Returns:
            Number of tasks blocked by this task
        """
        with self.db.get_session() as session:
            # Find all tasks that have this task_id in their dependencies
            all_tasks = session.query(Task).filter(Task.status == "pending").all()
            blocker_count = 0

            for task in all_tasks:
                if task.dependencies:
                    depends_on = task.dependencies.get("depends_on", [])
                    if task_id in depends_on:
                        blocker_count += 1

            return blocker_count

    def update_task_score(
        self, task_id: str, now: Optional[datetime] = None
    ) -> Optional[float]:
        """
        Update and persist task score in database.

        Args:
            task_id: Task ID to update
            now: Current time (defaults to utc_now())

        Returns:
            Updated score, or None if task not found
        """
        if now is None:
            now = utc_now()

        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None

            score = self.compute_score(task, now)
            task.score = score
            session.commit()
            return score

    def update_scores_for_tasks(
        self, task_ids: list[str], now: Optional[datetime] = None
    ) -> dict[str, float]:
        """
        Update scores for multiple tasks.

        Args:
            task_ids: List of task IDs to update
            now: Current time (defaults to utc_now())

        Returns:
            Dictionary mapping task_id to updated score
        """
        if now is None:
            now = utc_now()

        updated_scores = {}

        with self.db.get_session() as session:
            tasks = session.query(Task).filter(Task.id.in_(task_ids)).all()

            for task in tasks:
                score = self.compute_score(task, now)
                task.score = score
                updated_scores[task.id] = score

            session.commit()

        return updated_scores
