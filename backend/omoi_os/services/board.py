"""Board service for Kanban visualization and workflow management."""

from typing import List, Dict, Any, Optional, Union
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from omoi_os.models.board_column import BoardColumn
from omoi_os.models.ticket import Ticket
from omoi_os.services.event_bus import EventBusService, SystemEvent


class BoardService:
    """
    Service for Kanban board operations.

    Manages board columns, ticket movement, WIP limits, and visual
    workflow representation.
    """

    def __init__(self, event_bus: Optional[EventBusService] = None):
        """
        Initialize board service.

        Args:
            event_bus: Optional event bus for publishing board events.
        """
        self.event_bus = event_bus

    def get_board_view(
        self, session: Session, project_id: Optional[str] = None, user_id: Optional[Union[str, UUID]] = None
    ) -> Dict[str, Any]:
        """
        Get complete Kanban board view with all columns and tickets.

        Args:
            session: Database session.
            project_id: Optional project ID to filter tickets. If None, shows all tickets (cross-project board).
            user_id: Optional user ID to filter tickets. If provided, only shows tickets owned by this user.

        Returns:
            Dictionary with columns and tickets organized by column.
        """
        # Get all columns ordered by sequence
        columns = (
            session.execute(select(BoardColumn).order_by(BoardColumn.sequence_order))
            .scalars()
            .all()
        )

        # Build board view
        board = {"columns": [], "project_id": project_id}

        for column in columns:
            # Get tickets in this column (match phase_id to column's phase_mapping)
            tickets_in_column = []

            for phase_id in column.phase_mapping:
                query = select(Ticket).where(Ticket.phase_id == phase_id)
                # Filter by project if specified
                if project_id is not None:
                    query = query.where(Ticket.project_id == project_id)
                # Filter by user if specified (only show user's tickets)
                if user_id is not None:
                    query = query.where(Ticket.user_id == user_id)

                tickets = session.execute(query).scalars().all()
                tickets_in_column.extend(tickets)

            # Count active tasks per ticket
            column_data = {
                "id": column.id,
                "name": column.name,
                "description": column.description,
                "sequence_order": column.sequence_order,
                "wip_limit": column.wip_limit,
                "current_count": len(tickets_in_column),
                "wip_exceeded": (
                    column.wip_limit is not None
                    and len(tickets_in_column) > column.wip_limit
                ),
                "tickets": [
                    {
                        "id": t.id,
                        "title": t.title,
                        "phase_id": t.phase_id,
                        "priority": t.priority,
                        "status": t.status,
                        "approval_status": t.approval_status,
                        "context": t.context,  # Include context for spec_id tracking
                    }
                    for t in tickets_in_column
                ],
            }

            board["columns"].append(column_data)

        return board

    def move_ticket_to_column(
        self,
        session: Session,
        ticket_id: str,
        target_column_id: str,
        force: bool = False,
        project_id: Optional[str] = None,
    ) -> Ticket:
        """
        Move ticket to a different board column.

        This updates the ticket's phase_id to match the target column's first
        phase mapping.

        Args:
            session: Database session.
            ticket_id: Ticket to move.
            target_column_id: Target column ID.
            force: Skip WIP limit check if True.

        Returns:
            Updated ticket.

        Raises:
            ValueError: If column not found or WIP limit exceeded.
        """
        # Get ticket
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")

        # Get target column
        column = session.get(BoardColumn, target_column_id)
        if not column:
            raise ValueError(f"Column {target_column_id} not found")

        # Check WIP limit
        if not force:
            # Use ticket's project_id if not explicitly provided
            filter_project_id = project_id or ticket.project_id
            current_count = self._count_tickets_in_column(session, column, filter_project_id)
            if not column.can_accept_more_work(current_count):
                raise ValueError(
                    f"Column {target_column_id} WIP limit exceeded "
                    f"({current_count}/{column.wip_limit})"
                )

        # Get target phase (use first phase in mapping)
        if not column.phase_mapping:
            raise ValueError(f"Column {target_column_id} has no phase mapping")

        target_phase_id = column.phase_mapping[0]
        old_phase_id = ticket.phase_id

        # Update ticket phase
        ticket.phase_id = target_phase_id
        session.flush()

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="board.ticket_moved",
                    entity_type="ticket",
                    entity_id=str(ticket.id),
                    payload={
                        "from_phase": old_phase_id,
                        "to_phase": target_phase_id,
                        "from_column": self._find_column_for_phase(
                            session, old_phase_id
                        ),
                        "to_column": target_column_id,
                    },
                )
            )

        return ticket

    def check_wip_limits(
        self, session: Session, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Check WIP limits for all columns.

        Args:
            session: Database session.
            project_id: Optional project ID to filter tickets. If None, checks all projects.

        Returns:
            List of columns with WIP violations.
        """
        columns = session.execute(select(BoardColumn)).scalars().all()

        violations = []
        for column in columns:
            if column.wip_limit is not None:
                current_count = self._count_tickets_in_column(session, column, project_id)
                if current_count > column.wip_limit:
                    violations.append(
                        {
                            "column_id": column.id,
                            "column_name": column.name,
                            "wip_limit": column.wip_limit,
                            "current_count": current_count,
                            "excess": current_count - column.wip_limit,
                        }
                    )

        return violations

    def get_column_for_phase(
        self, session: Session, phase_id: str
    ) -> Optional[BoardColumn]:
        """
        Find which column a phase belongs to.

        Args:
            session: Database session.
            phase_id: Phase ID to look up.

        Returns:
            BoardColumn if found, None otherwise.
        """
        columns = session.execute(select(BoardColumn)).scalars().all()

        for column in columns:
            if column.includes_phase(phase_id):
                return column

        return None

    def auto_transition_ticket(
        self, session: Session, ticket_id: str
    ) -> Optional[Ticket]:
        """
        Automatically transition ticket to next column if configured.

        Args:
            session: Database session.
            ticket_id: Ticket to transition.

        Returns:
            Updated ticket if transitioned, None if no auto-transition.
        """
        ticket = session.get(Ticket, ticket_id)
        if not ticket:
            return None

        # Find current column
        current_column = self.get_column_for_phase(session, ticket.phase_id)
        if not current_column or not current_column.auto_transition_to:
            return None

        # Move to next column
        try:
            return self.move_ticket_to_column(
                session, ticket_id, current_column.auto_transition_to, force=False
            )
        except ValueError:
            # WIP limit exceeded or other error, don't auto-transition
            return None

    def get_column_stats(
        self, session: Session, project_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get statistics for all board columns.

        Args:
            session: Database session.
            project_id: Optional project ID to filter tickets. If None, shows all projects.

        Returns:
            List of column statistics.
        """
        columns = (
            session.execute(select(BoardColumn).order_by(BoardColumn.sequence_order))
            .scalars()
            .all()
        )

        stats = []
        for column in columns:
            ticket_count = self._count_tickets_in_column(session, column, project_id)

            stats.append(
                {
                    "column_id": column.id,
                    "name": column.name,
                    "ticket_count": ticket_count,
                    "wip_limit": column.wip_limit,
                    "utilization": (
                        ticket_count / column.wip_limit if column.wip_limit else None
                    ),
                    "wip_exceeded": (
                        column.wip_limit is not None and ticket_count > column.wip_limit
                    ),
                }
            )

        return stats

    def _count_tickets_in_column(
        self, session: Session, column: BoardColumn, project_id: Optional[str] = None
    ) -> int:
        """Count tickets in a column based on phase mapping."""
        total = 0
        for phase_id in column.phase_mapping:
            query = select(func.count(Ticket.id)).where(Ticket.phase_id == phase_id)
            # Filter by project if specified
            if project_id is not None:
                query = query.where(Ticket.project_id == project_id)
            count = session.execute(query).scalar()
            total += count or 0
        return total

    def _find_column_for_phase(self, session: Session, phase_id: str) -> Optional[str]:
        """Find column ID for a given phase."""
        column = self.get_column_for_phase(session, phase_id)
        return column.id if column else None

    def create_default_board(self, session: Session) -> List[BoardColumn]:
        """
        Create default Kanban board columns.

        Args:
            session: Database session.

        Returns:
            List of created columns.
        """
        default_columns = [
            {
                "id": "backlog",
                "name": "📋 Backlog",
                "description": "Tickets awaiting analysis",
                "sequence_order": 0,
                "phase_mapping": ["PHASE_BACKLOG"],
                "wip_limit": None,
                "is_terminal": False,
                "auto_transition_to": None,
                "color_theme": "gray",
            },
            {
                "id": "analyzing",
                "name": "🔍 Analyzing",
                "description": "Requirements analysis and design",
                "sequence_order": 1,
                "phase_mapping": ["PHASE_REQUIREMENTS", "PHASE_DESIGN"],
                "wip_limit": 5,
                "is_terminal": False,
                "auto_transition_to": None,
                "color_theme": "blue",
            },
            {
                "id": "building",
                "name": "🔨 Building",
                "description": "Active implementation work",
                "sequence_order": 2,
                "phase_mapping": ["PHASE_IMPLEMENTATION"],
                "wip_limit": 10,
                "is_terminal": False,
                "auto_transition_to": "testing",
                "color_theme": "yellow",
            },
            {
                "id": "testing",
                "name": "🧪 Testing",
                "description": "Validation and quality assurance",
                "sequence_order": 3,
                "phase_mapping": ["PHASE_TESTING"],
                "wip_limit": 8,
                "is_terminal": False,
                "auto_transition_to": None,
                "color_theme": "blue",
            },
            {
                "id": "deploying",
                "name": "🚀 Deploying",
                "description": "Ready for deployment",
                "sequence_order": 4,
                "phase_mapping": ["PHASE_DEPLOYMENT"],
                "wip_limit": 3,
                "is_terminal": False,
                "auto_transition_to": "done",
                "color_theme": "green",
            },
            {
                "id": "done",
                "name": "✅ Done",
                "description": "Completed tickets",
                "sequence_order": 5,
                "phase_mapping": ["PHASE_DONE"],
                "wip_limit": None,
                "is_terminal": True,
                "auto_transition_to": None,
                "color_theme": "green",
            },
            {
                "id": "blocked",
                "name": "🚫 Blocked",
                "description": "Blocked by dependencies",
                "sequence_order": 6,
                "phase_mapping": ["PHASE_BLOCKED"],
                "wip_limit": None,
                "is_terminal": True,
                "auto_transition_to": None,
                "color_theme": "red",
            },
        ]

        created_columns = []
        for col_data in default_columns:
            column = BoardColumn(**col_data)
            session.add(column)
            created_columns.append(column)

        session.flush()
        return created_columns
