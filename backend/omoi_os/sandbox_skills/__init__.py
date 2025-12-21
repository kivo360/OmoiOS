"""Sandbox Agent Skills.

This module provides skills that are uploaded to Daytona sandboxes
for Claude agents to use during task execution.

Usage:
    from omoi_os.sandbox_skills import get_skills_for_upload

    # Get all skills
    skills = get_skills_for_upload()

    # Get specific skills
    skills = get_skills_for_upload(["spec-driven-dev", "code-review"])

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


def get_skills_for_upload(
    skill_names: Optional[list[str]] = None,
    install_path: str = "/root/.claude/skills",
) -> dict[str, str]:
    """Get skills ready for upload to a sandbox.

    Args:
        skill_names: Specific skills to include. If None, includes all always_include skills.
        install_path: Path in sandbox where skills will be installed.

    Returns:
        Dict mapping sandbox file paths to file content.
        Example: {"/root/.claude/skills/code-review/SKILL.md": "...content..."}
    """
    manifest = get_skill_manifest()
    settings = manifest.get("settings", {})

    # Determine which skills to include
    if skill_names is None:
        skill_names = settings.get("always_include", [])

    # Add any always_include skills not already in the list
    always_include = set(settings.get("always_include", []))
    skill_names = list(set(skill_names) | always_include)

    result = {}

    for skill_name in skill_names:
        content = get_skill_content(skill_name)
        if content:
            # Create path like: /root/.claude/skills/code-review/SKILL.md
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
