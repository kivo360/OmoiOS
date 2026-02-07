"""Diagnostic service for stuck workflow detection and recovery."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Dict, List, Optional

import httpx
from sqlalchemy import desc, or_

from omoi_os.logging import get_logger
from omoi_os.models.diagnostic_run import DiagnosticRun
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.workflow_result import WorkflowResult
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.llm_service import get_llm_service
from omoi_os.schemas.diagnostic_analysis import DiagnosticAnalysis
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)

if TYPE_CHECKING:
    from omoi_os.services.discovery import DiscoveryService
    from omoi_os.services.memory import MemoryService
    from omoi_os.services.monitor import MonitorService
    from omoi_os.services.embedding import EmbeddingService
    from omoi_os.services.task_dedup import TaskDeduplicationService


class DiagnosticService:
    """Service for detecting stuck workflows and spawning diagnostic agents.

    Monitors workflows for stuck conditions (all tasks done but no validated result)
    and automatically spawns diagnostic agents to analyze and create recovery tasks.

    Safeguards against runaway task spawning:
    - Checks for pending diagnostic tasks before spawning new ones
    - Tracks consecutive failures and stops after max_consecutive_failures
    - Limits total diagnostic runs per workflow to max_diagnostics_per_workflow
    - Uses vector embeddings to detect semantically similar pending tasks (optional)
    """

    def __init__(
        self,
        db: DatabaseService,
        discovery: "DiscoveryService",
        memory: "MemoryService",
        monitor: "MonitorService",
        event_bus: Optional[EventBusService] = None,
        embedding_service: Optional["EmbeddingService"] = None,
    ):
        """Initialize diagnostic service.

        Args:
            db: Database service
            discovery: Discovery service for spawning recovery tasks
            memory: Memory service for context building
            monitor: Monitor service for metrics
            event_bus: Optional event bus for publishing events
            embedding_service: Optional embedding service for vector-based deduplication
        """
        self.db = db
        self.discovery = discovery
        self.memory = memory
        self.monitor = monitor
        self.event_bus = event_bus
        self._last_diagnostic: Dict[str, float] = {}  # workflow_id -> timestamp
        self._consecutive_failures: Dict[str, int] = {}  # workflow_id -> failure count

        # Load runaway prevention limits from config
        from omoi_os.config import get_app_settings

        settings = get_app_settings()
        self.max_consecutive_failures = settings.diagnostic.max_consecutive_failures
        self.max_diagnostics_per_workflow = (
            settings.diagnostic.max_diagnostics_per_workflow
        )

        # Initialize vector-based deduplication service (optional)
        self._task_dedup: Optional["TaskDeduplicationService"] = None
        if embedding_service:
            try:
                from omoi_os.services.task_dedup import TaskDeduplicationService

                self._task_dedup = TaskDeduplicationService(
                    db=db,
                    embedding_service=embedding_service,
                    similarity_threshold=0.90,  # Strict threshold for diagnostics
                )
                logger.info(
                    "Vector-based task deduplication enabled for diagnostic service"
                )
            except Exception as e:
                logger.warning(f"Could not initialize task deduplication: {e}")

    def find_stuck_workflows(
        self,
        cooldown_seconds: int = 60,
        stuck_threshold_seconds: int = 60,
    ) -> List[dict]:
        """Find workflows meeting all stuck conditions.

        Conditions (ALL must be true):
        1. Active workflow exists
        2. Tasks exist
        3. All tasks finished (no pending/running tasks)
        4. No validated WorkflowResult
        5. Cooldown passed
        6. Stuck time met

        Safeguard conditions (any true = skip):
        - Has pending diagnostic recovery tasks
        - Exceeded consecutive failure limit
        - Exceeded total diagnostic run limit

        Args:
            cooldown_seconds: Min time between diagnostics for same workflow
            stuck_threshold_seconds: Min time since last task activity

        Returns:
            List of stuck workflow info dicts
        """
        with self.db.get_session() as session:
            stuck = []

            # Get all non-done tickets
            tickets = session.query(Ticket).filter(Ticket.status != "done").all()

            for ticket in tickets:
                # Check if has tasks
                total_tasks = (
                    session.query(Task).filter(Task.ticket_id == ticket.id).count()
                )
                if total_tasks == 0:
                    continue

                # Check all tasks finished
                # Note: 'claiming' is a transient status during task assignment
                active_tasks = (
                    session.query(Task)
                    .filter(
                        Task.ticket_id == ticket.id,
                        Task.status.in_(
                            [
                                "pending",
                                "claiming",  # Transient status during atomic claim
                                "assigned",
                                "running",
                                "under_review",
                                "validation_in_progress",
                            ]
                        ),
                    )
                    .count()
                )

                if active_tasks > 0:
                    continue  # Has active tasks, not stuck

                # Check no validated WorkflowResult
                validated = (
                    session.query(WorkflowResult)
                    .filter(
                        WorkflowResult.workflow_id == ticket.id,
                        WorkflowResult.status == "validated",
                    )
                    .first()
                )

                if validated:
                    continue  # Has validated result, workflow complete

                # ===== SAFEGUARD: All tasks completed successfully without failures =====
                # Simple tasks (like creating a Python script) don't always produce
                # a WorkflowResult, but if all tasks completed and none failed,
                # the workflow succeeded - don't spawn diagnostics!
                completed_tasks = (
                    session.query(Task)
                    .filter(
                        Task.ticket_id == ticket.id,
                        Task.status == "completed",
                    )
                    .count()
                )
                failed_tasks = (
                    session.query(Task)
                    .filter(
                        Task.ticket_id == ticket.id,
                        Task.status == "failed",
                    )
                    .count()
                )

                # If we have completed tasks and NO failed tasks, workflow succeeded
                # This prevents runaway diagnostics for simple successful workflows
                if completed_tasks > 0 and failed_tasks == 0:
                    logger.debug(
                        f"Skipping workflow {ticket.id}: all {completed_tasks} tasks completed successfully (no WorkflowResult needed)"
                    )
                    continue

                # ===== SAFEGUARD: Diagnostic tasks already attempted for failed original tasks =====
                # Count COMPLETED diagnostic tasks - if we already tried diagnostics and they
                # completed but the original task is still failed, stop spawning more.
                # The workflow needs human intervention, not more diagnostic loops.
                completed_diagnostic_tasks = (
                    session.query(Task)
                    .filter(
                        Task.ticket_id == ticket.id,
                        Task.task_type.like("discovery_diagnostic%"),
                        Task.status == "completed",
                    )
                    .count()
                )

                # Count non-diagnostic failed tasks (original work that failed)
                failed_original_tasks = (
                    session.query(Task)
                    .filter(
                        Task.ticket_id == ticket.id,
                        Task.status == "failed",
                        ~Task.task_type.like("discovery_diagnostic%"),
                    )
                    .count()
                )

                if completed_diagnostic_tasks > 0 and failed_original_tasks > 0:
                    logger.info(
                        f"Skipping workflow {ticket.id}: {completed_diagnostic_tasks} diagnostic tasks "
                        f"completed but {failed_original_tasks} original task(s) still failed - "
                        "needs human review, not more diagnostics"
                    )
                    continue

                # ===== SAFEGUARD: Check for pending diagnostic tasks =====
                # If there are already pending/running diagnostic tasks, don't spawn more
                pending_diagnostic_tasks = (
                    session.query(Task)
                    .filter(
                        Task.ticket_id == ticket.id,
                        Task.task_type.like("discovery_diagnostic%"),
                        Task.status.in_(["pending", "claiming", "assigned", "running"]),
                    )
                    .count()
                )
                if pending_diagnostic_tasks > 0:
                    logger.debug(
                        f"Skipping workflow {ticket.id}: has {pending_diagnostic_tasks} pending diagnostic tasks"
                    )
                    continue

                # ===== SAFEGUARD: Check consecutive failure limit =====
                consecutive_failures = self._consecutive_failures.get(ticket.id, 0)
                if consecutive_failures >= self.max_consecutive_failures:
                    logger.warning(
                        f"Skipping workflow {ticket.id}: exceeded max consecutive failures ({consecutive_failures})"
                    )
                    continue

                # ===== SAFEGUARD: Check total diagnostic run limit =====
                total_diagnostic_runs = (
                    session.query(DiagnosticRun)
                    .filter(DiagnosticRun.workflow_id == ticket.id)
                    .count()
                )
                if total_diagnostic_runs >= self.max_diagnostics_per_workflow:
                    logger.warning(
                        f"Skipping workflow {ticket.id}: exceeded max total diagnostics ({total_diagnostic_runs})"
                    )
                    continue

                # ===== SAFEGUARD: Check clone readiness =====
                # Skip diagnostics for workflows that can't clone code into sandbox
                # (missing project, GitHub config, or user token)
                clone_ready, clone_reason = self._check_clone_readiness(session, ticket)
                if not clone_ready:
                    logger.debug(
                        f"Skipping workflow {ticket.id}: not clone-ready ({clone_reason})"
                    )
                    continue

                # Check cooldown
                now_timestamp = utc_now().timestamp()
                if ticket.id in self._last_diagnostic:
                    time_since_last = now_timestamp - self._last_diagnostic[ticket.id]
                    if time_since_last < cooldown_seconds:
                        continue  # Cooldown not passed

                # Check stuck time
                last_task = (
                    session.query(Task)
                    .filter(Task.ticket_id == ticket.id)
                    .order_by(desc(Task.completed_at))
                    .first()
                )

                if last_task:
                    if last_task.completed_at:
                        time_since = (
                            utc_now() - last_task.completed_at
                        ).total_seconds()
                    else:
                        time_since = (utc_now() - last_task.created_at).total_seconds()

                    if time_since >= stuck_threshold_seconds:
                        # Count task states
                        done_tasks = (
                            session.query(Task)
                            .filter(
                                Task.ticket_id == ticket.id, Task.status == "completed"
                            )
                            .count()
                        )
                        failed_tasks = (
                            session.query(Task)
                            .filter(
                                Task.ticket_id == ticket.id, Task.status == "failed"
                            )
                            .count()
                        )

                        stuck.append(
                            {
                                "workflow_id": ticket.id,
                                "time_stuck_seconds": int(time_since),
                                "total_tasks": total_tasks,
                                "done_tasks": done_tasks,
                                "failed_tasks": failed_tasks,
                            }
                        )

            return stuck

    async def spawn_diagnostic_agent(
        self,
        workflow_id: str,
        context: dict,
        max_tasks: int = 5,
    ) -> DiagnosticRun:
        """Create diagnostic run, generate hypotheses, and spawn recovery tasks.

        Args:
            workflow_id: ID of stuck workflow
            context: Rich diagnostic context
            max_tasks: Maximum number of recovery tasks to spawn

        Returns:
            Created DiagnosticRun record with spawned tasks
        """
        with self.db.get_session() as session:
            # Create diagnostic run record
            diagnostic_run = DiagnosticRun(
                workflow_id=workflow_id,
                triggered_at=utc_now(),
                total_tasks_at_trigger=context.get("total_tasks", 0),
                done_tasks_at_trigger=context.get("done_tasks", 0),
                failed_tasks_at_trigger=context.get("failed_tasks", 0),
                time_since_last_task_seconds=context.get("time_stuck_seconds", 0),
                workflow_goal=context.get("workflow_goal"),
                phases_analyzed=context.get("phases_analyzed"),
                agents_reviewed=context.get("agents_reviewed"),
                status="running",
            )
            session.add(diagnostic_run)
            session.commit()
            session.refresh(diagnostic_run)

            # Update cooldown tracking
            self._last_diagnostic[workflow_id] = utc_now().timestamp()

            diagnostic_run_id = diagnostic_run.id
            session.expunge(diagnostic_run)

            # Generate hypotheses using LLM analysis
            try:
                # Await async hypothesis generation
                analysis = await self.generate_hypotheses(context)

                # Extract diagnosis text from analysis
                diagnosis_parts = []
                if analysis.root_cause:
                    diagnosis_parts.append(f"Root Cause: {analysis.root_cause}")
                if analysis.hypotheses:
                    diagnosis_parts.append("\nHypotheses:")
                    for hyp in analysis.hypotheses[:3]:  # Top 3
                        diagnosis_parts.append(
                            f"  - {hyp.statement} (likelihood: {hyp.likelihood:.2f})"
                        )
                if analysis.recommendations:
                    diagnosis_parts.append("\nRecommendations:")
                    for rec in analysis.recommendations[:max_tasks]:
                        diagnosis_parts.append(
                            f"  - [{rec.priority}] {rec.description}"
                        )

                diagnosis_text = (
                    "\n".join(diagnosis_parts)
                    if diagnosis_parts
                    else "No specific diagnosis generated"
                )

                # Determine suggested phase and priority from recommendations
                suggested_phase = "PHASE_IMPLEMENTATION"  # Default
                suggested_priority = "HIGH"  # Default

                if analysis.recommendations:
                    # Use first recommendation's priority
                    suggested_priority = analysis.recommendations[0].priority
                    # Try to infer phase from recommendation (basic heuristic)
                    rec_desc = analysis.recommendations[0].description.lower()
                    if "test" in rec_desc or "validate" in rec_desc:
                        suggested_phase = "PHASE_TESTING"
                    elif "requirement" in rec_desc or "clarify" in rec_desc:
                        suggested_phase = "PHASE_REQUIREMENTS"
                    elif "implement" in rec_desc or "build" in rec_desc:
                        suggested_phase = "PHASE_IMPLEMENTATION"

            except Exception:
                # If hypothesis generation fails, use fallback
                diagnosis_text = f"Diagnostic triggered: Workflow stuck for {context.get('time_stuck_seconds', 0)} seconds. All tasks completed but no validated result."
                suggested_phase = "PHASE_IMPLEMENTATION"
                suggested_priority = "HIGH"

            # ===== SAFEGUARD: Vector-based semantic deduplication =====
            # Check for semantically similar pending diagnostic tasks before spawning
            if self._task_dedup:
                try:
                    dedup_result = self._task_dedup.check_similar_pending_diagnostic(
                        workflow_id=workflow_id,
                        description=diagnosis_text,
                        threshold=0.90,  # High threshold for strict matching
                    )
                    if dedup_result.is_duplicate:
                        logger.warning(
                            f"Skipping diagnostic spawn for workflow {workflow_id}: "
                            f"Found semantically similar pending task(s) with similarity {dedup_result.highest_similarity:.2f}. "
                            f"Similar tasks: {[c.task_id[:8] for c in dedup_result.candidates[:3]]}"
                        )
                        # Update diagnostic run to indicate skipped
                        with self.db.get_session() as session:
                            diagnostic_run = session.get(
                                DiagnosticRun, diagnostic_run_id
                            )
                            if diagnostic_run:
                                diagnostic_run.status = "skipped"
                                diagnostic_run.diagnosis = (
                                    f"Skipped: Found semantically similar pending task(s) "
                                    f"(similarity: {dedup_result.highest_similarity:.2f})"
                                )
                                diagnostic_run.completed_at = utc_now()
                                session.commit()
                                session.expunge(diagnostic_run)
                        return diagnostic_run
                except Exception as e:
                    logger.warning(
                        f"Vector deduplication check failed, continuing with spawn: {e}"
                    )

            # Spawn recovery tasks via DiscoveryService
            try:
                with self.db.get_session() as session:
                    spawned_tasks = await self.discovery.spawn_diagnostic_recovery(
                        session=session,
                        ticket_id=workflow_id,
                        diagnostic_run_id=diagnostic_run_id,
                        reason=diagnosis_text[
                            :2000
                        ],  # Allow detailed context for task description
                        suggested_phase=suggested_phase,
                        suggested_priority=suggested_priority,
                        max_tasks=max_tasks,
                    )

                    # Store embeddings for newly spawned tasks (for future dedup)
                    if self._task_dedup and spawned_tasks:
                        for task in spawned_tasks:
                            try:
                                self._task_dedup.generate_and_store_embedding(
                                    task, session
                                )
                            except Exception as e:
                                logger.debug(
                                    f"Could not store embedding for task {task.id}: {e}"
                                )

                    # Update diagnostic run with results
                    diagnostic_run = session.get(DiagnosticRun, diagnostic_run_id)
                    if diagnostic_run:
                        task_ids = [str(task.id) for task in spawned_tasks]
                        diagnostic_run.tasks_created_count = len(task_ids)
                        diagnostic_run.tasks_created_ids = {"task_ids": task_ids}
                        diagnostic_run.diagnosis = diagnosis_text
                        diagnostic_run.status = "completed"
                        diagnostic_run.completed_at = utc_now()
                        session.commit()
                        session.refresh(diagnostic_run)
                        session.expunge(diagnostic_run)

                    # Notify active agents about recovery tasks via intervention system
                    self._notify_agents_of_recovery_tasks(
                        session=session,
                        workflow_id=workflow_id,
                        spawned_tasks=spawned_tasks,
                        diagnosis_text=diagnosis_text,
                    )
            except Exception as e:
                # If spawning fails, mark as failed
                with self.db.get_session() as session:
                    diagnostic_run = session.get(DiagnosticRun, diagnostic_run_id)
                    if diagnostic_run:
                        diagnostic_run.status = "failed"
                        diagnostic_run.diagnosis = (
                            f"Failed to spawn recovery tasks: {str(e)}"
                        )
                        session.commit()
                        session.expunge(diagnostic_run)

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="diagnostic.triggered",
                        entity_type="diagnostic_run",
                        entity_id=diagnostic_run_id,
                        payload={
                            "workflow_id": workflow_id,
                            "time_stuck_seconds": context.get("time_stuck_seconds", 0),
                            "tasks_created": (
                                diagnostic_run.tasks_created_count
                                if diagnostic_run
                                else 0
                            ),
                        },
                    )
                )

            return diagnostic_run

    async def generate_hypotheses(
        self,
        context: dict,
    ) -> DiagnosticAnalysis:
        """
        Generate hypotheses and recommendations for a stuck workflow using PydanticAI.

        Args:
            context: Diagnostic context from build_diagnostic_context()

        Returns:
            DiagnosticAnalysis with hypotheses and recommendations
        """
        # Build prompt using template
        from omoi_os.services.template_service import get_template_service

        template_service = get_template_service()
        prompt = template_service.render(
            "prompts/diagnostic.md.j2",
            workflow_goal=context.get("workflow_goal", "Unknown"),
            current_phase=context.get("current_phase", "Unknown"),
            total_tasks=context.get("total_tasks", 0),
            done_tasks=context.get("done_tasks", 0),
            failed_tasks=context.get("failed_tasks", 0),
            time_stuck_seconds=context.get("time_stuck_seconds", 0),
            recent_tasks=context.get("recent_tasks", [])[:10],
        )

        system_prompt = template_service.render_system_prompt("system/diagnostic.md.j2")

        # Run analysis using LLM service
        llm = get_llm_service()
        return await llm.structured_output(
            prompt,
            output_type=DiagnosticAnalysis,
            system_prompt=system_prompt,
        )

    def build_diagnostic_context(
        self,
        workflow_id: str,
        max_agents: int = 15,
        max_analyses: int = 5,
    ) -> dict:
        """Build comprehensive context for diagnostic agent.

        Args:
            workflow_id: ID of workflow to analyze
            max_agents: Max number of recent agents to include
            max_analyses: Max number of analyses to include

        Returns:
            Structured context dict for diagnostic agent
        """
        with self.db.get_session() as session:
            # Get workflow info
            ticket = session.get(Ticket, workflow_id)
            if not ticket:
                return {}

            # Get all tasks for workflow
            tasks = (
                session.query(Task)
                .filter(Task.ticket_id == workflow_id)
                .order_by(desc(Task.completed_at))
                .limit(max_agents)
                .all()
            )

            # Get task summaries
            recent_tasks = []
            for task in tasks:
                recent_tasks.append(
                    {
                        "task_id": task.id,
                        "phase_id": task.phase_id,
                        "task_type": task.task_type,
                        "status": task.status,
                        "description": task.description,
                        "result": task.result,
                        "error_message": task.error_message,
                    }
                )

            # Count task states
            total_tasks = (
                session.query(Task).filter(Task.ticket_id == workflow_id).count()
            )
            done_tasks = (
                session.query(Task)
                .filter(Task.ticket_id == workflow_id, Task.status == "completed")
                .count()
            )
            failed_tasks = (
                session.query(Task)
                .filter(Task.ticket_id == workflow_id, Task.status == "failed")
                .count()
            )

            # Try to get workflow config
            try:
                from omoi_os.services.phase_loader import PhaseLoader

                loader = PhaseLoader()
                config = loader.load_workflow_config("software_development.yaml")
                workflow_goal = config.result_criteria
            except Exception:
                workflow_goal = ticket.description

            # Get Conductor analyses (last max_analyses)
            conductor_analyses = self._get_conductor_analyses(session, max_analyses)

            # Get submitted WorkflowResults (all submissions, even rejected)
            submitted_results = self._get_workflow_results(session, workflow_id)

            # Build context
            context = {
                "workflow_id": workflow_id,
                "workflow_goal": workflow_goal,
                "ticket_title": ticket.title,
                "ticket_description": ticket.description,
                "current_phase": ticket.phase_id,
                "total_tasks": total_tasks,
                "done_tasks": done_tasks,
                "failed_tasks": failed_tasks,
                "recent_tasks": recent_tasks[:max_agents],
                "agents_reviewed": {"count": len(recent_tasks), "tasks": recent_tasks},
                "phases_analyzed": {
                    "current_phase": ticket.phase_id,
                    "task_distribution": self._get_task_distribution(
                        session, workflow_id
                    ),
                },
                "conductor_analyses": conductor_analyses,
                "submitted_results": submitted_results,
            }

            return context

    def complete_diagnostic_run(
        self,
        run_id: str,
        tasks_created: List[str],
        diagnosis: str,
    ) -> Optional[DiagnosticRun]:
        """Mark diagnostic run as completed.

        Args:
            run_id: ID of diagnostic run
            tasks_created: List of task IDs created by diagnostic
            diagnosis: Diagnostic agent's analysis text

        Returns:
            Updated DiagnosticRun or None if not found
        """
        with self.db.get_session() as session:
            diagnostic_run = session.get(DiagnosticRun, run_id)
            if not diagnostic_run:
                return None

            diagnostic_run.tasks_created_count = len(tasks_created)
            diagnostic_run.tasks_created_ids = {"task_ids": tasks_created}
            diagnostic_run.diagnosis = diagnosis
            diagnostic_run.status = "completed"
            diagnostic_run.completed_at = utc_now()

            session.commit()
            session.refresh(diagnostic_run)
            session.expunge(diagnostic_run)

            # Publish completion event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="diagnostic.completed",
                        entity_type="diagnostic_run",
                        entity_id=run_id,
                        payload={
                            "workflow_id": diagnostic_run.workflow_id,
                            "tasks_created": len(tasks_created),
                        },
                    )
                )

            return diagnostic_run

    def get_diagnostic_runs(
        self,
        workflow_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[DiagnosticRun]:
        """Get diagnostic run history.

        Args:
            workflow_id: Optional filter by workflow
            limit: Max number of runs to return

        Returns:
            List of DiagnosticRun records
        """
        with self.db.get_session() as session:
            query = session.query(DiagnosticRun)

            if workflow_id:
                query = query.filter(DiagnosticRun.workflow_id == workflow_id)

            runs = query.order_by(desc(DiagnosticRun.triggered_at)).limit(limit).all()

            for run in runs:
                session.expunge(run)

            return runs

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _check_clone_readiness(self, session, ticket: Ticket) -> tuple[bool, str]:
        """Check if a workflow/ticket can clone code into a sandbox.

        Verifies the complete chain:
        Ticket → Project → Project.created_by → User → user.attributes.github_access_token

        If ticket is not linked to a project, attempts to auto-assign it to a
        suitable project that has valid GitHub config and an owner with a token.

        Args:
            session: Database session
            ticket: The ticket to check

        Returns:
            Tuple of (is_ready: bool, reason: str)
        """
        from omoi_os.models.user import User

        # Check 1: Ticket must be linked to a project
        # Orphan tickets cannot be diagnosed - they need to be created with a project
        # Auto-assignment is dangerous in multi-user environments (could assign to wrong user's project)
        if not ticket.project_id:
            logger.warning(
                f"Skipping diagnostic for orphan ticket {ticket.id} - "
                "ticket must be linked to a project at creation time"
            )
            return False, "ticket_not_linked_to_project"

        # Check 2: Project must exist
        project = ticket.project
        if not project:
            return False, "project_not_found"

        # Check 3: Project must have GitHub config
        if not project.github_owner or not project.github_repo:
            return False, "project_missing_github_config"

        # Check 4: Project must have an owner (created_by)
        if not project.created_by:
            return False, "project_has_no_owner"

        # Check 5: Owner must exist
        owner = session.get(User, project.created_by)
        if not owner:
            return False, "project_owner_not_found"

        # Check 6: Owner must have GitHub access token
        attrs = owner.attributes or {}
        if not attrs.get("github_access_token"):
            return False, "owner_missing_github_token"

        # All checks passed - clone should work
        return True, "ready"

    def _project_is_clone_ready(self, session, project) -> bool:
        """Check if a project is ready for cloning (has owner with token).

        Args:
            session: Database session
            project: Project to check

        Returns:
            True if project can clone repos, False otherwise
        """
        from omoi_os.models.user import User

        if not project.created_by:
            return False

        owner = session.get(User, project.created_by)
        if not owner:
            return False

        attrs = owner.attributes or {}
        return bool(attrs.get("github_access_token"))

    def _get_task_distribution(self, session, workflow_id: str) -> dict:
        """Get task count by phase for a workflow."""
        from sqlalchemy import func

        phase_counts = (
            session.query(Task.phase_id, func.count(Task.id))
            .filter(Task.ticket_id == workflow_id)
            .group_by(Task.phase_id)
            .all()
        )

        return {phase: count for phase, count in phase_counts}

    def _notify_agents_of_recovery_tasks(
        self,
        session,
        workflow_id: str,
        spawned_tasks: List[Task],
        diagnosis_text: str,
    ) -> None:
        """Notify active agents working on workflow about recovery tasks via intervention system.

        Finds all agents with active tasks for this workflow and sends intervention messages
        explaining why recovery tasks were spawned and how to coordinate.

        Args:
            session: Database session
            workflow_id: Workflow (ticket) ID
            spawned_tasks: List of recovery tasks that were spawned
            diagnosis_text: Diagnostic analysis explaining why recovery was needed
        """
        try:
            from omoi_os.models.agent import Agent
            from omoi_os.services.conversation_intervention import (
                ConversationInterventionService,
            )

            # Find all active tasks for this workflow - supports both legacy and sandbox modes
            # Legacy: has assigned_agent_id + conversation_id + persistence_dir
            # Sandbox: has sandbox_id
            active_tasks = (
                session.query(Task)
                .filter(
                    Task.ticket_id == workflow_id,
                    or_(
                        # Legacy mode
                        Task.assigned_agent_id.isnot(None),
                        # Sandbox mode
                        Task.sandbox_id.isnot(None),
                    ),
                    Task.status.in_(
                        [
                            "claiming",
                            "assigned",
                            "running",
                            "under_review",
                            "validation_in_progress",
                        ]
                    ),
                )
                .all()
            )

            if not active_tasks:
                return  # No active agents to notify

            # Separate tasks into legacy and sandbox groups
            legacy_tasks = []
            sandbox_tasks = []
            for task in active_tasks:
                if task.sandbox_id:
                    sandbox_tasks.append(task)
                elif (
                    task.assigned_agent_id
                    and task.conversation_id
                    and task.persistence_dir
                ):
                    legacy_tasks.append(task)

            # Group legacy tasks by agent
            agent_tasks = {}
            for task in legacy_tasks:
                agent_id = task.assigned_agent_id
                if agent_id not in agent_tasks:
                    agent_tasks[agent_id] = []
                agent_tasks[agent_id].append(task)

            # Build intervention message
            recovery_task_descriptions = [
                f"- {task.description[:100]}" for task in spawned_tasks[:3]
            ]
            if len(spawned_tasks) > 3:
                recovery_task_descriptions.append(
                    f"- ... and {len(spawned_tasks) - 3} more"
                )

            # Build intervention message (will be prefixed with [GUARDIAN INTERVENTION] by ConversationInterventionService)
            intervention_message = (
                f"DIAGNOSTIC RECOVERY: Workflow was stuck and diagnostic analysis identified issues. "
                f"{len(spawned_tasks)} recovery task(s) have been created:\n\n"
                + "\n".join(recovery_task_descriptions)
                + f"\n\nDiagnosis: {diagnosis_text[:300]}"
                f"\n\nPlease coordinate with these recovery tasks and adjust your work accordingly. "
                f"If you're blocked, consider pausing to let recovery tasks proceed first."
            )

            # Send intervention to each active agent
            intervention_service = ConversationInterventionService()
            notified_count = 0

            for agent_id, tasks in agent_tasks.items():
                # Use the first task's conversation info (all tasks for same agent share conversation)
                task = tasks[0]

                # Get workspace directory
                agent = session.get(Agent, agent_id)
                workspace_dir = None
                if agent and hasattr(agent, "workspace_dir"):
                    workspace_dir = agent.workspace_dir
                if not workspace_dir:
                    # Fallback: construct from task
                    from omoi_os.config import get_app_settings

                    app_settings = get_app_settings()
                    workspace_root = app_settings.workspace.root
                    workspace_dir = f"{workspace_root}/{task.id}"

                # Send intervention
                success = intervention_service.send_intervention(
                    conversation_id=task.conversation_id,
                    persistence_dir=task.persistence_dir,
                    workspace_dir=workspace_dir,
                    message=intervention_message,
                )

                if success:
                    notified_count += 1
                    logger.info(
                        f"Notified agent {agent_id[:8]} about {len(spawned_tasks)} recovery tasks "
                        f"for workflow {workflow_id}"
                    )

            # Notify sandbox agents via message injection API
            sandbox_notified = 0
            for task in sandbox_tasks:
                success = self._send_sandbox_diagnostic_notification(
                    task.sandbox_id, intervention_message
                )
                if success:
                    sandbox_notified += 1
                    logger.info(
                        f"Notified sandbox {task.sandbox_id[:8]} about {len(spawned_tasks)} recovery tasks "
                        f"for workflow {workflow_id}"
                    )

            total_notified = notified_count + sandbox_notified
            if total_notified > 0:
                logger.info(
                    f"Sent recovery task notifications to {total_notified} active agent(s) "
                    f"({notified_count} legacy, {sandbox_notified} sandbox) for workflow {workflow_id}"
                )

        except Exception as e:
            # Don't fail diagnostic if intervention notification fails
            logger.warning(
                f"Failed to notify agents about recovery tasks for workflow {workflow_id}: {e}",
                exc_info=True,
            )

    def _send_sandbox_diagnostic_notification(
        self, sandbox_id: str, message: str
    ) -> bool:
        """Send diagnostic notification to sandbox agent via message injection API."""
        base_url = (
            os.environ.get("MCP_SERVER_URL", "http://localhost:18000")
            .replace("/mcp", "")
            .rstrip("/")
        )

        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    f"{base_url}/api/v1/sandboxes/{sandbox_id}/messages",
                    json={
                        "content": message,
                        "message_type": "diagnostic_recovery",
                    },
                )

                if response.status_code == 200:
                    logger.info(
                        f"Successfully sent diagnostic notification to sandbox {sandbox_id}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Failed to send diagnostic notification: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(
                f"Failed to send diagnostic notification to sandbox {sandbox_id}: {e}"
            )
            return False

    def _get_conductor_analyses(self, session, max_analyses: int) -> List[dict]:
        """Get recent Conductor analyses for system context."""
        from sqlalchemy import text

        try:
            query = text("""
                SELECT 
                    id,
                    cycle_id,
                    coherence_score,
                    system_status,
                    num_agents,
                    duplicate_count,
                    termination_count,
                    coordination_count,
                    details,
                    created_at
                FROM conductor_analyses
                ORDER BY created_at DESC
                LIMIT :limit
            """)

            result = session.execute(query, {"limit": max_analyses})
            analyses = []
            for row in result.fetchall():
                analyses.append(
                    {
                        "id": str(row.id),
                        "cycle_id": str(row.cycle_id),
                        "coherence_score": float(row.coherence_score),
                        "system_status": row.system_status,
                        "num_agents": row.num_agents,
                        "duplicate_count": row.duplicate_count,
                        "termination_count": row.termination_count,
                        "coordination_count": row.coordination_count,
                        "details": row.details or {},
                        "created_at": (
                            row.created_at.isoformat() if row.created_at else None
                        ),
                    }
                )
            return analyses
        except Exception:
            # Table might not exist or query failed
            return []

    def _get_workflow_results(self, session, workflow_id: str) -> List[dict]:
        """Get all WorkflowResult submissions for a workflow (including rejected)."""
        try:
            results = (
                session.query(WorkflowResult)
                .filter(WorkflowResult.workflow_id == workflow_id)
                .order_by(desc(WorkflowResult.created_at))
                .all()
            )

            submitted_results = []
            for result in results:
                submitted_results.append(
                    {
                        "id": result.id,
                        "status": result.status,
                        "validated_at": (
                            result.validated_at.isoformat()
                            if result.validated_at
                            else None
                        ),
                        "validation_feedback": result.validation_feedback,
                        "markdown_file_path": result.markdown_file_path,
                        "explanation": result.explanation,
                        "created_at": (
                            result.created_at.isoformat() if result.created_at else None
                        ),
                    }
                )
            return submitted_results
        except Exception:
            return []

    # -------------------------------------------------------------------------
    # Failure Tracking Methods (Runaway Prevention)
    # -------------------------------------------------------------------------

    def record_diagnostic_task_failure(self, workflow_id: str) -> int:
        """Record a diagnostic task failure for a workflow.

        Increments the consecutive failure counter. When this reaches
        max_consecutive_failures, no more diagnostics will be spawned.

        Args:
            workflow_id: The workflow that had a diagnostic task fail

        Returns:
            Current consecutive failure count
        """
        current_count = self._consecutive_failures.get(workflow_id, 0)
        new_count = current_count + 1
        self._consecutive_failures[workflow_id] = new_count

        if new_count >= self.max_consecutive_failures:
            logger.warning(
                f"Workflow {workflow_id} reached max consecutive diagnostic failures ({new_count}). "
                "No more diagnostic tasks will be spawned until manually reset or a success occurs."
            )
        else:
            logger.info(
                f"Workflow {workflow_id} diagnostic failure recorded ({new_count}/{self.max_consecutive_failures})"
            )

        return new_count

    def record_diagnostic_task_success(self, workflow_id: str) -> None:
        """Record a diagnostic task success for a workflow.

        Resets the consecutive failure counter, allowing future diagnostics.

        Args:
            workflow_id: The workflow that had a diagnostic task succeed
        """
        if workflow_id in self._consecutive_failures:
            old_count = self._consecutive_failures[workflow_id]
            del self._consecutive_failures[workflow_id]
            logger.info(
                f"Workflow {workflow_id} diagnostic success - reset failure counter (was {old_count})"
            )

    def reset_failure_tracking(self, workflow_id: Optional[str] = None) -> None:
        """Reset failure tracking for a specific workflow or all workflows.

        Use this to manually allow diagnostics to resume after investigation.

        Args:
            workflow_id: Specific workflow to reset, or None to reset all
        """
        if workflow_id:
            if workflow_id in self._consecutive_failures:
                del self._consecutive_failures[workflow_id]
                logger.info(f"Reset failure tracking for workflow {workflow_id}")
        else:
            count = len(self._consecutive_failures)
            self._consecutive_failures.clear()
            logger.info(f"Reset failure tracking for all {count} workflows")

    def get_failure_stats(self) -> Dict[str, int]:
        """Get current failure tracking statistics.

        Returns:
            Dict mapping workflow_id to consecutive failure count
        """
        return dict(self._consecutive_failures)

    def check_diagnostic_task_outcomes(self) -> None:
        """Check recent diagnostic task outcomes and update failure tracking.

        This should be called periodically (e.g., in the monitoring loop) to
        detect when spawned diagnostic tasks have completed or failed.
        """
        with self.db.get_session() as session:
            # Find all diagnostic runs that have spawned tasks
            recent_runs = (
                session.query(DiagnosticRun)
                .filter(
                    DiagnosticRun.status == "completed",
                    DiagnosticRun.tasks_created_count > 0,
                )
                .order_by(desc(DiagnosticRun.completed_at))
                .limit(100)
                .all()
            )

            for run in recent_runs:
                if not run.tasks_created_ids:
                    continue

                task_ids = run.tasks_created_ids.get("task_ids", [])
                if not task_ids:
                    continue

                # Check the status of spawned tasks
                tasks = session.query(Task).filter(Task.id.in_(task_ids)).all()

                # Count statuses
                completed = sum(1 for t in tasks if t.status == "completed")
                failed = sum(1 for t in tasks if t.status == "failed")
                pending_or_running = sum(
                    1
                    for t in tasks
                    if t.status in ["pending", "claiming", "assigned", "running"]
                )

                # If any task succeeded, record success
                if completed > 0:
                    self.record_diagnostic_task_success(run.workflow_id)
                # If all tasks failed and none pending, record failure
                elif failed > 0 and pending_or_running == 0:
                    # Only record if we haven't already for this run
                    # (Use a simple check - if failure count is less than run count)
                    self.record_diagnostic_task_failure(run.workflow_id)
