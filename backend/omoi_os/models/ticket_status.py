"""Ticket status enumeration for Kanban state machine."""

from enum import StrEnum


class TicketStatus(StrEnum):
    """
    Ticket status enumeration per REQ-TKT-SM-001.

    States: backlog → analyzing → building → building-done → testing → done
    With optional 'blocked' overlay (handled via is_blocked flag).
    """

    BACKLOG = "backlog"
    ANALYZING = "analyzing"
    BUILDING = "building"
    BUILDING_DONE = "building-done"
    TESTING = "testing"
    DONE = "done"

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if status is terminal (DONE is the only terminal state)."""
        return status == cls.DONE.value

    @classmethod
    def is_blocked_state(cls, status: str) -> bool:
        """
        Check if status is a blocked state.
        
        Note: Blocked is handled as an overlay via is_blocked flag,
        not as a separate status value.
        """
        return False  # Blocked is an overlay, not a status


# Valid state transitions per REQ-TKT-SM-002
VALID_TRANSITIONS: dict[str, list[str]] = {
    TicketStatus.BACKLOG.value: [TicketStatus.ANALYZING.value],
    TicketStatus.ANALYZING.value: [TicketStatus.BUILDING.value],
    TicketStatus.BUILDING.value: [TicketStatus.BUILDING_DONE.value],
    TicketStatus.BUILDING_DONE.value: [TicketStatus.TESTING.value],
    TicketStatus.TESTING.value: [TicketStatus.DONE.value, TicketStatus.BUILDING.value],  # Can regress on fix needed
    TicketStatus.DONE.value: [],  # Terminal state
}

# Transitions FROM blocked state (when unblocked, can return to previous phase)
BLOCKED_TRANSITIONS: list[str] = [
    TicketStatus.ANALYZING.value,
    TicketStatus.BUILDING.value,
    TicketStatus.BUILDING_DONE.value,
    TicketStatus.TESTING.value,
]


def is_valid_transition(from_status: str, to_status: str, is_blocked: bool = False) -> bool:
    """
    Validate state transition per REQ-TKT-SM-002.

    Args:
        from_status: Current ticket status
        to_status: Target ticket status
        is_blocked: Whether ticket is currently blocked (overlay)

    Returns:
        True if transition is valid, False otherwise
    """
    # If currently blocked, can transition to unblock states
    # But the transition must still be valid from the current status
    # OR the target must be in BLOCKED_TRANSITIONS (unblock states)
    if is_blocked:
        # First check if it's a valid unblock transition (target in BLOCKED_TRANSITIONS)
        if to_status in BLOCKED_TRANSITIONS:
            return True
        # Otherwise, check if it would be valid if not blocked
        allowed = VALID_TRANSITIONS.get(from_status, [])
        return to_status in allowed

    # Check normal transitions
    allowed = VALID_TRANSITIONS.get(from_status, [])
    return to_status in allowed

