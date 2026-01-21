"""Phase-specific evaluators for spec generation.

Each evaluator validates the output of its corresponding phase,
checking for required fields, structure, and quality criteria.

Enhanced with validation patterns from the spec-driven-dev skill scripts:
- Normative language detection for requirements
- Circular dependency detection for tasks
- ID format validation (REQ-FEATURE-CATEGORY-NNN, TKT-NNN, TSK-NNN)
- Traceability statistics
- Discovery questions validation (EXPLORE phase)
- Feature summary validation (EXPLORE phase)
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
    - Has codebase_summary (non-empty string, 50+ chars)
    - Has project_type (non-empty string)
    - Has tech_stack (list with 2+ items)
    - Has key_files (list with 3+ entries, each with path and purpose)
    - Has structure (dict with directory mappings)
    - Has conventions (dict with naming, testing, patterns)
    - Has discovery_questions (list with 5 categories)
    - Has feature_summary (dict with name, scope_in, scope_out)
    - Has relevant_patterns (list, can be empty for greenfield)
    """

    threshold: float = 0.7

    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate EXPLORE phase output."""
        scores = {}
        issues = []
        warnings = []

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
            warnings.append("tech_stack has only 1 item")
        else:
            scores["tech_stack"] = 0.0
            issues.append("Missing or empty tech_stack")

        # Check structure (directory mappings)
        structure = output.get("structure", {})
        if isinstance(structure, dict) and len(structure) >= 2:
            scores["structure"] = 1.0
        elif isinstance(structure, dict) and len(structure) >= 1:
            scores["structure"] = 0.5
            warnings.append("structure has minimal mappings")
        else:
            scores["structure"] = 0.0
            issues.append("Missing or empty structure mapping")

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
                warnings.append("Some key_files missing path or purpose")
        else:
            scores["key_files"] = 0.0
            issues.append("key_files should have at least 3 entries")

        # Check conventions
        conventions = output.get("conventions", {})
        if isinstance(conventions, dict):
            has_naming = bool(conventions.get("naming"))
            has_testing = bool(conventions.get("testing"))
            has_patterns = isinstance(conventions.get("patterns"), list)
            convention_score = (has_naming + has_testing + has_patterns) / 3
            scores["conventions"] = convention_score
            if convention_score < 1.0:
                warnings.append("conventions missing some fields (naming, testing, patterns)")
        else:
            scores["conventions"] = 0.0
            issues.append("Missing conventions object")

        # Check discovery_questions (NEW - from enhanced prompts)
        discovery = output.get("discovery_questions", [])
        if isinstance(discovery, list) and len(discovery) >= 3:
            # Check categories are present
            categories = {q.get("category") for q in discovery if isinstance(q, dict)}
            expected_categories = {"Problem & Value", "Users & Journeys", "Scope & Boundaries",
                                   "Technical Context", "Trade-offs & Risks"}
            coverage = len(categories & expected_categories) / len(expected_categories)
            scores["discovery_questions"] = coverage
            if coverage < 1.0:
                missing = expected_categories - categories
                warnings.append(f"Missing discovery categories: {missing}")
        elif isinstance(discovery, list) and len(discovery) >= 1:
            scores["discovery_questions"] = 0.5
            warnings.append("discovery_questions has fewer than 3 categories")
        else:
            scores["discovery_questions"] = 0.0
            issues.append("Missing discovery_questions - critical for requirements gathering")

        # Check feature_summary (NEW - from enhanced prompts)
        feature_summary = output.get("feature_summary", {})
        if isinstance(feature_summary, dict):
            has_name = bool(feature_summary.get("name"))
            has_scope_in = isinstance(feature_summary.get("scope_in"), list)
            has_scope_out = isinstance(feature_summary.get("scope_out"), list)
            has_problem = bool(feature_summary.get("problem_statement"))

            summary_score = (has_name + has_scope_in + has_scope_out + has_problem) / 4
            scores["feature_summary"] = summary_score

            if not has_name:
                issues.append("feature_summary missing 'name' field")
            if not has_scope_in:
                warnings.append("feature_summary missing 'scope_in' list")
            if not has_scope_out:
                warnings.append("feature_summary missing 'scope_out' list")
        else:
            scores["feature_summary"] = 0.0
            issues.append("Missing feature_summary - critical for scoping")

        # Check relevant_patterns (optional for greenfield)
        patterns = output.get("relevant_patterns", [])
        if isinstance(patterns, list):
            scores["relevant_patterns"] = 1.0
        else:
            scores["relevant_patterns"] = 0.5
            warnings.append("relevant_patterns should be a list")

        # Check related_to_feature
        related = output.get("related_to_feature", [])
        if isinstance(related, list):
            scores["related_to_feature"] = 1.0
        else:
            scores["related_to_feature"] = 0.5
            warnings.append("related_to_feature should be a list")

        # Calculate overall score with updated weights
        weights = {
            "codebase_summary": 0.12,
            "project_type": 0.08,
            "tech_stack": 0.10,
            "structure": 0.10,
            "key_files": 0.15,
            "conventions": 0.10,
            "discovery_questions": 0.15,  # Important for quality specs
            "feature_summary": 0.12,       # Important for scoping
            "relevant_patterns": 0.04,
            "related_to_feature": 0.04,
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


class PRDEvaluator(BaseEvaluator):
    """Evaluator for PRD phase output.

    Validates:
    - Has overview (feature_name, one_liner, problem_statement, solution_summary)
    - Has goals (primary, secondary, success_metrics)
    - Has users (primary, secondary with role, description, needs)
    - Has user_stories (list with US-NNN format, role, want, benefit, priority, acceptance_criteria)
    - Has scope (in_scope, out_of_scope, dependencies)
    - Has assumptions (list)
    - Has constraints (technical, business)
    - Has risks (list with description, impact, mitigation)
    - Has open_questions (list)
    """

    threshold: float = 0.7

    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate PRD phase output."""
        scores = {}
        issues = []
        warnings = []

        # Check overview
        overview = output.get("overview", {})
        if isinstance(overview, dict):
            has_feature_name = bool(overview.get("feature_name"))
            has_one_liner = bool(overview.get("one_liner"))
            has_problem = bool(overview.get("problem_statement")) and len(overview.get("problem_statement", "")) > 30
            has_solution = bool(overview.get("solution_summary")) and len(overview.get("solution_summary", "")) > 30

            overview_score = (has_feature_name + has_one_liner + has_problem + has_solution) / 4
            scores["overview"] = overview_score

            if not has_feature_name:
                issues.append("overview missing 'feature_name'")
            if not has_one_liner:
                warnings.append("overview missing 'one_liner'")
            if not has_problem:
                issues.append("overview missing or brief 'problem_statement' (need 30+ chars)")
            if not has_solution:
                issues.append("overview missing or brief 'solution_summary' (need 30+ chars)")
        else:
            scores["overview"] = 0.0
            issues.append("Missing overview section")

        # Check goals
        goals = output.get("goals", {})
        if isinstance(goals, dict):
            has_primary = isinstance(goals.get("primary"), list) and len(goals.get("primary", [])) >= 1
            has_secondary = isinstance(goals.get("secondary"), list)
            success_metrics = goals.get("success_metrics", [])
            has_metrics = isinstance(success_metrics, list) and len(success_metrics) >= 1

            goals_score = (has_primary + has_secondary * 0.5 + has_metrics) / 2.5
            scores["goals"] = goals_score

            if not has_primary:
                issues.append("goals missing 'primary' goals list")
            if not has_metrics:
                issues.append("goals missing 'success_metrics' - critical for measuring success")

            # Validate success metrics structure
            if has_metrics:
                valid_metrics = 0
                for metric in success_metrics:
                    if isinstance(metric, dict):
                        has_metric_name = bool(metric.get("metric"))
                        has_target = bool(metric.get("target"))
                        has_measurement = bool(metric.get("measurement"))
                        if has_metric_name and has_target:
                            valid_metrics += 1
                        if not has_measurement:
                            warnings.append(f"Metric '{metric.get('metric', 'unknown')}' missing 'measurement' method")

                if valid_metrics < len(success_metrics):
                    warnings.append(f"{len(success_metrics) - valid_metrics}/{len(success_metrics)} metrics missing required fields")
        else:
            scores["goals"] = 0.0
            issues.append("Missing goals section")

        # Check users
        users = output.get("users", {})
        if isinstance(users, dict):
            primary_users = users.get("primary", [])
            secondary_users = users.get("secondary", [])
            has_primary = isinstance(primary_users, list) and len(primary_users) >= 1
            has_secondary = isinstance(secondary_users, list)

            users_score = 0.0
            if has_primary:
                # Validate primary user structure
                valid_users = 0
                for user in primary_users:
                    if isinstance(user, dict):
                        has_role = bool(user.get("role"))
                        has_description = bool(user.get("description"))
                        has_needs = isinstance(user.get("needs"), list)
                        if has_role and has_description:
                            valid_users += 1
                        if not has_needs:
                            warnings.append(f"User '{user.get('role', 'unknown')}' missing 'needs' list")

                users_score = valid_users / len(primary_users) if primary_users else 0
            else:
                issues.append("users missing 'primary' users list")

            scores["users"] = users_score
        else:
            scores["users"] = 0.0
            issues.append("Missing users section")

        # Check user_stories (critical for PRD)
        user_stories = output.get("user_stories", [])
        if isinstance(user_stories, list) and len(user_stories) >= 1:
            valid_stories = 0
            stories_with_acceptance = 0
            valid_id_count = 0

            for story in user_stories:
                if not isinstance(story, dict):
                    continue

                story_id = story.get("id", "")
                has_id = bool(story_id)
                has_role = bool(story.get("role"))
                has_want = bool(story.get("want"))
                has_benefit = bool(story.get("benefit"))
                has_priority = bool(story.get("priority"))
                has_acceptance = isinstance(story.get("acceptance_criteria"), list) and len(story.get("acceptance_criteria", [])) >= 1

                # Validate ID format (US-NNN)
                if story_id.startswith("US-"):
                    valid_id_count += 1
                elif story_id:
                    warnings.append(f"User story ID '{story_id}' should use US-NNN format")

                if has_id and has_role and has_want and has_benefit and has_priority:
                    valid_stories += 1
                else:
                    missing = []
                    if not has_id:
                        missing.append("id")
                    if not has_role:
                        missing.append("role")
                    if not has_want:
                        missing.append("want")
                    if not has_benefit:
                        missing.append("benefit")
                    if not has_priority:
                        missing.append("priority")
                    if missing:
                        warnings.append(f"User story {story_id or 'unknown'} missing: {', '.join(missing)}")

                if has_acceptance:
                    stories_with_acceptance += 1
                else:
                    warnings.append(f"User story {story_id} missing acceptance_criteria")

            story_count = len(user_stories)
            scores["user_stories_structure"] = valid_stories / story_count if story_count > 0 else 0
            scores["user_stories_id_format"] = valid_id_count / story_count if story_count > 0 else 0
            scores["user_stories_acceptance"] = stories_with_acceptance / story_count if story_count > 0 else 0

            if scores["user_stories_structure"] < 1.0:
                issues.append(f"{story_count - valid_stories}/{story_count} user stories missing required fields")
            if scores["user_stories_acceptance"] < 0.8:
                issues.append(f"Only {stories_with_acceptance}/{story_count} user stories have acceptance criteria")
        else:
            scores["user_stories_structure"] = 0.0
            scores["user_stories_id_format"] = 0.0
            scores["user_stories_acceptance"] = 0.0
            issues.append("Missing or empty user_stories list - critical for PRD")

        # Check scope
        scope = output.get("scope", {})
        if isinstance(scope, dict):
            has_in_scope = isinstance(scope.get("in_scope"), list) and len(scope.get("in_scope", [])) >= 1
            has_out_of_scope = isinstance(scope.get("out_of_scope"), list) and len(scope.get("out_of_scope", [])) >= 1
            has_dependencies = isinstance(scope.get("dependencies"), list)

            scope_score = (has_in_scope + has_out_of_scope + has_dependencies * 0.5) / 2.5
            scores["scope"] = scope_score

            if not has_in_scope:
                issues.append("scope missing 'in_scope' list")
            if not has_out_of_scope:
                warnings.append("scope missing 'out_of_scope' list - important for boundary setting")
        else:
            scores["scope"] = 0.0
            issues.append("Missing scope section")

        # Check assumptions
        assumptions = output.get("assumptions", [])
        if isinstance(assumptions, list) and len(assumptions) >= 1:
            scores["assumptions"] = 1.0
        else:
            scores["assumptions"] = 0.5
            warnings.append("No assumptions documented")

        # Check constraints
        constraints = output.get("constraints", {})
        if isinstance(constraints, dict):
            has_technical = isinstance(constraints.get("technical"), list) and len(constraints.get("technical", [])) >= 1
            has_business = isinstance(constraints.get("business"), list)

            constraints_score = (has_technical + has_business * 0.5) / 1.5
            scores["constraints"] = constraints_score

            if not has_technical:
                warnings.append("constraints missing 'technical' constraints")
        else:
            scores["constraints"] = 0.5
            warnings.append("Missing constraints section")

        # Check risks
        risks = output.get("risks", [])
        if isinstance(risks, list) and len(risks) >= 1:
            valid_risks = 0
            for risk in risks:
                if isinstance(risk, dict):
                    has_description = bool(risk.get("description"))
                    has_impact = bool(risk.get("impact"))
                    has_mitigation = bool(risk.get("mitigation"))
                    if has_description and has_impact:
                        valid_risks += 1
                    if not has_mitigation:
                        warnings.append(f"Risk '{risk.get('description', 'unknown')[:30]}...' missing mitigation strategy")

            scores["risks"] = valid_risks / len(risks) if risks else 0
        else:
            scores["risks"] = 0.3
            warnings.append("No risks documented - consider risk analysis")

        # Check open_questions
        open_questions = output.get("open_questions", [])
        if isinstance(open_questions, list):
            scores["open_questions"] = 1.0
        else:
            scores["open_questions"] = 0.5
            warnings.append("open_questions should be a list")

        # Calculate overall score with weights
        weights = {
            "overview": 0.15,
            "goals": 0.15,
            "users": 0.10,
            "user_stories_structure": 0.20,
            "user_stories_id_format": 0.05,
            "user_stories_acceptance": 0.10,
            "scope": 0.10,
            "assumptions": 0.03,
            "constraints": 0.05,
            "risks": 0.05,
            "open_questions": 0.02,
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


class RequirementsEvaluator(BaseEvaluator):
    """Evaluator for REQUIREMENTS phase output.

    Validates:
    - Has feature_name
    - Has requirements list with EARS format
    - Each requirement has id (REQ-FEATURE-CATEGORY-NNN), type, text, priority, acceptance_criteria
    - At least 2 acceptance criteria per requirement
    - Proper normative language (SHALL, SHOULD, MAY, MUST)
    - Valid ID format (REQ-{FEATURE}-{CATEGORY}-{NNN})
    - Has assumptions list
    - Has out_of_scope list
    - Has traceability object

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

        # Check feature_name
        feature_name = output.get("feature_name", "")
        if isinstance(feature_name, str) and len(feature_name) > 0:
            scores["feature_name"] = 1.0
        else:
            scores["feature_name"] = 0.5
            warnings.append("Missing feature_name")

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
            has_title = bool(req.get("title"))

            if has_id and has_type and has_text and has_priority:
                valid_reqs += 1

            # Validate ID format (REQ-FEATURE-CATEGORY-NNN)
            req_id = req.get("id", "")
            # Accept both strict (REQ-FEATURE-CATEGORY-NNN) and simple (REQ-NNN) formats
            if req_id.startswith("REQ-"):
                parts = req_id.split("-")
                if len(parts) >= 2:  # At minimum REQ-NNN
                    valid_id_count += 1
                else:
                    warnings.append(f"Requirement {req_id}: should follow REQ-FEATURE-CATEGORY-NNN format")
            else:
                warnings.append(f"Requirement ID '{req_id}' should start with 'REQ-'")

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
            elif detected["keywords"]:
                # Has normative language but no trigger - ubiquitous requirement
                ears_format_count += 0.5

            # Check acceptance criteria
            criteria = req.get("acceptance_criteria", [])
            if isinstance(criteria, list) and len(criteria) >= 2:
                criteria_count += 1
            elif isinstance(criteria, list) and len(criteria) >= 1:
                warnings.append(f"Requirement {req_id} has only 1 acceptance criterion (need 2+)")

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

        # Check out_of_scope (NEW - from enhanced prompts)
        out_of_scope = output.get("out_of_scope", [])
        if isinstance(out_of_scope, list) and len(out_of_scope) > 0:
            scores["out_of_scope"] = 1.0
        else:
            scores["out_of_scope"] = 0.5
            warnings.append("No out_of_scope items documented - important for boundary setting")

        # Check traceability (NEW - from enhanced prompts)
        traceability = output.get("traceability", {})
        if isinstance(traceability, dict) and len(traceability) > 0:
            scores["traceability"] = 1.0
        else:
            scores["traceability"] = 0.5
            warnings.append("No traceability links to PRD/design")

        # Calculate overall score with updated weights
        weights = {
            "feature_name": 0.05,
            "structure": 0.20,
            "normative_language": 0.20,
            "ears_format": 0.15,
            "acceptance_criteria": 0.20,
            "id_format": 0.05,
            "assumptions": 0.05,
            "out_of_scope": 0.05,
            "traceability": 0.05,
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


class DesignEvaluator(BaseEvaluator):
    """Evaluator for DESIGN phase output.

    Validates:
    - Has feature_name
    - Has architecture_overview (100+ chars)
    - Has components list with name, type, responsibility, interfaces
    - Has data_models with name, table_name, fields, indexes
    - Has api_endpoints with method, path, description, schemas
    - Has testing_strategy
    - Has error_handling strategy
    - Has security_considerations
    - Has integration_points

    Enhanced with validation from validate_specs.py:
    - Component responsibility validation
    - API endpoint completeness
    - Data model completeness
    """

    threshold: float = 0.7

    async def evaluate(self, output: Dict[str, Any], context: Dict[str, Any]) -> EvalResult:
        """Evaluate DESIGN phase output."""
        scores = {}
        issues = []
        warnings = []

        # Check feature_name
        feature_name = output.get("feature_name", "")
        if isinstance(feature_name, str) and len(feature_name) > 0:
            scores["feature_name"] = 1.0
        else:
            scores["feature_name"] = 0.5
            warnings.append("Missing feature_name")

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
            valid_components = 0
            for c in components:
                if not isinstance(c, dict):
                    continue
                has_name = bool(c.get("name"))
                has_type = bool(c.get("type"))
                has_responsibility = bool(c.get("responsibility"))
                has_interfaces = isinstance(c.get("interfaces"), list)

                if has_name and has_responsibility:
                    valid_components += 1
                if not has_type:
                    warnings.append(f"Component '{c.get('name', 'unknown')}' missing 'type'")
                if not has_interfaces:
                    warnings.append(f"Component '{c.get('name', 'unknown')}' missing 'interfaces'")

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

        # Check data_models with enhanced validation
        data_models = output.get("data_models", [])
        if isinstance(data_models, list) and len(data_models) >= 1:
            valid_models = 0
            for dm in data_models:
                if not isinstance(dm, dict):
                    continue
                has_name = bool(dm.get("name"))
                has_table = bool(dm.get("table_name"))
                has_fields = isinstance(dm.get("fields"), dict) and len(dm.get("fields", {})) > 0
                has_indexes = isinstance(dm.get("indexes"), list)

                if has_name and has_fields:
                    valid_models += 1
                if not has_table:
                    warnings.append(f"Data model '{dm.get('name', 'unknown')}' missing 'table_name'")
                if not has_indexes:
                    warnings.append(f"Data model '{dm.get('name', 'unknown')}' missing 'indexes'")

            scores["data_models"] = valid_models / len(data_models) if data_models else 0
        else:
            scores["data_models"] = 0.3  # Not always required, but encouraged

        # Check api_endpoints with enhanced validation
        api_endpoints = output.get("api_endpoints", [])
        if isinstance(api_endpoints, list) and len(api_endpoints) >= 1:
            valid_endpoints = 0
            for ep in api_endpoints:
                if not isinstance(ep, dict):
                    continue
                has_method = bool(ep.get("method"))
                has_path = bool(ep.get("path"))
                has_description = bool(ep.get("description"))
                has_auth = "auth_required" in ep
                has_response = bool(ep.get("response_schema"))

                if has_method and has_path and has_description:
                    valid_endpoints += 1
                if not has_auth:
                    warnings.append(f"API endpoint {ep.get('method', '?')} {ep.get('path', '?')} missing 'auth_required'")
                if not has_response:
                    warnings.append(f"API endpoint {ep.get('method', '?')} {ep.get('path', '?')} missing 'response_schema'")

            scores["api_endpoints"] = valid_endpoints / len(api_endpoints) if api_endpoints else 0
        else:
            scores["api_endpoints"] = 0.3  # Not always required

        # Check testing_strategy
        testing = output.get("testing_strategy", {})
        if isinstance(testing, dict) and len(testing) > 0:
            has_unit = isinstance(testing.get("unit_tests"), list)
            has_integration = isinstance(testing.get("integration_tests"), list)
            testing_score = (has_unit + has_integration) / 2
            scores["testing_strategy"] = testing_score
            if not has_unit:
                warnings.append("testing_strategy missing 'unit_tests'")
            if not has_integration:
                warnings.append("testing_strategy missing 'integration_tests'")
        elif isinstance(testing, str) and len(testing) > 20:
            scores["testing_strategy"] = 0.7
        else:
            scores["testing_strategy"] = 0.0
            issues.append("Missing or brief testing_strategy")

        # Check error_handling (NEW - from enhanced prompts)
        error_handling = output.get("error_handling", {})
        if isinstance(error_handling, dict) and len(error_handling) > 0:
            scores["error_handling"] = 1.0
        else:
            scores["error_handling"] = 0.3
            warnings.append("Missing error_handling strategy")

        # Check security_considerations (NEW - from enhanced prompts)
        security = output.get("security_considerations", [])
        if isinstance(security, list) and len(security) >= 2:
            scores["security_considerations"] = 1.0
        elif isinstance(security, list) and len(security) >= 1:
            scores["security_considerations"] = 0.7
            warnings.append("security_considerations has only 1 item")
        else:
            scores["security_considerations"] = 0.3
            warnings.append("Missing security_considerations")

        # Check integration_points (NEW - from enhanced prompts)
        integration = output.get("integration_points", [])
        if isinstance(integration, list) and len(integration) >= 1:
            scores["integration_points"] = 1.0
        else:
            scores["integration_points"] = 0.5
            warnings.append("Missing integration_points")

        # Calculate overall score with updated weights
        weights = {
            "feature_name": 0.05,
            "architecture_overview": 0.15,
            "components": 0.20,
            "data_models": 0.15,
            "api_endpoints": 0.15,
            "testing_strategy": 0.10,
            "error_handling": 0.08,
            "security_considerations": 0.07,
            "integration_points": 0.05,
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


class TasksEvaluator(BaseEvaluator):
    """Evaluator for TASKS phase output.

    Validates:
    - Has feature_name
    - Has tickets list (TKT-NNN format IDs)
    - Has tasks list (TSK-NNN format IDs)
    - Each ticket has id, title, description, priority, estimate, tasks, acceptance_criteria
    - Each task has id, title, description, type, parent_ticket, estimated_hours
    - Tasks have valid dependencies (no circular, all refs exist)
    - Tasks are atomic (estimated 1-4 hours)
    - Has critical_path defined
    - Has total_estimated_hours

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

        # Check feature_name
        feature_name = output.get("feature_name", "")
        if isinstance(feature_name, str) and len(feature_name) > 0:
            scores["feature_name"] = 1.0
        else:
            scores["feature_name"] = 0.5
            warnings.append("Missing feature_name")

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
                    if not ticket_id.startswith("TKT-"):
                        warnings.append(f"Ticket ID '{ticket_id}' should use TKT-NNN format")

                # Check required fields
                has_id = bool(ticket_id)
                has_title = bool(ticket.get("title"))
                has_description = bool(ticket.get("description"))
                has_priority = bool(ticket.get("priority"))
                has_estimate = bool(ticket.get("estimate"))
                has_tasks = isinstance(ticket.get("tasks"), list) and len(ticket.get("tasks", [])) > 0
                has_acceptance = isinstance(ticket.get("acceptance_criteria"), list)

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
                    if missing:
                        warnings.append(f"Ticket {ticket_id or 'unknown'} missing: {', '.join(missing)}")

                if not has_estimate:
                    warnings.append(f"Ticket {ticket_id} missing 'estimate' (S/M/L/XL)")
                if not has_acceptance:
                    warnings.append(f"Ticket {ticket_id} missing 'acceptance_criteria'")

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
        tasks_with_files = 0
        task_ids = set()

        # Get ticket IDs for parent validation
        ticket_ids = {t.get("id") for t in tickets if isinstance(t, dict) and t.get("id")}

        for task in tasks:
            if not isinstance(task, dict):
                continue

            task_id = task.get("id")
            if task_id:
                task_ids.add(task_id)

                # Validate ID format (TSK-NNN)
                if task_id.startswith("TSK-"):
                    valid_id_count += 1
                else:
                    warnings.append(f"Task ID '{task_id}' should use TSK-NNN format")

            # Check required fields
            has_id = bool(task_id)
            has_title = bool(task.get("title"))
            has_description = bool(task.get("description"))
            has_type = bool(task.get("type"))
            has_priority = bool(task.get("priority"))

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

            # Check files_to_create/files_to_modify
            has_files = (
                isinstance(task.get("files_to_create"), list) or
                isinstance(task.get("files_to_modify"), list)
            )
            if has_files:
                tasks_with_files += 1
            else:
                warnings.append(f"Task {task_id} missing files_to_create/files_to_modify")

            # Check atomicity (1-4 hours estimate)
            estimate = task.get("estimated_hours", 0)
            if isinstance(estimate, (int, float)) and 0 < estimate <= 4:
                atomic_tasks += 1
            elif isinstance(estimate, (int, float)) and estimate > 4:
                warnings.append(f"Task {task_id} estimated at {estimate}h - consider breaking down (target: 1-4h)")

            # Check acceptance_criteria
            if not isinstance(task.get("acceptance_criteria"), list):
                warnings.append(f"Task {task_id} missing acceptance_criteria")

            # Check requirements_addressed
            if not isinstance(task.get("requirements_addressed"), list):
                warnings.append(f"Task {task_id} missing requirements_addressed")

        task_count = len(tasks)

        scores["structure"] = valid_tasks / task_count if task_count > 0 else 0
        scores["atomicity"] = atomic_tasks / task_count if task_count > 0 else 0
        scores["id_format"] = valid_id_count / task_count if task_count > 0 else 0
        scores["files_specified"] = tasks_with_files / task_count if task_count > 0 else 0

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

        # Check total_estimated_hours
        total_hours = output.get("total_estimated_hours", 0)
        if isinstance(total_hours, (int, float)) and total_hours > 0:
            scores["total_hours"] = 1.0
        else:
            scores["total_hours"] = 0.5
            warnings.append("Missing or invalid total_estimated_hours")

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

        # Calculate overall score with updated weights
        weights = {
            "feature_name": 0.03,
            "tickets": 0.12,
            "structure": 0.15,
            "atomicity": 0.12,
            "id_format": 0.05,
            "files_specified": 0.08,
            "parent_tickets": 0.12,
            "circular_deps": 0.15,
            "dependencies": 0.08,
            "critical_path": 0.05,
            "total_hours": 0.05,
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


class SyncEvaluator(BaseEvaluator):
    """Evaluator for SYNC phase output.

    Validates:
    - Has validation_results with all checks
    - Has coverage_matrix with requirement coverage
    - Has traceability_stats
    - Has dependency_analysis
    - Has spec_summary with totals
    - Has ready_for_execution flag
    - Has recommendations list

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
            # Check for required validation fields
            has_req_covered = "all_requirements_covered" in validation
            has_deps_valid = "no_circular_dependencies" in validation
            has_ids_valid = "all_ids_valid" in validation

            validation_score = (has_req_covered + has_deps_valid + has_ids_valid) / 3
            scores["validation_results"] = validation_score

            # Check for any reported validation failures
            if validation.get("all_requirements_covered") is False:
                issues.append("Not all requirements are covered by tasks")
            if validation.get("no_circular_dependencies") is False:
                issues.append("Circular dependencies detected in validation")
            if validation.get("issues_found") and len(validation["issues_found"]) > 0:
                for issue in validation["issues_found"][:3]:  # Limit to 3
                    issues.append(f"Validation issue: {issue}")
        else:
            scores["validation_results"] = 0.0
            issues.append("Missing validation_results")

        # Check coverage_matrix
        coverage = output.get("coverage_matrix", [])
        if isinstance(coverage, list) and len(coverage) > 0:
            scores["coverage_matrix"] = 1.0

            # Analyze coverage
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
                issues.append(f"{not_covered} requirements not covered by any task")
            if partially_covered > 0:
                warnings.append(f"{partially_covered} requirements only partially covered")
        else:
            scores["coverage_matrix"] = 0.0
            issues.append("Missing coverage_matrix")

        # Check traceability_stats (NEW - from enhanced prompts)
        trace_stats = output.get("traceability_stats", {})
        if isinstance(trace_stats, dict) and len(trace_stats) > 0:
            has_reqs = isinstance(trace_stats.get("requirements"), dict)
            has_tickets = isinstance(trace_stats.get("tickets"), dict)
            has_tasks = isinstance(trace_stats.get("tasks"), dict)
            has_deps = isinstance(trace_stats.get("dependencies"), dict)

            stats_score = (has_reqs + has_tickets + has_tasks + has_deps) / 4
            scores["traceability_stats"] = stats_score

            if not has_reqs:
                warnings.append("traceability_stats missing 'requirements'")
            if not has_tasks:
                warnings.append("traceability_stats missing 'tasks'")
        else:
            scores["traceability_stats"] = 0.0
            issues.append("Missing traceability_stats")

        # Check dependency_analysis (NEW - from enhanced prompts)
        dep_analysis = output.get("dependency_analysis", {})
        if isinstance(dep_analysis, dict) and len(dep_analysis) > 0:
            has_task_graph = isinstance(dep_analysis.get("task_dependency_graph"), dict)
            has_critical = isinstance(dep_analysis.get("critical_path"), list)

            dep_score = (has_task_graph + has_critical) / 2
            scores["dependency_analysis"] = dep_score

            if not has_task_graph:
                warnings.append("dependency_analysis missing 'task_dependency_graph'")
            if not has_critical:
                warnings.append("dependency_analysis missing 'critical_path'")
        else:
            scores["dependency_analysis"] = 0.0
            issues.append("Missing dependency_analysis")

        # Check spec_summary
        summary = output.get("spec_summary", {})
        if isinstance(summary, dict):
            # Check for required fields
            has_total_tasks = "total_tasks" in summary
            has_total_reqs = "total_requirements" in summary
            has_hours = "total_estimated_hours" in summary
            has_coverage = "requirement_coverage_percent" in summary

            summary_score = (has_total_tasks + has_total_reqs + has_hours + has_coverage) / 4
            scores["spec_summary"] = summary_score

            if not has_total_tasks:
                warnings.append("spec_summary missing 'total_tasks'")
            if not has_total_reqs:
                warnings.append("spec_summary missing 'total_requirements'")
            if not has_coverage:
                warnings.append("spec_summary missing 'requirement_coverage_percent'")

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

        # Check blockers
        blockers = output.get("blockers", [])
        if isinstance(blockers, list):
            if len(blockers) > 0:
                scores["blockers"] = 0.5
                for blocker in blockers[:3]:
                    issues.append(f"Blocker: {blocker}")
            else:
                scores["blockers"] = 1.0
        else:
            scores["blockers"] = 0.5
            warnings.append("Missing blockers list")

        # Check recommendations (NEW - from enhanced prompts)
        recommendations = output.get("recommendations", [])
        if isinstance(recommendations, list) and len(recommendations) > 0:
            scores["recommendations"] = 1.0
        else:
            scores["recommendations"] = 0.5
            warnings.append("No recommendations provided")

        # Calculate traceability stats if we have enough context
        if context.get("requirements") and context.get("tasks"):
            requirements = context["requirements"].get("requirements", [])
            tasks = context["tasks"].get("tasks", [])

            calc_stats = calculate_traceability_stats(requirements, tasks)

            # Add stats to details
            scores["traceability_coverage"] = calc_stats["requirements"]["coverage"] / 100

            if calc_stats["requirements"]["coverage"] < 80:
                warnings.append(
                    f"Only {calc_stats['requirements']['coverage']:.1f}% requirements coverage"
                )

        # Calculate overall score with updated weights
        weights = {
            "validation_results": 0.20,
            "coverage_matrix": 0.15,
            "traceability_stats": 0.15,
            "dependency_analysis": 0.10,
            "spec_summary": 0.15,
            "ready_for_execution": 0.15,
            "blockers": 0.05,
            "recommendations": 0.05,
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
        phase: Phase name (explore, prd, requirements, design, tasks, sync)

    Returns:
        The appropriate evaluator instance
    """
    evaluators = {
        "explore": ExploreEvaluator(),
        "prd": PRDEvaluator(),
        "requirements": RequirementsEvaluator(),
        "design": DesignEvaluator(),
        "tasks": TasksEvaluator(),
        "sync": SyncEvaluator(),
    }

    if phase not in evaluators:
        raise ValueError(f"Unknown phase: {phase}")

    return evaluators[phase]
