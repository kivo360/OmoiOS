"""Tests for PHASE_IMPLEMENTATION phase and ticket creation.

This test module verifies:
- Tickets can be created with phase_id: PHASE_IMPLEMENTATION
- Tickets can have status: "building"
- The implementation phase is correctly configured in the system
"""

import pytest

from omoi_os.models import phases
from omoi_os.models.ticket import Ticket


class TestImplementationPhase:
    """Tests for the PHASE_IMPLEMENTATION phase configuration."""

    def test_implementation_phase_exists(self):
        """Verify PHASE_IMPLEMENTATION enum value exists."""
        assert hasattr(phases.Phase, "IMPLEMENTATION")
        assert phases.Phase.IMPLEMENTATION.value == "PHASE_IMPLEMENTATION"

    def test_implementation_phase_in_sequence(self):
        """Verify PHASE_IMPLEMENTATION is in the phase sequence at the correct position."""
        assert phases.Phase.IMPLEMENTATION in phases.PHASE_SEQUENCE
        # Implementation should come after Design (index 2) at index 3
        assert phases.PHASE_SEQUENCE.index(phases.Phase.IMPLEMENTATION) == 3

    def test_implementation_phase_transitions(self):
        """Verify PHASE_IMPLEMENTATION has correct transition targets."""
        transitions = phases.PHASE_TRANSITIONS[phases.Phase.IMPLEMENTATION]
        # Implementation can transition to Testing or Blocked
        assert phases.Phase.TESTING in transitions
        assert phases.Phase.BLOCKED in transitions
        # Should not be able to skip to Done or Deployment directly
        assert phases.Phase.DONE not in transitions
        assert phases.Phase.DEPLOYMENT not in transitions

    def test_design_can_transition_to_implementation(self):
        """Verify that DESIGN phase can transition to IMPLEMENTATION."""
        design_transitions = phases.PHASE_TRANSITIONS[phases.Phase.DESIGN]
        assert phases.Phase.IMPLEMENTATION in design_transitions

    def test_blocked_can_return_to_implementation(self):
        """Verify that BLOCKED phase can return to IMPLEMENTATION."""
        blocked_transitions = phases.PHASE_TRANSITIONS[phases.Phase.BLOCKED]
        assert phases.Phase.IMPLEMENTATION in blocked_transitions


class TestTicketWithImplementationPhase:
    """Tests for creating tickets in the implementation phase."""

    def test_ticket_with_implementation_phase_id(self):
        """Verify a ticket can be created with PHASE_IMPLEMENTATION phase_id."""
        ticket = Ticket(
            title="Test Implementation Ticket",
            phase_id=phases.Phase.IMPLEMENTATION.value,
            priority="HIGH",
            status="building",
        )
        assert ticket.phase_id == "PHASE_IMPLEMENTATION"
        assert ticket.title == "Test Implementation Ticket"

    def test_ticket_with_building_status(self):
        """Verify a ticket can be created with 'building' status."""
        ticket = Ticket(
            title="Test Building Status",
            phase_id=phases.Phase.IMPLEMENTATION.value,
            priority="HIGH",
            status="building",
        )
        assert ticket.status == "building"

    def test_ticket_implementation_phase_with_all_priorities(self):
        """Verify tickets in implementation phase work with all priority levels."""
        priorities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

        for priority in priorities:
            ticket = Ticket(
                title=f"Test {priority} Priority",
                phase_id=phases.Phase.IMPLEMENTATION.value,
                priority=priority,
                status="building",
            )
            assert ticket.priority == priority
            assert ticket.phase_id == "PHASE_IMPLEMENTATION"

    def test_ticket_valid_statuses_for_implementation(self):
        """Verify valid statuses for implementation phase tickets."""
        # Per REQ-TKT-SM-001: backlog, analyzing, building, building-done, testing, done
        valid_statuses = ["backlog", "analyzing", "building", "building-done", "testing", "done"]

        for status in valid_statuses:
            ticket = Ticket(
                title=f"Test {status} Status",
                phase_id=phases.Phase.IMPLEMENTATION.value,
                priority="HIGH",
                status=status,
            )
            assert ticket.status == status


class TestContinuousModeSupport:
    """Tests verifying continuous mode support for implementation tasks."""

    def test_implementation_phase_allows_task_creation(self):
        """Verify the implementation phase configuration supports task creation.

        This validates that the phase system is properly configured for
        continuous mode task execution.
        """
        # Verify the phase exists and has valid transitions
        impl_phase = phases.Phase.IMPLEMENTATION
        assert impl_phase.value == "PHASE_IMPLEMENTATION"

        # Verify it's not a terminal phase (can transition out)
        transitions = phases.PHASE_TRANSITIONS[impl_phase]
        assert len(transitions) > 0, "Implementation phase must have transitions"

    def test_implementation_phase_is_not_terminal(self):
        """Verify PHASE_IMPLEMENTATION is not a terminal phase.

        Terminal phases (like DONE) cannot have tasks created against them.
        Implementation phase should support ongoing task creation.
        """
        impl_phase = phases.Phase.IMPLEMENTATION
        # DONE is the terminal phase, IMPLEMENTATION should have transitions
        assert phases.PHASE_TRANSITIONS[impl_phase] != ()
        assert phases.PHASE_TRANSITIONS[phases.Phase.DONE] == ()

    def test_implementation_phase_order_is_after_design(self):
        """Verify implementation phase comes after design in the workflow."""
        design_idx = phases.PHASE_SEQUENCE.index(phases.Phase.DESIGN)
        impl_idx = phases.PHASE_SEQUENCE.index(phases.Phase.IMPLEMENTATION)
        assert impl_idx == design_idx + 1, "Implementation should immediately follow Design"
