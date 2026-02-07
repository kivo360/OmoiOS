"""Sandbox Modules - Python modules uploaded to Daytona sandboxes.

This module provides the spec-sandbox subsystem files for upload to
Daytona sandboxes. The spec-sandbox is a standalone package that handles
spec-driven development phases (EXPLORE -> REQUIREMENTS -> DESIGN -> TASKS -> SYNC).

Usage:
    from omoi_os.sandbox_modules import get_spec_sandbox_files

    # Get all files needed for spec-sandbox
    files = get_spec_sandbox_files()

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
