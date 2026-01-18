"""Phase-specific evaluators for spec generation.

Each evaluator validates the output of its corresponding phase,
checking for required fields, structure, and quality criteria.

Enhanced with validation patterns from the spec-driven-dev skill scripts:
- Normative language detection for requirements
- Circular dependency detection for tasks
- ID format validation
- Traceability statistics
"""

from typing import Any, Dict, List, Optional

from spec_sandbox.evaluators.base import BaseEvaluator, EvalResult
from spec_sandbox.evaluators.validation import (
    ValidationResult,
    detect_circular_dependencies,
    validate_task_references,
    validate_requirement_text,
    validate_requirements_addressed,
    validate_component_responsibilities,
    validate_id_format,
    calculate_traceability_stats,
    detect_normative_language,
)


class ExploreEvaluator(BaseEvaluator):
    """Evaluator for EXPLORE phase output.

    Validates:
    - Has codebase_summary (non-empty string)
    - Has project_type (non-empty string)
    - Has tech_stack (list with items)
    - Has key_files (list with file info)
    - Has relevant_patterns (list, can be empty for greenfield)
    """

    threshold: float = 0.7

    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate EXPLORE phase output."""
        scores = {}
        issues = []

        # Check codebase_summary
        summary = output.get("codebase_summary", "")
        if isinstance(summary, str) and len(summary) > 50:
            scores["codebase_summary"] = 1.0
        elif isinstance(summary, str) and len(summary) > 0:
            scores["codebase_summary"] = 0.5
            issues.append("codebase_summary is too brief (< 50 chars)")
        else:
            scores["codebase_summary"] = 0.0
            issues.append("Missing or empty codebase_summary")

        # Check project_type
        project_type = output.get("project_type", "")
        if isinstance(project_type, str) and len(project_type) > 5:
            scores["project_type"] = 1.0
        else:
            scores["project_type"] = 0.0
            issues.append("Missing or invalid project_type")

        # Check tech_stack
        tech_stack = output.get("tech_stack", [])
        if isinstance(tech_stack, list) and len(tech_stack) >= 2:
            scores["tech_stack"] = 1.0
        elif isinstance(tech_stack, list) and len(tech_stack) >= 1:
            scores["tech_stack"] = 0.5
            issues.append("tech_stack has only 1 item")
        else:
            scores["tech_stack"] = 0.0
            issues.append("Missing or empty tech_stack")

        # Check key_files
        key_files = output.get("key_files", [])
        if isinstance(key_files, list) and len(key_files) >= 3:
            # Check that files have path and purpose
            valid_files = sum(
                1 for f in key_files
                if isinstance(f, dict) and f.get("path") and f.get("purpose")
            )
            scores["key_files"] = min(1.0, valid_files / 3)
            if valid_files < len(key_files):
                issues.append(f"Some key_files missing path or purpose")
        else:
            scores["key_files"] = 0.0
            issues.append("key_files should have at least 3 entries")

        # Check relevant_patterns (optional for greenfield)
        patterns = output.get("relevant_patterns", [])
        if isinstance(patterns, list):
            scores["relevant_patterns"] = 1.0
        else:
            scores["relevant_patterns"] = 0.5
            issues.append("relevant_patterns should be a list")

        # Calculate overall score
        weights = {
            "codebase_summary": 0.25,
            "project_type": 0.15,
            "tech_stack": 0.20,
            "key_files": 0.30,
            "relevant_patterns": 0.10,
        }

        total_score = sum(scores[k] * weights[k] for k in scores)

        feedback = None
        if issues:
            feedback = "Issues found:\n- " + "\n- ".join(issues)

        return self._create_result(
            score=total_score,
            feedback=feedback,
            details=scores,
        )


class RequirementsEvaluator(BaseEvaluator):
    """Evaluator for REQUIREMENTS phase output.

    Validates:
    - Has requirements list with EARS format
    - Each requirement has id, type, text, priority, acceptance_criteria
    - At least 2 acceptance criteria per requirement
    - Proper normative language (SHALL, SHOULD, MAY, MUST)
    - Valid ID format (REQ-XXX-YYY-NNN)
    - Has assumptions list

    Enhanced with validation from validate_specs.py:
    - Normative language detection
    - EARS trigger detection (WHEN, WHILE, WHERE, IF)
    """

    threshold: float = 0.7

    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate REQUIREMENTS phase output."""
        scores = {}
        issues = []
        warnings = []

        # Check requirements list
        requirements = output.get("requirements", [])
        if not isinstance(requirements, list) or len(requirements) == 0:
            return self._create_result(
                score=0.0,
                feedback="Missing or empty requirements list",
                details={"requirements": 0.0},
            )

        # Validate each requirement
        valid_reqs = 0
        ears_format_count = 0
        criteria_count = 0
        normative_count = 0
        valid_id_count = 0

        for req in requirements:
            if not isinstance(req, dict):
                continue

            # Check required fields
            has_id = bool(req.get("id"))
            has_type = bool(req.get("type"))
            has_text = bool(req.get("text"))
            has_priority = bool(req.get("priority"))

            if has_id and has_type and has_text and has_priority:
                valid_reqs += 1

            # Validate ID format
            req_id = req.get("id", "")
            is_valid_id, id_error = validate_id_format(req_id, "requirement", strict=False)
            if is_valid_id:
                valid_id_count += 1
            elif id_error:
                warnings.append(f"Requirement {req_id}: {id_error}")

            # Check normative language using validation module
            text = req.get("text", "")
            text_validation = validate_requirement_text(text)

            if text_validation.is_valid:
                normative_count += 1
            else:
                for error in text_validation.errors:
                    issues.append(f"Requirement {req_id}: {error.message}")
                for warning in text_validation.warnings:
                    warnings.append(f"Requirement {req_id}: {warning.message}")

            # Check EARS format (WHEN/SHALL pattern)
            detected = detect_normative_language(text)
            if detected["triggers"] and detected["keywords"]:
                ears_format_count += 1

            # Check acceptance criteria
            criteria = req.get("acceptance_criteria", [])
            if isinstance(criteria, list) and len(criteria) >= 2:
                criteria_count += 1

        req_count = len(requirements)

        # Score components
        scores["structure"] = valid_reqs / req_count if req_count > 0 else 0
        scores["normative_language"] = normative_count / req_count if req_count > 0 else 0
        scores["ears_format"] = ears_format_count / req_count if req_count > 0 else 0
        scores["acceptance_criteria"] = criteria_count / req_count if req_count > 0 else 0
        scores["id_format"] = valid_id_count / req_count if req_count > 0 else 0

        if scores["structure"] < 1.0:
            issues.append(f"{req_count - valid_reqs}/{req_count} requirements missing required fields")
        if scores["normative_language"] < 0.8:
            issues.append(f"Only {normative_count}/{req_count} requirements use proper normative language")
        if scores["ears_format"] < 0.5:
            warnings.append(f"Only {ears_format_count}/{req_count} requirements use full EARS format (WHEN/SHALL)")
        if scores["acceptance_criteria"] < 0.8:
            issues.append(f"Only {criteria_count}/{req_count} requirements have 2+ acceptance criteria")

        # Check assumptions
        assumptions = output.get("assumptions", [])
        if isinstance(assumptions, list) and len(assumptions) > 0:
            scores["assumptions"] = 1.0
        else:
            scores["assumptions"] = 0.5
            warnings.append("No assumptions documented")

        # Calculate overall score
        weights = {
            "structure": 0.25,
            "normative_language": 0.25,
            "ears_format": 0.15,
            "acceptance_criteria": 0.20,
            "id_format": 0.05,
            "assumptions": 0.10,
        }

        total_score = sum(scores[k] * weights[k] for k in scores)

        feedback_parts = []
        if issues:
            feedback_parts.append("Issues found:\n- " + "\n- ".join(issues))
        if warnings:
            feedback_parts.append("Warnings:\n- " + "\n- ".join(warnings))

        feedback = "\n\n".join(feedback_parts) if feedback_parts else None

        return self._create_result(
            score=total_score,
            feedback=feedback,
            details=scores,
        )


class DesignEvaluator(BaseEvaluator):
    """Evaluator for DESIGN phase output.

    Validates:
    - Has architecture_overview
    - Has components list with responsibilities
    - Has data_models (if applicable)
    - Has api_endpoints (if applicable)
    - Has testing_strategy

    Enhanced with validation from validate_specs.py:
    - Component responsibility validation
    - Coupling analysis
    """

    threshold: float = 0.7

    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate DESIGN phase output."""
        scores = {}
        issues = []
        warnings = []

        # Check architecture_overview
        overview = output.get("architecture_overview", "")
        if isinstance(overview, str) and len(overview) > 100:
            scores["architecture_overview"] = 1.0
        elif isinstance(overview, str) and len(overview) > 0:
            scores["architecture_overview"] = 0.5
            issues.append("architecture_overview is brief (< 100 chars)")
        else:
            scores["architecture_overview"] = 0.0
            issues.append("Missing architecture_overview")

        # Check components with enhanced validation
        components = output.get("components", [])
        if isinstance(components, list) and len(components) >= 1:
            # Check component structure
            valid_components = sum(
                1 for c in components
                if isinstance(c, dict) and c.get("name") and c.get("responsibility")
            )
            scores["components"] = valid_components / len(components) if components else 0

            if valid_components < len(components):
                issues.append("Some components missing name or responsibility")

            # Validate component responsibilities
            comp_validation = validate_component_responsibilities(components)
            for error in comp_validation.errors:
                issues.append(error.message)
            for warning in comp_validation.warnings:
                warnings.append(warning.message)
        else:
            scores["components"] = 0.0
            issues.append("No components defined")

        # Check data_models (optional but encouraged)
        data_models = output.get("data_models", [])
        if isinstance(data_models, list) and len(data_models) >= 1:
            scores["data_models"] = 1.0
            # Validate data model structure
            for dm in data_models:
                if isinstance(dm, dict):
                    if not dm.get("name"):
                        warnings.append("Data model missing 'name' field")
                    if not dm.get("fields") and not dm.get("purpose"):
                        warnings.append(f"Data model '{dm.get('name', 'unknown')}' missing fields/purpose")
        else:
            scores["data_models"] = 0.5  # Not always required

        # Check api_endpoints (optional but encouraged)
        api_endpoints = output.get("api_endpoints", [])
        if isinstance(api_endpoints, list) and len(api_endpoints) >= 1:
            scores["api_endpoints"] = 1.0
            # Validate endpoint structure
            for ep in api_endpoints:
                if isinstance(ep, dict):
                    if not ep.get("method"):
                        warnings.append(f"API endpoint missing 'method'")
                    if not ep.get("path"):
                        warnings.append(f"API endpoint missing 'path'")
        else:
            scores["api_endpoints"] = 0.5  # Not always required

        # Check testing_strategy
        testing = output.get("testing_strategy", "")
        if isinstance(testing, str) and len(testing) > 20:
            scores["testing_strategy"] = 1.0
        else:
            scores["testing_strategy"] = 0.0
            issues.append("Missing or brief testing_strategy")

        # Calculate overall score
        weights = {
            "architecture_overview": 0.30,
            "components": 0.30,
            "data_models": 0.15,
            "api_endpoints": 0.15,
            "testing_strategy": 0.10,
        }

        total_score = sum(scores[k] * weights[k] for k in scores)

        feedback_parts = []
        if issues:
            feedback_parts.append("Issues found:\n- " + "\n- ".join(issues))
        if warnings:
            feedback_parts.append("Warnings:\n- " + "\n- ".join(warnings))

        feedback = "\n\n".join(feedback_parts) if feedback_parts else None

        return self._create_result(
            score=total_score,
            feedback=feedback,
            details=scores,
        )


class TasksEvaluator(BaseEvaluator):
    """Evaluator for TASKS phase output.

    Validates:
    - Has tickets list (logical groupings of work)
    - Has tasks list (discrete work units)
    - Each ticket has id, title, description, priority, tasks list
    - Each task has id, title, description, type, parent_ticket
    - Tasks have valid dependencies (no circular, all refs exist)
    - Tasks are atomic (estimated 1-4 hours)
    - Has critical_path defined

    Enhanced with validation from spec_cli.py:
    - Circular dependency detection using DFS
    - Reference validation
    - Valid ID format (TKT-NNN for tickets, TSK-NNN for tasks)
    - Ticket-to-task relationship validation
    """

    threshold: float = 0.7

    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate TASKS phase output."""
        scores = {}
        issues = []
        warnings = []

        # Check tickets list
        tickets = output.get("tickets", [])
        if not isinstance(tickets, list) or len(tickets) == 0:
            # Legacy format support: if no tickets but has tasks, warn but continue
            if output.get("tasks"):
                warnings.append("No tickets defined - using legacy tasks-only format")
                scores["tickets"] = 0.5
            else:
                return self._create_result(
                    score=0.0,
                    feedback="Missing or empty tickets list",
                    details={"tickets": 0.0},
                )
        else:
            # Validate tickets
            valid_tickets = 0
            ticket_ids = set()
            ticket_task_refs = {}  # TKT-001 -> [TSK-001, TSK-002]

            for ticket in tickets:
                if not isinstance(ticket, dict):
                    continue

                ticket_id = ticket.get("id")
                if ticket_id:
                    ticket_ids.add(ticket_id)
                    ticket_task_refs[ticket_id] = ticket.get("tasks", [])

                    # Validate ID format (TKT-NNN)
                    if not (ticket_id.startswith("TKT-") or ticket_id.startswith("TICKET-")):
                        warnings.append(f"Ticket ID '{ticket_id}' should use TKT-NNN format")

                # Check required fields
                has_id = bool(ticket_id)
                has_title = bool(ticket.get("title"))
                has_description = bool(ticket.get("description"))
                has_priority = bool(ticket.get("priority"))
                has_tasks = isinstance(ticket.get("tasks"), list) and len(ticket.get("tasks", [])) > 0

                if has_id and has_title and has_description and has_priority and has_tasks:
                    valid_tickets += 1
                else:
                    missing = []
                    if not has_id:
                        missing.append("id")
                    if not has_title:
                        missing.append("title")
                    if not has_description:
                        missing.append("description")
                    if not has_priority:
                        missing.append("priority")
                    if not has_tasks:
                        missing.append("tasks list")
                    warnings.append(f"Ticket {ticket_id or 'unknown'} missing: {', '.join(missing)}")

            ticket_count = len(tickets)
            scores["tickets"] = valid_tickets / ticket_count if ticket_count > 0 else 0

            if scores["tickets"] < 1.0:
                issues.append(f"{ticket_count - valid_tickets}/{ticket_count} tickets missing required fields")

        # Check tasks list
        tasks = output.get("tasks", [])
        if not isinstance(tasks, list) or len(tasks) == 0:
            return self._create_result(
                score=0.0,
                feedback="Missing or empty tasks list",
                details={"tasks": 0.0},
            )

        # Validate each task
        valid_tasks = 0
        atomic_tasks = 0
        valid_id_count = 0
        tasks_with_parent = 0
        task_ids = set()

        # Get ticket IDs for parent validation
        ticket_ids = {t.get("id") for t in tickets if isinstance(t, dict) and t.get("id")}

        for task in tasks:
            if not isinstance(task, dict):
                continue

            task_id = task.get("id")
            if task_id:
                task_ids.add(task_id)

                # Validate ID format (TSK-NNN or TASK-NNN for legacy)
                is_valid_id, id_error = validate_id_format(task_id, "task", strict=False)
                if is_valid_id or task_id.startswith("TSK-"):
                    valid_id_count += 1
                elif id_error:
                    warnings.append(id_error)

            # Check required fields
            has_id = bool(task_id)
            has_title = bool(task.get("title"))
            has_description = bool(task.get("description")) or bool(task.get("objective"))
            has_type = bool(task.get("type"))

            if has_id and has_title and has_description and has_type:
                valid_tasks += 1

            # Check parent_ticket relationship
            parent_ticket = task.get("parent_ticket")
            if parent_ticket:
                if parent_ticket in ticket_ids:
                    tasks_with_parent += 1
                else:
                    warnings.append(f"Task {task_id} references unknown parent_ticket: {parent_ticket}")
            elif tickets:  # Only warn if tickets are expected
                warnings.append(f"Task {task_id} missing parent_ticket")

            # Check atomicity (1-4 hours estimate)
            estimate = task.get("estimated_hours", 0)
            if isinstance(estimate, (int, float)) and 0 < estimate <= 4:
                atomic_tasks += 1
            elif isinstance(estimate, (int, float)) and estimate > 4:
                warnings.append(f"Task {task_id} estimated at {estimate}h - consider breaking down (target: 1-4h)")

        task_count = len(tasks)

        scores["structure"] = valid_tasks / task_count if task_count > 0 else 0
        scores["atomicity"] = atomic_tasks / task_count if task_count > 0 else 0
        scores["id_format"] = valid_id_count / task_count if task_count > 0 else 0

        # Score parent ticket relationships (if tickets exist)
        if tickets:
            scores["parent_tickets"] = tasks_with_parent / task_count if task_count > 0 else 0
            if scores["parent_tickets"] < 0.8:
                issues.append(f"Only {tasks_with_parent}/{task_count} tasks have valid parent_ticket")
        else:
            scores["parent_tickets"] = 0.5  # N/A for legacy format

        if scores["structure"] < 1.0:
            issues.append(f"{task_count - valid_tasks}/{task_count} tasks missing required fields")
        if scores["atomicity"] < 0.7:
            issues.append(f"Only {atomic_tasks}/{task_count} tasks are atomic (1-4 hours)")

        # Check for circular dependencies using validation module
        circular_errors = detect_circular_dependencies(tasks)
        if circular_errors:
            scores["circular_deps"] = 0.0
            for error in circular_errors:
                issues.append(error.message)
        else:
            scores["circular_deps"] = 1.0

        # Check that all dependency references exist
        ref_errors = validate_task_references(tasks)
        if ref_errors:
            scores["dependencies"] = max(0.0, 1.0 - len(ref_errors) * 0.2)
            for error in ref_errors:
                issues.append(error.message)
        else:
            scores["dependencies"] = 1.0

        # Check critical_path
        critical_path = output.get("critical_path", [])
        if isinstance(critical_path, list) and len(critical_path) >= 1:
            # Validate critical path references valid tasks
            invalid_path = [t for t in critical_path if t not in task_ids]
            if invalid_path:
                scores["critical_path"] = 0.5
                warnings.append(f"critical_path references unknown tasks: {invalid_path}")
            else:
                scores["critical_path"] = 1.0
        else:
            scores["critical_path"] = 0.5
            warnings.append("No critical_path defined")

        # Check requirements traceability if requirements available in context
        requirements = context.get("requirements", {}).get("requirements", [])
        if requirements:
            trace_result = validate_requirements_addressed(tasks, requirements)
            if trace_result.errors:
                for error in trace_result.errors:
                    issues.append(error.message)
            if trace_result.warnings:
                for warning in trace_result.warnings:
                    warnings.append(warning.message)

        # Calculate overall score
        weights = {
            "tickets": 0.15,
            "structure": 0.20,
            "atomicity": 0.15,
            "id_format": 0.05,
            "parent_tickets": 0.15,
            "circular_deps": 0.15,
            "dependencies": 0.10,
            "critical_path": 0.05,
        }

        total_score = sum(scores.get(k, 0) * weights[k] for k in weights)

        feedback_parts = []
        if issues:
            feedback_parts.append("Issues found:\n- " + "\n- ".join(issues))
        if warnings:
            feedback_parts.append("Warnings:\n- " + "\n- ".join(warnings))

        feedback = "\n\n".join(feedback_parts) if feedback_parts else None

        return self._create_result(
            score=total_score,
            feedback=feedback,
            details=scores,
        )


class SyncEvaluator(BaseEvaluator):
    """Evaluator for SYNC phase output.

    Validates:
    - Has validation_results
    - Has coverage_matrix
    - Has spec_summary with traceability stats
    - Has ready_for_execution flag

    Enhanced with traceability stats format from ParseResult.get_traceability_stats()
    """

    threshold: float = 0.7

    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate SYNC phase output."""
        scores = {}
        issues = []
        warnings = []

        # Check validation_results
        validation = output.get("validation_results", {})
        if isinstance(validation, dict) and len(validation) > 0:
            scores["validation_results"] = 1.0

            # Check for any reported validation failures
            if validation.get("all_requirements_covered") is False:
                warnings.append("Not all requirements are covered by tasks")
            if validation.get("circular_dependencies"):
                issues.append("Circular dependencies detected in validation")
        else:
            scores["validation_results"] = 0.0
            issues.append("Missing validation_results")

        # Check coverage_matrix
        coverage = output.get("coverage_matrix", [])
        if isinstance(coverage, list):
            scores["coverage_matrix"] = 1.0

            # Analyze coverage
            if coverage:
                fully_covered = sum(
                    1 for item in coverage
                    if isinstance(item, dict) and item.get("status") == "fully_covered"
                )
                partially_covered = sum(
                    1 for item in coverage
                    if isinstance(item, dict) and item.get("status") == "partially_covered"
                )
                not_covered = sum(
                    1 for item in coverage
                    if isinstance(item, dict) and item.get("status") == "not_covered"
                )

                if not_covered > 0:
                    warnings.append(f"{not_covered} requirements not covered by any task")
                if partially_covered > 0:
                    warnings.append(f"{partially_covered} requirements only partially covered")
        else:
            scores["coverage_matrix"] = 0.0
            issues.append("Missing coverage_matrix")

        # Check spec_summary with traceability stats format
        summary = output.get("spec_summary", {})
        if isinstance(summary, dict):
            # Check for required fields (compatible with skill script format)
            has_total_tasks = "total_tasks" in summary
            has_total_reqs = "total_requirements" in summary
            has_hours = "total_estimated_hours" in summary

            if has_total_tasks and has_total_reqs:
                scores["spec_summary"] = 1.0
            elif has_total_tasks:
                scores["spec_summary"] = 0.7
                warnings.append("spec_summary missing total_requirements")
            else:
                scores["spec_summary"] = 0.5
                issues.append("spec_summary missing required fields")

            # Validate totals against context
            if context.get("tasks", {}).get("tasks"):
                actual_tasks = len(context["tasks"]["tasks"])
                reported_tasks = summary.get("total_tasks", 0)
                if actual_tasks != reported_tasks:
                    warnings.append(f"spec_summary reports {reported_tasks} tasks but found {actual_tasks}")
        else:
            scores["spec_summary"] = 0.0
            issues.append("Missing spec_summary")

        # Check ready_for_execution
        ready = output.get("ready_for_execution")
        if ready is True:
            scores["ready_for_execution"] = 1.0
        elif ready is False:
            scores["ready_for_execution"] = 0.5
            issues.append("Spec marked as NOT ready for execution")
        else:
            scores["ready_for_execution"] = 0.0
            issues.append("Missing ready_for_execution flag")

        # Calculate traceability stats if we have enough context
        if context.get("requirements") and context.get("tasks"):
            requirements = context["requirements"].get("requirements", [])
            tasks = context["tasks"].get("tasks", [])

            trace_stats = calculate_traceability_stats(requirements, tasks)

            # Add stats to details
            scores["traceability_coverage"] = trace_stats["requirements"]["coverage"] / 100

            if trace_stats["requirements"]["coverage"] < 80:
                warnings.append(
                    f"Only {trace_stats['requirements']['coverage']:.1f}% requirements coverage"
                )

        # Calculate overall score
        weights = {
            "validation_results": 0.30,
            "coverage_matrix": 0.25,
            "spec_summary": 0.25,
            "ready_for_execution": 0.20,
        }

        total_score = sum(scores.get(k, 0) * weights.get(k, 0) for k in weights)

        feedback_parts = []
        if issues:
            feedback_parts.append("Issues found:\n- " + "\n- ".join(issues))
        if warnings:
            feedback_parts.append("Warnings:\n- " + "\n- ".join(warnings))

        feedback = "\n\n".join(feedback_parts) if feedback_parts else None

        return self._create_result(
            score=total_score,
            feedback=feedback,
            details=scores,
        )


def get_evaluator(phase: str) -> BaseEvaluator:
    """Get the evaluator for a specific phase.

    Args:
        phase: Phase name (explore, requirements, design, tasks, sync)

    Returns:
        The appropriate evaluator instance
    """
    evaluators = {
        "explore": ExploreEvaluator(),
        "requirements": RequirementsEvaluator(),
        "design": DesignEvaluator(),
        "tasks": TasksEvaluator(),
        "sync": SyncEvaluator(),
    }

    if phase not in evaluators:
        raise ValueError(f"Unknown phase: {phase}")

    return evaluators[phase]
