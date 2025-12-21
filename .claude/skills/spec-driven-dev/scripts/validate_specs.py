#!/usr/bin/env python3
"""
Validate spec documents for completeness and consistency.

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


def validate_requirements(file_path: Path) -> ValidationResult:
    """Validate a requirements document."""
    result = ValidationResult(file=file_path, doc_type="requirements")
    content = file_path.read_text()

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

    # Check for status
    if "**Status**:" not in content:
        result.warnings.append("Missing Status field")

    # Check for created date
    if "**Created**:" not in content:
        result.warnings.append("Missing Created date")

    return result


def validate_design(file_path: Path) -> ValidationResult:
    """Validate a design document."""
    result = ValidationResult(file=file_path, doc_type="design")
    content = file_path.read_text()

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

    # Check for status
    if "**Status**:" not in content:
        result.warnings.append("Missing Status field")

    # Check for related requirements link
    if "requirements" not in content.lower() and "Requirements" not in content:
        result.warnings.append("No link to requirements document")

    return result


def validate_ticket(file_path: Path) -> ValidationResult:
    """Validate a ticket document."""
    result = ValidationResult(file=file_path, doc_type="ticket")
    content = file_path.read_text()

    # Check for TKT-XXX format
    tkt_pattern = r"TKT-(?:[A-Z]+-)?(\d{3})"
    tkts = re.findall(tkt_pattern, content)

    if not tkts:
        result.errors.append("No ticket ID found (expected TKT-XXX format)")

    # Check for required fields
    required_fields = [
        "**Status**:",
        "**Priority**:",
    ]

    for field_name in required_fields:
        if field_name not in content:
            result.errors.append(f"Missing required field: {field_name}")

    # Check for acceptance criteria
    if "## Acceptance Criteria" not in content:
        result.warnings.append("Missing Acceptance Criteria section")

    # Check for traceability
    if "## Traceability" not in content and "**Requirements**:" not in content:
        result.warnings.append("Missing traceability to requirements")

    return result


def validate_task(file_path: Path) -> ValidationResult:
    """Validate a task document."""
    result = ValidationResult(file=file_path, doc_type="task")
    content = file_path.read_text()

    # Check for TSK-XXX format
    tsk_pattern = r"TSK-(?:[A-Z]+-)?(\d{3})"
    tsks = re.findall(tsk_pattern, content)

    if not tsks:
        result.errors.append("No task ID found (expected TSK-XXX format)")

    # Check for parent ticket reference
    if "**Parent Ticket**:" not in content and "TKT-" not in content:
        result.errors.append("Missing parent ticket reference")

    # Check for required fields
    required_fields = [
        "**Status**:",
    ]

    for field_name in required_fields:
        if field_name not in content:
            result.errors.append(f"Missing required field: {field_name}")

    # Check for deliverables
    if "## Deliverables" not in content:
        result.warnings.append("Missing Deliverables section")

    # Check for acceptance criteria
    if "## Acceptance Criteria" not in content:
        result.warnings.append("Missing Acceptance Criteria section")

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
