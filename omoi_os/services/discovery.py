"""Discovery service for tracking adaptive workflow branching."""

from typing import Optional, Dict, Any, List

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.task import Task
from omoi_os.models.task_discovery import DiscoveryType, TaskDiscovery
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now


class DiscoveryService:
    """
    Service for recording agent discoveries and spawning branch tasks.

    Implements the Hephaestus pattern: track WHY workflows branch and WHAT
    agents discovered that led to new work being created.
    """

    def __init__(self, event_bus: Optional[EventBusService] = None):
        """
        Initialize discovery service.

        Args:
            event_bus: Optional event bus for publishing discovery events.
        """
        self.event_bus = event_bus

    def record_discovery(
        self,
        session: Session,
        source_task_id: str,
        discovery_type: str,
        description: str,
        priority_boost: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TaskDiscovery:
        """
        Record a discovery made by an agent during task execution.

        Args:
            session: Database session.
            source_task_id: Task that made the discovery.
            discovery_type: Type of discovery (use DiscoveryType constants).
            description: What was discovered.
            priority_boost: Whether this discovery should escalate priority.
            metadata: Additional context about the discovery.

        Returns:
            Created TaskDiscovery record.
        """
        # Verify source task exists
        task = session.get(Task, source_task_id)
        if not task:
            raise ValueError(f"Source task {source_task_id} not found")

        # Create discovery record
        discovery = TaskDiscovery(
            source_task_id=source_task_id,
            discovery_type=discovery_type,
            description=description,
            spawned_task_ids=[],
            discovered_at=utc_now(),
            priority_boost=priority_boost,
            resolution_status="open",
            metadata=metadata,
        )

        session.add(discovery)
        session.flush()

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="discovery.recorded",
                    entity_type="task_discovery",
                    entity_id=str(discovery.id),
                    payload={
                        "source_task_id": source_task_id,
                        "discovery_type": discovery_type,
                        "priority_boost": priority_boost,
                    },
                )
            )

        return discovery

    def record_discovery_and_branch(
        self,
        session: Session,
        source_task_id: str,
        discovery_type: str,
        description: str,
        spawn_phase_id: str,
        spawn_description: str,
        spawn_priority: Optional[str] = None,
        priority_boost: bool = False,
        spawn_metadata: Optional[Dict[str, Any]] = None,
    ) -> tuple[TaskDiscovery, Task]:
        """
        Record discovery and immediately spawn a branch task.

        This implements the Hephaestus pattern: discovery → automatic branching.
        
        **IMPORTANT**: This method bypasses PhaseModel.allowed_transitions restrictions
        for discovery-based spawning, enabling Hephaestus-style free-form branching.
        Normal phase transitions still enforce allowed_transitions, but discoveries can
        spawn tasks in ANY phase (e.g., Phase 3 validation agent can spawn Phase 1
        investigation tasks).

        Args:
            session: Database session.
            source_task_id: Task that made the discovery.
            discovery_type: Type of discovery.
            description: Discovery description.
            spawn_phase_id: Phase ID for the spawned task (can be ANY phase - bypasses allowed_transitions).
            spawn_description: Description for the spawned task.
            spawn_priority: Priority for spawned task (defaults to source task priority).
            priority_boost: Whether to boost priority.
            spawn_metadata: Metadata for spawned task.

        Returns:
            Tuple of (discovery_record, spawned_task).
        """
        # Get source task
        source_task = session.get(Task, source_task_id)
        if not source_task:
            raise ValueError(f"Source task {source_task_id} not found")

        # Record discovery
        discovery = self.record_discovery(
            session=session,
            source_task_id=source_task_id,
            discovery_type=discovery_type,
            description=description,
            priority_boost=priority_boost,
            metadata=spawn_metadata,
        )

        # Determine priority for spawned task
        if spawn_priority is None:
            spawn_priority = source_task.priority
            if priority_boost and spawn_priority != "CRITICAL":
                # Boost priority one level
                priority_map = {"LOW": "MEDIUM", "MEDIUM": "HIGH", "HIGH": "CRITICAL"}
                spawn_priority = priority_map.get(spawn_priority, "HIGH")

        # Create spawned task
        spawned_task = Task(
            ticket_id=source_task.ticket_id,
            phase_id=spawn_phase_id,
            task_type=f"discovery_{discovery_type}",
            description=spawn_description,
            priority=spawn_priority,
            status="pending",
            result={"triggered_by_discovery": discovery.id},
        )

        session.add(spawned_task)
        session.flush()

        # Link spawned task to discovery
        discovery.add_spawned_task(spawned_task.id)

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="discovery.branch_created",
                    entity_type="task_discovery",
                    entity_id=str(discovery.id),
                    payload={
                        "discovery_type": discovery_type,
                        "spawned_task_id": spawned_task.id,
                        "spawn_phase": spawn_phase_id,
                        "priority_boost": priority_boost,
                    },
                )
            )

        return discovery, spawned_task

    def get_discoveries_by_task(
        self,
        session: Session,
        task_id: str,
        resolution_status: Optional[str] = None,
    ) -> List[TaskDiscovery]:
        """
        Get all discoveries made by a specific task.

        Args:
            session: Database session.
            task_id: Source task ID.
            resolution_status: Optional filter by status.

        Returns:
            List of discoveries.
        """
        query = select(TaskDiscovery).where(TaskDiscovery.source_task_id == task_id)

        if resolution_status:
            query = query.where(TaskDiscovery.resolution_status == resolution_status)

        return list(session.execute(query).scalars().all())

    def get_discoveries_by_type(
        self,
        session: Session,
        discovery_type: str,
        limit: int = 50,
    ) -> List[TaskDiscovery]:
        """
        Get discoveries by type (useful for pattern analysis).

        Args:
            session: Database session.
            discovery_type: Type to filter by.
            limit: Maximum results.

        Returns:
            List of discoveries of the specified type.
        """
        query = (
            select(TaskDiscovery)
            .where(TaskDiscovery.discovery_type == discovery_type)
            .order_by(TaskDiscovery.discovered_at.desc())
            .limit(limit)
        )

        return list(session.execute(query).scalars().all())

    def get_workflow_graph(self, session: Session, ticket_id: str) -> Dict[str, Any]:
        """
        Build a workflow graph showing all discoveries and branches for a ticket.

        Args:
            session: Database session.
            ticket_id: Ticket ID to analyze.

        Returns:
            Dictionary representing the branching structure.
        """
        # Get all tasks for ticket
        tasks = (
            session.execute(select(Task).where(Task.ticket_id == ticket_id))
            .scalars()
            .all()
        )

        # Build graph structure
        graph = {"nodes": [], "edges": []}

        for task in tasks:
            # Add task node
            graph["nodes"].append(
                {
                    "id": task.id,
                    "phase": task.phase_id,
                    "description": task.description,
                    "status": task.status,
                }
            )

            # Get discoveries for this task
            discoveries = self.get_discoveries_by_task(session, task.id)

            for discovery in discoveries:
                # Add discovery edges
                for spawned_id in discovery.spawned_task_ids:
                    graph["edges"].append(
                        {
                            "from": task.id,
                            "to": spawned_id,
                            "discovery_type": discovery.discovery_type,
                            "description": discovery.description,
                        }
                    )

        return graph

    def mark_discovery_resolved(
        self, session: Session, discovery_id: str
    ) -> TaskDiscovery:
        """
        Mark a discovery as resolved.

        Args:
            session: Database session.
            discovery_id: Discovery to resolve.

        Returns:
            Updated discovery record.
        """
        discovery = session.get(TaskDiscovery, discovery_id)
        if not discovery:
            raise ValueError(f"Discovery {discovery_id} not found")

        discovery.mark_resolved()
        session.flush()

        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="discovery.resolved",
                    entity_type="task_discovery",
                    entity_id=str(discovery.id),
                    payload={
                        "discovery_type": discovery.discovery_type,
                        "spawned_count": len(discovery.spawned_task_ids),
                    },
                )
            )

        return discovery

    def spawn_diagnostic_recovery(
        self,
        session: Session,
        ticket_id: str,
        diagnostic_run_id: str,
        reason: str,
        suggested_phase: str = "PHASE_FINAL",
        suggested_priority: str = "HIGH",
        max_tasks: int = 5,
    ) -> List[Task]:
        """Spawn diagnostic recovery tasks using Discovery pattern.
        
        Creates a diagnostic discovery and spawns recovery tasks to help
        stuck workflows progress toward their goal.
        
        Args:
            session: Database session.
            ticket_id: Workflow (ticket) that is stuck.
            diagnostic_run_id: ID of the diagnostic run triggering this.
            reason: Why the diagnostic was triggered.
            suggested_phase: Phase for recovery task(s).
            suggested_priority: Priority for recovery task(s).
            max_tasks: Maximum number of recovery tasks to spawn.
            
        Returns:
            List of spawned recovery Tasks.
        """
        # Find last completed task to use as source
        last_task = (
            session.query(Task)
            .filter(Task.ticket_id == ticket_id)
            .order_by(Task.completed_at.desc().nullsfirst())
            .first()
        )

        if not last_task:
            raise ValueError(f"No tasks found for ticket {ticket_id}")

        spawned_tasks = []
        
        # Spawn single recovery task (can be extended to spawn multiple based on analysis)
        discovery, spawned_task = self.record_discovery_and_branch(
            session=session,
            source_task_id=last_task.id,
            discovery_type=DiscoveryType.DIAGNOSTIC_NO_RESULT,
            description=f"Diagnostic: {reason}",
            spawn_phase_id=suggested_phase,
            spawn_description=f"Diagnostic recovery: {reason}",
            spawn_priority=suggested_priority,
            priority_boost=True,
            spawn_metadata={"diagnostic_run_id": diagnostic_run_id},
        )
        
        spawned_tasks.append(spawned_task)
        
        # Limit to max_tasks
        if len(spawned_tasks) > max_tasks:
            spawned_tasks = spawned_tasks[:max_tasks]

        return spawned_tasks
