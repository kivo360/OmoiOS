"""Spec Sync Service - Syncs phase data to database with deduplication.

This service handles the SYNC phase of the spec-driven development workflow,
persisting generated requirements, tasks, and acceptance criteria to the database
with deduplication to prevent duplicates during retries.

Flow:
1. State machine generates phase data (exploration, requirements, design, tasks)
2. SYNC phase is triggered to persist this data
3. SpecSyncService reads phase_data from spec
4. Deduplicate each entity before insertion
5. Create database records for non-duplicate entities
6. Mark spec as ready for execution
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from omoi_os.logging import get_logger
from omoi_os.models.spec import (
    Spec,
    SpecAcceptanceCriterion,
    SpecRequirement,
    SpecTask,
)
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.embedding import EmbeddingService
from omoi_os.services.spec_dedup import (
    SpecDeduplicationService,
    compute_content_hash,
    get_spec_dedup_service,
)

logger = get_logger(__name__)


@dataclass
class SyncStats:
    """Statistics from a sync operation."""

    requirements_created: int = 0
    requirements_skipped: int = 0
    criteria_created: int = 0
    criteria_skipped: int = 0
    tasks_created: int = 0
    tasks_skipped: int = 0
    tickets_created: int = 0
    tickets_skipped: int = 0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "requirements_created": self.requirements_created,
            "requirements_skipped": self.requirements_skipped,
            "criteria_created": self.criteria_created,
            "criteria_skipped": self.criteria_skipped,
            "tasks_created": self.tasks_created,
            "tasks_skipped": self.tasks_skipped,
            "tickets_created": self.tickets_created,
            "tickets_skipped": self.tickets_skipped,
            "errors": self.errors,
        }


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    spec_id: str
    stats: SyncStats = field(default_factory=SyncStats)
    message: str = ""


class SpecSyncService:
    """Service for syncing phase data to database with deduplication.

    This service is the bridge between the state machine (which generates
    structured data from LLM responses) and the database (which stores
    the actual requirements, tasks, and criteria records).

    Key features:
    1. Bulk deduplication before insertion
    2. Hierarchical sync (requirements -> criteria)
    3. Idempotent operations (safe to retry)
    4. Detailed statistics for monitoring
    """

    def __init__(
        self,
        db: DatabaseService,
        embedding_service: Optional[EmbeddingService] = None,
    ):
        """Initialize the sync service.

        Args:
            db: Database service for queries.
            embedding_service: Optional embedding service for semantic deduplication.
        """
        self.db = db
        self.embedding_service = embedding_service
        self.dedup_service = get_spec_dedup_service(db, embedding_service)

    async def sync_spec(
        self,
        spec_id: str,
        session: Optional[AsyncSession] = None,
    ) -> SyncResult:
        """Sync all phase data for a spec to the database.

        This is the main entry point for the SYNC phase. It reads the
        phase_data from the spec and persists requirements, tasks, and
        criteria with deduplication.

        Args:
            spec_id: ID of the spec to sync.
            session: Optional async session.

        Returns:
            SyncResult with success status and statistics.
        """
        stats = SyncStats()

        async def _sync(sess: AsyncSession) -> SyncResult:
            # Load spec with phase data
            result = await sess.execute(
                select(Spec)
                .filter(Spec.id == spec_id)
                .options(
                    selectinload(Spec.requirements).selectinload(
                        SpecRequirement.criteria
                    ),
                    selectinload(Spec.tasks),
                )
            )
            spec = result.scalar_one_or_none()

            if not spec:
                return SyncResult(
                    success=False,
                    spec_id=spec_id,
                    message="Spec not found",
                )

            if not spec.phase_data:
                return SyncResult(
                    success=True,
                    spec_id=spec_id,
                    stats=stats,
                    message="No phase data to sync",
                )

            # Sync requirements from requirements phase
            requirements_data = spec.phase_data.get("requirements", {})
            if requirements_data:
                await self._sync_requirements(
                    sess, spec, requirements_data, stats
                )

            # Sync tasks from tasks phase
            tasks_data = spec.phase_data.get("tasks", {})
            if tasks_data:
                await self._sync_tasks(sess, spec, tasks_data, stats)

            # Update linked_tickets count on spec
            if stats.tickets_created > 0:
                spec.linked_tickets = (spec.linked_tickets or 0) + stats.tickets_created

            # Update spec embedding and hash for deduplication
            await self._update_spec_dedup_fields(sess, spec)

            # Commit all changes
            await sess.commit()

            logger.info(
                "Spec sync complete",
                extra={
                    "spec_id": spec_id,
                    "stats": stats.to_dict(),
                },
            )

            return SyncResult(
                success=True,
                spec_id=spec_id,
                stats=stats,
                message=f"Synced {stats.requirements_created} requirements, "
                f"{stats.tasks_created} tasks "
                f"(skipped {stats.requirements_skipped + stats.tasks_skipped} duplicates)",
            )

        if session:
            return await _sync(session)
        else:
            async with self.db.get_async_session() as sess:
                return await _sync(sess)

    async def _sync_requirements(
        self,
        session: AsyncSession,
        spec: Spec,
        requirements_data: dict,
        stats: SyncStats,
    ) -> None:
        """Sync requirements from phase data to database.

        Args:
            session: Async database session.
            spec: The spec being synced.
            requirements_data: Requirements phase output data.
            stats: Statistics tracker.
        """
        requirements = requirements_data.get("requirements", [])
        if not requirements:
            return

        logger.info(
            f"Syncing {len(requirements)} requirements for spec {spec.id}"
        )

        # Bulk deduplication
        dedup_result = await self.dedup_service.deduplicate_requirements_bulk(
            spec_id=spec.id,
            requirements=requirements,
            session=session,
        )

        # Create non-duplicate requirements
        for req_data in dedup_result.to_create:
            try:
                new_req = SpecRequirement(
                    spec_id=spec.id,
                    title=req_data.get("title", ""),
                    condition=req_data.get("condition", ""),
                    action=req_data.get("action", ""),
                    status="pending",
                    content_hash=req_data.get("content_hash"),
                    embedding_vector=req_data.get("embedding_vector"),
                )
                session.add(new_req)
                await session.flush()  # Get the ID

                stats.requirements_created += 1

                # Sync acceptance criteria for this requirement
                criteria = req_data.get("acceptance_criteria", [])
                if criteria:
                    await self._sync_criteria(
                        session, new_req.id, criteria, stats
                    )

            except Exception as e:
                logger.error(f"Failed to create requirement: {e}")
                stats.errors.append(f"Requirement creation failed: {e}")

        stats.requirements_skipped = len(dedup_result.to_skip)

    async def _sync_criteria(
        self,
        session: AsyncSession,
        requirement_id: str,
        criteria: List[dict],
        stats: SyncStats,
    ) -> None:
        """Sync acceptance criteria for a requirement.

        Args:
            session: Async database session.
            requirement_id: ID of the parent requirement.
            criteria: List of criterion data dictionaries.
            stats: Statistics tracker.
        """
        # Bulk deduplication for criteria
        dedup_result = await self.dedup_service.deduplicate_criteria_bulk(
            requirement_id=requirement_id,
            criteria=[{"text": c} if isinstance(c, str) else c for c in criteria],
            session=session,
        )

        for crit_data in dedup_result.to_create:
            try:
                text = crit_data.get("text", "")
                if isinstance(crit_data, str):
                    text = crit_data

                new_criterion = SpecAcceptanceCriterion(
                    requirement_id=requirement_id,
                    text=text,
                    completed=False,
                    content_hash=crit_data.get("content_hash") if isinstance(crit_data, dict) else compute_content_hash(text),
                )
                session.add(new_criterion)
                stats.criteria_created += 1

            except Exception as e:
                logger.error(f"Failed to create criterion: {e}")
                stats.errors.append(f"Criterion creation failed: {e}")

        stats.criteria_skipped += len(dedup_result.to_skip)

    async def _sync_tasks(
        self,
        session: AsyncSession,
        spec: Spec,
        tasks_data: dict,
        stats: SyncStats,
    ) -> None:
        """Sync tasks from phase data to database.

        The TASKS phase output has two arrays:
        - tickets: Logical groupings of work (what appears on the kanban board)
        - tasks: Discrete work units with parent_ticket references

        This method creates:
        1. Ticket records from the 'tickets' array (kanban board items)
        2. Task records from the 'tasks' array (work units linked to tickets)
        3. SpecTask records for spec tracking (linked to tasks)

        Falls back to 1:1 mapping if only 'tasks' array is present (legacy format).

        Args:
            session: Async database session.
            spec: The spec being synced.
            tasks_data: Tasks phase output data with 'tickets' and 'tasks' arrays.
            stats: Statistics tracker.
        """
        tickets = tasks_data.get("tickets", [])
        tasks = tasks_data.get("tasks", [])

        # Map priority values
        priority_map = {
            "critical": "CRITICAL",
            "high": "HIGH",
            "medium": "MEDIUM",
            "low": "LOW",
        }

        # Track local ticket IDs to database IDs for linking tasks
        ticket_id_map: Dict[str, str] = {}  # local_id -> db_id

        # Phase 1: Create Tickets (logical work groupings for kanban board)
        if tickets:
            logger.info(f"Syncing {len(tickets)} tickets for spec {spec.id}")

            for ticket_data in tickets:
                try:
                    local_id = ticket_data.get("id", "")
                    title = ticket_data.get("title", "")
                    description = ticket_data.get("description", "")
                    priority = ticket_data.get("priority", "MEDIUM").upper()
                    requirements_refs = ticket_data.get("requirements", [])
                    task_refs = ticket_data.get("tasks", [])
                    dependencies = ticket_data.get("dependencies", [])

                    # Check for duplicate ticket
                    existing_ticket = await session.execute(
                        select(Ticket).where(
                            Ticket.title == title,
                            Ticket.project_id == spec.project_id,
                            Ticket.context["spec_id"].astext == spec.id,
                        )
                    )
                    if existing_ticket.scalar_one_or_none():
                        stats.tickets_skipped += 1
                        continue

                    new_ticket = Ticket(
                        title=title,
                        description=description,
                        phase_id="backlog",
                        status="backlog",
                        priority=priority if priority in priority_map.values() else "MEDIUM",
                        project_id=spec.project_id,
                        dependencies={
                            "blocked_by": dependencies,
                            "requirements": requirements_refs,
                            "task_refs": task_refs,
                        } if dependencies or requirements_refs else None,
                        context={
                            "spec_id": spec.id,
                            "local_ticket_id": local_id,
                            "source": "spec_sync",
                            "workflow_mode": "spec_driven",
                        },
                    )
                    session.add(new_ticket)
                    await session.flush()
                    stats.tickets_created += 1
                    ticket_id_map[local_id] = new_ticket.id

                    logger.debug(
                        f"Created ticket: {title}",
                        extra={"spec_id": spec.id, "ticket_id": new_ticket.id},
                    )

                except Exception as e:
                    logger.error(f"Failed to create ticket: {e}")
                    stats.errors.append(f"Ticket creation failed: {e}")

        # Phase 2: Create Tasks (discrete work units linked to tickets)
        if tasks:
            logger.info(f"Syncing {len(tasks)} tasks for spec {spec.id}")

            # Bulk deduplication for SpecTasks
            dedup_result = await self.dedup_service.deduplicate_tasks_bulk(
                spec_id=spec.id,
                tasks=tasks,
                session=session,
            )

            for task_data in dedup_result.to_create:
                try:
                    title = task_data.get("title", "")
                    description = task_data.get("description", "")
                    parent_ticket_local_id = task_data.get("parent_ticket", "")
                    task_type = task_data.get("type", "implementation")
                    priority = task_data.get("priority", "medium").lower()
                    dependencies = task_data.get("dependencies", {})
                    estimated_hours = task_data.get("estimated_hours")

                    # Create SpecTask for spec tracking
                    new_spec_task = SpecTask(
                        spec_id=spec.id,
                        title=title,
                        description=description,
                        phase=task_data.get("phase", "Implementation"),
                        priority=priority,
                        status="pending",
                        dependencies=dependencies.get("depends_on", []) if isinstance(dependencies, dict) else [],
                        estimated_hours=estimated_hours,
                        content_hash=task_data.get("content_hash"),
                        embedding_vector=task_data.get("embedding_vector"),
                    )
                    session.add(new_spec_task)
                    await session.flush()
                    stats.tasks_created += 1

                    # Find or create parent ticket for this task
                    parent_ticket_id = ticket_id_map.get(parent_ticket_local_id)

                    if not parent_ticket_id and not tickets:
                        # Legacy format: No tickets array, create ticket per task
                        ticket_priority = priority_map.get(priority, "MEDIUM")
                        new_ticket = Ticket(
                            title=title,
                            description=description,
                            phase_id="backlog",
                            status="backlog",
                            priority=ticket_priority,
                            project_id=spec.project_id,
                            context={
                                "spec_id": spec.id,
                                "spec_task_id": new_spec_task.id,
                                "source": "spec_sync",
                                "workflow_mode": "spec_driven",
                            },
                        )
                        session.add(new_ticket)
                        await session.flush()
                        stats.tickets_created += 1
                        parent_ticket_id = new_ticket.id

                    if parent_ticket_id:
                        # Create Task (work unit) linked to the Ticket
                        new_task = Task(
                            ticket_id=parent_ticket_id,
                            phase_id="backlog",
                            task_type=task_type,
                            title=title,
                            description=description,
                            priority=priority_map.get(priority, "MEDIUM"),
                            status="pending",
                            dependencies=dependencies if isinstance(dependencies, dict) else {"depends_on": []},
                        )
                        session.add(new_task)

                        logger.debug(
                            f"Created task under ticket: {title}",
                            extra={
                                "spec_id": spec.id,
                                "spec_task_id": new_spec_task.id,
                                "ticket_id": parent_ticket_id,
                            },
                        )

                except Exception as e:
                    logger.error(f"Failed to create task: {e}")
                    stats.errors.append(f"Task creation failed: {e}")

            stats.tasks_skipped = len(dedup_result.to_skip)

    async def _update_spec_dedup_fields(
        self,
        session: AsyncSession,
        spec: Spec,
    ) -> None:
        """Update spec's content hash and embedding for deduplication.

        Args:
            session: Async database session.
            spec: The spec to update.
        """
        content = f"{spec.title}\n{spec.description or ''}"
        spec.content_hash = compute_content_hash(content)

        # Generate embedding if service is available
        if self.embedding_service:
            try:
                embedding = self.embedding_service.generate_embedding(content)
                if embedding:
                    spec.embedding_vector = embedding
            except Exception as e:
                logger.warning(f"Failed to generate spec embedding: {e}")

    async def sync_requirements_only(
        self,
        spec_id: str,
        requirements: List[dict],
        session: Optional[AsyncSession] = None,
    ) -> SyncStats:
        """Sync only requirements (useful for incremental updates).

        Args:
            spec_id: ID of the spec.
            requirements: List of requirement data dictionaries.
            session: Optional async session.

        Returns:
            SyncStats with creation/skip counts.
        """
        stats = SyncStats()

        async def _sync(sess: AsyncSession) -> SyncStats:
            # Verify spec exists
            result = await sess.execute(
                select(Spec).filter(Spec.id == spec_id)
            )
            spec = result.scalar_one_or_none()
            if not spec:
                stats.errors.append("Spec not found")
                return stats

            # Bulk deduplication
            dedup_result = await self.dedup_service.deduplicate_requirements_bulk(
                spec_id=spec_id,
                requirements=requirements,
                session=sess,
            )

            # Create non-duplicate requirements
            for req_data in dedup_result.to_create:
                try:
                    new_req = SpecRequirement(
                        spec_id=spec_id,
                        title=req_data.get("title", ""),
                        condition=req_data.get("condition", ""),
                        action=req_data.get("action", ""),
                        status="pending",
                        content_hash=req_data.get("content_hash"),
                        embedding_vector=req_data.get("embedding_vector"),
                    )
                    sess.add(new_req)
                    await sess.flush()

                    stats.requirements_created += 1

                    # Sync criteria
                    criteria = req_data.get("acceptance_criteria", [])
                    if criteria:
                        await self._sync_criteria(
                            sess, new_req.id, criteria, stats
                        )

                except Exception as e:
                    stats.errors.append(f"Requirement creation failed: {e}")

            stats.requirements_skipped = len(dedup_result.to_skip)
            await sess.commit()
            return stats

        if session:
            return await _sync(session)
        else:
            async with self.db.get_async_session() as sess:
                return await _sync(sess)

    async def sync_tasks_only(
        self,
        spec_id: str,
        tasks: List[dict],
        session: Optional[AsyncSession] = None,
    ) -> SyncStats:
        """Sync only tasks (useful for incremental updates).

        Args:
            spec_id: ID of the spec.
            tasks: List of task data dictionaries.
            session: Optional async session.

        Returns:
            SyncStats with creation/skip counts.
        """
        stats = SyncStats()

        async def _sync(sess: AsyncSession) -> SyncStats:
            # Verify spec exists
            result = await sess.execute(
                select(Spec).filter(Spec.id == spec_id)
            )
            spec = result.scalar_one_or_none()
            if not spec:
                stats.errors.append("Spec not found")
                return stats

            # Bulk deduplication
            dedup_result = await self.dedup_service.deduplicate_tasks_bulk(
                spec_id=spec_id,
                tasks=tasks,
                session=sess,
            )

            # Create non-duplicate tasks
            for task_data in dedup_result.to_create:
                try:
                    new_task = SpecTask(
                        spec_id=spec_id,
                        title=task_data.get("title", ""),
                        description=task_data.get("description"),
                        phase=task_data.get("phase", "Implementation"),
                        priority=task_data.get("priority", "medium"),
                        status="pending",
                        dependencies=task_data.get("dependencies", []),
                        estimated_hours=task_data.get("estimated_hours"),
                        content_hash=task_data.get("content_hash"),
                        embedding_vector=task_data.get("embedding_vector"),
                    )
                    sess.add(new_task)
                    stats.tasks_created += 1

                except Exception as e:
                    stats.errors.append(f"Task creation failed: {e}")

            stats.tasks_skipped = len(dedup_result.to_skip)
            await sess.commit()
            return stats

        if session:
            return await _sync(session)
        else:
            async with self.db.get_async_session() as sess:
                return await _sync(sess)


# =============================================================================
# Factory Function
# =============================================================================


def get_spec_sync_service(
    db: DatabaseService,
    embedding_service: Optional[EmbeddingService] = None,
) -> SpecSyncService:
    """Factory function to create a SpecSyncService instance.

    Args:
        db: Database service.
        embedding_service: Optional embedding service for semantic deduplication.

    Returns:
        Configured SpecSyncService instance.
    """
    return SpecSyncService(db=db, embedding_service=embedding_service)
