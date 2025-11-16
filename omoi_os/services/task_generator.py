"""Task generator service for phase-specific task generation."""

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.task_templates import get_templates_for_phase


class TaskGeneratorService:
    """Generates phase-specific tasks from templates."""

    def __init__(self, db: DatabaseService, queue: TaskQueueService):
        """
        Initialize task generator service.

        Args:
            db: DatabaseService instance
            queue: TaskQueueService instance
        """
        self.db = db
        self.queue = queue

    def generate_phase_tasks(self, ticket_id: str, phase_id: str) -> list[Task]:
        """
        Generate all tasks for a phase based on templates.

        Args:
            ticket_id: Ticket ID
            phase_id: Phase to generate tasks for

        Returns:
            List of generated Task objects

        Raises:
            ValueError: If ticket not found
        """
        # Get ticket from database
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket not found: {ticket_id}")
            
            # Expunge ticket so it can be used outside the session
            session.expunge(ticket)

        # Get templates for phase
        templates = self.get_templates_for_phase(phase_id)
        
        # Generate tasks from templates
        tasks = []
        for template in templates:
            task = self.generate_task_from_template(ticket, template)
            tasks.append(task)

        return tasks

    def generate_task_from_template(
        self,
        ticket: Ticket,
        template: dict,
        dependencies: list[str] | None = None,
    ) -> Task:
        """
        Generate single task from template.

        Args:
            ticket: Ticket object
            template: Task template dict with keys:
                - task_type: Type of task
                - description_template: Template string with {ticket_title}, {ticket_priority} variables
                - priority: Task priority (CRITICAL, HIGH, MEDIUM, LOW)
            dependencies: Optional list of task IDs this depends on

        Returns:
            Created Task object
        """
        # Format description template with ticket variables
        description = template["description_template"].format(
            ticket_title=ticket.title,
            ticket_priority=ticket.priority,
        )

        # Prepare dependencies dict
        dependencies_dict = None
        if dependencies:
            dependencies_dict = {"depends_on": dependencies}

        # Create task using queue service
        task = self.queue.enqueue_task(
            ticket_id=ticket.id,
            phase_id=ticket.phase_id,
            task_type=template["task_type"],
            description=description,
            priority=template["priority"],
            dependencies=dependencies_dict,
        )

        return task

    def get_templates_for_phase(self, phase_id: str) -> list[dict]:
        """
        Get task templates for a phase.

        Args:
            phase_id: Phase identifier (e.g., "PHASE_REQUIREMENTS")

        Returns:
            List of task template dictionaries
        """
        return get_templates_for_phase(phase_id)
