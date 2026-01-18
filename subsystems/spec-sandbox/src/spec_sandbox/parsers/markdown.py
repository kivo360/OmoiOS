"""Markdown frontmatter parsing utilities.

Parses markdown files with YAML frontmatter, extracting structured data
and body content for the sync-to-API workflow.
"""

from pathlib import Path
from typing import Any, Dict, Tuple, Type, TypeVar, Union

import yaml
from pydantic import BaseModel, ValidationError

from spec_sandbox.schemas.frontmatter import TaskFrontmatter, TicketFrontmatter

T = TypeVar("T", bound=BaseModel)


class MarkdownParseError(Exception):
    """Error parsing markdown file."""

    pass


def parse_markdown_with_frontmatter(
    content: Union[str, Path],
) -> Tuple[Dict[str, Any], str]:
    """Parse markdown content, extracting frontmatter and body.

    Args:
        content: Either markdown string or Path to markdown file

    Returns:
        Tuple of (frontmatter_dict, markdown_body)

    Raises:
        MarkdownParseError: If frontmatter cannot be parsed
    """
    if isinstance(content, Path):
        if not content.exists():
            raise MarkdownParseError(f"File not found: {content}")
        text = content.read_text(encoding="utf-8")
    else:
        text = content

    text = text.strip()

    # Check for frontmatter delimiter
    if not text.startswith("---"):
        return {}, text

    # Find end of frontmatter
    end_idx = text.find("---", 3)
    if end_idx == -1:
        raise MarkdownParseError("Unclosed frontmatter: missing closing '---'")

    frontmatter_str = text[3:end_idx].strip()
    body = text[end_idx + 3 :].strip()

    # Parse YAML
    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as e:
        raise MarkdownParseError(f"Invalid YAML in frontmatter: {e}") from e

    return frontmatter, body


def parse_and_validate(
    content: Union[str, Path],
    model: Type[T],
) -> Tuple[T, str]:
    """Parse markdown and validate frontmatter against a Pydantic model.

    Args:
        content: Either markdown string or Path to markdown file
        model: Pydantic model class to validate against

    Returns:
        Tuple of (validated_model, markdown_body)

    Raises:
        MarkdownParseError: If parsing or validation fails
    """
    frontmatter, body = parse_markdown_with_frontmatter(content)

    try:
        validated = model.model_validate(frontmatter)
    except ValidationError as e:
        raise MarkdownParseError(f"Frontmatter validation failed: {e}") from e

    return validated, body


def parse_ticket_markdown(content: Union[str, Path]) -> Tuple[TicketFrontmatter, str]:
    """Parse a ticket markdown file.

    Args:
        content: Either markdown string or Path to ticket markdown file

    Returns:
        Tuple of (TicketFrontmatter, description_body)

    Raises:
        MarkdownParseError: If parsing or validation fails
    """
    return parse_and_validate(content, TicketFrontmatter)


def parse_task_markdown(content: Union[str, Path]) -> Tuple[TaskFrontmatter, str]:
    """Parse a task markdown file.

    Args:
        content: Either markdown string or Path to task markdown file

    Returns:
        Tuple of (TaskFrontmatter, description_body)

    Raises:
        MarkdownParseError: If parsing or validation fails
    """
    return parse_and_validate(content, TaskFrontmatter)


def frontmatter_to_yaml(model: BaseModel) -> str:
    """Convert a Pydantic model to YAML frontmatter string.

    Args:
        model: Pydantic model instance

    Returns:
        YAML string (without --- delimiters)
    """
    # Convert to dict, handling dates and enums
    data = model.model_dump(mode="json")
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


def create_markdown_with_frontmatter(model: BaseModel, body: str) -> str:
    """Create a complete markdown string with frontmatter.

    Args:
        model: Pydantic model for frontmatter
        body: Markdown body content

    Returns:
        Complete markdown string with frontmatter
    """
    frontmatter_yaml = frontmatter_to_yaml(model)
    return f"---\n{frontmatter_yaml}---\n\n{body}"
