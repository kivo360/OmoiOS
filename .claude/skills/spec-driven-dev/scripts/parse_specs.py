#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "pyyaml>=6.0",
# ]
# ///
"""
Parse .omoi_os/ spec files into structured data.

This module provides the SpecParser class that reads markdown files
with YAML frontmatter and converts them into structured dataclasses.

Supports:
- Requirements (.omoi_os/requirements/*.md)
- Designs (.omoi_os/designs/*.md)
- Tickets (.omoi_os/tickets/*.md)
- Tasks (.omoi_os/tasks/*.md)

Usage:
    from parse_specs import SpecParser

    parser = SpecParser()
    result = parser.parse_all()

    for req in result.requirements:
        print(f"{req.id}: {req.title}")

    for ticket in result.tickets:
        print(f"{ticket.id}: {ticket.title}")

    for task in result.get_ready_tasks():
        print(f"Ready: {task.id}")
"""

import re
from datetime import date
from pathlib import Path
from typing import Optional

import yaml

from models import (
    AcceptanceCriterion,
    ApiEndpoint,
    DataModel,
    ParsedDesign,
    ParsedRequirement,
    ParsedTask,
    ParsedTicket,
    ParseResult,
    TaskDependencies,
    TicketDependencies,
    ValidationError,
)


class SpecParser:
    """Parse spec files from .omoi_os/ directory."""

    def __init__(self, root_dir: Optional[Path] = None):
        """Initialize parser with project root directory.

        Args:
            root_dir: Project root directory. If None, will search upward
                     from current directory for .omoi_os/ folder.
        """
        self.root = root_dir or self._find_project_root()
        self.omoi_dir = self.root / ".omoi_os"

    def _find_project_root(self) -> Path:
        """Find project root by looking for .omoi_os or common markers."""
        current = Path.cwd()

        for parent in [current] + list(current.parents):
            if (parent / ".omoi_os").exists():
                return parent
            if (parent / ".git").exists():
                return parent

        return current

    def _parse_frontmatter(self, content: str) -> tuple[dict, str]:
        """Extract YAML frontmatter and markdown body from content.

        Supports two formats:
        1. YAML frontmatter (preferred): ---\nkey: value\n---
        2. Markdown metadata (legacy): **Key**: Value

        Args:
            content: Full file content

        Returns:
            Tuple of (frontmatter dict, remaining markdown body)

        Raises:
            ValueError: If frontmatter is missing or invalid
        """
        # Check for YAML frontmatter delimiters
        if content.startswith("---"):
            # Find end of frontmatter
            end_match = re.search(r"\n---\s*\n", content[3:])
            if end_match:
                frontmatter_text = content[3 : end_match.start() + 3]
                body = content[end_match.end() + 3 :]

                try:
                    frontmatter = yaml.safe_load(frontmatter_text)
                except yaml.YAMLError as e:
                    raise ValueError(f"Invalid YAML frontmatter: {e}")

                if not isinstance(frontmatter, dict):
                    raise ValueError("Frontmatter must be a YAML mapping")

                return frontmatter, body

        # Fallback: Parse markdown-style metadata
        # Format: **Key**: Value or **Key:** Value
        frontmatter = {}
        body_lines = []
        in_header = True

        for line in content.split("\n"):
            if in_header:
                # Check for markdown metadata pattern
                md_match = re.match(r"\*\*([^*]+)\*\*:?\s*(.+)", line)
                if md_match:
                    key = md_match.group(1).strip().lower().replace(" ", "_")
                    value = md_match.group(2).strip()
                    frontmatter[key] = value
                elif line.startswith("# "):
                    # Title line - extract id from it if possible
                    title = line[2:].strip()
                    frontmatter["title"] = title
                    # Try to extract ID from title like "REQ-XXX: Title" or "# Title"
                    id_match = re.match(r"(REQ-[A-Z0-9-]+|[A-Z]+-\d+)", title)
                    if id_match:
                        frontmatter["id"] = id_match.group(1)
                elif line.strip() == "" or line.startswith("##"):
                    # End of header section
                    in_header = False
                    body_lines.append(line)
            else:
                body_lines.append(line)

        body = "\n".join(body_lines)

        # Generate missing required fields for requirements/designs
        if "id" not in frontmatter:
            # Use feature as ID fallback
            if "feature" in frontmatter:
                frontmatter["id"] = frontmatter["feature"]
            # Or generate from title
            elif "title" in frontmatter:
                # Convert title to ID-like format
                title_id = frontmatter["title"].lower().replace(" ", "-")
                title_id = re.sub(r"[^a-z0-9-]", "", title_id)
                frontmatter["id"] = title_id

        if "status" not in frontmatter:
            # Normalize status values
            status = frontmatter.get("status", "draft")
            if isinstance(status, str):
                frontmatter["status"] = status.lower()
            else:
                frontmatter["status"] = "draft"

        if "created" not in frontmatter:
            # Parse from markdown if present
            created_str = frontmatter.pop("created_date", None) or frontmatter.get(
                "created"
            )
            if created_str:
                try:
                    frontmatter["created"] = (
                        date.fromisoformat(created_str)
                        if isinstance(created_str, str)
                        else created_str
                    )
                except (ValueError, TypeError):
                    frontmatter["created"] = date.today()
            else:
                frontmatter["created"] = date.today()

        if "updated" not in frontmatter:
            frontmatter["updated"] = frontmatter.get("created", date.today())

        return frontmatter, body

    def _parse_date(self, value) -> date:
        """Parse date from various formats."""
        if isinstance(value, date):
            return value
        if isinstance(value, str):
            return date.fromisoformat(value)
        raise ValueError(f"Cannot parse date: {value}")

    def _extract_description(self, body: str) -> str:
        """Extract description section from markdown body."""
        # Look for ## Description, ## Objective, or ## Summary section
        match = re.search(
            r"##\s+(?:Description|Objective|Summary)\s*\n(.*?)(?=\n##|\n---|\Z)",
            body,
            re.DOTALL | re.IGNORECASE,
        )
        if match:
            return match.group(1).strip()
        return ""

    def _extract_full_body(self, body: str) -> str:
        """Extract the full markdown body (everything after the title).

        This preserves all sections (Summary, Acceptance Criteria, Technical Details, etc.)
        for rich context in AI-assisted task execution.
        """
        # Remove the main title (# TKT-XXX: Title) if present
        lines = body.strip().split("\n")
        if lines and lines[0].startswith("# "):
            lines = lines[1:]
        return "\n".join(lines).strip()

    def _extract_section(self, body: str, section_name: str) -> str:
        """Extract a named section from markdown body."""
        pattern = rf"##\s+{re.escape(section_name)}\s*\n(.*?)(?=\n##|\n---|\Z)"
        match = re.search(pattern, body, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_acceptance_criteria(self, body: str) -> list[AcceptanceCriterion]:
        """Extract acceptance criteria checkboxes from markdown body."""
        criteria = []
        # Look for checkbox patterns: - [ ] text or - [x] text
        pattern = r"- \[([ xX])\] (.+?)(?=\n|$)"
        matches = re.findall(pattern, body)
        for check, text in matches:
            criteria.append(
                AcceptanceCriterion(text=text.strip(), completed=check.lower() == "x")
            )
        return criteria

    # ========================================================================
    # Requirement Parsing
    # ========================================================================

    def parse_requirement(self, file_path: Path) -> ParsedRequirement:
        """Parse a requirement markdown file.

        Args:
            file_path: Path to requirement .md file

        Returns:
            ParsedRequirement instance

        Raises:
            ValueError: If file is missing required fields or has invalid format
        """
        content = file_path.read_text()
        frontmatter, body = self._parse_frontmatter(content)

        # Required fields
        required = ["id", "title", "status", "created", "updated"]
        for field_name in required:
            if field_name not in frontmatter:
                raise ValueError(f"Missing required field: {field_name}")

        # Extract EARS-style requirement from body
        condition = self._extract_section(body, "Condition") or self._extract_section(
            body, "When"
        )
        action = self._extract_section(body, "Action") or self._extract_section(
            body, "The System Shall"
        )

        # If not in sections, try to parse from structured format
        if not condition and not action:
            # Look for WHEN...THE SYSTEM SHALL pattern
            ears_match = re.search(
                r"WHEN\s+(.+?)\s+THE SYSTEM SHALL\s+(.+?)(?=\n\n|\Z)",
                body,
                re.DOTALL | re.IGNORECASE,
            )
            if ears_match:
                condition = ears_match.group(1).strip()
                action = ears_match.group(2).strip()

        return ParsedRequirement(
            id=frontmatter["id"],
            title=frontmatter["title"],
            status=frontmatter["status"],
            created=self._parse_date(frontmatter["created"]),
            updated=self._parse_date(frontmatter["updated"]),
            category=frontmatter.get("category", "functional"),
            priority=frontmatter.get("priority", "MEDIUM"),
            condition=condition,
            action=action,
            rationale=self._extract_section(body, "Rationale"),
            acceptance_criteria=self._extract_acceptance_criteria(body),
            linked_tickets=frontmatter.get("tickets", []) or [],
            linked_design=frontmatter.get("design_ref"),
            file_path=str(file_path),
        )

    # ========================================================================
    # Design Parsing
    # ========================================================================

    def parse_design(self, file_path: Path) -> ParsedDesign:
        """Parse a design markdown file.

        Args:
            file_path: Path to design .md file

        Returns:
            ParsedDesign instance

        Raises:
            ValueError: If file is missing required fields or has invalid format
        """
        content = file_path.read_text()
        frontmatter, body = self._parse_frontmatter(content)

        # Required fields
        required = ["id", "title", "status", "created", "updated"]
        for field_name in required:
            if field_name not in frontmatter:
                raise ValueError(f"Missing required field: {field_name}")

        # Parse API endpoints from frontmatter or body
        api_endpoints = []
        api_data = frontmatter.get("api_endpoints", []) or []
        for ep in api_data:
            if isinstance(ep, dict):
                api_endpoints.append(
                    ApiEndpoint(
                        method=ep.get("method", "GET"),
                        path=ep.get("path", ""),
                        description=ep.get("description", ""),
                        request_body=ep.get("request_body"),
                        response=ep.get("response"),
                    )
                )

        # Parse data models from frontmatter
        data_models = []
        models_data = frontmatter.get("data_models", []) or []
        for model in models_data:
            if isinstance(model, dict):
                data_models.append(
                    DataModel(
                        name=model.get("name", ""),
                        description=model.get("description", ""),
                        fields=model.get("fields", {}),
                        relationships=model.get("relationships", []),
                    )
                )

        return ParsedDesign(
            id=frontmatter["id"],
            title=frontmatter["title"],
            status=frontmatter["status"],
            created=self._parse_date(frontmatter["created"]),
            updated=self._parse_date(frontmatter["updated"]),
            feature=frontmatter.get("feature", ""),
            requirements=frontmatter.get("requirements", []) or [],
            architecture=self._extract_section(body, "Architecture Overview")
            or self._extract_section(body, "Architecture"),
            data_models=data_models,
            api_endpoints=api_endpoints,
            components=frontmatter.get("components", []) or [],
            error_handling=self._extract_section(body, "Error Handling"),
            security_considerations=self._extract_section(body, "Security"),
            implementation_notes=self._extract_section(body, "Implementation Notes")
            or self._extract_section(body, "Notes"),
            file_path=str(file_path),
        )

    # ========================================================================
    # Ticket Parsing
    # ========================================================================

    def parse_ticket(self, file_path: Path) -> ParsedTicket:
        """Parse a ticket markdown file.

        Args:
            file_path: Path to ticket .md file

        Returns:
            ParsedTicket instance

        Raises:
            ValueError: If file is missing required fields or has invalid format
        """
        content = file_path.read_text()
        frontmatter, body = self._parse_frontmatter(content)

        # Required fields
        required = [
            "id",
            "title",
            "status",
            "priority",
            "estimate",
            "created",
            "updated",
        ]
        for field in required:
            if field not in frontmatter:
                raise ValueError(f"Missing required field: {field}")

        # Parse dependencies
        deps_data = frontmatter.get("dependencies", {})
        dependencies = TicketDependencies(
            blocked_by=deps_data.get("blocked_by", []) or [],
            blocks=deps_data.get("blocks", []) or [],
            related=deps_data.get("related", []) or [],
        )

        return ParsedTicket(
            id=frontmatter["id"],
            title=frontmatter["title"],
            status=frontmatter["status"],
            priority=frontmatter["priority"],
            estimate=frontmatter["estimate"],
            created=self._parse_date(frontmatter["created"]),
            updated=self._parse_date(frontmatter["updated"]),
            feature=frontmatter.get("feature"),
            requirements=frontmatter.get("requirements", []) or [],
            design_ref=frontmatter.get("design_ref"),
            tasks=frontmatter.get("tasks", []) or [],
            dependencies=dependencies,
            description=self._extract_description(body),
            full_body=self._extract_full_body(body),
            file_path=str(file_path),
        )

    def parse_task(self, file_path: Path) -> ParsedTask:
        """Parse a task markdown file.

        Args:
            file_path: Path to task .md file

        Returns:
            ParsedTask instance

        Raises:
            ValueError: If file is missing required fields or has invalid format
        """
        content = file_path.read_text()
        frontmatter, body = self._parse_frontmatter(content)

        # Required fields
        required = ["id", "title", "status", "parent_ticket", "estimate", "created"]
        for field in required:
            if field not in frontmatter:
                raise ValueError(f"Missing required field: {field}")

        # Parse dependencies
        deps_data = frontmatter.get("dependencies", {})
        dependencies = TaskDependencies(
            depends_on=deps_data.get("depends_on", []) or [],
            blocks=deps_data.get("blocks", []) or [],
        )

        return ParsedTask(
            id=frontmatter["id"],
            title=frontmatter["title"],
            status=frontmatter["status"],
            parent_ticket=frontmatter["parent_ticket"],
            estimate=frontmatter["estimate"],
            created=self._parse_date(frontmatter["created"]),
            assignee=frontmatter.get("assignee"),
            dependencies=dependencies,
            objective=self._extract_description(body),
            full_body=self._extract_full_body(body),
            file_path=str(file_path),
        )

    def parse_all(self) -> ParseResult:
        """Parse all spec files (requirements, designs, tickets, tasks).

        Returns:
            ParseResult with all specs and any parse errors
        """
        result = ParseResult()

        # Parse requirements
        requirements_dir = self.omoi_dir / "requirements"
        if requirements_dir.exists():
            for md_file in sorted(requirements_dir.glob("*.md")):
                # Skip template files
                if "template" in md_file.name.lower():
                    continue
                try:
                    req = self.parse_requirement(md_file)
                    result.requirements.append(req)
                except ValueError as e:
                    result.errors.append(
                        ValidationError(
                            error_type="parse_error",
                            message=str(e),
                            source_id=md_file.name,
                        )
                    )

        # Parse designs
        designs_dir = self.omoi_dir / "designs"
        if designs_dir.exists():
            for md_file in sorted(designs_dir.glob("*.md")):
                # Skip template files
                if "template" in md_file.name.lower():
                    continue
                try:
                    design = self.parse_design(md_file)
                    result.designs.append(design)
                except ValueError as e:
                    result.errors.append(
                        ValidationError(
                            error_type="parse_error",
                            message=str(e),
                            source_id=md_file.name,
                        )
                    )

        # Parse tickets
        tickets_dir = self.omoi_dir / "tickets"
        if tickets_dir.exists():
            for md_file in sorted(tickets_dir.glob("*.md")):
                try:
                    ticket = self.parse_ticket(md_file)
                    result.tickets.append(ticket)
                except ValueError as e:
                    result.errors.append(
                        ValidationError(
                            error_type="parse_error",
                            message=str(e),
                            source_id=md_file.name,
                        )
                    )

        # Parse tasks
        tasks_dir = self.omoi_dir / "tasks"
        if tasks_dir.exists():
            for md_file in sorted(tasks_dir.glob("*.md")):
                try:
                    task = self.parse_task(md_file)
                    result.tasks.append(task)
                except ValueError as e:
                    result.errors.append(
                        ValidationError(
                            error_type="parse_error",
                            message=str(e),
                            source_id=md_file.name,
                        )
                    )

        return result

    def list_requirements(self) -> list[ParsedRequirement]:
        """List all parsed requirements."""
        return self.parse_all().requirements

    def list_designs(self) -> list[ParsedDesign]:
        """List all parsed designs."""
        return self.parse_all().designs

    def list_tickets(self) -> list[ParsedTicket]:
        """List all parsed tickets."""
        return self.parse_all().tickets

    def list_tasks(self) -> list[ParsedTask]:
        """List all parsed tasks."""
        return self.parse_all().tasks

    def get_requirement(self, req_id: str) -> Optional[ParsedRequirement]:
        """Get a specific requirement by ID."""
        return self.parse_all().get_requirement(req_id)

    def get_design(self, design_id: str) -> Optional[ParsedDesign]:
        """Get a specific design by ID."""
        return self.parse_all().get_design(design_id)

    def get_ticket(self, ticket_id: str) -> Optional[ParsedTicket]:
        """Get a specific ticket by ID."""
        return self.parse_all().get_ticket(ticket_id)

    def get_task(self, task_id: str) -> Optional[ParsedTask]:
        """Get a specific task by ID."""
        return self.parse_all().get_task(task_id)


if __name__ == "__main__":
    # Quick test
    parser = SpecParser()
    result = parser.parse_all()

    print(f"Found:")
    print(f"  {len(result.requirements)} requirements")
    print(f"  {len(result.designs)} designs")
    print(f"  {len(result.tickets)} tickets")
    print(f"  {len(result.tasks)} tasks")

    if result.errors:
        print(f"\nParse Errors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  {error}")

    # Show traceability stats
    if result.requirements or result.designs or result.tickets:
        stats = result.get_traceability_stats()
        print(f"\nTraceability Coverage:")
        if result.requirements:
            print(
                f"  Requirements: {stats['requirements']['linked']}/{stats['requirements']['total']} linked ({stats['requirements']['coverage']:.1f}%)"
            )
        if result.designs:
            print(
                f"  Designs: {stats['designs']['linked']}/{stats['designs']['total']} linked ({stats['designs']['coverage']:.1f}%)"
            )
        if result.tickets:
            print(
                f"  Tickets: {stats['tickets']['linked']}/{stats['tickets']['total']} linked ({stats['tickets']['coverage']:.1f}%)"
            )
        print(f"  Tasks: {stats['tasks']['done']}/{stats['tasks']['total']} done")
