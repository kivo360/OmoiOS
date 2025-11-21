"""Diagnostic service for stuck workflow detection and recovery."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Dict, List, Optional

from sqlalchemy import desc

from omoi_os.models.diagnostic_run import DiagnosticRun
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.workflow_result import WorkflowResult
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.llm_service import get_llm_service
from omoi_os.schemas.diagnostic_analysis import DiagnosticAnalysis
from omoi_os.utils.datetime import utc_now

if TYPE_CHECKING:
    from omoi_os.services.discovery import DiscoveryService
    from omoi_os.services.memory import MemoryService
    from omoi_os.services.monitor import MonitorService


class DiagnosticService:
    """Service for detecting stuck workflows and spawning diagnostic agents.
    
    Monitors workflows for stuck conditions (all tasks done but no validated result)
    and automatically spawns diagnostic agents to analyze and create recovery tasks.
    """

    def __init__(
        self,
        db: DatabaseService,
        discovery: "DiscoveryService",
        memory: "MemoryService",
        monitor: "MonitorService",
        event_bus: Optional[EventBusService] = None,
    ):
        """Initialize diagnostic service.
        
        Args:
            db: Database service
            discovery: Discovery service for spawning recovery tasks
            memory: Memory service for context building
            monitor: Monitor service for metrics
            event_bus: Optional event bus for publishing events
        """
        self.db = db
        self.discovery = discovery
        self.memory = memory
        self.monitor = monitor
        self.event_bus = event_bus
        self._last_diagnostic: Dict[str, float] = {}  # workflow_id -> timestamp

    def find_stuck_workflows(
        self,
        cooldown_seconds: int = 60,
        stuck_threshold_seconds: int = 60,
    ) -> List[dict]:
        """Find workflows meeting all stuck conditions.
        
        Conditions (ALL must be true):
        1. Active workflow exists
        2. Tasks exist
        3. All tasks finished
        4. No validated WorkflowResult
        5. Cooldown passed
        6. Stuck time met
        
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
                active_tasks = (
                    session.query(Task)
                    .filter(
                        Task.ticket_id == ticket.id,
                        Task.status.in_([
                            "pending",
                            "assigned",
                            "running",
                            "under_review",
                            "validation_in_progress",
                        ]),
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
                        time_since = (utc_now() - last_task.completed_at).total_seconds()
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
                            .filter(Task.ticket_id == ticket.id, Task.status == "failed")
                            .count()
                        )

                        stuck.append({
                            "workflow_id": ticket.id,
                            "time_stuck_seconds": int(time_since),
                            "total_tasks": total_tasks,
                            "done_tasks": done_tasks,
                            "failed_tasks": failed_tasks,
                        })

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
                        diagnosis_parts.append(f"  - {hyp.statement} (likelihood: {hyp.likelihood:.2f})")
                if analysis.recommendations:
                    diagnosis_parts.append("\nRecommendations:")
                    for rec in analysis.recommendations[:max_tasks]:
                        diagnosis_parts.append(f"  - [{rec.priority}] {rec.description}")
                
                diagnosis_text = "\n".join(diagnosis_parts) if diagnosis_parts else "No specific diagnosis generated"
                
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
                
            except Exception as e:
                # If hypothesis generation fails, use fallback
                diagnosis_text = f"Diagnostic triggered: Workflow stuck for {context.get('time_stuck_seconds', 0)} seconds. All tasks completed but no validated result."
                suggested_phase = "PHASE_IMPLEMENTATION"
                suggested_priority = "HIGH"

            # Spawn recovery tasks via DiscoveryService
            try:
                with self.db.get_session() as session:
                    spawned_tasks = self.discovery.spawn_diagnostic_recovery(
                        session=session,
                        ticket_id=workflow_id,
                        diagnostic_run_id=diagnostic_run_id,
                        reason=diagnosis_text[:500],  # Truncate if too long
                        suggested_phase=suggested_phase,
                        suggested_priority=suggested_priority,
                        max_tasks=max_tasks,
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
            except Exception as e:
                # If spawning fails, mark as failed
                with self.db.get_session() as session:
                    diagnostic_run = session.get(DiagnosticRun, diagnostic_run_id)
                    if diagnostic_run:
                        diagnostic_run.status = "failed"
                        diagnostic_run.diagnosis = f"Failed to spawn recovery tasks: {str(e)}"
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
                            "tasks_created": diagnostic_run.tasks_created_count if diagnostic_run else 0,
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
                recent_tasks.append({
                    "task_id": task.id,
                    "phase_id": task.phase_id,
                    "task_type": task.task_type,
                    "status": task.status,
                    "description": task.description,
                    "result": task.result,
                    "error_message": task.error_message,
                })

            # Count task states
            total_tasks = session.query(Task).filter(Task.ticket_id == workflow_id).count()
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
                    "task_distribution": self._get_task_distribution(session, workflow_id),
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

            runs = (
                query.order_by(desc(DiagnosticRun.triggered_at))
                .limit(limit)
                .all()
            )

            for run in runs:
                session.expunge(run)

            return runs

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

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
                analyses.append({
                    "id": str(row.id),
                    "cycle_id": str(row.cycle_id),
                    "coherence_score": float(row.coherence_score),
                    "system_status": row.system_status,
                    "num_agents": row.num_agents,
                    "duplicate_count": row.duplicate_count,
                    "termination_count": row.termination_count,
                    "coordination_count": row.coordination_count,
                    "details": row.details or {},
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                })
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
                submitted_results.append({
                    "id": result.id,
                    "status": result.status,
                    "validated_at": result.validated_at.isoformat() if result.validated_at else None,
                    "validation_feedback": result.validation_feedback,
                    "markdown_file_path": result.markdown_file_path,
                    "explanation": result.explanation,
                    "created_at": result.created_at.isoformat() if result.created_at else None,
                })
            return submitted_results
        except Exception:
            return []

