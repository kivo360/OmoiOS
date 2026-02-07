"""Sandbox Modules - Python modules uploaded to Daytona sandboxes.

This module provides Python code that is uploaded to Daytona sandboxes
for the spec state machine and other functionality that requires
omoi_os code to run inside the sandbox.

The sandbox doesn't have the full omoi_os package installed, so we
upload individual modules that are needed for specific functionality.

Usage:
    from omoi_os.sandbox_modules import get_spec_state_machine_files

    # Get all files needed for spec state machine
    files = get_spec_state_machine_files()

    # Upload to sandbox
    for sandbox_path, content in files.items():
        sandbox.fs.upload_file(content.encode("utf-8"), sandbox_path)
"""

from pathlib import Path
from typing import Optional


def _read_file(file_path: Path) -> Optional[str]:
    """Read a file and return its content."""
    try:
        return file_path.read_text()
    except (FileNotFoundError, UnicodeDecodeError):
        return None


def get_spec_state_machine_files(
    install_path: str = "/tmp/omoi_os",
) -> dict[str, str]:
    """Get all files needed for the SpecStateMachine to run in a sandbox.

    This includes:
    - omoi_os/workers/spec_state_machine.py
    - omoi_os/schemas/spec_generation.py
    - omoi_os/evals/*.py (evaluators)
    - omoi_os/services/embedding.py (stub for sandbox)
    - omoi_os/services/spec_sync.py (stub for sandbox)

    Args:
        install_path: Base path in sandbox where modules will be installed.

    Returns:
        Dict mapping sandbox file paths to file content.
        Example: {"/tmp/omoi_os/workers/spec_state_machine.py": "...content..."}
    """
    result = {}

    # Base directory of omoi_os package
    omoi_os_root = Path(__file__).parent.parent

    # Files to upload (relative to omoi_os root)
    files_to_upload = [
        # State machine
        "workers/spec_state_machine.py",
        # Schemas
        "schemas/spec_generation.py",
        # Evaluators
        "evals/__init__.py",
        "evals/base.py",
        "evals/exploration_eval.py",
        "evals/requirement_eval.py",
        "evals/design_eval.py",
        "evals/task_eval.py",
    ]

    for relative_path in files_to_upload:
        file_path = omoi_os_root / relative_path
        content = _read_file(file_path)
        if content:
            sandbox_path = f"{install_path}/{relative_path}"
            result[sandbox_path] = content

    # Add __init__.py files to make proper packages
    init_files = [
        "__init__.py",
        "workers/__init__.py",
        "schemas/__init__.py",
        "services/__init__.py",
    ]

    for init_path in init_files:
        file_path = omoi_os_root / init_path
        content = _read_file(file_path)
        if content:
            sandbox_path = f"{install_path}/{init_path}"
            result[sandbox_path] = content
        else:
            # Create minimal __init__.py if it doesn't exist
            sandbox_path = f"{install_path}/{init_path}"
            result[sandbox_path] = '"""Auto-generated __init__.py for sandbox."""\n'

    # Add stub services that work without database
    result[f"{install_path}/services/embedding.py"] = _get_embedding_stub()
    result[f"{install_path}/services/spec_sync.py"] = _get_spec_sync_stub()

    return result


def _get_embedding_stub() -> str:
    """Get stub embedding service for sandbox (no external dependencies)."""
    return '''"""Stub Embedding Service for sandbox environments.

This is a minimal implementation that works without external dependencies.
The real EmbeddingService requires API keys and network access.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Stub embedding service for sandbox - returns None for all operations."""

    def __init__(self, *args, **kwargs):
        logger.info("Using stub EmbeddingService (sandbox mode)")

    async def embed_text(self, text: str) -> Optional[list[float]]:
        """Return None - embeddings not available in sandbox."""
        return None

    async def embed_texts(self, texts: list[str]) -> list[Optional[list[float]]]:
        """Return None for each text."""
        return [None] * len(texts)


def get_embedding_service(*args, **kwargs) -> EmbeddingService:
    """Get stub embedding service."""
    return EmbeddingService()
'''


def _get_spec_sync_stub() -> str:
    """Get stub spec sync service for sandbox (logs instead of syncing)."""
    return '''"""Stub Spec Sync Service for sandbox environments.

This is a minimal implementation that logs sync operations instead of
actually persisting to the database. The real SpecSyncService requires
database access.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""
    success: bool = True
    message: str = ""
    created_ids: dict = field(default_factory=dict)
    updated_ids: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


class SpecSyncService:
    """Stub spec sync service for sandbox - logs operations."""

    def __init__(self, *args, **kwargs):
        logger.info("Using stub SpecSyncService (sandbox mode)")

    async def sync_spec(self, spec_id: str, phase_data: dict) -> SyncResult:
        """Log sync operation instead of persisting."""
        logger.info(f"[STUB] Would sync spec {spec_id} with data keys: {list(phase_data.keys())}")
        return SyncResult(success=True, message="Stub sync - logged but not persisted")

    async def sync_requirements(self, spec_id: str, requirements: list) -> SyncResult:
        """Log requirements sync."""
        logger.info(f"[STUB] Would sync {len(requirements)} requirements for spec {spec_id}")
        return SyncResult(success=True, message=f"Stub: {len(requirements)} requirements")

    async def sync_tickets(self, spec_id: str, tickets: list) -> SyncResult:
        """Log tickets sync."""
        logger.info(f"[STUB] Would sync {len(tickets)} tickets for spec {spec_id}")
        return SyncResult(success=True, message=f"Stub: {len(tickets)} tickets")

    async def sync_tasks(self, spec_id: str, tasks: list) -> SyncResult:
        """Log tasks sync."""
        logger.info(f"[STUB] Would sync {len(tasks)} tasks for spec {spec_id}")
        return SyncResult(success=True, message=f"Stub: {len(tasks)} tasks")


def get_spec_sync_service(*args, **kwargs) -> SpecSyncService:
    """Get stub spec sync service."""
    return SpecSyncService()
'''


def get_module_init_script(install_path: str = "/tmp/omoi_os") -> str:
    """Get a shell script to set up the Python path for sandbox modules.

    This script should be sourced or run before the worker starts to ensure
    the uploaded modules can be imported.

    Args:
        install_path: Base path where modules are installed.

    Returns:
        Shell script content.
    """
    return f"""#!/bin/bash
# Set up Python path for sandbox omoi_os modules

export PYTHONPATH="{install_path}:$PYTHONPATH"

# Verify the modules are importable
python3 -c "from omoi_os.workers.spec_state_machine import SpecStateMachine; print('✅ SpecStateMachine imported successfully')" 2>/dev/null || echo "⚠️ SpecStateMachine import failed"
"""


def get_spec_sandbox_files(
    install_path: str = "/tmp/spec_sandbox_pkg",
) -> dict[str, str]:
    """Get all files needed for the spec-sandbox subsystem to run in a sandbox.

    The spec-sandbox is a standalone subsystem that emits proper spec.* events
    via HTTPReporter. It's uploaded to the sandbox as a package that can be
    imported as `spec_sandbox`.

    This includes all files from subsystems/spec-sandbox/src/spec_sandbox/:
    - config.py (settings from environment)
    - worker/state_machine.py (main state machine)
    - reporters/*.py (http, array, jsonl, console)
    - schemas/*.py (events, spec, frontmatter)
    - evaluators/*.py (phase evaluation)
    - executor/*.py (Claude executor)
    - generators/*.py (markdown generation)
    - prompts/*.py (phase prompts)
    - services/*.py (ticket creator)
    - parsers/*.py (markdown parsing)
    - sync/*.py (sync service)

    Args:
        install_path: Base path in sandbox where the package will be installed.

    Returns:
        Dict mapping sandbox file paths to file content.
        Example: {"/tmp/spec_sandbox_pkg/spec_sandbox/config.py": "...content..."}
    """
    result = {}
    import os

    # Base directory of spec-sandbox subsystem
    # This file is at: backend/omoi_os/sandbox_modules/__init__.py
    #
    # In development (monorepo):
    #   - This file: senior_sandbox/backend/omoi_os/sandbox_modules/__init__.py
    #   - spec-sandbox: senior_sandbox/subsystems/spec-sandbox/src/spec_sandbox/
    #
    # In Docker:
    #   - This file: /app/omoi_os/sandbox_modules/__init__.py
    #   - spec-sandbox: /app/subsystems/spec-sandbox/src/spec_sandbox/

    # Try multiple paths to find spec-sandbox
    potential_paths = []

    # Path 1: Docker layout (/app/subsystems/...)
    # In Docker, /app contains both the backend code AND subsystems
    app_root = Path(__file__).parent.parent.parent  # /app or backend/
    potential_paths.append(
        app_root / "subsystems" / "spec-sandbox" / "src" / "spec_sandbox"
    )

    # Path 2: Monorepo layout (backend/../subsystems/...)
    monorepo_root = app_root.parent
    potential_paths.append(
        monorepo_root / "subsystems" / "spec-sandbox" / "src" / "spec_sandbox"
    )

    # Path 3: cwd-relative paths
    potential_paths.append(
        Path(os.getcwd()) / "subsystems" / "spec-sandbox" / "src" / "spec_sandbox"
    )
    potential_paths.append(
        Path(os.getcwd()).parent
        / "subsystems"
        / "spec-sandbox"
        / "src"
        / "spec_sandbox"
    )

    # Find the first path that exists
    spec_sandbox_src = None
    for path in potential_paths:
        if path.exists():
            spec_sandbox_src = path
            break

    if spec_sandbox_src is None:
        return {}

    # Recursively collect all .py files
    for py_file in spec_sandbox_src.rglob("*.py"):
        relative_path = py_file.relative_to(spec_sandbox_src)
        content = _read_file(py_file)
        if content:
            sandbox_path = f"{install_path}/spec_sandbox/{relative_path}"
            result[sandbox_path] = content

    return result


def get_spec_sandbox_dependencies_install_script() -> str:
    """Get a shell script to install spec-sandbox dependencies.

    The spec-sandbox requires these packages:
    - httpx (for HTTPReporter)
    - pydantic, pydantic-settings (for config)
    - pyyaml (for YAML parsing)
    - click (for CLI, though we don't use it in sandbox)
    - claude-agent-sdk (for executor)

    Returns:
        Shell script content that installs dependencies.
    """
    return """#!/bin/bash
# Install spec-sandbox dependencies

# Try uv first (faster), fall back to pip
if command -v uv &> /dev/null; then
    uv pip install httpx pydantic pydantic-settings pyyaml 2>/dev/null || pip install httpx pydantic pydantic-settings pyyaml
else
    pip install httpx pydantic pydantic-settings pyyaml
fi
"""
