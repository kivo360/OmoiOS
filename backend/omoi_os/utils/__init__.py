"""Utility modules for OmoiOS."""

from omoi_os.utils.datetime import utc_now, utc_datetime
from omoi_os.utils.mermaid import (
    MermaidValidationResult,
    sanitize_mermaid_diagram,
    sanitize_markdown_mermaid_blocks,
    extract_mermaid_blocks,
    validate_mermaid_with_cli,
    validate_mermaid_sync,
)

__all__ = [
    # Datetime utilities
    "utc_now",
    "utc_datetime",
    # Mermaid utilities
    "MermaidValidationResult",
    "sanitize_mermaid_diagram",
    "sanitize_markdown_mermaid_blocks",
    "extract_mermaid_blocks",
    "validate_mermaid_with_cli",
    "validate_mermaid_sync",
]

