"""Phase definitions for ticket workflow."""

from enum import Enum


class Phase(str, Enum):
    """Phase identifiers for ticket workflow."""
    
    REQUIREMENTS = "PHASE_REQUIREMENTS"
    DESIGN = "PHASE_DESIGN"
    IMPLEMENTATION = "PHASE_IMPLEMENTATION"
    TESTING = "PHASE_TESTING"
    DEPLOYMENT = "PHASE_DEPLOYMENT"

    def __str__(self) -> str:
        """Return the phase value."""
        return self.value
