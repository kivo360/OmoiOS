"""Validation utilities for spec evaluators.

Provides validation patterns adapted from the spec-driven-dev skill scripts:
- Normative language detection (SHALL, SHOULD, MAY, MUST)
- ID format validation (REQ-XXX-YYY-NNN, TASK-XXX, etc.)
- Circular dependency detection
- Reference validation

These patterns ensure generated specs are compatible with the
.omoi_os/ file format used by the skill scripts.
"""

import re
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple


@dataclass
class ValidationError:
    """Validation error with context."""

    error_type: str
    message: str
    source_id: Optional[str] = None
    target_id: Optional[str] = None
    severity: str = "error"  # "error" or "warning"


@dataclass
class ValidationResult:
    """Result of validation with errors and warnings."""

    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Return True if no errors (warnings are acceptable)."""
        return len(self.errors) == 0

    @property
    def total_issues(self) -> int:
        """Total number of issues (errors + warnings)."""
        return len(self.errors) + len(self.warnings)

    def add_error(
        self,
        error_type: str,
        message: str,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> None:
        """Add an error."""
        self.errors.append(
            ValidationError(
                error_type=error_type,
                message=message,
                source_id=source_id,
                target_id=target_id,
                severity="error",
            )
        )

    def add_warning(
        self,
        error_type: str,
        message: str,
        source_id: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> None:
        """Add a warning."""
        self.warnings.append(
            ValidationError(
                error_type=error_type,
                message=message,
                source_id=source_id,
                target_id=target_id,
                severity="warning",
            )
        )


# =============================================================================
# ID Format Validation
# =============================================================================

# Standard ID patterns compatible with skill scripts
ID_PATTERNS = {
    "requirement": re.compile(r"^REQ-[A-Z]{2,6}-[A-Z]{2,6}-\d{3}$"),
    "task": re.compile(r"^TASK-\d{3}$"),
    "ticket": re.compile(r"^TKT-(?:[A-Z]+-)?(\d{3})$"),
    "design": re.compile(r"^DESIGN-[A-Z]{2,6}-\d{3}$"),
}

# Relaxed patterns for generated IDs (more flexible)
RELAXED_ID_PATTERNS = {
    "requirement": re.compile(r"^REQ-[A-Z0-9-]+$", re.IGNORECASE),
    "task": re.compile(r"^TASK-\d+$", re.IGNORECASE),
    "ticket": re.compile(r"^TKT-[A-Z0-9-]+$", re.IGNORECASE),
    "design": re.compile(r"^DESIGN-[A-Z0-9-]+$", re.IGNORECASE),
}


def validate_id_format(
    id_value: str,
    id_type: str,
    strict: bool = False,
) -> Tuple[bool, Optional[str]]:
    """Validate an ID matches the expected format.

    Args:
        id_value: The ID to validate
        id_type: Type of ID (requirement, task, ticket, design)
        strict: If True, use strict patterns; otherwise use relaxed

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not id_value:
        return False, f"Empty {id_type} ID"

    patterns = ID_PATTERNS if strict else RELAXED_ID_PATTERNS

    if id_type not in patterns:
        return False, f"Unknown ID type: {id_type}"

    pattern = patterns[id_type]
    if pattern.match(id_value):
        return True, None

    expected = {
        "requirement": "REQ-XXX-YYY-NNN (e.g., REQ-AUTH-CORE-001)",
        "task": "TASK-NNN (e.g., TASK-001)",
        "ticket": "TKT-XXX or TKT-PREFIX-NNN",
        "design": "DESIGN-XXX-NNN (e.g., DESIGN-AUTH-001)",
    }

    return False, f"Invalid {id_type} ID format: {id_value}. Expected: {expected.get(id_type, 'unknown')}"


# =============================================================================
# Normative Language Detection
# =============================================================================

# EARS format keywords
NORMATIVE_KEYWORDS = {
    "SHALL": "mandatory requirement",
    "SHALL NOT": "mandatory prohibition",
    "SHOULD": "recommended requirement",
    "SHOULD NOT": "recommended prohibition",
    "MAY": "optional requirement",
    "MUST": "mandatory requirement (alternative to SHALL)",
    "MUST NOT": "mandatory prohibition (alternative to SHALL NOT)",
}

# EARS trigger patterns
EARS_TRIGGERS = {
    "WHEN": "event-driven trigger",
    "WHILE": "state-driven trigger",
    "WHERE": "context-driven trigger",
    "IF": "conditional trigger",
}


def detect_normative_language(text: str) -> Dict[str, List[str]]:
    """Detect normative language in requirement text.

    Args:
        text: Requirement text to analyze

    Returns:
        Dict with 'keywords' and 'triggers' found
    """
    result = {
        "keywords": [],
        "triggers": [],
    }

    text_upper = text.upper()

    # Check for normative keywords
    for keyword in NORMATIVE_KEYWORDS:
        if keyword in text_upper:
            result["keywords"].append(keyword)

    # Check for EARS triggers
    for trigger in EARS_TRIGGERS:
        # Look for trigger at word boundary
        pattern = rf"\b{trigger}\b"
        if re.search(pattern, text_upper):
            result["triggers"].append(trigger)

    return result


def validate_requirement_text(text: str) -> ValidationResult:
    """Validate requirement text uses proper normative language.

    Args:
        text: Requirement text to validate

    Returns:
        ValidationResult with any issues found
    """
    result = ValidationResult()

    if not text or not text.strip():
        result.add_error("empty_text", "Requirement text is empty")
        return result

    detected = detect_normative_language(text)

    # Must have at least one normative keyword
    if not detected["keywords"]:
        result.add_error(
            "missing_normative",
            "Requirement must use normative language (SHALL, SHOULD, MAY, MUST)",
        )

    # Check for proper EARS format
    has_shall = any(k in ["SHALL", "MUST"] for k in detected["keywords"])
    has_trigger = len(detected["triggers"]) > 0

    if has_shall and not has_trigger:
        result.add_warning(
            "missing_trigger",
            "Consider using EARS format with trigger (WHEN/WHILE/WHERE/IF)",
        )

    # Check for common anti-patterns
    text_lower = text.lower()

    if "will be" in text_lower or "is going to" in text_lower:
        result.add_warning(
            "weak_language",
            "Use normative 'SHALL' instead of 'will be' or 'is going to'",
        )

    if "etc" in text_lower or "and so on" in text_lower:
        result.add_warning(
            "vague_language",
            "Avoid vague terms like 'etc' - be specific",
        )

    return result


# =============================================================================
# Circular Dependency Detection
# =============================================================================


def detect_circular_dependencies(
    tasks: List[Dict[str, Any]],
) -> List[ValidationError]:
    """Detect circular dependencies in task graph using DFS.

    This algorithm is adapted from spec_cli.py in the skill scripts.

    Args:
        tasks: List of task dicts with 'id' and 'dependencies' fields

    Returns:
        List of ValidationErrors for any cycles found
    """
    errors = []

    # Build adjacency list
    task_deps: Dict[str, List[str]] = {}
    for task in tasks:
        task_id = task.get("id", "")
        deps = task.get("dependencies", [])
        if isinstance(deps, list):
            task_deps[task_id] = deps
        else:
            task_deps[task_id] = []

    # Track visited and recursion stack
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    path: List[str] = []

    def dfs(task_id: str) -> Optional[List[str]]:
        """DFS to detect cycle, returns cycle path if found."""
        if task_id in rec_stack:
            # Found cycle - extract the cycle from path
            if task_id in path:
                cycle_start = path.index(task_id)
                return path[cycle_start:] + [task_id]
            return [task_id]

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
    for task in tasks:
        task_id = task.get("id", "")
        if task_id and task_id not in visited:
            cycle = dfs(task_id)
            if cycle:
                cycle_str = " -> ".join(cycle)
                errors.append(
                    ValidationError(
                        error_type="circular_dependency",
                        message=f"Circular dependency detected: {cycle_str}",
                        source_id=cycle[0],
                        target_id=cycle[-1] if len(cycle) > 1 else cycle[0],
                        severity="error",
                    )
                )
                # Reset for next search
                visited.clear()
                rec_stack.clear()
                path.clear()

    return errors


# =============================================================================
# Reference Validation
# =============================================================================


def validate_task_references(
    tasks: List[Dict[str, Any]],
) -> List[ValidationError]:
    """Validate that all task dependency references exist.

    Args:
        tasks: List of task dicts with 'id' and 'dependencies' fields

    Returns:
        List of ValidationErrors for missing references
    """
    errors = []

    # Get all task IDs
    task_ids = {task.get("id") for task in tasks if task.get("id")}

    # Check each task's dependencies
    for task in tasks:
        task_id = task.get("id", "unknown")
        deps = task.get("dependencies", [])

        if isinstance(deps, list):
            for dep_id in deps:
                if dep_id not in task_ids:
                    errors.append(
                        ValidationError(
                            error_type="missing_reference",
                            message=f"Task references unknown dependency: {dep_id}",
                            source_id=task_id,
                            target_id=dep_id,
                            severity="error",
                        )
                    )

    return errors


def validate_requirements_addressed(
    tasks: List[Dict[str, Any]],
    requirements: List[Dict[str, Any]],
) -> ValidationResult:
    """Validate that all requirements are addressed by at least one task.

    Args:
        tasks: List of task dicts with 'requirements_addressed' field
        requirements: List of requirement dicts with 'id' field

    Returns:
        ValidationResult with coverage analysis
    """
    result = ValidationResult()

    # Get all requirement IDs
    req_ids = {req.get("id") for req in requirements if req.get("id")}

    # Get addressed requirements from tasks
    addressed: Set[str] = set()
    for task in tasks:
        task_reqs = task.get("requirements_addressed", [])
        if isinstance(task_reqs, list):
            addressed.update(task_reqs)

    # Find unaddressed requirements
    unaddressed = req_ids - addressed
    for req_id in unaddressed:
        result.add_warning(
            "unaddressed_requirement",
            f"Requirement {req_id} is not addressed by any task",
            source_id=req_id,
        )

    # Find references to unknown requirements
    unknown = addressed - req_ids
    for req_id in unknown:
        result.add_error(
            "unknown_requirement",
            f"Task references unknown requirement: {req_id}",
            target_id=req_id,
        )

    return result


# =============================================================================
# Component Validation
# =============================================================================


def validate_component_responsibilities(
    components: List[Dict[str, Any]],
) -> ValidationResult:
    """Validate component definitions have proper responsibilities.

    Args:
        components: List of component dicts

    Returns:
        ValidationResult with any issues
    """
    result = ValidationResult()

    for component in components:
        name = component.get("name", "unknown")
        responsibility = component.get("responsibility", "")

        if not responsibility:
            result.add_error(
                "missing_responsibility",
                f"Component '{name}' has no responsibility defined",
                source_id=name,
            )
        elif len(responsibility) < 10:
            result.add_warning(
                "brief_responsibility",
                f"Component '{name}' has very brief responsibility",
                source_id=name,
            )

        # Check for dependencies
        deps = component.get("dependencies", [])
        if isinstance(deps, list) and len(deps) > 5:
            result.add_warning(
                "high_coupling",
                f"Component '{name}' has {len(deps)} dependencies - consider decomposition",
                source_id=name,
            )

    return result


# =============================================================================
# Traceability Validation
# =============================================================================


def calculate_traceability_stats(
    requirements: List[Dict[str, Any]],
    tasks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Calculate traceability statistics.

    Compatible with the format used by ParseResult.get_traceability_stats()
    in the skill scripts.

    Args:
        requirements: List of requirement dicts
        tasks: List of task dicts

    Returns:
        Dict with traceability statistics
    """
    # Get requirement IDs
    req_ids = {req.get("id") for req in requirements if req.get("id")}

    # Get addressed requirements
    addressed: Set[str] = set()
    for task in tasks:
        task_reqs = task.get("requirements_addressed", [])
        if isinstance(task_reqs, list):
            addressed.update(task_reqs)

    # Calculate coverage
    linked_reqs = addressed.intersection(req_ids)
    total_reqs = len(req_ids)
    req_coverage = (len(linked_reqs) / total_reqs * 100) if total_reqs > 0 else 0

    # Task status breakdown
    task_status = defaultdict(int)
    for task in tasks:
        status = task.get("status", "pending")
        task_status[status] += 1

    return {
        "requirements": {
            "total": total_reqs,
            "linked": len(linked_reqs),
            "coverage": req_coverage,
        },
        "tasks": {
            "total": len(tasks),
            "done": task_status.get("done", 0),
            "in_progress": task_status.get("in_progress", 0),
            "pending": task_status.get("pending", len(tasks) - task_status.get("done", 0) - task_status.get("in_progress", 0)),
        },
        "orphans": {
            "requirements": list(req_ids - addressed),
        },
    }
