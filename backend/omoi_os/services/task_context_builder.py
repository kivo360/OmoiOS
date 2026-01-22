"""Task Context Builder Service.

Builds comprehensive task context for sandbox execution, including:
- Task details
- Ticket context
- Spec requirements with acceptance criteria
- Design artifacts
- Related spec tasks

This context is injected at sandbox creation time so the worker
has everything it needs without making additional API calls.
"""

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from omoi_os.logging import get_logger
from omoi_os.models.spec import Spec, SpecAcceptanceCriterion, SpecRequirement, SpecTask
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService

logger = get_logger(__name__)


@dataclass
class AcceptanceCriterionContext:
    """Context for a single acceptance criterion."""

    id: str
    text: str
    completed: bool
    requirement_id: str

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "completed": self.completed,
            "requirement_id": self.requirement_id,
        }


@dataclass
class RequirementContext:
    """Context for a single requirement."""

    id: str
    title: str
    description: str
    type: str
    priority: str
    acceptance_criteria: list[AcceptanceCriterionContext] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "type": self.type,
            "priority": self.priority,
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
        }


@dataclass
class DesignContext:
    """Context for design artifacts."""

    architecture: Optional[str] = None
    data_model: Optional[str] = None
    interfaces: Optional[str] = None
    error_handling: Optional[str] = None
    security: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "architecture": self.architecture,
            "data_model": self.data_model,
            "interfaces": self.interfaces,
            "error_handling": self.error_handling,
            "security": self.security,
        }


@dataclass
class SpecTaskContext:
    """Context for a spec task (not the execution task)."""

    id: str
    title: str
    description: str
    phase: str
    priority: str
    status: str
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "phase": self.phase,
            "priority": self.priority,
            "status": self.status,
            "dependencies": self.dependencies,
        }


@dataclass
class FullTaskContext:
    """Complete context for task execution in sandbox."""

    # Task info
    task_id: str
    task_type: str
    task_description: str
    task_priority: str
    phase_id: str

    # Ticket info
    ticket_id: str
    ticket_title: str
    ticket_description: str
    ticket_priority: str
    ticket_context: dict = field(default_factory=dict)

    # Spec info (optional - only if task is spec-driven)
    spec_id: Optional[str] = None
    spec_title: Optional[str] = None
    spec_description: Optional[str] = None
    spec_phase: Optional[str] = None
    spec_task_id: Optional[str] = None

    # Requirements with acceptance criteria
    requirements: list[RequirementContext] = field(default_factory=list)

    # Design artifacts
    design: Optional[DesignContext] = None

    # Related spec tasks (for context)
    spec_tasks: list[SpecTaskContext] = field(default_factory=list)

    # Current spec task being executed
    current_spec_task: Optional[SpecTaskContext] = None

    # Revision feedback (if task previously failed validation)
    revision_feedback: Optional[str] = None
    revision_recommendations: Optional[list[str]] = None
    validation_iteration: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {
            "task": {
                "id": self.task_id,
                "type": self.task_type,
                "description": self.task_description,
                "priority": self.task_priority,
                "phase_id": self.phase_id,
            },
            "ticket": {
                "id": self.ticket_id,
                "title": self.ticket_title,
                "description": self.ticket_description,
                "priority": self.ticket_priority,
                "context": self.ticket_context,
            },
        }

        # Add spec context if available
        if self.spec_id:
            result["spec"] = {
                "id": self.spec_id,
                "title": self.spec_title,
                "description": self.spec_description,
                "phase": self.spec_phase,
                "spec_task_id": self.spec_task_id,
            }

            result["requirements"] = [r.to_dict() for r in self.requirements]

            if self.design:
                result["design"] = self.design.to_dict()

            result["spec_tasks"] = [t.to_dict() for t in self.spec_tasks]

            if self.current_spec_task:
                result["current_spec_task"] = self.current_spec_task.to_dict()

        # Add revision context if present
        if self.revision_feedback:
            result["revision"] = {
                "feedback": self.revision_feedback,
                "recommendations": self.revision_recommendations or [],
                "iteration": self.validation_iteration,
            }

        return result

    def to_markdown(self) -> str:
        """Convert to markdown format for inclusion in system prompt."""
        lines = []

        lines.append("# Task Context")
        lines.append("")

        # Task details
        lines.append("## Task")
        lines.append(f"- **ID**: {self.task_id}")
        lines.append(f"- **Type**: {self.task_type}")
        lines.append(f"- **Priority**: {self.task_priority}")
        lines.append(f"- **Phase**: {self.phase_id}")
        lines.append("")
        lines.append("### Description")
        lines.append(self.task_description or "No description provided")
        lines.append("")

        # Ticket details
        lines.append("## Ticket")
        lines.append(f"- **Title**: {self.ticket_title}")
        lines.append(f"- **Priority**: {self.ticket_priority}")
        lines.append("")
        if self.ticket_description:
            lines.append("### Ticket Description")
            lines.append(self.ticket_description)
            lines.append("")

        # Spec context (if spec-driven)
        if self.spec_id:
            lines.append("## Specification")
            lines.append(f"- **Spec ID**: {self.spec_id}")
            lines.append(f"- **Title**: {self.spec_title}")
            lines.append(f"- **Phase**: {self.spec_phase}")
            lines.append("")
            if self.spec_description:
                lines.append("### Spec Description")
                lines.append(self.spec_description)
                lines.append("")

            # Current spec task
            if self.current_spec_task:
                lines.append("## Current Spec Task")
                lines.append(f"- **ID**: {self.current_spec_task.id}")
                lines.append(f"- **Title**: {self.current_spec_task.title}")
                lines.append(f"- **Phase**: {self.current_spec_task.phase}")
                lines.append(f"- **Status**: {self.current_spec_task.status}")
                if self.current_spec_task.dependencies:
                    lines.append(f"- **Dependencies**: {', '.join(self.current_spec_task.dependencies)}")
                lines.append("")
                if self.current_spec_task.description:
                    lines.append("### Task Description")
                    lines.append(self.current_spec_task.description)
                    lines.append("")

            # Requirements with acceptance criteria
            if self.requirements:
                lines.append("## Requirements")
                lines.append("")
                for req in self.requirements:
                    lines.append(f"### {req.id}: {req.title}")
                    lines.append(f"- **Type**: {req.type}")
                    lines.append(f"- **Priority**: {req.priority}")
                    lines.append("")
                    lines.append(req.description)
                    lines.append("")

                    if req.acceptance_criteria:
                        lines.append("#### Acceptance Criteria")
                        for criterion in req.acceptance_criteria:
                            status = "✅" if criterion.completed else "⬜"
                            lines.append(f"- {status} **{criterion.id}**: {criterion.text}")
                        lines.append("")

            # Design artifacts
            if self.design:
                lines.append("## Design")
                if self.design.architecture:
                    lines.append("### Architecture")
                    lines.append(self.design.architecture)
                    lines.append("")
                if self.design.data_model:
                    lines.append("### Data Model")
                    lines.append(self.design.data_model)
                    lines.append("")
                if self.design.interfaces:
                    lines.append("### Interfaces")
                    lines.append(self.design.interfaces)
                    lines.append("")
                if self.design.error_handling:
                    lines.append("### Error Handling")
                    lines.append(self.design.error_handling)
                    lines.append("")
                if self.design.security:
                    lines.append("### Security")
                    lines.append(self.design.security)
                    lines.append("")

        # Revision feedback
        if self.revision_feedback:
            lines.append("## ⚠️ Revision Required")
            lines.append(f"**Iteration**: {self.validation_iteration}")
            lines.append("")
            lines.append("### Feedback")
            lines.append(self.revision_feedback)
            lines.append("")
            if self.revision_recommendations:
                lines.append("### Recommendations")
                for rec in self.revision_recommendations:
                    lines.append(f"- {rec}")
                lines.append("")

        return "\n".join(lines)


class TaskContextBuilder:
    """Builds comprehensive task context for sandbox execution."""

    def __init__(self, db: DatabaseService):
        """Initialize the builder.

        Args:
            db: Database service for data access
        """
        self.db = db

    async def build_context(self, task_id: str) -> FullTaskContext:
        """Build full context for a task.

        Args:
            task_id: ID of the task to build context for

        Returns:
            FullTaskContext with all available context
        """
        async with self.db.get_async_session() as session:
            # Get task with ticket
            result = await session.execute(
                select(Task)
                .filter(Task.id == task_id)
                .options(selectinload(Task.ticket))
            )
            task = result.scalar_one_or_none()

            if not task:
                raise ValueError(f"Task not found: {task_id}")

            ticket = task.ticket
            if not ticket:
                raise ValueError(f"Task has no associated ticket: {task_id}")

            # Build base context
            context = FullTaskContext(
                task_id=str(task.id),
                task_type=task.task_type or "implement_feature",
                task_description=task.description or "",
                task_priority=task.priority or "MEDIUM",
                phase_id=task.phase_id or "PHASE_IMPLEMENTATION",
                ticket_id=str(ticket.id),
                ticket_title=ticket.title or "",
                ticket_description=ticket.description or "",
                ticket_priority=ticket.priority or "MEDIUM",
                ticket_context=ticket.context or {},
            )

            # Check for revision feedback in task result
            if task.result:
                context.revision_feedback = task.result.get("revision_feedback")
                context.revision_recommendations = task.result.get("revision_recommendations")
                context.validation_iteration = task.result.get("validation_iteration")

                # Get spec context if this is a spec-driven task
                spec_id = task.result.get("spec_id")
                spec_task_id = task.result.get("spec_task_id")

                if spec_id:
                    await self._add_spec_context(session, context, spec_id, spec_task_id)

            return context

    async def _add_spec_context(
        self,
        session,
        context: FullTaskContext,
        spec_id: str,
        spec_task_id: Optional[str] = None,
    ) -> None:
        """Add spec-related context to the task context.

        Args:
            session: Database session
            context: Context to augment
            spec_id: ID of the spec
            spec_task_id: Optional ID of the specific spec task
        """
        # Get spec with requirements, criteria, and tasks
        result = await session.execute(
            select(Spec)
            .filter(Spec.id == spec_id)
            .options(
                selectinload(Spec.requirements).selectinload(SpecRequirement.criteria),
                selectinload(Spec.tasks),
            )
        )
        spec = result.scalar_one_or_none()

        if not spec:
            logger.warning("spec_not_found", spec_id=spec_id)
            return

        # Add basic spec info
        context.spec_id = spec.id
        context.spec_title = spec.title
        context.spec_description = spec.description
        context.spec_phase = spec.phase
        context.spec_task_id = spec_task_id

        # Add requirements with acceptance criteria
        for req in spec.requirements:
            req_context = RequirementContext(
                id=req.id,
                title=req.title or "",
                description=req.description or "",
                type=req.type or "functional",
                priority=req.priority or "medium",
            )

            for criterion in req.criteria:
                req_context.acceptance_criteria.append(
                    AcceptanceCriterionContext(
                        id=criterion.id,
                        text=criterion.text or "",
                        completed=criterion.completed or False,
                        requirement_id=req.id,
                    )
                )

            context.requirements.append(req_context)

        # Add design artifacts
        if spec.design:
            context.design = DesignContext(
                architecture=spec.design.get("architecture"),
                data_model=spec.design.get("data_model"),
                interfaces=spec.design.get("interfaces"),
                error_handling=spec.design.get("error_handling"),
                security=spec.design.get("security"),
            )

        # Add spec tasks
        for spec_task in spec.tasks:
            task_ctx = SpecTaskContext(
                id=spec_task.id,
                title=spec_task.title or "",
                description=spec_task.description or "",
                phase=spec_task.phase or "",
                priority=spec_task.priority or "medium",
                status=spec_task.status or "pending",
                dependencies=spec_task.dependencies or [],
            )
            context.spec_tasks.append(task_ctx)

            # Track current spec task
            if spec_task_id and spec_task.id == spec_task_id:
                context.current_spec_task = task_ctx

    def build_context_sync(self, task_id: str) -> FullTaskContext:
        """Build full context for a task (synchronous version).

        Args:
            task_id: ID of the task to build context for

        Returns:
            FullTaskContext with all available context
        """
        with self.db.get_session() as session:
            # Get task with ticket
            task = (
                session.query(Task)
                .filter(Task.id == task_id)
                .options(selectinload(Task.ticket))
                .one_or_none()
            )

            if not task:
                raise ValueError(f"Task not found: {task_id}")

            ticket = task.ticket
            if not ticket:
                raise ValueError(f"Task has no associated ticket: {task_id}")

            # Build base context
            context = FullTaskContext(
                task_id=str(task.id),
                task_type=task.task_type or "implement_feature",
                task_description=task.description or "",
                task_priority=task.priority or "MEDIUM",
                phase_id=task.phase_id or "PHASE_IMPLEMENTATION",
                ticket_id=str(ticket.id),
                ticket_title=ticket.title or "",
                ticket_description=ticket.description or "",
                ticket_priority=ticket.priority or "MEDIUM",
                ticket_context=ticket.context or {},
            )

            # Check for revision feedback in task result
            if task.result:
                context.revision_feedback = task.result.get("revision_feedback")
                context.revision_recommendations = task.result.get("revision_recommendations")
                context.validation_iteration = task.result.get("validation_iteration")

                # Get spec context if this is a spec-driven task
                spec_id = task.result.get("spec_id")
                spec_task_id = task.result.get("spec_task_id")

                if spec_id:
                    self._add_spec_context_sync(session, context, spec_id, spec_task_id)

            return context

    def _add_spec_context_sync(
        self,
        session,
        context: FullTaskContext,
        spec_id: str,
        spec_task_id: Optional[str] = None,
    ) -> None:
        """Add spec-related context to the task context (synchronous).

        Args:
            session: Database session
            context: Context to augment
            spec_id: ID of the spec
            spec_task_id: Optional ID of the specific spec task
        """
        spec = (
            session.query(Spec)
            .filter(Spec.id == spec_id)
            .options(
                selectinload(Spec.requirements).selectinload(SpecRequirement.criteria),
                selectinload(Spec.tasks),
            )
            .one_or_none()
        )

        if not spec:
            logger.warning("spec_not_found", spec_id=spec_id)
            return

        # Add basic spec info
        context.spec_id = spec.id
        context.spec_title = spec.title
        context.spec_description = spec.description
        context.spec_phase = spec.phase
        context.spec_task_id = spec_task_id

        # Add requirements with acceptance criteria
        for req in spec.requirements:
            req_context = RequirementContext(
                id=req.id,
                title=req.title or "",
                description=req.description or "",
                type=req.type or "functional",
                priority=req.priority or "medium",
            )

            for criterion in req.criteria:
                req_context.acceptance_criteria.append(
                    AcceptanceCriterionContext(
                        id=criterion.id,
                        text=criterion.text or "",
                        completed=criterion.completed or False,
                        requirement_id=req.id,
                    )
                )

            context.requirements.append(req_context)

        # Add design artifacts
        if spec.design:
            context.design = DesignContext(
                architecture=spec.design.get("architecture"),
                data_model=spec.design.get("data_model"),
                interfaces=spec.design.get("interfaces"),
                error_handling=spec.design.get("error_handling"),
                security=spec.design.get("security"),
            )

        # Add spec tasks
        for spec_task in spec.tasks:
            task_ctx = SpecTaskContext(
                id=spec_task.id,
                title=spec_task.title or "",
                description=spec_task.description or "",
                phase=spec_task.phase or "",
                priority=spec_task.priority or "medium",
                status=spec_task.status or "pending",
                dependencies=spec_task.dependencies or [],
            )
            context.spec_tasks.append(task_ctx)

            # Track current spec task
            if spec_task_id and spec_task.id == spec_task_id:
                context.current_spec_task = task_ctx


@lru_cache(maxsize=1)
def get_task_context_builder(db: Optional[DatabaseService] = None) -> TaskContextBuilder:
    """Get or create TaskContextBuilder instance.

    Args:
        db: Database service (required on first call)

    Returns:
        TaskContextBuilder instance
    """
    if db is None:
        from omoi_os.services.database import get_database_service
        db = get_database_service()

    return TaskContextBuilder(db=db)
