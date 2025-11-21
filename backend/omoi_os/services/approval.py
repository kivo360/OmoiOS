"""Ticket approval service for human-in-the-loop approval gate (REQ-THA-*)."""

from datetime import timedelta
from typing import Optional

from omoi_os.config import ApprovalSettings
from omoi_os.models.approval_status import ApprovalStatus
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.utils.datetime import utc_now


class InvalidApprovalStateError(Exception):
    """Raised when approval state transition is invalid."""

    pass


class ApprovalService:
    """Core service for ticket approval workflow management (REQ-THA-*)."""

    def __init__(
        self,
        db: DatabaseService,
        event_bus: Optional[EventBusService] = None,
        config: Optional[ApprovalSettings] = None,
    ):
        """
        Initialize approval service.

        Args:
            db: Database service
            event_bus: Event bus service for publishing events
            config: Approval configuration settings
        """
        self.db = db
        self.event_bus = event_bus
        self.config = config if config else ApprovalSettings()

    def create_ticket_with_approval(
        self,
        ticket: Ticket,
        requested_by_agent_id: Optional[str] = None,
    ) -> Ticket:
        """
        Create ticket with approval gate if enabled (REQ-THA-002).

        Args:
            ticket: Ticket to create (must be attached to a session)
            requested_by_agent_id: Agent ID that requested this ticket

        Returns:
            Created ticket with approval status set
        """
        if self.config.ticket_human_review:
            # Set approval status to pending (REQ-THA-002)
            ticket.approval_status = ApprovalStatus.PENDING_REVIEW.value
            ticket.approval_deadline_at = utc_now() + timedelta(
                seconds=self.config.approval_timeout_seconds
            )
            ticket.requested_by_agent_id = requested_by_agent_id

            # Note: ticket should already be added to session by caller
            # We just update its fields; caller will flush/commit
            # Event will be emitted after flush when ticket.id is available

        else:
            # Skip approval gate (REQ-THA-002)
            ticket.approval_status = ApprovalStatus.APPROVED.value
            ticket.requested_by_agent_id = requested_by_agent_id

            # Note: ticket should already be added to session by caller

        return ticket

    def _emit_pending_event(self, ticket: Ticket) -> None:
        """Emit TICKET_APPROVAL_PENDING event after ticket is flushed (REQ-THA-010)."""
        if self.event_bus and ticket.id:
            self.event_bus.publish(
                SystemEvent(
                    event_type="TICKET_APPROVAL_PENDING",
                    entity_type="ticket",
                    entity_id=str(ticket.id),
                    payload={
                        "ticket_id": str(ticket.id),
                        "deadline_at": ticket.approval_deadline_at.isoformat()
                        if ticket.approval_deadline_at
                        else None,
                    },
                )
            )

    def approve_ticket(
        self,
        ticket_id: str,
        approver_id: str,
    ) -> Ticket:
        """
        Approve a pending ticket (REQ-THA-004).

        Args:
            ticket_id: Ticket ID to approve
            approver_id: ID of the approver (human user)

        Returns:
            Updated ticket

        Raises:
            InvalidApprovalStateError: If ticket is not in pending_review state
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket not found: {ticket_id}")

            # Validate state (REQ-THA-010)
            if ticket.approval_status != ApprovalStatus.PENDING_REVIEW.value:
                raise InvalidApprovalStateError(
                    f"Cannot approve ticket in state: {ticket.approval_status}"
                )

            # Update status (REQ-THA-004)
            ticket.approval_status = ApprovalStatus.APPROVED.value
            ticket.approval_deadline_at = None

            session.commit()
            session.refresh(ticket)

            # Extract attributes before expunging
            ticket_data = {
                "id": ticket.id,
                "approval_status": ticket.approval_status,
                "approval_deadline_at": ticket.approval_deadline_at,
            }

            # Expunge so ticket can be used outside session
            session.expunge(ticket)

            # Audit log (REQ-THA-006, REQ-THA-010)
            # Note: Full audit logging would go to a dedicated audit table
            # For now, we log via events

            # Emit approval event (REQ-THA-010)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="TICKET_APPROVED",
                        entity_type="ticket",
                        entity_id=str(ticket_id),
                        payload={
                            "ticket_id": str(ticket_id),
                            "approver_id": approver_id,
                        },
                    )
                )

            # Update ticket object with extracted data
            ticket.id = ticket_data["id"]
            ticket.approval_status = ticket_data["approval_status"]
            ticket.approval_deadline_at = ticket_data["approval_deadline_at"]

            return ticket

    def reject_ticket(
        self,
        ticket_id: str,
        rejection_reason: str,
        rejector_id: str,
    ) -> Ticket:
        """
        Reject a pending ticket (REQ-THA-004).

        Args:
            ticket_id: Ticket ID to reject
            rejection_reason: Reason for rejection
            rejector_id: ID of the rejector (human user)

        Returns:
            Updated ticket (before deletion/archival)

        Raises:
            InvalidApprovalStateError: If ticket is not in pending_review state
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket not found: {ticket_id}")

            # Validate state (REQ-THA-010)
            if ticket.approval_status != ApprovalStatus.PENDING_REVIEW.value:
                raise InvalidApprovalStateError(
                    f"Cannot reject ticket in state: {ticket.approval_status}"
                )

            # Update status (REQ-THA-004)
            ticket.approval_status = ApprovalStatus.REJECTED.value
            ticket.rejection_reason = rejection_reason

            session.commit()
            session.refresh(ticket)

            # Audit log (REQ-THA-006, REQ-THA-010)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="TICKET_REJECTED",
                        entity_type="ticket",
                        entity_id=str(ticket_id),
                        payload={
                            "ticket_id": str(ticket_id),
                            "rejection_reason": rejection_reason,
                            "rejector_id": rejector_id,
                        },
                    )
                )

            # Handle rejection action (REQ-THA-004)
            if self.config.on_reject == "delete":
                # Delete ticket and related tasks (cascade)
                session.delete(ticket)
                session.commit()
            else:  # archive
                # Archive would be handled by setting a flag or moving to archive table
                # For now, we just mark as rejected
                pass

            return ticket

    def handle_timeout(self, ticket_id: str) -> Optional[Ticket]:
        """
        Handle ticket approval timeout (REQ-THA-004).

        Args:
            ticket_id: Ticket ID that timed out

        Returns:
            Updated ticket if it was still pending, None otherwise
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return None

            # Only process if still pending (REQ-THA-004)
            if ticket.approval_status != ApprovalStatus.PENDING_REVIEW.value:
                return None

            # Update status to timed out
            ticket.approval_status = ApprovalStatus.TIMED_OUT.value
            ticket.rejection_reason = "Approval timeout exceeded"

            session.commit()
            session.refresh(ticket)

            # Audit log (REQ-THA-006, REQ-THA-010)
            if self.event_bus:
                self.event_bus.publish(
                    SystemEvent(
                        event_type="TICKET_TIMED_OUT",
                        entity_type="ticket",
                        entity_id=str(ticket_id),
                        payload={"ticket_id": str(ticket_id)},
                    )
                )

            # Handle timeout action (same as rejection) (REQ-THA-004)
            if self.config.on_reject == "delete":
                session.delete(ticket)
                session.commit()
                return None
            else:  # archive
                pass

            return ticket

    def check_timeouts(self) -> list[str]:
        """
        Check for tickets that have exceeded their approval deadline (REQ-THA-004, REQ-THA-009).

        Returns:
            List of ticket IDs that have timed out
        """
        now = utc_now()
        timed_out_ticket_ids = []

        with self.db.get_session() as session:
            # Find tickets still in pending_review with deadline passed
            pending_tickets = (
                session.query(Ticket)
                .filter(
                    Ticket.approval_status == ApprovalStatus.PENDING_REVIEW.value,
                    Ticket.approval_deadline_at.isnot(None),
                    Ticket.approval_deadline_at <= now,
                )
                .all()
            )

            for ticket in pending_tickets:
                self.handle_timeout(ticket.id)
                timed_out_ticket_ids.append(ticket.id)

        return timed_out_ticket_ids

    def get_pending_count(self) -> int:
        """
        Get count of tickets pending approval (REQ-THA-*).

        Returns:
            Number of tickets in pending_review state
        """
        with self.db.get_session() as session:
            count = (
                session.query(Ticket)
                .filter(Ticket.approval_status == ApprovalStatus.PENDING_REVIEW.value)
                .count()
            )
            return count

    def get_approval_status(self, ticket_id: str) -> Optional[dict]:
        """
        Get approval status for a ticket (REQ-THA-*).

        Args:
            ticket_id: Ticket ID

        Returns:
            Approval status dict or None if ticket not found
        """
        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                return None

            return {
                "ticket_id": str(ticket_id),
                "approval_status": ticket.approval_status,
                "deadline_at": ticket.approval_deadline_at.isoformat()
                if ticket.approval_deadline_at
                else None,
                "requested_by_agent_id": ticket.requested_by_agent_id,
                "rejection_reason": ticket.rejection_reason,
            }

