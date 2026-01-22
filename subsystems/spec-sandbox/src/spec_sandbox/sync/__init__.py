"""Markdown sync service for spec-sandbox.

Syncs generated markdown files with frontmatter to the backend API.

Sync Behavior:
- CREATE: New tickets/tasks are created if they don't exist
- UPDATE: If item exists but description differs, update it
- SKIP: If item exists with same description, skip
- FAILED: If sync operation fails
"""

from spec_sandbox.sync.service import (
    MarkdownSyncService,
    SyncAction,
    SyncConfig,
    SyncResult,
    SyncSummary,
)

__all__ = [
    "MarkdownSyncService",
    "SyncAction",
    "SyncConfig",
    "SyncResult",
    "SyncSummary",
]
