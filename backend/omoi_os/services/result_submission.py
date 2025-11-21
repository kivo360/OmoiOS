"""Result submission service for task-level and workflow-level results."""

from __future__ import annotations

from typing import List, Optional

from omoi_os.models.agent_result import AgentResult
from omoi_os.models.task import Task
from omoi_os.models.workflow_result import WorkflowResult
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.phase_loader import PhaseLoader
from omoi_os.services.validation_helpers import read_markdown_file
from omoi_os.utils.datetime import utc_now


class ResultSubmissionService:
    """Service for submitting and validating task-level and workflow-level results.
    
    Handles two types of results:
    1. AgentResult - Task-level achievements with verification tracking
    2. WorkflowResult - Workflow-level completion with automatic validation
    """

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        phase_loader: Optional[PhaseLoader] = None,
    ):
        """Initialize result submission service.
        
        Args:
            db: Database service
            event_bus: Optional event bus for publishing events
            phase_loader: Optional phase loader for workflow config
        """
        self.db = db
        self.event_bus = event_bus
        self.phase_loader = phase_loader or PhaseLoader()

    # -------------------------------------------------------------------------
    # Task-Level Results (AgentResult)
    # -------------------------------------------------------------------------

    def report_task_result(
        self,
        agent_id: str,
        task_id: str,
        markdown_file_path: str,
        result_type: str,
        summary: str,
    ) -> AgentResult:
        """Submit task-level result.
        
        Args:
            agent_id: ID of agent submitting result
            task_id: ID of task being reported on
            markdown_file_path: Path to markdown result file
            result_type: Type of result (implementation, analysis, fix, etc.)
            summary: Brief summary of result
            
        Returns:
            Created AgentResult record
            
        Raises:
            FileNotFoundError: If markdown file doesn't exist
            ValueError: If file validation fails or agent doesn't own task
        """
        # Verify agent owns task
        with self.db.get_session() as session:
            task = session.get(Task, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            if task.assigned_agent_id != agent_id:
                raise ValueError(
                    f"Task {task_id} is not assigned to agent {agent_id}"
                )

        # Validate and read file
        markdown_content = read_markdown_file(markdown_file_path)

        # Create result record
        with self.db.get_session() as session:
            result = AgentResult(
                agent_id=agent_id,
                task_id=task_id,
                markdown_content=markdown_content,
                markdown_file_path=markdown_file_path,
                result_type=result_type,
                summary=summary,
                verification_status="unverified",
            )
            session.add(result)
            session.commit()
            session.refresh(result)
            session.expunge(result)

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="result.task.submitted",
                        entity_type="agent_result",
                        entity_id=result.id,
                        payload={
                            "agent_id": agent_id,
                            "task_id": task_id,
                            "result_type": result_type,
                        },
                    )
                )

            return result

    def verify_task_result(
        self,
        result_id: str,
        validation_review_id: str,
        verified: bool,
    ) -> Optional[AgentResult]:
        """Mark task result as verified or disputed.
        
        Args:
            result_id: ID of result to verify
            validation_review_id: ID of validation review that verified it
            verified: True if verified, False if disputed
            
        Returns:
            Updated AgentResult or None if not found
        """
        with self.db.get_session() as session:
            result = session.get(AgentResult, result_id)
            if not result:
                return None

            result.verification_status = "verified" if verified else "disputed"
            result.verified_at = utc_now()
            result.verified_by_validation_id = validation_review_id

            session.commit()
            session.refresh(result)
            session.expunge(result)

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type=f"result.task.{'verified' if verified else 'disputed'}",
                        entity_type="agent_result",
                        entity_id=result.id,
                        payload={
                            "task_id": result.task_id,
                            "verification_status": result.verification_status,
                        },
                    )
                )

            return result

    def get_task_results(self, task_id: str) -> List[AgentResult]:
        """Get all results for a task.
        
        Args:
            task_id: ID of task
            
        Returns:
            List of AgentResult records
        """
        with self.db.get_session() as session:
            results = (
                session.query(AgentResult)
                .filter(AgentResult.task_id == task_id)
                .order_by(AgentResult.created_at)
                .all()
            )

            for result in results:
                session.expunge(result)

            return results

    # -------------------------------------------------------------------------
    # Workflow-Level Results (WorkflowResult)
    # -------------------------------------------------------------------------

    def submit_workflow_result(
        self,
        workflow_id: str,
        agent_id: str,
        markdown_file_path: str,
        explanation: Optional[str] = None,
        evidence: Optional[List[str]] = None,
    ) -> WorkflowResult:
        """Submit workflow-level result.
        
        Args:
            workflow_id: ID of workflow (ticket_id)
            agent_id: ID of agent submitting result
            markdown_file_path: Path to result markdown file
            explanation: Optional explanation of what was accomplished
            evidence: Optional list of evidence items
            
        Returns:
            Created WorkflowResult record
            
        Raises:
            FileNotFoundError: If markdown file doesn't exist
            ValueError: If file validation fails
        """
        # Validate file (will raise if invalid)
        read_markdown_file(markdown_file_path)

        # Create result record
        with self.db.get_session() as session:
            result = WorkflowResult(
                workflow_id=workflow_id,
                agent_id=agent_id,
                markdown_file_path=markdown_file_path,
                explanation=explanation,
                evidence={"items": evidence} if evidence else None,
                status="pending_validation",
            )
            session.add(result)
            session.commit()
            session.refresh(result)
            session.expunge(result)

            # Publish event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="result.workflow.submitted",
                        entity_type="workflow_result",
                        entity_id=result.id,
                        payload={
                            "workflow_id": workflow_id,
                            "agent_id": agent_id,
                        },
                    )
                )

            return result

    def validate_workflow_result(
        self,
        result_id: str,
        passed: bool,
        feedback: str,
        evidence: List[dict],
        validator_agent_id: str,
    ) -> dict:
        """Validate workflow result (validator agents only).
        
        Args:
            result_id: ID of workflow result to validate
            passed: Whether validation passed
            feedback: Validation feedback
            evidence: List of evidence items checked
            validator_agent_id: ID of validator agent
            
        Returns:
            Dict with validation status and action taken
            
        Raises:
            ValueError: If result not found
        """
        with self.db.get_session() as session:
            result = session.get(WorkflowResult, result_id)
            if not result:
                raise ValueError(f"WorkflowResult {result_id} not found")

            # Update validation status
            result.status = "validated" if passed else "rejected"
            result.validated_at = utc_now()
            result.validation_feedback = feedback

            session.commit()
            session.refresh(result)

            workflow_id = result.workflow_id
            session.expunge(result)

            # Publish validation event
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="result.workflow.validated",
                        entity_type="workflow_result",
                        entity_id=result.id,
                        payload={
                            "workflow_id": workflow_id,
                            "passed": passed,
                            "validator_agent_id": validator_agent_id,
                        },
                    )
                )

            # Determine action to take
            action_taken = "none"
            
            if passed:
                # Load workflow config to check on_result_found
                try:
                    config = self._load_workflow_config(workflow_id)
                    on_result_found = config.get("on_result_found", "stop_all")
                    
                    if on_result_found == "stop_all":
                        # Trigger workflow termination
                        if self.event_bus:
                            self.event_bus.publish(
                                SystemEvent(
                                    event_type="workflow.termination.requested",
                                    entity_type="ticket",
                                    entity_id=workflow_id,
                                    payload={
                                        "result_id": result_id,
                                        "reason": "validated_result_found",
                                    },
                                )
                            )
                        action_taken = "workflow_terminated"
                    elif on_result_found == "do_nothing":
                        action_taken = "result_logged"
                except Exception:
                    # If config loading fails, default to logging only
                    action_taken = "result_logged"

            return {
                "result_id": result_id,
                "validation_status": result.status,
                "passed": passed,
                "action_taken": action_taken,
            }

    def list_workflow_results(self, workflow_id: str) -> List[WorkflowResult]:
        """Get all results for a workflow.
        
        Args:
            workflow_id: ID of workflow (ticket_id)
            
        Returns:
            List of WorkflowResult records
        """
        with self.db.get_session() as session:
            results = (
                session.query(WorkflowResult)
                .filter(WorkflowResult.workflow_id == workflow_id)
                .order_by(WorkflowResult.created_at)
                .all()
            )

            for result in results:
                session.expunge(result)

            return results

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _load_workflow_config(self, workflow_id: str) -> dict:
        """Load workflow configuration from YAML.
        
        Args:
            workflow_id: ID of workflow (ticket_id)
            
        Returns:
            Dict with has_result, result_criteria, on_result_found
        """
        # For now, try to load default software_development.yaml
        # In production, this would be per-workflow or per-ticket
        try:
            config = self.phase_loader.load_workflow_config("software_development.yaml")
            return {
                "has_result": config.has_result,
                "result_criteria": config.result_criteria,
                "on_result_found": config.on_result_found,
            }
        except Exception:
            # Fallback to safe defaults
            return {
                "has_result": False,
                "result_criteria": "",
                "on_result_found": "do_nothing",
            }

