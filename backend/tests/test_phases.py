"""Tests for phase enums and transition definitions."""

import pytest

from omoi_os.models import phases


def test_phase_enum_values():
    """Test that all phase enum values are correct."""
    assert phases.Phase.BACKLOG.value == "PHASE_BACKLOG"
    assert phases.Phase.REQUIREMENTS.value == "PHASE_REQUIREMENTS"
    assert phases.Phase.DESIGN.value == "PHASE_DESIGN"
    assert phases.Phase.IMPLEMENTATION.value == "PHASE_IMPLEMENTATION"
    assert phases.Phase.TESTING.value == "PHASE_TESTING"
    assert phases.Phase.DEPLOYMENT.value == "PHASE_DEPLOYMENT"
    assert phases.Phase.DONE.value == "PHASE_DONE"
    assert phases.Phase.BLOCKED.value == "PHASE_BLOCKED"


def test_phase_sequence_order():
    """Test that phase sequence is in correct order."""
    expected = [
        phases.Phase.BACKLOG,
        phases.Phase.REQUIREMENTS,
        phases.Phase.DESIGN,
        phases.Phase.IMPLEMENTATION,
        phases.Phase.TESTING,
        phases.Phase.DEPLOYMENT,
        phases.Phase.DONE,
    ]
    assert phases.PHASE_SEQUENCE == expected


@pytest.mark.parametrize(
    ("from_phase", "to_phase"),
    [
        (phases.Phase.BACKLOG, phases.Phase.REQUIREMENTS),
        (phases.Phase.REQUIREMENTS, phases.Phase.DESIGN),
        (phases.Phase.DESIGN, phases.Phase.IMPLEMENTATION),
        (phases.Phase.IMPLEMENTATION, phases.Phase.TESTING),
        (phases.Phase.TESTING, phases.Phase.DEPLOYMENT),
        (phases.Phase.TESTING, phases.Phase.IMPLEMENTATION),  # regression allowed
        (phases.Phase.BLOCKED, phases.Phase.REQUIREMENTS),
    ],
)
def test_phase_transitions_valid(from_phase, to_phase):
    """Test that valid transitions are defined correctly."""
    assert to_phase in phases.PHASE_TRANSITIONS[from_phase]


@pytest.mark.parametrize(
    ("from_phase", "to_phase"),
    [
        (phases.Phase.BACKLOG, phases.Phase.DEPLOYMENT),
        (phases.Phase.REQUIREMENTS, phases.Phase.DONE),
        (phases.Phase.DONE, phases.Phase.IMPLEMENTATION),
    ],
)
def test_phase_transitions_invalid(from_phase, to_phase):
    """Test that invalid transitions are not in transition map."""
    assert to_phase not in phases.PHASE_TRANSITIONS[from_phase]






