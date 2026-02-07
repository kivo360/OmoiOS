"""Agent status enumeration for lifecycle state machine."""

from enum import StrEnum


class AgentStatus(StrEnum):
    """
    Agent status enumeration per REQ-ALM-004.

    States: SPAWNING → IDLE → RUNNING → (DEGRADED|FAILED|QUARANTINED|TERMINATED)
    """

    SPAWNING = "SPAWNING"
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    TERMINATED = "TERMINATED"

    @classmethod
    def is_terminal(cls, status: str) -> bool:
        """Check if status is terminal (TERMINATED is the only terminal state)."""
        return status == cls.TERMINATED.value

    @classmethod
    def is_active(cls, status: str) -> bool:
        """Check if status is active (can receive tasks)."""
        return status in [cls.IDLE.value, cls.RUNNING.value]

    @classmethod
    def is_operational(cls, status: str) -> bool:
        """Check if status is operational (not failed/terminated/quarantined)."""
        return status not in [
            cls.FAILED.value,
            cls.TERMINATED.value,
            cls.QUARANTINED.value,
        ]


# Valid state transitions per REQ-ALM-004
VALID_TRANSITIONS: dict[str, list[str]] = {
    AgentStatus.SPAWNING.value: [
        AgentStatus.IDLE.value,
        AgentStatus.FAILED.value,
        AgentStatus.TERMINATED.value,
    ],
    AgentStatus.IDLE.value: [
        AgentStatus.RUNNING.value,
        AgentStatus.DEGRADED.value,
        AgentStatus.QUARANTINED.value,
        AgentStatus.TERMINATED.value,
    ],
    AgentStatus.RUNNING.value: [
        AgentStatus.IDLE.value,
        AgentStatus.FAILED.value,
        AgentStatus.DEGRADED.value,
        AgentStatus.QUARANTINED.value,
    ],
    AgentStatus.DEGRADED.value: [
        AgentStatus.IDLE.value,
        AgentStatus.FAILED.value,
        AgentStatus.QUARANTINED.value,
        AgentStatus.TERMINATED.value,
    ],
    AgentStatus.FAILED.value: [
        AgentStatus.QUARANTINED.value,
        AgentStatus.TERMINATED.value,
    ],
    AgentStatus.QUARANTINED.value: [
        AgentStatus.IDLE.value,
        AgentStatus.TERMINATED.value,
    ],
    AgentStatus.TERMINATED.value: [],  # Terminal state
}


def is_valid_transition(from_status: str, to_status: str) -> bool:
    """
    Validate agent status transition per REQ-ALM-004.

    Args:
        from_status: Current agent status
        to_status: Target agent status

    Returns:
        True if transition is valid, False otherwise
    """
    # Check if from_status exists in valid transitions
    allowed = VALID_TRANSITIONS.get(from_status, [])
    return to_status in allowed
