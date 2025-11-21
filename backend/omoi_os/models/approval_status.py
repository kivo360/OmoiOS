"""Approval status enum and helper functions (REQ-THA-001)."""

from enum import Enum


class ApprovalStatus(str, Enum):
    """Approval status values for tickets (REQ-THA-001)."""

    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"

    @classmethod
    def is_pending(cls, status: str) -> bool:
        """Check if status is pending review."""
        return status == cls.PENDING_REVIEW.value

    @classmethod
    def is_final(cls, status: str) -> bool:
        """Check if status is a final state (approved, rejected, or timed_out)."""
        return status in (cls.APPROVED.value, cls.REJECTED.value, cls.TIMED_OUT.value)

    @classmethod
    def can_proceed(cls, status: str) -> bool:
        """Check if ticket can proceed to workflow (must be approved)."""
        return status == cls.APPROVED.value

