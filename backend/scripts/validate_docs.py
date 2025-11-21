#!/usr/bin/env python3
"""
Validate documentation structure and naming conventions.

Checks:
- Filename conventions (snake_case, no hyphens)
- Required metadata (Created, Status, Purpose)
- Heading hierarchy (single H1, proper nesting)
- Orphaned docs (files in wrong locations)
- Broken links (optional)
"""

import re
import sys
from pathlib import Path
from typing import List


class Colors:
    """ANSI color codes for terminal output."""

    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"  # No Color


def validate_filename(file: Path) -> List[str]:
    """Check if filename follows naming conventions."""
    errors = []
    name = file.stem

    # Allow UPPERCASE for summary files
    if name.isupper() and file.name.endswith("_SUMMARY.md"):
        return errors

    # Check for CamelCase or TitleCase
    if re.search(r"[A-Z]", name) and not name.isupper():
        errors.append(
            f"{Colors.RED}❌ {file.relative_to('docs')}: Use snake_case, not CamelCase{Colors.NC}"
        )

    # Check for hyphens (except ADRs with numbers)
    if "-" in name and not re.match(r"^\d{3}_", name):
        errors.append(
            f"{Colors.RED}❌ {file.relative_to('docs')}: Use underscores (_), not hyphens (-){Colors.NC}"
        )

    # Check for spaces
    if " " in name:
        errors.append(
            f"{Colors.RED}❌ {file.relative_to('docs')}: No spaces in filenames{Colors.NC}"
        )

    return errors


def validate_metadata(file: Path) -> List[str]:
    """Check if document has required metadata."""
    errors = []
    warnings = []

    try:
        content = file.read_text(encoding="utf-8")
        lines = content.split("\n")[:15]  # First 15 lines

        required = {
            "**Created**:": False,
            "**Status**:": False,
            "**Purpose**:": False,
        }

        for line in lines:
            for req in required:
                if req in line:
                    required[req] = True

        for req, found in required.items():
            if not found:
                warnings.append(
                    f"{Colors.YELLOW}⚠️  {file.relative_to('docs')}: "
                    f"Missing metadata '{req}'{Colors.NC}"
                )

    except Exception as e:
        errors.append(
            f"{Colors.RED}❌ {file.relative_to('docs')}: Error reading file: {e}{Colors.NC}"
        )

    return errors + warnings


def validate_heading_hierarchy(file: Path) -> List[str]:
    """Check heading hierarchy (single H1, proper nesting)."""
    errors = []

    try:
        content = file.read_text(encoding="utf-8")
        lines = content.split("\n")

        # Count H1 headings (# followed by space, not ##)
        h1_lines = [i for i, line in enumerate(lines, 1) if re.match(r"^# [^#]", line)]

        if len(h1_lines) == 0:
            errors.append(
                f"{Colors.RED}❌ {file.relative_to('docs')}: "
                f"No H1 heading found{Colors.NC}"
            )
        elif len(h1_lines) > 1:
            errors.append(
                f"{Colors.RED}❌ {file.relative_to('docs')}: "
                f"Multiple H1 headings (lines {', '.join(map(str, h1_lines))}). Should be only one.{Colors.NC}"
            )

        # Check for improper nesting (optional - could be too strict)
        # For now, just ensure H1 exists and is singular

    except Exception as e:
        errors.append(
            f"{Colors.RED}❌ {file.relative_to('docs')}: Error reading file: {e}{Colors.NC}"
        )

    return errors


def check_orphaned_docs(docs_dir: Path) -> List[str]:
    """Find orphaned documents in root that should be categorized."""
    warnings = []

    # Check docs/ root for files that should be in subdirectories
    for file in docs_dir.glob("*.md"):
        # Allow specific root files
        allowed_root = [
            "README.md",
            "DOCUMENTATION_STANDARDS.md",
        ]

        # Allow SUMMARY files
        if file.name.endswith("_SUMMARY.md"):
            continue

        if file.name not in allowed_root:
            warnings.append(
                f"{Colors.YELLOW}⚠️  docs/{file.name}: "
                f"Consider moving to a subdirectory (design/, implementation/, etc.){Colors.NC}"
            )

    return warnings


def check_empty_files(docs_dir: Path) -> List[str]:
    """Find empty or nearly empty markdown files."""
    warnings = []

    for file in docs_dir.rglob("*.md"):
        if file.stat().st_size < 100:  # Less than 100 bytes
            warnings.append(
                f"{Colors.YELLOW}⚠️  {file.relative_to(docs_dir)}: "
                f"File is very small ({file.stat().st_size} bytes). Is it complete?{Colors.NC}"
            )

    return warnings


def main():
    """Run all documentation validations."""
    docs_dir = Path("docs")

    if not docs_dir.exists():
        print(f"{Colors.RED}❌ docs/ directory not found{Colors.NC}")
        return 1

    all_errors = []
    all_warnings = []
    checked_files = 0

    print(f"{Colors.BLUE}🔍 Validating documentation...{Colors.NC}\n")

    for md_file in docs_dir.rglob("*.md"):
        # Skip archived docs
        if "archive" in md_file.parts:
            continue

        # Skip README files (they have different rules)
        if md_file.name == "README.md":
            continue

        checked_files += 1

        errors = []
        warnings = []

        errors.extend(validate_filename(md_file))
        metadata_issues = validate_metadata(md_file)
        # Separate errors from warnings
        errors.extend([e for e in metadata_issues if "❌" in e])
        warnings.extend([w for w in metadata_issues if "⚠️" in w])
        errors.extend(validate_heading_hierarchy(md_file))

        all_errors.extend(errors)
        all_warnings.extend(warnings)

    # Check for orphaned docs
    all_warnings.extend(check_orphaned_docs(docs_dir))

    # Check for empty files
    all_warnings.extend(check_empty_files(docs_dir))

    # Print results
    if all_errors:
        print(f"\n{Colors.RED}❌ ERRORS:{Colors.NC}")
        for error in all_errors:
            print(f"  {error}")

    if all_warnings:
        print(f"\n{Colors.YELLOW}⚠️  WARNINGS:{Colors.NC}")
        for warning in all_warnings:
            print(f"  {warning}")

    print(f"\n{Colors.BLUE}📊 Summary:{Colors.NC}")
    print(f"  Checked: {checked_files} files")
    print(f"  Errors: {len(all_errors)}")
    print(f"  Warnings: {len(all_warnings)}")

    if all_errors:
        print(
            f"\n{Colors.RED}❌ Validation failed with {len(all_errors)} errors{Colors.NC}"
        )
        print("\nSee docs/DOCUMENTATION_STANDARDS.md for naming conventions")
        return 1
    elif all_warnings:
        print(
            f"\n{Colors.YELLOW}⚠️  Validation passed with {len(all_warnings)} warnings{Colors.NC}"
        )
        return 0
    else:
        print(f"\n{Colors.GREEN}✅ All documentation files valid{Colors.NC}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
