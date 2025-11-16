"""Phase definitions and transition metadata."""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class Phase(StrEnum):
    """Ticket workflow phases."""

    BACKLOG = "PHASE_BACKLOG"
    REQUIREMENTS = "PHASE_REQUIREMENTS"
    DESIGN = "PHASE_DESIGN"
    IMPLEMENTATION = "PHASE_IMPLEMENTATION"
    TESTING = "PHASE_TESTING"
    DEPLOYMENT = "PHASE_DEPLOYMENT"
    DONE = "PHASE_DONE"
    BLOCKED = "PHASE_BLOCKED"


PHASE_SEQUENCE: Final[list[Phase]] = [
    Phase.BACKLOG,
    Phase.REQUIREMENTS,
    Phase.DESIGN,
    Phase.IMPLEMENTATION,
    Phase.TESTING,
    Phase.DEPLOYMENT,
    Phase.DONE,
]


PHASE_TRANSITIONS: Final[dict[Phase, tuple[Phase, ...]]] = {
    Phase.BACKLOG: (Phase.REQUIREMENTS, Phase.BLOCKED),
    Phase.REQUIREMENTS: (Phase.DESIGN, Phase.BLOCKED),
    Phase.DESIGN: (Phase.IMPLEMENTATION, Phase.BLOCKED),
    Phase.IMPLEMENTATION: (Phase.TESTING, Phase.BLOCKED),
    Phase.TESTING: (Phase.DEPLOYMENT, Phase.IMPLEMENTATION, Phase.BLOCKED),
    Phase.DEPLOYMENT: (Phase.DONE, Phase.BLOCKED),
    Phase.DONE: (),
    Phase.BLOCKED: (
        Phase.BACKLOG,
        Phase.REQUIREMENTS,
        Phase.DESIGN,
        Phase.IMPLEMENTATION,
        Phase.TESTING,
    ),
}


__all__ = ["Phase", "PHASE_SEQUENCE", "PHASE_TRANSITIONS"]




