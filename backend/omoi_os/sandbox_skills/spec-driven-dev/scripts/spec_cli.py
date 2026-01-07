#!/usr/bin/env python3
"""
Unified CLI for spec-driven development.

Parse, validate, and visualize tickets and tasks from .omoi_os/ directory.

Usage:
    # Show all tickets and tasks
    uv run python spec_cli.py show all

    # Show only tickets
    uv run python spec_cli.py show tickets

    # Show only tasks
    uv run python spec_cli.py show tasks

    # Show dependency graph
    uv run python spec_cli.py show graph

    # Show ready tasks (no blocking dependencies)
    uv run python spec_cli.py show ready

    # Validate specs (check for circular dependencies, missing refs)
    uv run python spec_cli.py validate

    # Export to JSON
    uv run python spec_cli.py export json

    # Sync to API (Phase 4)
    uv run python spec_cli.py sync push
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Optional

from models import ParseResult, ParsedTask, ParsedTicket, ValidationError
from parse_specs import SpecParser


# ============================================================================
# Validation (Phase 3)
# ============================================================================


def detect_circular_dependencies(result: ParseResult) -> list[ValidationError]:
    """Detect circular dependencies in task graph.

    Uses DFS to find cycles in the dependency graph.
    """
    errors = []

    # Build adjacency list for tasks
    task_deps = {t.id: t.dependencies.depends_on for t in result.tasks}

    # Track visited and recursion stack
    visited = set()
    rec_stack = set()
    path = []

    def dfs(task_id: str) -> Optional[list[str]]:
        """DFS to detect cycle, returns cycle path if found."""
        if task_id in rec_stack:
            # Found cycle - extract the cycle from path
            cycle_start = path.index(task_id)
            return path[cycle_start:] + [task_id]

        if task_id in visited:
            return None

        visited.add(task_id)
        rec_stack.add(task_id)
        path.append(task_id)

        for dep in task_deps.get(task_id, []):
            cycle = dfs(dep)
            if cycle:
                return cycle

        path.pop()
        rec_stack.remove(task_id)
        return None

    # Check each task as starting point
    for task in result.tasks:
        if task.id not in visited:
            cycle = dfs(task.id)
            if cycle:
                cycle_str = " -> ".join(cycle)
                errors.append(
                    ValidationError(
                        error_type="circular_dependency",
                        message=f"Circular dependency detected: {cycle_str}",
                        source_id=cycle[0],
                        target_id=cycle[-1],
                    )
                )
                # Reset for next search
                visited.clear()
                rec_stack.clear()
                path.clear()

    return errors


def validate_references(result: ParseResult) -> list[ValidationError]:
    """Validate that all referenced IDs exist."""
    errors = []

    # Get all known IDs
    ticket_ids = {t.id for t in result.tickets}
    task_ids = {t.id for t in result.tasks}

    # Check ticket dependencies
    for ticket in result.tickets:
        for dep_id in ticket.dependencies.blocked_by:
            if dep_id not in ticket_ids:
                errors.append(
                    ValidationError(
                        error_type="missing_reference",
                        message=f"blocked_by references unknown ticket: {dep_id}",
                        source_id=ticket.id,
                        target_id=dep_id,
                    )
                )
        for dep_id in ticket.dependencies.blocks:
            if dep_id not in ticket_ids:
                errors.append(
                    ValidationError(
                        error_type="missing_reference",
                        message=f"blocks references unknown ticket: {dep_id}",
                        source_id=ticket.id,
                        target_id=dep_id,
                    )
                )

    # Check task dependencies
    for task in result.tasks:
        # Check parent ticket exists
        if task.parent_ticket not in ticket_ids:
            errors.append(
                ValidationError(
                    error_type="missing_reference",
                    message=f"parent_ticket references unknown ticket: {task.parent_ticket}",
                    source_id=task.id,
                    target_id=task.parent_ticket,
                )
            )

        for dep_id in task.dependencies.depends_on:
            if dep_id not in task_ids:
                errors.append(
                    ValidationError(
                        error_type="missing_reference",
                        message=f"depends_on references unknown task: {dep_id}",
                        source_id=task.id,
                        target_id=dep_id,
                    )
                )
        for dep_id in task.dependencies.blocks:
            if dep_id not in task_ids:
                errors.append(
                    ValidationError(
                        error_type="missing_reference",
                        message=f"blocks references unknown task: {dep_id}",
                        source_id=task.id,
                        target_id=dep_id,
                    )
                )

    return errors


def validate_specs(result: ParseResult) -> list[ValidationError]:
    """Run all validation checks."""
    errors = list(result.errors)  # Start with parse errors
    errors.extend(detect_circular_dependencies(result))
    errors.extend(validate_references(result))
    return errors


# ============================================================================
# Display Functions
# ============================================================================


def print_header(title: str, char: str = "=", width: int = 70):
    """Print a section header."""
    print(char * width)
    print(f" {title}")
    print(char * width)


def print_tickets(tickets: list[ParsedTicket]):
    """Print all tickets."""
    print_header(f"TICKETS ({len(tickets)} total)")
    print()

    for ticket in tickets:
        print(f"{ticket.id}: {ticket.title}")
        print(f"  Status: {ticket.status} | Priority: {ticket.priority} | Estimate: {ticket.estimate}")

        # Truncate description
        desc = ticket.description[:100] + "..." if len(ticket.description) > 100 else ticket.description
        desc = desc.replace("\n", " ")
        if desc:
            print(f"  Description: {desc}")

        if ticket.tasks:
            print(f"  Tasks: {', '.join(ticket.tasks)}")

        if ticket.dependencies.blocked_by:
            print(f"  Blocked By: {', '.join(ticket.dependencies.blocked_by)}")
        if ticket.dependencies.blocks:
            print(f"  Blocks: {', '.join(ticket.dependencies.blocks)}")

        print()


def print_tasks(tasks: list[ParsedTask], result: Optional[ParseResult] = None):
    """Print all tasks with cross-ticket dependency awareness."""
    print_header(f"TASKS ({len(tasks)} total)")
    print()

    for task in tasks:
        # Use ParseResult for cross-ticket blocking if available
        if result:
            is_blocked, reason = result.is_task_blocked(task)
        else:
            # Fallback to simple task-only blocking
            completed_tasks = {t.id for t in tasks if t.status == "done"}
            is_blocked = task.is_blocked(completed_tasks)
            reason = "blocked by task dependency" if is_blocked else ""

        status_indicator = f"[BLOCKED: {reason}] " if is_blocked else ""

        print(f"{status_indicator}{task.id}: {task.title}")
        print(f"  Parent: {task.parent_ticket} | Status: {task.status} | Estimate: {task.estimate}")

        # Truncate objective
        obj = task.objective[:100] + "..." if len(task.objective) > 100 else task.objective
        obj = obj.replace("\n", " ")
        if obj:
            print(f"  Objective: {obj}")

        if task.dependencies.depends_on:
            print(f"  Depends On: {', '.join(task.dependencies.depends_on)}")
        if task.dependencies.blocks:
            print(f"  Blocks: {', '.join(task.dependencies.blocks)}")

        print()


def print_dependency_graph(result: ParseResult):
    """Print ASCII dependency graph for tasks."""
    print_header("TASK DEPENDENCY GRAPH")
    print()

    # Build reverse dependency map (what blocks what)
    blocked_by: dict[str, list[str]] = defaultdict(list)
    for task in result.tasks:
        for dep in task.dependencies.depends_on:
            blocked_by[dep].append(task.id)

    # Get task title by ID
    task_titles = {t.id: t.title for t in result.tasks}

    # Find root tasks (no dependencies)
    root_tasks = [t for t in result.tasks if not t.dependencies.depends_on]

    def print_tree(task_id: str, prefix: str = "", is_last: bool = True):
        """Recursively print task tree."""
        connector = "└─> " if is_last else "├─> "
        title = task_titles.get(task_id, "Unknown")
        title_short = title[:40] + "..." if len(title) > 40 else title

        print(f"{prefix}{connector}{task_id} ({title_short})")

        children = blocked_by.get(task_id, [])
        for i, child in enumerate(children):
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_tree(child, new_prefix, i == len(children) - 1)

    for i, task in enumerate(root_tasks):
        if i > 0:
            print()
        print_tree(task.id, "", i == len(root_tasks) - 1)

    if not root_tasks:
        print("No root tasks found (all tasks have dependencies)")

    print()


def print_cross_ticket_graph(result: ParseResult):
    """Print ASCII dependency graph for tickets (cross-ticket dependencies)."""
    print_header("CROSS-TICKET DEPENDENCY GRAPH")
    print()

    # Build graph: ticket -> tickets it blocks
    graph = result.get_cross_ticket_dependency_graph()
    completed_tickets = result.get_completed_tickets()

    # Get ticket info
    ticket_info = {t.id: t for t in result.tickets}

    if not any(t.dependencies.blocked_by or t.dependencies.blocks for t in result.tickets):
        print("No cross-ticket dependencies defined.")
        print()
        print("To add cross-ticket dependencies, use the dependencies field in ticket YAML:")
        print()
        print("  dependencies:")
        print("    blocked_by: [TKT-001]  # This ticket waits for TKT-001")
        print("    blocks: [TKT-003]      # This ticket blocks TKT-003")
        print()
        return

    # Find root tickets (not blocked by any OTHER ticket)
    all_blocked_by = set()
    for ticket in result.tickets:
        all_blocked_by.update(ticket.dependencies.blocked_by)

    # Root tickets are those that block others but aren't blocked themselves
    root_tickets = [t for t in result.tickets if not t.dependencies.blocked_by]

    def print_ticket_tree(ticket_id: str, prefix: str = "", is_last: bool = True):
        """Recursively print ticket tree."""
        connector = "└─> " if is_last else "├─> "
        ticket = ticket_info.get(ticket_id)
        if not ticket:
            print(f"{prefix}{connector}{ticket_id} (unknown)")
            return

        status_mark = "✓" if ticket_id in completed_tickets else "○"
        title_short = ticket.title[:35] + "..." if len(ticket.title) > 35 else ticket.title
        task_count = len(result.get_tasks_for_ticket(ticket_id))

        print(f"{prefix}{connector}[{status_mark}] {ticket_id} ({title_short}) [{task_count} tasks]")

        children = graph.get(ticket_id, [])
        for i, child in enumerate(children):
            new_prefix = prefix + ("    " if is_last else "│   ")
            print_ticket_tree(child, new_prefix, i == len(children) - 1)

    for i, ticket in enumerate(root_tickets):
        if i > 0:
            print()
        print_ticket_tree(ticket.id, "", i == len(root_tickets) - 1)

    print()
    print("Legend: ✓ = all tasks complete, ○ = incomplete")
    print()


def print_ready_tasks(result: ParseResult):
    """Print tasks that are ready to work on."""
    ready = result.get_ready_tasks()

    print_header(f"READY TASKS ({len(ready)} available)")
    print()

    if not ready:
        print("No tasks are ready. Either:")
        print("  - All tasks have pending dependencies")
        print("  - All tasks are already completed or in progress")
        print()
        return

    for task in ready:
        print(f"- {task.id}: {task.title}")
        print(f"    Parent: {task.parent_ticket} | Estimate: {task.estimate}")
        if task.objective:
            obj = task.objective[:80] + "..." if len(task.objective) > 80 else task.objective
            obj = obj.replace("\n", " ")
            print(f"    {obj}")
        print()


def print_requirements(result: ParseResult):
    """Print all requirements."""
    print_header(f"REQUIREMENTS ({len(result.requirements)} total)")
    print()

    if not result.requirements:
        print("No requirements found in .omoi_os/requirements/")
        print()
        return

    for req in result.requirements:
        print(f"{req.id}: {req.title}")
        print(f"  Status: {req.status} | Priority: {req.priority} | Category: {req.category}")

        if req.condition:
            cond = req.condition[:60] + "..." if len(req.condition) > 60 else req.condition
            print(f"  WHEN: {cond}")

        if req.action:
            act = req.action[:60] + "..." if len(req.action) > 60 else req.action
            print(f"  THE SYSTEM SHALL: {act}")

        if req.acceptance_criteria:
            print(f"  Acceptance Criteria: {len(req.acceptance_criteria)} items")

        if req.linked_tickets:
            print(f"  Linked Tickets: {', '.join(req.linked_tickets)}")

        print()


def print_designs(result: ParseResult):
    """Print all designs."""
    print_header(f"DESIGNS ({len(result.designs)} total)")
    print()

    if not result.designs:
        print("No designs found in .omoi_os/designs/")
        print()
        return

    for design in result.designs:
        print(f"{design.id}: {design.title}")
        print(f"  Feature: {design.feature} | Status: {design.status}")

        if design.requirements:
            print(f"  Implements Requirements: {', '.join(design.requirements)}")

        if design.data_models:
            print(f"  Data Models: {', '.join(dm.name for dm in design.data_models)}")

        if design.api_endpoints:
            print(f"  API Endpoints: {len(design.api_endpoints)} defined")

        if design.components:
            print(f"  Components: {', '.join(design.components[:3])}", end="")
            if len(design.components) > 3:
                print(f" +{len(design.components) - 3} more")
            else:
                print()

        print()


def print_traceability(result: ParseResult):
    """Print full traceability matrix: Requirements → Designs → Tickets → Tasks."""
    stats = result.get_traceability_stats()
    trace = result.get_full_traceability()

    print_header("TRACEABILITY MATRIX")
    print()

    # Summary stats
    print("COVERAGE SUMMARY:")
    print(f"  Requirements: {stats['requirements']['linked']}/{stats['requirements']['total']} linked ({stats['requirements']['coverage']:.1f}%)")
    print(f"  Designs:      {stats['designs']['linked']}/{stats['designs']['total']} linked ({stats['designs']['coverage']:.1f}%)")
    print(f"  Tickets:      {stats['tickets']['linked']}/{stats['tickets']['total']} linked ({stats['tickets']['coverage']:.1f}%)")
    print()
    print(f"TASK STATUS:")
    print(f"  Done: {stats['tasks']['done']} | In Progress: {stats['tasks']['in_progress']} | Pending: {stats['tasks']['pending']}")
    print()

    # Orphans
    if any(trace["orphans"].values()):
        print("ORPHANED ITEMS (not linked):")
        if trace["orphans"]["requirements"]:
            print(f"  Requirements without tickets: {', '.join(trace['orphans']['requirements'])}")
        if trace["orphans"]["designs"]:
            print(f"  Designs without tickets: {', '.join(trace['orphans']['designs'])}")
        if trace["orphans"]["tickets"]:
            print(f"  Tickets without requirements: {', '.join(trace['orphans']['tickets'])}")
        print()

    # Detailed traceability
    print_header("REQUIREMENT → IMPLEMENTATION TRACE", char="-")
    print()

    for req_id, req_data in trace["requirements"].items():
        req = req_data["requirement"]
        print(f"┌─ REQ: {req_id}: {req.title}")

        # Show linked design
        if req_data["linked_design"]:
            print(f"│  └─> Design: {req_data['linked_design']}")

        # Show linked tickets
        if req_data["tickets"]:
            print(f"│  └─> Tickets: {', '.join(req_data['tickets'])}")

            # Show tasks for each ticket
            for ticket_id in req_data["tickets"]:
                tasks = result.get_tasks_for_ticket(ticket_id)
                if tasks:
                    done_count = sum(1 for t in tasks if t.status == "done")
                    print(f"│       └─> Tasks for {ticket_id}: {done_count}/{len(tasks)} complete")
        else:
            print("│  └─> (no implementing tickets)")

        print("└" + "─" * 50)
        print()

    # Ticket → Task breakdown
    print_header("TICKET → TASK BREAKDOWN", char="-")
    print()

    for ticket in result.tickets:
        tasks = result.get_tasks_for_ticket(ticket.id)
        done = sum(1 for t in tasks if t.status == "done")
        total = len(tasks)
        progress = f"{done}/{total}" if total > 0 else "no tasks"

        # Check if blocked
        is_blocked = ticket.is_blocked()
        blocked_marker = " [BLOCKED]" if is_blocked else ""

        print(f"┌─ {ticket.id}: {ticket.title}{blocked_marker}")
        print(f"│  Status: {ticket.status} | Progress: {progress}")

        if ticket.requirements:
            print(f"│  Implements: {', '.join(ticket.requirements)}")

        if tasks:
            for task in tasks:
                status_char = "✓" if task.status == "done" else "○"
                print(f"│    [{status_char}] {task.id}: {task.title[:40]}")

        print("└" + "─" * 50)
        print()


def print_validation(errors: list[ValidationError]):
    """Print validation results."""
    print_header("VALIDATION")
    print()

    if not errors:
        print("✓ No circular dependencies detected")
        print("✓ All task references valid")
        print("✓ All ticket references valid")
        print()
        return

    print(f"✗ Found {len(errors)} validation error(s):")
    print()

    for error in errors:
        print(f"  [{error.error_type}] {error.source_id}")
        print(f"    {error.message}")
        print()


def show_all(result: ParseResult):
    """Show everything: requirements, designs, tickets, tasks, graphs, traceability, validation."""
    print_requirements(result)
    print_designs(result)
    print_tickets(result.tickets)
    print_tasks(result.tasks, result)
    print_dependency_graph(result)
    print_cross_ticket_graph(result)
    print_ready_tasks(result)
    print_traceability(result)

    errors = validate_specs(result)
    print_validation(errors)


# ============================================================================
# Export Functions
# ============================================================================


def export_json(result: ParseResult) -> str:
    """Export all specs as JSON."""
    data = {
        "requirements": [
            {
                "id": r.id,
                "title": r.title,
                "status": r.status,
                "created": r.created.isoformat(),
                "updated": r.updated.isoformat(),
                "category": r.category,
                "priority": r.priority,
                "condition": r.condition,
                "action": r.action,
                "rationale": r.rationale,
                "acceptance_criteria": [
                    {"text": ac.text, "completed": ac.completed}
                    for ac in r.acceptance_criteria
                ],
                "linked_tickets": r.linked_tickets,
                "linked_design": r.linked_design,
            }
            for r in result.requirements
        ],
        "designs": [
            {
                "id": d.id,
                "title": d.title,
                "status": d.status,
                "created": d.created.isoformat(),
                "updated": d.updated.isoformat(),
                "feature": d.feature,
                "requirements": d.requirements,
                "architecture": d.architecture,
                "data_models": [
                    {
                        "name": dm.name,
                        "description": dm.description,
                        "fields": dm.fields,
                        "relationships": dm.relationships,
                    }
                    for dm in d.data_models
                ],
                "api_endpoints": [
                    {
                        "method": ep.method,
                        "path": ep.path,
                        "description": ep.description,
                    }
                    for ep in d.api_endpoints
                ],
                "components": d.components,
                "error_handling": d.error_handling,
                "security_considerations": d.security_considerations,
                "implementation_notes": d.implementation_notes,
            }
            for d in result.designs
        ],
        "tickets": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "priority": t.priority,
                "estimate": t.estimate,
                "created": t.created.isoformat(),
                "updated": t.updated.isoformat(),
                "feature": t.feature,
                "requirements": t.requirements,
                "design_ref": t.design_ref,
                "tasks": t.tasks,
                "dependencies": {
                    "blocked_by": t.dependencies.blocked_by,
                    "blocks": t.dependencies.blocks,
                    "related": t.dependencies.related,
                },
                "description": t.description,
            }
            for t in result.tickets
        ],
        "tasks": [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "parent_ticket": t.parent_ticket,
                "estimate": t.estimate,
                "created": t.created.isoformat(),
                "assignee": t.assignee,
                "dependencies": {
                    "depends_on": t.dependencies.depends_on,
                    "blocks": t.dependencies.blocks,
                },
                "objective": t.objective,
            }
            for t in result.tasks
        ],
        "traceability": result.get_traceability_stats(),
    }
    return json.dumps(data, indent=2)


# ============================================================================
# Main CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(
        description="Parse, validate, and visualize specs from .omoi_os/",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s show all           Show all requirements, designs, tickets, tasks
  %(prog)s show requirements  Show only requirements
  %(prog)s show designs       Show only designs
  %(prog)s show tickets       Show only tickets
  %(prog)s show tasks         Show only tasks
  %(prog)s show graph         Show task dependency graph
  %(prog)s show traceability  Show full traceability matrix
  %(prog)s show ready         Show tasks ready to work on
  %(prog)s validate           Run validation checks
  %(prog)s export json        Export to JSON format
  %(prog)s sync-specs push    Sync requirements/designs to API
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # show command
    show_parser = subparsers.add_parser("show", help="Show specs")
    show_parser.add_argument(
        "what",
        choices=["all", "requirements", "designs", "tickets", "tasks", "graph", "ticket-graph", "traceability", "ready"],
        help="What to show (graph=task deps, ticket-graph=cross-ticket deps, traceability=full matrix)",
    )

    # validate command
    subparsers.add_parser("validate", help="Validate specs")

    # export command
    export_parser = subparsers.add_parser("export", help="Export specs")
    export_parser.add_argument(
        "format",
        choices=["json"],
        help="Export format",
    )

    # Default API URL from environment or fallback to production
    # In sandbox environments, OMOIOS_API_URL is auto-injected by the orchestrator
    default_api_url = os.environ.get("OMOIOS_API_URL", "https://api.omoios.dev")
    default_project_id = os.environ.get("OMOIOS_PROJECT_ID")

    # projects command
    projects_parser = subparsers.add_parser("projects", help="List API projects")
    projects_parser.add_argument(
        "--api-url",
        default=default_api_url,
        help="API base URL (or set OMOIOS_API_URL env var)",
    )
    projects_parser.add_argument(
        "--api-key",
        help="API key for authentication (or set OMOIOS_API_KEY env var)",
    )

    # project command (show single project with tickets/tasks)
    project_parser = subparsers.add_parser("project", help="Show project details with tickets and tasks")
    project_parser.add_argument(
        "project_id",
        nargs="?",
        default=default_project_id,
        help="Project ID to display (or set OMOIOS_PROJECT_ID env var)",
    )
    project_parser.add_argument(
        "--api-url",
        default=default_api_url,
        help="API base URL (or set OMOIOS_API_URL env var)",
    )
    project_parser.add_argument(
        "--api-key",
        help="API key for authentication (or set OMOIOS_API_KEY env var)",
    )

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync with API")
    sync_parser.add_argument(
        "action",
        choices=["push", "diff"],
        help="Sync action (push=create/update, diff=dry run)",
    )
    sync_parser.add_argument(
        "--api-url",
        default=default_api_url,
        help="API base URL (or set OMOIOS_API_URL env var)",
    )
    sync_parser.add_argument(
        "--project-id",
        default=default_project_id,
        help="Project ID to associate tickets with (or set OMOIOS_PROJECT_ID env var)",
    )
    sync_parser.add_argument(
        "--email",
        help="Email for login (or set OMOIOS_EMAIL env var)",
    )
    sync_parser.add_argument(
        "--password",
        help="Password for login (or set OMOIOS_PASSWORD env var)",
    )
    sync_parser.add_argument(
        "--token",
        help="JWT access token (or set OMOIOS_TOKEN env var)",
    )
    sync_parser.add_argument(
        "--api-key",
        help="API key for authentication (or set OMOIOS_API_KEY env var)",
    )

    # sync-specs command (sync requirements/designs to API)
    sync_specs_parser = subparsers.add_parser("sync-specs", help="Sync requirements/designs to API specs")
    sync_specs_parser.add_argument(
        "action",
        choices=["push", "diff"],
        help="Sync action (push=create/update, diff=dry run)",
    )
    sync_specs_parser.add_argument(
        "--api-url",
        default=default_api_url,
        help="API base URL (or set OMOIOS_API_URL env var)",
    )
    sync_specs_parser.add_argument(
        "--project-id",
        default=default_project_id,
        help="Project ID to associate spec with (or set OMOIOS_PROJECT_ID env var)",
    )
    sync_specs_parser.add_argument(
        "--spec-title",
        help="Spec title (defaults to design feature name)",
    )
    sync_specs_parser.add_argument(
        "--api-key",
        help="API key for authentication (or set OMOIOS_API_KEY env var)",
    )
    sync_specs_parser.add_argument(
        "--token",
        help="JWT access token (or set OMOIOS_TOKEN env var)",
    )

    # traceability command (show API traceability)
    trace_parser = subparsers.add_parser("api-trace", help="Show traceability from API")
    trace_parser.add_argument(
        "project_id",
        nargs="?",
        default=default_project_id,
        help="Project ID to show traceability for (or set OMOIOS_PROJECT_ID env var)",
    )
    trace_parser.add_argument(
        "--api-url",
        default=default_api_url,
        help="API base URL (or set OMOIOS_API_URL env var)",
    )
    trace_parser.add_argument(
        "--api-key",
        help="API key for authentication (or set OMOIOS_API_KEY env var)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Parse all specs
    spec_parser = SpecParser()
    result = spec_parser.parse_all()

    if args.command == "show":
        if args.what == "all":
            show_all(result)
        elif args.what == "requirements":
            print_requirements(result)
        elif args.what == "designs":
            print_designs(result)
        elif args.what == "tickets":
            print_tickets(result.tickets)
        elif args.what == "tasks":
            print_tasks(result.tasks, result)
        elif args.what == "graph":
            print_dependency_graph(result)
        elif args.what == "ticket-graph":
            print_cross_ticket_graph(result)
        elif args.what == "traceability":
            print_traceability(result)
        elif args.what == "ready":
            print_ready_tasks(result)

    elif args.command == "validate":
        errors = validate_specs(result)
        print_validation(errors)
        if errors:
            sys.exit(1)

    elif args.command == "export":
        if args.format == "json":
            print(export_json(result))

    elif args.command == "projects":
        import asyncio
        import os
        from api_client import OmoiOSClient

        async def list_projects():
            api_key = args.api_key or os.environ.get("OMOIOS_API_KEY")
            client = OmoiOSClient(base_url=args.api_url, api_key=api_key)
            projects = await client.list_projects()
            if projects:
                print_header(f"PROJECTS ({len(projects)} total)")
                print()
                for p in projects:
                    print(f"  {p.get('id', 'N/A')}: {p.get('name', 'Unnamed')}")
                    if p.get('description'):
                        desc = p['description'][:60] + "..." if len(p['description']) > 60 else p['description']
                        print(f"    {desc}")
                print()
            else:
                print("No projects found.")

        asyncio.run(list_projects())

    elif args.command == "project":
        import asyncio
        import os
        from api_client import OmoiOSClient

        if not args.project_id:
            print("Error: project_id is required. Provide it as an argument or set OMOIOS_PROJECT_ID env var.")
            sys.exit(1)

        async def show_project():
            api_key = args.api_key or os.environ.get("OMOIOS_API_KEY")
            client = OmoiOSClient(base_url=args.api_url, api_key=api_key)
            data = await client.get_project_with_tickets(args.project_id)

            if "error" in data:
                print(f"Error: {data['error']}")
                sys.exit(1)

            project = data.get("project", {})
            tickets = data.get("tickets", [])

            print_header(f"PROJECT: {project.get('name', 'Unknown')}")
            print()
            print(f"  ID: {project.get('id', 'N/A')}")
            if project.get('description'):
                print(f"  Description: {project['description'][:80]}")
            print()
            print(f"  Total Tickets: {data.get('total_tickets', 0)}")
            print(f"  Total Tasks: {data.get('total_tasks', 0)}")
            print()

            if not tickets:
                print("  No tickets found for this project.")
                return

            # Group tickets by status
            by_status = {}
            for t in tickets:
                status = t.get("status", "unknown")
                if status not in by_status:
                    by_status[status] = []
                by_status[status].append(t)

            # Print tickets grouped by status
            print_header("TICKETS BY STATUS", char="-")
            print()

            for status, status_tickets in sorted(by_status.items()):
                print(f"  [{status.upper()}] ({len(status_tickets)} tickets)")
                print()

                for ticket in status_tickets:
                    print(f"    {ticket.get('id', 'N/A')[:20]}...")
                    print(f"      Title: {ticket.get('title', 'No title')}")
                    print(f"      Priority: {ticket.get('priority', 'N/A')}")

                    tasks = ticket.get("tasks", [])
                    if tasks:
                        print(f"      Tasks: ({len(tasks)} total)")
                        for task in tasks[:5]:  # Show max 5 tasks per ticket
                            task_status = task.get("status", "unknown")
                            print(f"        - [{task_status}] {task.get('title', task.get('description', 'No title')[:40])}")
                        if len(tasks) > 5:
                            print(f"        ... and {len(tasks) - 5} more tasks")
                    else:
                        print("      Tasks: None")
                    print()

        asyncio.run(show_project())

    elif args.command == "sync":
        import asyncio
        import os
        from api_client import run_sync

        api_key = getattr(args, 'api_key', None) or os.environ.get("OMOIOS_API_KEY")
        success = asyncio.run(
            run_sync(
                args.api_url,
                args.action,
                args.project_id,
                args.email,
                args.password,
                args.token,
                api_key,
            )
        )
        if not success:
            sys.exit(1)

    elif args.command == "sync-specs":
        import asyncio
        import os
        from api_client import OmoiOSClient, print_sync_summary

        if not args.project_id:
            print("Error: --project-id is required. Provide it as an argument or set OMOIOS_PROJECT_ID env var.")
            sys.exit(1)

        async def run_sync_specs():
            api_key = args.api_key or os.environ.get("OMOIOS_API_KEY")
            token = args.token or os.environ.get("OMOIOS_TOKEN")

            client = OmoiOSClient(base_url=args.api_url, api_key=api_key, token=token)

            # Check connection
            print(f"Connecting to {args.api_url}...")
            connected, msg = await client.check_connection()
            if not connected:
                print(f"Error: Cannot connect to API: {msg}")
                return False

            print("Connected!")
            print(f"Project ID: {args.project_id}")
            print(f"Requirements: {len(result.requirements)}")
            print(f"Designs: {len(result.designs)}")
            print()

            # Run sync
            if args.action == "diff":
                print("Checking what would change (dry run)...")
                summary = await client.diff_specs(
                    result,
                    args.project_id,
                    args.spec_title,
                )
            else:  # push
                print("Syncing specs to API...")
                summary = await client.sync_specs(
                    result,
                    args.project_id,
                    args.spec_title,
                )

            print_sync_summary(summary)
            return summary.failed == 0

        success = asyncio.run(run_sync_specs())
        if not success:
            sys.exit(1)

    elif args.command == "api-trace":
        import asyncio
        import os
        from api_client import OmoiOSClient

        if not args.project_id:
            print("Error: project_id is required. Provide it as an argument or set OMOIOS_PROJECT_ID env var.")
            sys.exit(1)

        async def show_api_traceability():
            api_key = args.api_key or os.environ.get("OMOIOS_API_KEY")
            client = OmoiOSClient(base_url=args.api_url, api_key=api_key)

            print(f"Fetching traceability from {args.api_url}...")
            trace = await client.get_full_traceability(args.project_id)

            print_header("API TRACEABILITY MATRIX")
            print()

            # Specs summary
            specs = trace.get("specs", [])
            print(f"SPECS: {len(specs)} total")
            for spec in specs:
                req_count = len(spec.get("requirements", []))
                ticket_count = len(spec.get("linked_tickets", []))
                print(f"  [{spec['status']}] {spec['id'][:20]}...")
                print(f"       Title: {spec['title']}")
                print(f"       Requirements: {req_count} | Linked Tickets: {ticket_count}")
                print()

            # Tickets summary
            tickets = trace.get("tickets", [])
            orphans = trace.get("orphan_tickets", [])
            print(f"LINKED TICKETS: {len(tickets)} total")
            for ticket in tickets[:10]:  # Show max 10
                task_count = len(ticket.get("tasks", []))
                print(f"  [{ticket['status']}] {ticket['id'][:20]}...")
                print(f"       Title: {ticket['title'][:50]}")
                print(f"       Tasks: {task_count}")
            if len(tickets) > 10:
                print(f"  ... and {len(tickets) - 10} more tickets")
            print()

            if orphans:
                print(f"ORPHAN TICKETS (not linked to specs): {len(orphans)}")
                for ticket in orphans[:5]:
                    print(f"  - {ticket['id'][:20]}... {ticket['title'][:40]}")
                if len(orphans) > 5:
                    print(f"  ... and {len(orphans) - 5} more")
                print()

        asyncio.run(show_api_traceability())


if __name__ == "__main__":
    main()
