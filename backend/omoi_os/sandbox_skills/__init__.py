"""Sandbox Agent Skills.

This module provides skills that are uploaded to Daytona sandboxes
for Claude agents to use during task execution.

Usage:
    from omoi_os.sandbox_skills import get_skills_for_upload

    # Get all skills (includes all files: SKILL.md, scripts, references, etc.)
    skills = get_skills_for_upload()

    # Get specific skills
    skills = get_skills_for_upload(["spec-driven-dev", "code-review"])

    # Get only SKILL.md files (backward compatible)
    skills = get_skills_for_upload(include_all_files=False)

    # Upload to sandbox
    for skill_path, content in skills.items():
        sandbox.fs.upload_file(content.encode("utf-8"), skill_path)
"""

from pathlib import Path
from typing import Optional

import yaml


def get_skill_manifest() -> dict:
    """Load the skill manifest."""
    manifest_path = Path(__file__).parent / "manifest.yaml"
    if manifest_path.exists():
        with open(manifest_path) as f:
            return yaml.safe_load(f)
    return {"skills": [], "settings": {}}


def get_available_skills() -> list[str]:
    """Get list of available skill names."""
    manifest = get_skill_manifest()
    return [skill["name"] for skill in manifest.get("skills", [])]


def get_always_include_skills() -> list[str]:
    """Get skills that should always be included."""
    manifest = get_skill_manifest()
    return manifest.get("settings", {}).get("always_include", [])


def get_skill_content(skill_name: str) -> Optional[str]:
    """Get the content of a skill's SKILL.md file."""
    skill_path = Path(__file__).parent / skill_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text()
    return None


def get_skill_files(skill_name: str) -> dict[str, str]:
    """Get all files for a skill (SKILL.md, scripts, references, etc.).

    Args:
        skill_name: Name of the skill directory.

    Returns:
        Dict mapping relative paths to file content.
        Example: {"SKILL.md": "...", "scripts/api_client.py": "..."}
    """
    skill_dir = Path(__file__).parent / skill_name
    if not skill_dir.exists():
        return {}

    result = {}

    # Walk through all files in the skill directory
    for file_path in skill_dir.rglob("*"):
        if file_path.is_file():
            # Skip __pycache__ and .pyc files
            if "__pycache__" in str(file_path) or file_path.suffix == ".pyc":
                continue

            # Get relative path from skill directory
            relative_path = file_path.relative_to(skill_dir)

            # Read file content (text files only)
            try:
                content = file_path.read_text()
                result[str(relative_path)] = content
            except UnicodeDecodeError:
                # Skip binary files
                continue

    return result


def get_skill_set(mode: str) -> list[str]:
    """Get skills for a specific execution mode.

    Args:
        mode: Execution mode - "exploration", "implementation", "validation".

    Returns:
        List of skill names for the specified mode.
    """
    manifest = get_skill_manifest()
    settings = manifest.get("settings", {})
    skill_sets = settings.get("skill_sets", {})
    return skill_sets.get(mode, [])


def get_skills_for_upload(
    skill_names: Optional[list[str]] = None,
    install_path: str = "/root/.claude/skills",
    include_all_files: bool = True,
    mode: Optional[str] = None,
) -> dict[str, str]:
    """Get skills ready for upload to a sandbox.

    Args:
        skill_names: Specific skills to include. Added to mode-based skills if provided.
        install_path: Path in sandbox where skills will be installed.
        include_all_files: If True, include all files (scripts, references, etc.).
                          If False, only include SKILL.md files.
        mode: Execution mode - "exploration", "implementation", "validation".
              If None, falls back to always_include only.

    Returns:
        Dict mapping sandbox file paths to file content.
        Example: {"/root/.claude/skills/code-review/SKILL.md": "...content..."}

    Modes:
        - exploration: For feature definition - creates specs, tickets, tasks
        - implementation: For task execution - writes code, runs tests
        - validation: For verifying implementation meets requirements
    """
    manifest = get_skill_manifest()
    settings = manifest.get("settings", {})

    # Start with always_include (truly universal skills)
    skills_to_load = set(settings.get("always_include", []))

    # Add mode-specific skills if mode is provided
    if mode:
        skill_sets = settings.get("skill_sets", {})
        mode_skills = skill_sets.get(mode, [])
        skills_to_load |= set(mode_skills)

    # Add any explicitly requested skills
    if skill_names:
        skills_to_load |= set(skill_names)

    result = {}

    for skill_name in skills_to_load:
        if include_all_files:
            # Get all files for the skill
            skill_files = get_skill_files(skill_name)
            for relative_path, content in skill_files.items():
                sandbox_path = f"{install_path}/{skill_name}/{relative_path}"
                result[sandbox_path] = content
        else:
            # Only get SKILL.md (backward compatible)
            content = get_skill_content(skill_name)
            if content:
                sandbox_path = f"{install_path}/{skill_name}/SKILL.md"
                result[sandbox_path] = content

    return result


def get_skills_archive() -> bytes:
    """Get all skills as a tar.gz archive.

    This is useful for uploading all skills at once to a sandbox.

    Returns:
        Bytes of tar.gz archive containing all skills.
    """
    import io
    import tarfile

    skills = get_skills_for_upload(skill_names=get_available_skills())

    # Create tar archive in memory
    archive_buffer = io.BytesIO()
    with tarfile.open(fileobj=archive_buffer, mode="w:gz") as tar:
        for path, content in skills.items():
            # Remove leading slash for tar
            tar_path = path.lstrip("/")
            content_bytes = content.encode("utf-8")

            # Create tarinfo
            info = tarfile.TarInfo(name=tar_path)
            info.size = len(content_bytes)

            # Add to archive
            tar.addfile(info, io.BytesIO(content_bytes))

    return archive_buffer.getvalue()
