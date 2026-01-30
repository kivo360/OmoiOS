"""Ownership Validation Service for parallel task file conflict prevention.

This service validates file ownership to prevent merge conflicts when multiple
parallel tasks modify the same files. It enforces ownership rules at two levels:

1. Task-level validation: Before spawning a sandbox, check if the task's owned_files
   patterns conflict with any parallel sibling tasks (tasks from the same join/split).

2. File-level validation: During execution, validate if a specific file modification
   is allowed based on the task's ownership patterns.

File ownership patterns use glob syntax:
- "src/services/user/**" - All files under src/services/user/
- "*.py" - All Python files in root
- "src/**/*.ts" - All TypeScript files under src/

The validation is lenient by design:
- Tasks without owned_files patterns have no restrictions
- Validation only triggers when both tasks have ownership patterns
- Conflicts are logged but execution can proceed (warn-only mode available)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import fnmatch
from typing import List, Optional, Set, Dict, Any
from functools import lru_cache

from omoi_os.logging import get_logger
from omoi_os.models.task import Task
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now

logger = get_logger(__name__)


@dataclass
class ValidationResult:
    """Result of ownership validation."""

    valid: bool
    conflicts: List[str]  # List of conflicting patterns/files
    warnings: List[str]
    conflicting_task_ids: List[str]  # IDs of tasks with conflicts
    conflict_details: List[Dict[str, Any]] = field(default_factory=list)  # Detailed conflict info

    @property
    def has_warnings(self) -> bool:
        return bool(self.warnings)

    @property
    def has_conflicts(self) -> bool:
        return bool(self.conflicts)

    def to_merge_metrics(self) -> Dict[str, Any]:
        """Convert to metrics format for MergeAttempt audit trail."""
        return {
            "total_conflicts": len(self.conflicts) + len(self.warnings),
            "conflict_count": len(self.conflicts),
            "warning_count": len(self.warnings),
            "conflicting_task_ids": self.conflicting_task_ids,
            "conflict_patterns": self.conflict_details,
            "timestamp": utc_now().isoformat(),
        }


@dataclass
class OwnershipConflict:
    """Detailed information about an ownership conflict."""

    task_id: str
    task_title: Optional[str]
    pattern: str
    overlapping_patterns: List[str]


class OwnershipValidationService:
    """Validates file ownership to prevent conflicts between parallel tasks.

    This service is designed to work with the CoordinationService and
    SynthesisService to ensure parallel tasks don't modify the same files.

    Usage:
        ownership_service = OwnershipValidationService(db)

        # Before spawning a sandbox
        result = ownership_service.validate_task_ownership(task)
        if not result.valid:
            raise OwnershipConflictError(result.conflicts)

        # During execution (for MCP tool validation)
        if not ownership_service.validate_file_modification(task_id, "src/user/service.py"):
            logger.warning("Task attempting to modify file outside ownership")
    """

    def __init__(
        self,
        db: DatabaseService,
        strict_mode: bool = False,
    ):
        """Initialize the ownership validation service.

        Args:
            db: Database service for persistence
            strict_mode: If True, conflicts block execution. If False, just warn.
        """
        self.db = db
        self.strict_mode = strict_mode
        logger.info(
            "ownership_validation_service_initialized",
            strict_mode=strict_mode,
        )

    def validate_task_ownership(
        self,
        task: Task,
        check_parallel_siblings: bool = True,
    ) -> ValidationResult:
        """Validate a task's file ownership against parallel siblings.

        This should be called before spawning a sandbox to ensure no conflicts
        with other parallel tasks from the same split/join.

        Args:
            task: Task to validate
            check_parallel_siblings: Whether to check for conflicts with siblings

        Returns:
            ValidationResult with conflict information
        """
        conflicts: List[str] = []
        warnings: List[str] = []
        conflicting_task_ids: List[str] = []
        conflict_details: List[Dict[str, Any]] = []  # For MergeAttempt metrics

        # If task has no ownership patterns, no restrictions apply
        if not task.owned_files:
            return ValidationResult(
                valid=True,
                conflicts=[],
                warnings=[],
                conflicting_task_ids=[],
                conflict_details=[],
            )

        if not check_parallel_siblings:
            return ValidationResult(
                valid=True,
                conflicts=[],
                warnings=[],
                conflicting_task_ids=[],
                conflict_details=[],
            )

        # Get parallel sibling task data (as dicts to avoid detached instance issues)
        siblings_data = self._get_parallel_siblings_data(task)

        for sibling_data in siblings_data:
            sibling_owned_files = sibling_data.get("owned_files")
            if not sibling_owned_files:
                continue

            # Check for pattern overlaps
            overlaps = self._find_pattern_overlaps(
                task.owned_files, sibling_owned_files
            )

            if overlaps:
                sibling_id = sibling_data["id"]
                for overlap in overlaps:
                    conflict_msg = (
                        f"Ownership conflict with task {sibling_id[:8]}: "
                        f"pattern '{overlap['task_pattern']}' overlaps with "
                        f"'{overlap['sibling_pattern']}'"
                    )
                    conflicts.append(conflict_msg)

                    # Capture detailed metrics for MergeAttempt audit trail
                    conflict_details.append({
                        "task_id": str(task.id),
                        "sibling_task_id": sibling_id,
                        "task_pattern": overlap["task_pattern"],
                        "sibling_pattern": overlap["sibling_pattern"],
                        "detected_at": utc_now().isoformat(),
                    })

                conflicting_task_ids.append(sibling_id)

        # Determine validity based on strict mode
        is_valid = not conflicts if self.strict_mode else True

        if conflicts and not self.strict_mode:
            warnings.extend(conflicts)
            conflicts = []  # Move to warnings in lenient mode

        # Log with detailed metrics for observability
        if conflicts or warnings:
            logger.warning(
                "ownership_validation_conflicts_detected",
                extra={
                    "task_id": str(task.id),
                    "ticket_id": str(task.ticket_id) if task.ticket_id else None,
                    "conflict_count": len(conflicts),
                    "warning_count": len(warnings),
                    "conflicting_tasks": conflicting_task_ids,
                    "conflict_patterns": [d["task_pattern"] for d in conflict_details],
                    "strict_mode": self.strict_mode,
                    "would_block_merge": bool(conflicts),
                },
            )

            # Record conflict metrics for MergeAttempt monitoring
            self._record_conflict_metrics(
                task_id=str(task.id),
                ticket_id=str(task.ticket_id) if task.ticket_id else None,
                conflict_details=conflict_details,
            )

        return ValidationResult(
            valid=is_valid,
            conflicts=conflicts,
            warnings=warnings,
            conflicting_task_ids=conflicting_task_ids,
            conflict_details=conflict_details,
        )

    def _record_conflict_metrics(
        self,
        task_id: str,
        ticket_id: Optional[str],
        conflict_details: List[Dict[str, Any]],
    ) -> None:
        """Record conflict metrics for monitoring and MergeAttempt creation.

        This logs detailed metrics that can be used to:
        1. Monitor real conflict patterns over time
        2. Create MergeAttempt records for audit trail
        3. Analyze which file patterns cause the most conflicts

        Args:
            task_id: ID of the task being validated
            ticket_id: ID of the ticket containing the task
            conflict_details: List of detailed conflict information
        """
        if not conflict_details:
            return

        # Group conflicts by sibling task for analysis
        conflicts_by_sibling: Dict[str, List[Dict[str, Any]]] = {}
        for detail in conflict_details:
            sibling_id = detail["sibling_task_id"]
            if sibling_id not in conflicts_by_sibling:
                conflicts_by_sibling[sibling_id] = []
            conflicts_by_sibling[sibling_id].append(detail)

        # Log aggregated conflict metrics
        logger.info(
            "ownership_conflict_metrics",
            extra={
                "task_id": task_id,
                "ticket_id": ticket_id,
                "total_conflicts": len(conflict_details),
                "conflicting_sibling_count": len(conflicts_by_sibling),
                "conflicts_by_sibling": {
                    sid: len(conflicts) for sid, conflicts in conflicts_by_sibling.items()
                },
                "unique_patterns_involved": len(
                    set(d["task_pattern"] for d in conflict_details)
                ),
                "timestamp": utc_now().isoformat(),
            },
        )

    def validate_file_modification(
        self,
        task_id: str,
        file_path: str,
    ) -> bool:
        """Check if a task is allowed to modify a specific file.

        This can be used during execution (e.g., in MCP tool validation)
        to ensure tasks only modify files within their ownership patterns.

        Args:
            task_id: ID of the task attempting the modification
            file_path: Path of the file being modified

        Returns:
            True if modification is allowed, False otherwise
        """
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                logger.warning(
                    "task_not_found_for_ownership_check",
                    task_id=task_id,
                )
                return True  # Allow if task not found (lenient)

            # No ownership patterns = no restrictions
            if not task.owned_files:
                return True

            # Check if file matches any ownership pattern
            return self._file_matches_patterns(file_path, task.owned_files)

    def check_file_ownership(
        self,
        task_id: str,
        file_path: str,
    ) -> Optional[str]:
        """Check who owns a file and return the owning task ID if any.

        This finds which task (if any) has claimed ownership of a file
        within a ticket's parallel tasks.

        Args:
            task_id: ID of a task in the ticket (for context)
            file_path: Path of the file to check

        Returns:
            Task ID of the owner, or None if no owner
        """
        with self.db.get_session() as session:
            task = session.query(Task).filter(Task.id == task_id).first()
            if not task:
                return None

            # Get all tasks in the same ticket that have ownership patterns
            ticket_tasks = (
                session.query(Task)
                .filter(Task.ticket_id == task.ticket_id)
                .filter(Task.owned_files.isnot(None))
                .all()
            )

            for t in ticket_tasks:
                if self._file_matches_patterns(file_path, t.owned_files or []):
                    return str(t.id)

            return None

    def _get_parallel_siblings_data(self, task: Task) -> List[dict]:
        """Get parallel sibling task data (tasks from the same join/split).

        Parallel siblings are identified by:
        1. Same ticket_id (working on same feature)
        2. Similar phase_id (working in parallel phases)
        3. Not the same task
        4. Status is not completed/failed (still relevant for conflicts)

        Args:
            task: Task to find siblings for

        Returns:
            List of dictionaries with sibling id and owned_files
        """
        with self.db.get_session() as session:
            # Get tasks from the same ticket that could be running in parallel
            # We look for tasks that:
            # - Are in the same ticket
            # - Are not the same task
            # - Are in a status that could conflict (pending, assigned, running)
            siblings = (
                session.query(Task.id, Task.owned_files)
                .filter(Task.ticket_id == task.ticket_id)
                .filter(Task.id != task.id)
                .filter(Task.status.in_(["pending", "assigned", "running", "claiming"]))
                .filter(Task.owned_files.isnot(None))
                .all()
            )

            # Return as list of dicts to avoid detached instance issues
            return [{"id": str(s.id), "owned_files": s.owned_files} for s in siblings]

    def _find_pattern_overlaps(
        self,
        task_patterns: List[str],
        sibling_patterns: List[str],
    ) -> List[dict]:
        """Find overlapping patterns between two sets of ownership patterns.

        Two patterns overlap if they could match the same files.
        This is a conservative check - we err on the side of finding overlaps.

        Args:
            task_patterns: Ownership patterns from the task
            sibling_patterns: Ownership patterns from the sibling

        Returns:
            List of overlap dictionaries with pattern details
        """
        overlaps = []

        for task_pattern in task_patterns:
            for sibling_pattern in sibling_patterns:
                if self._patterns_may_overlap(task_pattern, sibling_pattern):
                    overlaps.append({
                        "task_pattern": task_pattern,
                        "sibling_pattern": sibling_pattern,
                    })

        return overlaps

    def _patterns_may_overlap(
        self,
        pattern1: str,
        pattern2: str,
    ) -> bool:
        """Check if two glob patterns may match the same files.

        This is a conservative check - returns True if there's any chance
        of overlap, even if the patterns are not identical.

        Args:
            pattern1: First glob pattern
            pattern2: Second glob pattern

        Returns:
            True if patterns may overlap
        """
        # Exact match is definitely an overlap
        if pattern1 == pattern2:
            return True

        # Normalize patterns for comparison
        p1_normalized = pattern1.rstrip("/")
        p2_normalized = pattern2.rstrip("/")

        # Check if one pattern is a prefix of the other
        # e.g., "src/**" and "src/services/**"
        if p1_normalized.startswith(p2_normalized.replace("**", "").rstrip("/")):
            return True
        if p2_normalized.startswith(p1_normalized.replace("**", "").rstrip("/")):
            return True

        # Check if patterns share a common directory prefix
        p1_parts = p1_normalized.split("/")
        p2_parts = p2_normalized.split("/")

        # Find common prefix (excluding wildcards)
        common_prefix = []
        for p1_part, p2_part in zip(p1_parts, p2_parts):
            if p1_part == p2_part and "*" not in p1_part:
                common_prefix.append(p1_part)
            elif p1_part == "**" or p2_part == "**":
                # Recursive wildcard could match anything
                return True
            elif "*" in p1_part or "*" in p2_part:
                # Wildcards at the same level could overlap
                return True
            else:
                break

        # If they have no common prefix, they can't overlap
        if not common_prefix:
            return False

        # If they have a common prefix, they might overlap
        return True

    def _file_matches_patterns(
        self,
        file_path: str,
        patterns: List[str],
    ) -> bool:
        """Check if a file path matches any of the ownership patterns.

        Args:
            file_path: Path of the file
            patterns: List of glob patterns

        Returns:
            True if file matches any pattern
        """
        # Normalize file path
        normalized_path = file_path.lstrip("./")

        for pattern in patterns:
            if self._file_matches_pattern(normalized_path, pattern):
                return True

        return False

    def _file_matches_pattern(
        self,
        file_path: str,
        pattern: str,
    ) -> bool:
        """Check if a file path matches a single glob pattern.

        Handles recursive wildcards (**) specially.

        Args:
            file_path: Normalized file path
            pattern: Glob pattern

        Returns:
            True if file matches pattern
        """
        # Handle recursive wildcard patterns
        if "**" in pattern:
            # Convert ** to a regex-like match
            # Split pattern on **
            parts = pattern.split("**")

            if len(parts) == 2:
                prefix, suffix = parts
                prefix = prefix.rstrip("/")
                suffix = suffix.lstrip("/")

                # File must start with prefix (if non-empty)
                if prefix and not file_path.startswith(prefix):
                    return False

                # File must end with suffix pattern (if non-empty)
                if suffix:
                    # Get the part of the file path after the prefix
                    if prefix:
                        remaining = file_path[len(prefix):].lstrip("/")
                    else:
                        remaining = file_path

                    # The suffix could match any part of the remaining path
                    # For now, use fnmatch on the basename or full remaining path
                    return fnmatch(remaining, f"*{suffix}") or fnmatch(
                        remaining.split("/")[-1], suffix
                    )

                # If no suffix, just check prefix
                return True

        # Standard glob matching
        return fnmatch(file_path, pattern)


# Singleton instance management
_ownership_service: Optional[OwnershipValidationService] = None


def get_ownership_validation_service(
    db: Optional[DatabaseService] = None,
    strict_mode: bool = False,
) -> OwnershipValidationService:
    """Get or create the OwnershipValidationService singleton.

    Args:
        db: Database service (required on first call)
        strict_mode: Whether to enforce strict ownership validation

    Returns:
        OwnershipValidationService instance
    """
    global _ownership_service

    if _ownership_service is None:
        if db is None:
            raise ValueError(
                "db is required on first call to get_ownership_validation_service"
            )
        _ownership_service = OwnershipValidationService(db=db, strict_mode=strict_mode)

    return _ownership_service


def reset_ownership_service() -> None:
    """Reset the singleton (for testing)."""
    global _ownership_service
    _ownership_service = None


class OwnershipConflictError(Exception):
    """Raised when ownership validation fails in strict mode."""

    def __init__(
        self,
        conflicts: List[str],
        conflicting_task_ids: List[str],
    ):
        self.conflicts = conflicts
        self.conflicting_task_ids = conflicting_task_ids
        message = f"Ownership conflicts detected: {', '.join(conflicts[:3])}"
        if len(conflicts) > 3:
            message += f" (and {len(conflicts) - 3} more)"
        super().__init__(message)
