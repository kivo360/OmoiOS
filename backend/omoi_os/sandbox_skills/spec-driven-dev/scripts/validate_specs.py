#!/usr/bin/env python3
"""
Validate spec documents for completeness and consistency.

Uses YAML frontmatter validation (consistent with parse_specs.py).

Usage:
    python validate_specs.py [--path PATH]
    python validate_specs.py --requirements
    python validate_specs.py --designs
    python validate_specs.py --tickets
    python validate_specs.py --tasks

Examples:
    python validate_specs.py                        # Validate all
    python validate_specs.py --requirements         # Only requirements
    python validate_specs.py --path .omoi_os        # Custom path
"""

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ValidationResult:
    """Result of validating a document."""
    file: Path
    doc_type: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def get_project_root() -> Path:
    """Find project root by looking for .omoi_os or common markers."""
    current = Path.cwd()

    for parent in [current] + list(current.parents):
        if (parent / ".omoi_os").exists():
            return parent
        if (parent / ".git").exists():
            return parent

    return current


def parse_frontmatter(content: str) -> tuple[dict | None, str]:
    """Extract YAML frontmatter and markdown body from content.

    Returns:
        Tuple of (frontmatter dict or None if missing, remaining markdown body)
    """
    if not content.startswith("---"):
        return None, content

    # Find end of frontmatter
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return None, content

    frontmatter_text = content[3 : end_match.start() + 3]
    body = content[end_match.end() + 3 :]

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
    except yaml.YAMLError:
        return None, content

    if not isinstance(frontmatter, dict):
        return None, content

    return frontmatter, body


def validate_requirements(file_path: Path) -> ValidationResult:
    """Validate a requirements document."""
    result = ValidationResult(file=file_path, doc_type="requirements")
    content = file_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    # Check for required sections
    required_sections = [
        "## Document Overview",
        "## Revision History",
    ]

    for section in required_sections:
        if section not in content:
            result.warnings.append(f"Missing section: {section}")

    # Check for REQ-XXX-YYY-NNN format
    req_pattern = r"REQ-[A-Z]+-[A-Z]+-\d{3}"
    reqs = re.findall(req_pattern, content)

    if not reqs:
        result.errors.append("No requirements found (expected REQ-XXX-YYY-NNN format)")

    # Check for normative language
    normative = ["SHALL", "MUST", "SHOULD", "MAY"]
    has_normative = any(word in content for word in normative)

    if not has_normative:
        result.warnings.append("No normative language found (SHALL/MUST/SHOULD/MAY)")

    # Check for status - support both YAML frontmatter and markdown
    if frontmatter:
        if "status" not in frontmatter:
            result.warnings.append("Missing status field in frontmatter")
        if "created" not in frontmatter:
            result.warnings.append("Missing created field in frontmatter")
    else:
        # Fallback to old markdown style check
        if "**Status**:" not in content:
            result.warnings.append("Missing Status field (no frontmatter found)")
        if "**Created**:" not in content:
            result.warnings.append("Missing Created date (no frontmatter found)")

    return result


def validate_design(file_path: Path) -> ValidationResult:
    """Validate a design document."""
    result = ValidationResult(file=file_path, doc_type="design")
    content = file_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    # Check for required sections
    required_sections = [
        "## Architecture Overview",
        "## Revision History",
    ]

    for section in required_sections:
        if section not in content:
            result.warnings.append(f"Missing section: {section}")

    # Check for architecture diagram
    if "```mermaid" not in content:
        result.warnings.append("No Mermaid diagram found")

    # Check for component responsibilities
    if "Responsibilities" not in content:
        result.warnings.append("No component responsibilities documented")

    # Check for status - support both YAML frontmatter and markdown
    if frontmatter:
        if "status" not in frontmatter:
            result.warnings.append("Missing status field in frontmatter")
    else:
        if "**Status**:" not in content:
            result.warnings.append("Missing Status field (no frontmatter found)")

    # Check for related requirements link
    if "requirements" not in content.lower() and "Requirements" not in content:
        result.warnings.append("No link to requirements document")

    return result


def validate_ticket(file_path: Path) -> ValidationResult:
    """Validate a ticket document (YAML frontmatter format)."""
    result = ValidationResult(file=file_path, doc_type="ticket")
    content = file_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    if not frontmatter:
        result.errors.append("Missing YAML frontmatter")
        return result

    # Check for ticket ID in frontmatter
    if "id" not in frontmatter:
        result.errors.append("Missing 'id' field in frontmatter")
    elif not frontmatter["id"].startswith("TKT-"):
        result.errors.append(f"Invalid ticket ID format: {frontmatter['id']} (expected TKT-XXX)")

    # Check for required fields in frontmatter
    required_fields = {
        "id": "Ticket ID (e.g., TKT-001)",
        "title": "Ticket title",
        "status": "Status (backlog, in_progress, done, etc.)",
        "priority": "Priority (LOW, MEDIUM, HIGH, CRITICAL)",
        "estimate": "Estimate (XS, S, M, L, XL)",
        "created": "Created date",
        "updated": "Updated date",
    }

    for field_key, description in required_fields.items():
        if field_key not in frontmatter:
            result.errors.append(f"Missing required field: {field_key} ({description})")

    # Validate status value
    valid_statuses = ["backlog", "ready", "in_progress", "review", "done", "blocked"]
    if frontmatter.get("status") and frontmatter["status"] not in valid_statuses:
        result.warnings.append(f"Non-standard status: {frontmatter['status']} (expected one of: {', '.join(valid_statuses)})")

    # Validate priority value
    valid_priorities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    if frontmatter.get("priority") and frontmatter["priority"] not in valid_priorities:
        result.warnings.append(f"Non-standard priority: {frontmatter['priority']} (expected one of: {', '.join(valid_priorities)})")

    # Validate estimate value
    valid_estimates = ["XS", "S", "M", "L", "XL"]
    if frontmatter.get("estimate") and frontmatter["estimate"] not in valid_estimates:
        result.warnings.append(f"Non-standard estimate: {frontmatter['estimate']} (expected one of: {', '.join(valid_estimates)})")

    # Check for acceptance criteria in body
    if "## Acceptance Criteria" not in body:
        result.warnings.append("Missing Acceptance Criteria section in body")

    # Check for requirements traceability
    if not frontmatter.get("requirements"):
        result.warnings.append("No requirements linked (consider adding requirements field)")

    # Check for dependency structure
    deps = frontmatter.get("dependencies", {})
    if deps:
        expected_dep_fields = ["blocked_by", "blocks", "related"]
        for dep_field in expected_dep_fields:
            if dep_field not in deps:
                result.warnings.append(f"Missing dependencies.{dep_field} field")

    return result


def validate_task(file_path: Path) -> ValidationResult:
    """Validate a task document (YAML frontmatter format)."""
    result = ValidationResult(file=file_path, doc_type="task")
    content = file_path.read_text()
    frontmatter, body = parse_frontmatter(content)

    if not frontmatter:
        result.errors.append("Missing YAML frontmatter")
        return result

    # Check for task ID in frontmatter
    if "id" not in frontmatter:
        result.errors.append("Missing 'id' field in frontmatter")
    elif not frontmatter["id"].startswith("TSK-"):
        result.errors.append(f"Invalid task ID format: {frontmatter['id']} (expected TSK-XXX)")

    # Check for required fields in frontmatter
    required_fields = {
        "id": "Task ID (e.g., TSK-001)",
        "title": "Task title",
        "status": "Status (pending, in_progress, done, etc.)",
        "parent_ticket": "Parent ticket ID (e.g., TKT-001)",
        "estimate": "Estimate (XS, S, M, L, XL)",
        "created": "Created date",
    }

    for field_key, description in required_fields.items():
        if field_key not in frontmatter:
            result.errors.append(f"Missing required field: {field_key} ({description})")

    # Check parent ticket reference format
    if frontmatter.get("parent_ticket") and not frontmatter["parent_ticket"].startswith("TKT-"):
        result.errors.append(f"Invalid parent_ticket format: {frontmatter['parent_ticket']} (expected TKT-XXX)")

    # Validate status value
    valid_statuses = ["pending", "in_progress", "review", "done", "blocked"]
    if frontmatter.get("status") and frontmatter["status"] not in valid_statuses:
        result.warnings.append(f"Non-standard status: {frontmatter['status']} (expected one of: {', '.join(valid_statuses)})")

    # Validate estimate value
    valid_estimates = ["XS", "S", "M", "L", "XL"]
    if frontmatter.get("estimate") and frontmatter["estimate"] not in valid_estimates:
        result.warnings.append(f"Non-standard estimate: {frontmatter['estimate']} (expected one of: {', '.join(valid_estimates)})")

    # Check for objective/description in body
    if "## Objective" not in body and "## Description" not in body:
        result.warnings.append("Missing Objective/Description section in body")

    # Check for acceptance criteria in body
    if "## Acceptance Criteria" not in body:
        result.warnings.append("Missing Acceptance Criteria section in body")

    # Check for dependency structure
    deps = frontmatter.get("dependencies", {})
    if deps:
        expected_dep_fields = ["depends_on", "blocks"]
        for dep_field in expected_dep_fields:
            if dep_field not in deps:
                result.warnings.append(f"Missing dependencies.{dep_field} field")

    return result


def validate_all(omoi_path: Path, doc_types: list[str]) -> list[ValidationResult]:
    """Validate all documents of specified types."""
    results = []

    validators = {
        "requirements": (omoi_path / "requirements", validate_requirements),
        "designs": (omoi_path / "designs", validate_design),
        "tickets": (omoi_path / "tickets", validate_ticket),
        "tasks": (omoi_path / "tasks", validate_task),
    }

    for doc_type in doc_types:
        if doc_type not in validators:
            continue

        directory, validator = validators[doc_type]

        if not directory.exists():
            continue

        for md_file in directory.glob("*.md"):
            result = validator(md_file)
            results.append(result)

    return results


def print_results(results: list[ValidationResult]) -> int:
    """Print validation results and return exit code."""
    if not results:
        print("No documents found to validate")
        return 0

    total_errors = 0
    total_warnings = 0

    for result in results:
        if result.errors or result.warnings:
            print(f"\n{result.doc_type}: {result.file.name}")

            for error in result.errors:
                print(f"  ERROR: {error}")
                total_errors += 1

            for warning in result.warnings:
                print(f"  WARNING: {warning}")
                total_warnings += 1

    print(f"\n{'=' * 40}")
    print(f"Total: {len(results)} documents")
    print(f"Errors: {total_errors}")
    print(f"Warnings: {total_warnings}")

    valid_count = sum(1 for r in results if r.is_valid)
    print(f"Valid: {valid_count}/{len(results)}")

    return 1 if total_errors > 0 else 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate spec documents for completeness"
    )
    parser.add_argument(
        "--path",
        default=None,
        help="Path to .omoi_os directory (auto-detected if not specified)"
    )
    parser.add_argument(
        "--requirements",
        action="store_true",
        help="Validate only requirements"
    )
    parser.add_argument(
        "--designs",
        action="store_true",
        help="Validate only designs"
    )
    parser.add_argument(
        "--tickets",
        action="store_true",
        help="Validate only tickets"
    )
    parser.add_argument(
        "--tasks",
        action="store_true",
        help="Validate only tasks"
    )

    args = parser.parse_args()

    # Determine path
    if args.path:
        omoi_path = Path(args.path)
    else:
        root = get_project_root()
        omoi_path = root / ".omoi_os"

    if not omoi_path.exists():
        print(f"Error: {omoi_path} does not exist")
        sys.exit(1)

    # Determine which types to validate
    doc_types = []
    if args.requirements:
        doc_types.append("requirements")
    if args.designs:
        doc_types.append("designs")
    if args.tickets:
        doc_types.append("tickets")
    if args.tasks:
        doc_types.append("tasks")

    # Default to all if none specified
    if not doc_types:
        doc_types = ["requirements", "designs", "tickets", "tasks"]

    # Run validation
    results = validate_all(omoi_path, doc_types)
    exit_code = print_results(results)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
