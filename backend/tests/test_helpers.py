"""Helper functions for creating test data."""

from omoi_os.models.agent import Agent
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService


def create_test_ticket(
    db: DatabaseService,
    title: str = "Test Ticket",
    description: str | None = None,
    phase_id: str = "PHASE_REQUIREMENTS",
    status: str = "pending",
    priority: str = "MEDIUM",
    ticket_id: str | None = None,
) -> Ticket:
    """Create a test ticket."""
    with db.get_session() as session:
        ticket = Ticket(
            title=title,
            description=description,
            phase_id=phase_id,
            status=status,
            priority=priority,
        )
        if ticket_id:
            ticket.id = ticket_id
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        session.expunge(ticket)
        return ticket


def create_test_task(
    db: DatabaseService,
    ticket_id: str,
    phase_id: str = "PHASE_REQUIREMENTS",
    task_type: str = "test_task",
    description: str = "Test task description",
    priority: str = "MEDIUM",
    status: str = "pending",
) -> Task:
    """Create a test task."""
    with db.get_session() as session:
        task = Task(
            ticket_id=ticket_id,
            phase_id=phase_id,
            task_type=task_type,
            description=description,
            priority=priority,
            status=status,
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        session.expunge(task)
        return task


def create_test_agent(
    db: DatabaseService,
    agent_type: str = "worker",
    phase_id: str | None = "PHASE_REQUIREMENTS",
    status: str = "idle",
    capabilities: list[str] | None = None,
    capacity: int = 1,
    health_status: str = "healthy",
    tags: list[str] | None = None,
) -> Agent:
    """Create a test agent."""
    if capabilities is None:
        capabilities = ["bash", "file_editor"]

    with db.get_session() as session:
        agent = Agent(
            agent_type=agent_type,
            phase_id=phase_id,
            status=status,
            capabilities=capabilities,
            capacity=capacity,
            health_status=health_status,
            tags=tags,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)
        session.expunge(agent)
        return agent

