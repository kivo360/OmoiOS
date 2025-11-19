"""ACE workflow engine orchestrator (REQ-MEM-ACE-004)."""

from typing import Optional, Dict, Any
from dataclasses import dataclass

from sqlalchemy.orm import Session

from omoi_os.services.database import DatabaseService
from omoi_os.services.ace_executor import Executor, ExecutorResult
from omoi_os.services.ace_reflector import Reflector, ReflectorResult
from omoi_os.services.ace_curator import Curator, CuratorResult
from omoi_os.services.memory import MemoryService
from omoi_os.services.embedding import EmbeddingService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.models.task import Task


@dataclass
class ACEResult:
    """Complete ACE workflow result (REQ-MEM-ACE-004)."""
    
    # Executor phase
    memory_id: str
    memory_type: str
    files_linked: list[str]
    
    # Reflector phase
    tags_added: list[str]
    insights_found: list[Dict[str, Any]]  # Serialized Insight objects
    errors_identified: list[Dict[str, Any]]  # Serialized Error objects
    related_playbook_entries: list[str]  # Entry IDs
    
    # Curator phase
    playbook_delta: Dict[str, Any]  # Serialized PlaybookDelta
    updated_bullets: list[Dict[str, Any]]  # Serialized PlaybookBullet objects
    change_id: Optional[str]


class ACEEngine:
    """
    ACE workflow engine orchestrator (REQ-MEM-ACE-004).
    
    Responsibilities:
    - Orchestrate three-phase workflow (Executor → Reflector → Curator)
    - Coordinate service calls and handle failures
    - Track workflow metrics
    - Return structured ACEResult
    """
    
    def __init__(
        self,
        db: DatabaseService,
        memory_service: MemoryService,
        embedding_service: EmbeddingService,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize ACE workflow engine.
        
        Args:
            db: Database service
            memory_service: Memory service
            embedding_service: Embedding service
            event_bus: Optional event bus for publishing events
        """
        self.db = db
        self.executor = Executor(memory_service, embedding_service)
        self.reflector = Reflector(embedding_service)
        self.curator = Curator(embedding_service)
        self.event_bus = event_bus
    
    def execute_workflow(
        self,
        task_id: str,
        goal: str,
        result: str,
        tool_usage: list[Dict[str, Any]],
        feedback: str,
        agent_id: str,
    ) -> ACEResult:
        """
        Execute complete ACE workflow (REQ-MEM-ACE-004).
        
        Runs Executor → Reflector → Curator in sequence.
        
        Args:
            task_id: Task ID
            goal: What the agent was trying to accomplish
            result: What actually happened
            tool_usage: List of tool usage records
            feedback: Output from environment (stdout, stderr, test results)
            agent_id: Agent ID that completed the task
            
        Returns:
            ACEResult with memory_id, tags, insights, playbook_delta
        """
        with self.db.get_session() as session:
            # Get task to find ticket_id
            task = session.get(Task, task_id)
            if not task:
                raise ValueError(f"Task {task_id} not found")
            
            ticket_id = task.ticket_id
            
            # Phase 1: Executor (REQ-MEM-ACE-001)
            executor_result = self.executor.execute(
                session=session,
                task_id=task_id,
                goal=goal,
                result=result,
                tool_usage=tool_usage,
                feedback=feedback,
            )
            session.flush()
            
            # Phase 2: Reflector (REQ-MEM-ACE-002)
            reflector_result = self.reflector.analyze(
                session=session,
                executor_result=executor_result,
                memory_id=executor_result.memory_id,
                feedback=feedback,
                ticket_id=ticket_id,
                goal=goal,
                result=result,
            )
            session.flush()
            
            # Phase 3: Curator (REQ-MEM-ACE-003)
            curator_result = self.curator.curate(
                session=session,
                executor_result=executor_result,
                reflector_result=reflector_result,
                ticket_id=ticket_id,
                memory_id=executor_result.memory_id,
                agent_id=agent_id,
            )
            session.commit()
            
            # Publish event (REQ-MEM-ACE-004)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="ace.workflow.completed",
                        entity_type="task_memory",
                        entity_id=executor_result.memory_id,
                        payload={
                            "task_id": task_id,
                            "ticket_id": ticket_id,
                            "memory_id": executor_result.memory_id,
                            "memory_type": executor_result.memory_type,
                            "files_linked": executor_result.files_linked,
                            "insights_count": len(reflector_result.insights_found),
                            "errors_count": len(reflector_result.errors_identified),
                            "playbook_updates": len(curator_result.updated_bullets),
                            "change_id": curator_result.change_id,
                        },
                    )
                )
            
            # Build result
            return ACEResult(
                memory_id=executor_result.memory_id,
                memory_type=executor_result.memory_type,
                files_linked=executor_result.files_linked,
                tags_added=reflector_result.tags_added,
                insights_found=[
                    {
                        "insight_type": i.insight_type,
                        "content": i.content,
                        "confidence": i.confidence,
                    }
                    for i in reflector_result.insights_found
                ],
                errors_identified=[
                    {
                        "error_type": e.error_type,
                        "message": e.message,
                        "context": e.context,
                    }
                    for e in reflector_result.errors_identified
                ],
                related_playbook_entries=reflector_result.related_playbook_entries,
                playbook_delta={
                    "operations": [
                        {
                            "operation": op.operation,
                            "content": op.content,
                            "category": op.category,
                            "tags": op.tags,
                        }
                        for op in curator_result.playbook_delta.operations
                    ],
                    "summary": curator_result.playbook_delta.summary,
                },
                updated_bullets=[
                    {
                        "id": b.id,
                        "content": b.content,
                        "category": b.category,
                        "tags": b.tags,
                        "supporting_memory_ids": b.supporting_memory_ids,
                    }
                    for b in curator_result.updated_bullets
                ],
                change_id=curator_result.change_id,
            )

