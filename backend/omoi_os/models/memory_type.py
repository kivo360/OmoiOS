"""Memory type enumeration for memory taxonomy (REQ-MEM-TAX-001, REQ-MEM-TAX-002)."""

from enum import Enum


class MemoryType(str, Enum):
    """Memory type enumeration per REQ-MEM-TAX-001."""

    ERROR_FIX = "error_fix"
    DISCOVERY = "discovery"
    DECISION = "decision"
    LEARNING = "learning"
    WARNING = "warning"
    CODEBASE_KNOWLEDGE = "codebase_knowledge"

    @classmethod
    def all_types(cls) -> list[str]:
        """Get all memory type values as a list."""
        return [t.value for t in cls]

    @classmethod
    def is_valid(cls, memory_type: str) -> bool:
        """Check if memory type is valid (REQ-MEM-TAX-002)."""
        return memory_type in cls.all_types()
