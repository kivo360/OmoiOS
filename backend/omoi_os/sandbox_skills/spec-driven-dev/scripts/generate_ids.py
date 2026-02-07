#!/usr/bin/env python3
"""
Generate next ticket or task IDs.

Usage:
    python generate_ids.py ticket [--prefix PREFIX]
    python generate_ids.py task [--prefix PREFIX]
    python generate_ids.py --list

Examples:
    python generate_ids.py ticket                    # TKT-001
    python generate_ids.py ticket --prefix COLLAB    # TKT-COLLAB-001
    python generate_ids.py task                      # TSK-001
    python generate_ids.py --list                    # Show all existing IDs
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional


def get_project_root() -> Path:
    """Find project root by looking for .omoi_os or common markers."""
    current = Path.cwd()

    for parent in [current] + list(current.parents):
        if (parent / ".omoi_os").exists():
            return parent
        if (parent / ".git").exists():
            return parent

    return current


def extract_ids(directory: Path, pattern: str) -> list[tuple[str, int]]:
    """Extract IDs from markdown files in a directory."""
    ids = []

    if not directory.exists():
        return ids

    # Pattern like TKT-001 or TKT-PREFIX-001
    id_regex = re.compile(rf"({pattern}(?:-[A-Z]+)?-(\d+))")

    for md_file in directory.glob("*.md"):
        content = md_file.read_text()
        matches = id_regex.findall(content)
        for full_id, num in matches:
            ids.append((full_id, int(num)))

    # Also check filenames
    for md_file in directory.glob("*.md"):
        match = id_regex.match(md_file.stem.upper())
        if match:
            ids.append((match.group(1), int(match.group(2))))

    return ids


def get_next_id(id_type: str, prefix: Optional[str] = None) -> str:
    """Generate the next ID for tickets or tasks."""
    root = get_project_root()
    omoi_dir = root / ".omoi_os"

    if id_type == "ticket":
        directory = omoi_dir / "tickets"
        base = "TKT"
    else:
        directory = omoi_dir / "tasks"
        base = "TSK"

    # Get existing IDs
    existing = extract_ids(directory, base)

    # Filter by prefix if specified
    if prefix:
        prefix = prefix.upper()
        full_base = f"{base}-{prefix}"
        relevant = [(id_, num) for id_, num in existing if id_.startswith(full_base)]
    else:
        full_base = base
        # Get IDs without custom prefix
        relevant = [
            (id_, num) for id_, num in existing if re.match(rf"{base}-\d+$", id_)
        ]

    # Find next number
    if relevant:
        max_num = max(num for _, num in relevant)
        next_num = max_num + 1
    else:
        next_num = 1

    # Format ID
    if prefix:
        new_id = f"{base}-{prefix}-{next_num:03d}"
    else:
        new_id = f"{base}-{next_num:03d}"

    return new_id


def list_all_ids() -> None:
    """List all existing ticket and task IDs."""
    root = get_project_root()
    omoi_dir = root / ".omoi_os"

    print("Existing IDs:")
    print("-" * 40)

    # Tickets
    tickets_dir = omoi_dir / "tickets"
    ticket_ids = extract_ids(tickets_dir, "TKT")
    if ticket_ids:
        print("\nTickets:")
        for id_, _ in sorted(set(ticket_ids)):
            print(f"  {id_}")
    else:
        print("\nTickets: None")

    # Tasks
    tasks_dir = omoi_dir / "tasks"
    task_ids = extract_ids(tasks_dir, "TSK")
    if task_ids:
        print("\nTasks:")
        for id_, _ in sorted(set(task_ids)):
            print(f"  {id_}")
    else:
        print("\nTasks: None")


def main():
    parser = argparse.ArgumentParser(description="Generate next ticket or task IDs")
    parser.add_argument(
        "type", nargs="?", choices=["ticket", "task"], help="Type of ID to generate"
    )
    parser.add_argument(
        "--prefix", help="Optional prefix for the ID (e.g., COLLAB for TKT-COLLAB-001)"
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_ids", help="List all existing IDs"
    )

    args = parser.parse_args()

    if args.list_ids:
        list_all_ids()
        return

    if not args.type:
        parser.print_help()
        sys.exit(1)

    next_id = get_next_id(args.type, args.prefix)
    print(next_id)


if __name__ == "__main__":
    main()
