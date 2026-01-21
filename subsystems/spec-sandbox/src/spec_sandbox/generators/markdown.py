"""Markdown generator for spec artifacts.

Generates markdown files with YAML frontmatter from phase outputs.
These files match the templates from the spec-driven-dev skill:
- requirements_template.md - EARS format requirements
- design_template.md - Product design document
- task_template.md - Individual task files
- ticket_template.md - Parent tickets containing tasks
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import yaml


class MarkdownGenerator:
    """Generator for markdown files with YAML frontmatter.

    Produces markdown documentation for each spec phase:
    - Requirements document with EARS format
    - Design document with architecture diagrams
    - Ticket files with task breakdown
    - Task files with implementation details
    - Spec summary with coverage matrix

    Directory Structure (matches spec-driven-dev skill):
    ```
    .omoi_os/
    ├── requirements/
    │   └── REQ-{feature}.md
    ├── designs/
    │   └── {feature}.md
    ├── tickets/
    │   └── TKT-NNN.md
    ├── tasks/
    │   ├── index.md
    │   └── TSK-NNN.md
    └── SPEC_SUMMARY.md
    ```
    """

    def __init__(
        self,
        output_dir: Path,
        spec_id: str,
        spec_title: str,
        use_omoi_os_structure: bool = True,
    ) -> None:
        self.base_output_dir = output_dir
        # Use .omoi_os subdirectory by default (matches skill structure)
        if use_omoi_os_structure:
            self.output_dir = output_dir / ".omoi_os"
        else:
            self.output_dir = output_dir
        self.spec_id = spec_id
        self.spec_title = spec_title
        self.created_date = datetime.now().strftime("%Y-%m-%d")
        self.use_omoi_os_structure = use_omoi_os_structure

    def generate_all(
        self,
        explore_output: Optional[Dict[str, Any]] = None,
        prd_output: Optional[Dict[str, Any]] = None,
        requirements_output: Optional[Dict[str, Any]] = None,
        design_output: Optional[Dict[str, Any]] = None,
        tasks_output: Optional[Dict[str, Any]] = None,
        sync_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Path]:
        """Generate all markdown files from phase outputs.

        Returns dict mapping artifact type to file path.
        """
        artifacts: Dict[str, Path] = {}

        if prd_output:
            path = self._write_prd(prd_output, explore_output)
            artifacts["prd"] = path

        if requirements_output:
            path = self._write_requirements(requirements_output, explore_output)
            artifacts["requirements"] = path

        if design_output:
            path = self._write_design(design_output, explore_output, requirements_output)
            artifacts["design"] = path

        if tasks_output:
            paths = self._write_tasks(tasks_output, design_output)
            artifacts["tasks_index"] = paths["index"]
            for task_id, task_path in paths.get("task_files", {}).items():
                artifacts[f"task:{task_id}"] = task_path
            for ticket_id, ticket_path in paths.get("ticket_files", {}).items():
                artifacts[f"ticket:{ticket_id}"] = ticket_path

        if sync_output:
            path = self._write_spec_summary(
                sync_output,
                requirements_output,
                design_output,
                tasks_output,
            )
            artifacts["spec_summary"] = path

        return artifacts

    def _write_requirements(
        self,
        output: Dict[str, Any],
        explore_output: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Write requirements markdown document.

        Structure: .omoi_os/requirements/REQ-{feature}.md
        """
        markdown = generate_requirements_markdown(
            output=output,
            spec_id=self.spec_id,
            spec_title=self.spec_title,
            created_date=self.created_date,
            explore_output=explore_output,
        )

        # Use .omoi_os/requirements/ subdirectory (matches skill structure)
        if self.use_omoi_os_structure:
            requirements_dir = self.output_dir / "requirements"
            requirements_dir.mkdir(parents=True, exist_ok=True)
            # File naming: REQ-{feature}.md (matches skill)
            safe_feature = self.spec_id.replace(" ", "-").lower()
            path = requirements_dir / f"REQ-{safe_feature}.md"
        else:
            path = self.output_dir / "requirements.md"
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(markdown)
        return path

    def _write_prd(
        self,
        output: Dict[str, Any],
        explore_output: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Write PRD markdown document.

        Structure: .omoi_os/prd/{feature}.md
        """
        markdown = generate_prd_markdown(
            output=output,
            spec_id=self.spec_id,
            spec_title=self.spec_title,
            created_date=self.created_date,
            explore_output=explore_output,
        )

        # Use .omoi_os/prd/ subdirectory
        if self.use_omoi_os_structure:
            prd_dir = self.output_dir / "prd"
            prd_dir.mkdir(parents=True, exist_ok=True)
            safe_feature = self.spec_id.replace(" ", "-").lower()
            path = prd_dir / f"{safe_feature}.md"
        else:
            path = self.output_dir / "prd.md"
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(markdown)
        return path

    def _write_design(
        self,
        output: Dict[str, Any],
        explore_output: Optional[Dict[str, Any]] = None,
        requirements_output: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Write design markdown document.

        Structure: .omoi_os/designs/{feature}.md
        """
        markdown = generate_design_markdown(
            output=output,
            spec_id=self.spec_id,
            spec_title=self.spec_title,
            created_date=self.created_date,
            explore_output=explore_output,
            requirements_output=requirements_output,
        )

        # Use .omoi_os/designs/ subdirectory (matches skill structure)
        if self.use_omoi_os_structure:
            designs_dir = self.output_dir / "designs"
            designs_dir.mkdir(parents=True, exist_ok=True)
            # File naming: {feature}.md (matches skill)
            safe_feature = self.spec_id.replace(" ", "-").lower()
            path = designs_dir / f"{safe_feature}.md"
        else:
            path = self.output_dir / "design.md"
            path.parent.mkdir(parents=True, exist_ok=True)

        path.write_text(markdown)
        return path

    def _write_tasks(
        self,
        output: Dict[str, Any],
        design_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Write task and ticket markdown files.

        Creates:
        - tasks/index.md - Overview of all tasks
        - tasks/TSK-{NUM}.md - Individual task files
        - tickets/TKT-{NUM}.md - Ticket files (if tickets present)
        """
        tasks_dir = self.output_dir / "tasks"
        tasks_dir.mkdir(parents=True, exist_ok=True)

        result: Dict[str, Any] = {"task_files": {}, "ticket_files": {}}

        # Write index file
        index_markdown = generate_tasks_index_markdown(
            output=output,
            spec_id=self.spec_id,
            spec_title=self.spec_title,
            created_date=self.created_date,
        )
        index_path = tasks_dir / "index.md"
        index_path.write_text(index_markdown)
        result["index"] = index_path

        # Write individual task files
        tasks = output.get("tasks", [])
        for task in tasks:
            if not isinstance(task, dict):
                continue

            task_id = task.get("id", "")
            if not task_id:
                continue

            task_markdown = generate_task_markdown(
                task=task,
                spec_id=self.spec_id,
                created_date=self.created_date,
                design_output=design_output,
            )

            task_path = tasks_dir / f"{task_id}.md"
            task_path.write_text(task_markdown)
            result["task_files"][task_id] = task_path

        # Write ticket files if present
        tickets = output.get("tickets", [])
        if tickets:
            tickets_dir = self.output_dir / "tickets"
            tickets_dir.mkdir(parents=True, exist_ok=True)

            for ticket in tickets:
                if not isinstance(ticket, dict):
                    continue

                ticket_id = ticket.get("id", "")
                if not ticket_id:
                    continue

                ticket_markdown = generate_ticket_markdown(
                    ticket=ticket,
                    spec_id=self.spec_id,
                    spec_title=self.spec_title,
                    created_date=self.created_date,
                )

                ticket_path = tickets_dir / f"{ticket_id}.md"
                ticket_path.write_text(ticket_markdown)
                result["ticket_files"][ticket_id] = ticket_path

        return result

    def _write_spec_summary(
        self,
        sync_output: Dict[str, Any],
        requirements_output: Optional[Dict[str, Any]] = None,
        design_output: Optional[Dict[str, Any]] = None,
        tasks_output: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Write spec summary markdown document."""
        markdown = generate_spec_summary_markdown(
            sync_output=sync_output,
            requirements_output=requirements_output,
            design_output=design_output,
            tasks_output=tasks_output,
            spec_id=self.spec_id,
            spec_title=self.spec_title,
            created_date=self.created_date,
        )

        path = self.output_dir / "SPEC_SUMMARY.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(markdown)
        return path


def _yaml_frontmatter(data: Dict[str, Any]) -> str:
    """Generate YAML frontmatter block."""
    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return f"---\n{yaml_str}---\n\n"


# =============================================================================
# REQUIREMENTS MARKDOWN - Matches requirements_template.md
# =============================================================================


def generate_requirements_markdown(
    output: Dict[str, Any],
    spec_id: str,
    spec_title: str,
    created_date: str,
    explore_output: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate requirements markdown matching requirements_template.md.

    Uses EARS format (Easy Approach to Requirements Syntax):
    - WHEN <condition>, THE SYSTEM SHALL <action>
    - Includes state machines, data models, configuration, API specs
    """
    requirements = output.get("requirements", [])
    assumptions = output.get("assumptions", [])
    out_of_scope = output.get("out_of_scope", [])
    open_questions = output.get("open_questions", [])
    traceability = output.get("traceability", [])

    # Extract domain from first requirement ID or use spec_id
    domain = "SPEC"
    if requirements and isinstance(requirements[0], dict):
        first_id = requirements[0].get("id", "")
        if first_id and "-" in first_id:
            parts = first_id.split("-")
            if len(parts) >= 2:
                domain = parts[1]

    # Group requirements by category/area
    categories: Dict[str, List[Dict[str, Any]]] = {}
    for req in requirements:
        if not isinstance(req, dict):
            continue
        cat = req.get("category", "functional")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(req)

    # Build frontmatter
    frontmatter = {
        "id": f"REQ-{domain}-001",
        "title": f"{spec_title} Requirements",
        "feature": spec_id,
        "created": created_date,
        "updated": created_date,
        "status": "draft",
        "category": list(categories.keys())[0] if categories else "functional",
        "priority": "HIGH",
        "design_ref": f"designs/{spec_id}.md",
    }

    # Add EARS condition/action from first requirement if available
    if requirements and isinstance(requirements[0], dict):
        frontmatter["condition"] = requirements[0].get("condition", "")
        frontmatter["action"] = requirements[0].get("action", "")

    lines = [_yaml_frontmatter(frontmatter)]

    # ==========================================================================
    # DOCUMENT HEADER
    # ==========================================================================
    lines.append(f"# {spec_title} Requirements\n\n")

    lines.append("## Document Overview\n\n")
    lines.append(f"This document contains the requirements for **{spec_title}** ")
    lines.append(f"generated from spec `{spec_id}`.\n\n")

    if explore_output:
        feature_summary = explore_output.get("feature_summary", {})
        if feature_summary.get("goal"):
            lines.append(f"**Goal**: {feature_summary['goal']}\n\n")

    lines.append(f"**Parent Document**: [Design](../designs/{spec_id}.md)\n\n")
    lines.append("---\n\n")

    # ==========================================================================
    # REQUIREMENTS BY DOMAIN AREA (Section 1, 2, etc.)
    # ==========================================================================
    section_num = 1

    for category, reqs in categories.items():
        lines.append(f"## {section_num}. {category.title()} Requirements\n\n")

        for req in reqs:
            req_id = req.get("id", f"REQ-{domain}-{section_num:03d}")
            title = req.get("title", "Untitled")
            condition = req.get("condition", "")
            action = req.get("action", req.get("text", ""))
            priority = req.get("priority", "MEDIUM")
            acceptance_criteria = req.get("acceptance_criteria", [])
            notes = req.get("notes", "")
            prd_section = req.get("prd_section", "")

            lines.append(f"#### {req_id}: {title}\n\n")

            # EARS format
            if condition:
                lines.append(f"WHEN {condition},\n")
            lines.append(f"THE SYSTEM SHALL {action}\n\n")

            # Acceptance criteria
            if acceptance_criteria:
                lines.append("**Acceptance Criteria:**\n")
                for criterion in acceptance_criteria:
                    lines.append(f"- {criterion}\n")
                lines.append("\n")

            # Metadata
            if priority:
                lines.append(f"**Priority**: {priority}\n")
            if prd_section:
                lines.append(f"**PRD Section**: {prd_section}\n")
            if notes:
                lines.append(f"\n*Note: {notes}*\n")
            lines.append("\n")

        section_num += 1

    # ==========================================================================
    # STATE MACHINE (if present)
    # ==========================================================================
    state_machine = output.get("state_machine", {})
    if state_machine:
        lines.append(f"## {section_num}. State Machine\n\n")

        states = state_machine.get("states", [])
        transitions = state_machine.get("transitions", [])
        guards = state_machine.get("guards", [])

        if states:
            lines.append(f"#### REQ-{domain}-SM-001: States\n")
            lines.append(f"{spec_title} SHALL support the following states:\n\n")

            lines.append("```mermaid\n")
            lines.append("stateDiagram-v2\n")
            lines.append(f"    [*] --> {states[0]}\n")
            for i, state in enumerate(states[:-1]):
                next_state = states[i + 1]
                lines.append(f"    {state} --> {next_state} : Trigger\n")
            lines.append(f"    {states[-1]} --> [*]\n")
            lines.append("```\n\n")

        if transitions:
            lines.append(f"#### REQ-{domain}-SM-002: Transitions\n")
            lines.append("Valid transitions:\n```\n")
            for trans in transitions:
                lines.append(f"{trans}\n")
            lines.append("```\n\n")

        if guards:
            lines.append(f"#### REQ-{domain}-SM-003: Guards\n")
            for guard in guards:
                lines.append(f"- {guard}\n")
            lines.append("\n")

        section_num += 1

    # ==========================================================================
    # DATA MODEL REQUIREMENTS
    # ==========================================================================
    data_models = output.get("data_models", [])
    if data_models:
        lines.append(f"## {section_num}. Data Model Requirements\n\n")

        for model in data_models:
            if not isinstance(model, dict):
                continue
            name = model.get("name", "Entity")
            fields = model.get("fields", {})
            table_name = model.get("table_name", name.lower() + "s")

            lines.append(f"### {section_num}.1 {name} Model\n")
            lines.append(f"#### REQ-{domain}-DM-001\n")
            lines.append(f"{name} SHALL include the following fields:\n")
            for field_name, field_type in fields.items():
                nullable = "(nullable)" if "null" in str(field_type).lower() else ""
                lines.append(f"- `{field_name}: {field_type}` {nullable}\n")
            lines.append("\n")

            lines.append(f"### {section_num}.2 {name} (DB Table)\n")
            lines.append(f"#### REQ-{domain}-DM-002\n")
            lines.append(f"The system SHALL persist {name} with at least the following fields:\n")
            lines.append(f"- `id TEXT PK`\n")
            for field_name, field_type in fields.items():
                if field_name != "id":
                    lines.append(f"- `{field_name} {_python_type_to_sql(field_type)}`\n")
            lines.append("- `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP`\n\n")

        section_num += 1

    # ==========================================================================
    # CONFIGURATION (Normative)
    # ==========================================================================
    configuration = output.get("configuration", [])
    if configuration:
        lines.append(f"## {section_num}. Configuration (Normative)\n\n")
        lines.append("| Parameter | Default | Range | Description |\n")
        lines.append("|-----------|---------|-------|-------------|\n")
        for config in configuration:
            if isinstance(config, dict):
                param = config.get("name", "param")
                default = config.get("default", "-")
                range_val = config.get("range", "-")
                desc = config.get("description", "")
                lines.append(f"| {param} | {default} | {range_val} | {desc} |\n")
        lines.append("\n")
        section_num += 1

    # ==========================================================================
    # API (Normative)
    # ==========================================================================
    api_endpoints = output.get("api_endpoints", [])
    if api_endpoints:
        lines.append(f"## {section_num}. API (Normative)\n\n")

        lines.append(f"### {section_num}.1 Endpoints Table\n\n")
        lines.append("| Endpoint | Method | Purpose | Request Body (min) | Responses |\n")
        lines.append("|----------|--------|---------|--------------------|----------|\n")
        for endpoint in api_endpoints:
            if not isinstance(endpoint, dict):
                continue
            method = endpoint.get("method", "GET")
            path = endpoint.get("path", "/")
            purpose = endpoint.get("description", endpoint.get("purpose", ""))[:30]
            req = endpoint.get("request_schema", "-")
            resp = endpoint.get("response_schema", "-")
            lines.append(f"| {path} | {method} | {purpose} | {req} | {resp} |\n")
        lines.append("\n")

        lines.append("Notes:\n")
        lines.append("- All responses MUST include a stable `error` field on failure.\n\n")

        # Event contracts
        event_contracts = output.get("event_contracts", [])
        if event_contracts:
            lines.append(f"### {section_num}.2 WebSocket/Event Contracts\n\n")
            lines.append("| Event | When Emitted | Payload (min) |\n")
            lines.append("|-------|--------------|---------------|\n")
            for event in event_contracts:
                if isinstance(event, dict):
                    name = event.get("name", "event")
                    when = event.get("when", "")
                    payload = event.get("payload", {})
                    payload_str = json.dumps(payload) if payload else "-"
                    lines.append(f"| {name} | {when} | `{payload_str}` |\n")
            lines.append("\n")

        section_num += 1

    # ==========================================================================
    # SLOs & Performance
    # ==========================================================================
    slos = output.get("slos", [])
    if slos:
        lines.append(f"## {section_num}. SLOs & Performance\n\n")
        for i, slo in enumerate(slos):
            if isinstance(slo, dict):
                lines.append(f"#### REQ-{domain}-SLO-{i+1:03d}\n")
                lines.append(f"{slo.get('description', slo.get('metric', ''))}\n\n")
            else:
                lines.append(f"#### REQ-{domain}-SLO-{i+1:03d}\n")
                lines.append(f"{slo}\n\n")
        section_num += 1

    # ==========================================================================
    # Security & Audit
    # ==========================================================================
    security = output.get("security", [])
    if security:
        lines.append(f"## {section_num}. Security & Audit\n\n")
        for i, sec in enumerate(security):
            lines.append(f"#### REQ-{domain}-SEC-{i+1:03d}\n")
            if isinstance(sec, dict):
                lines.append(f"{sec.get('description', '')}\n\n")
            else:
                lines.append(f"{sec}\n\n")
        section_num += 1

    # ==========================================================================
    # Integration Requirements
    # ==========================================================================
    integrations = output.get("integrations", [])
    if integrations:
        lines.append(f"## {section_num}. Integration Requirements\n\n")
        for i, integration in enumerate(integrations):
            lines.append(f"#### REQ-{domain}-INT-{i+1:03d}: Integration\n")
            if isinstance(integration, dict):
                system = integration.get("system", "External System")
                purpose = integration.get("purpose", "")
                lines.append(f"THE SYSTEM SHALL integrate with {system} for {purpose}.\n\n")
            else:
                lines.append(f"THE SYSTEM SHALL integrate with {integration}.\n\n")
        section_num += 1

    # ==========================================================================
    # Pydantic Reference Models
    # ==========================================================================
    if data_models:
        lines.append(f"## {section_num}. Pydantic Reference Models\n\n")
        lines.append("```python\n")
        lines.append("from __future__ import annotations\n")
        lines.append("from datetime import datetime\n")
        lines.append("from enum import Enum\n")
        lines.append("from typing import Any, Dict, List, Optional\n")
        lines.append("from pydantic import BaseModel, Field\n\n\n")

        # Status enum if we have state machine
        if state_machine and state_machine.get("states"):
            lines.append("class StatusEnum(str, Enum):\n")
            for state in state_machine["states"]:
                lines.append(f'    {state.upper()} = "{state.lower()}"\n')
            lines.append("\n\n")

        for model in data_models:
            if not isinstance(model, dict):
                continue
            name = model.get("name", "Entity")
            fields = model.get("fields", {})

            # Main model
            lines.append(f"class {name}(BaseModel):\n")
            for field_name, field_type in fields.items():
                py_type = _normalize_python_type(field_type)
                lines.append(f"    {field_name}: {py_type}\n")
            lines.append("    created_at: datetime\n\n\n")

            # Request model
            lines.append(f"class {name}Request(BaseModel):\n")
            for field_name, field_type in fields.items():
                if field_name != "id":
                    py_type = _normalize_python_type(field_type)
                    lines.append(f"    {field_name}: {py_type}\n")
            lines.append("\n\n")

            # Response model
            lines.append(f"class {name}Response(BaseModel):\n")
            lines.append("    status: str\n")
            lines.append("    message: str\n")
            lines.append(f"    data: Optional[{name}] = None\n")
            lines.append("```\n\n")

        section_num += 1

    # ==========================================================================
    # Assumptions & Out of Scope
    # ==========================================================================
    if assumptions:
        lines.append("---\n\n")
        lines.append("## Assumptions\n\n")
        for assumption in assumptions:
            lines.append(f"- {assumption}\n")
        lines.append("\n")

    if out_of_scope:
        lines.append("## Out of Scope\n\n")
        for item in out_of_scope:
            lines.append(f"- {item}\n")
        lines.append("\n")

    if open_questions:
        lines.append("## Open Questions\n\n")
        for question in open_questions:
            lines.append(f"- [ ] {question}\n")
        lines.append("\n")

    # ==========================================================================
    # Related Documents & Revision History
    # ==========================================================================
    lines.append("---\n\n")
    lines.append("## Related Documents\n\n")
    lines.append(f"- [{spec_title} Design](../designs/{spec_id}.md)\n\n")

    lines.append("---\n\n")
    lines.append("## Revision History\n\n")
    lines.append("| Version | Date | Author | Changes |\n")
    lines.append("|---------|------|--------|--------|\n")
    lines.append(f"| 1.0 | {created_date} | spec-sandbox | Initial draft |\n")

    return "".join(lines)


# =============================================================================
# PRD MARKDOWN - Product Requirements Document
# =============================================================================


def generate_prd_markdown(
    output: Dict[str, Any],
    spec_id: str,
    spec_title: str,
    created_date: str,
    explore_output: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate PRD markdown for product requirements document.

    Includes overview, goals, users, user stories, scope,
    assumptions, constraints, risks, and open questions.
    """
    overview = output.get("overview", {})
    goals = output.get("goals", {})
    users = output.get("users", {})
    user_stories = output.get("user_stories", [])
    scope = output.get("scope", {})
    assumptions = output.get("assumptions", [])
    constraints = output.get("constraints", {})
    risks = output.get("risks", [])
    open_questions = output.get("open_questions", [])

    # Build frontmatter
    feature_name = overview.get("feature_name", spec_title)
    frontmatter = {
        "id": f"PRD-{spec_id.upper()}",
        "title": f"{feature_name} PRD",
        "feature": spec_id,
        "created": created_date,
        "updated": created_date,
        "status": "draft",
        "version": "1.0",
    }

    lines = [_yaml_frontmatter(frontmatter)]

    # ==========================================================================
    # DOCUMENT HEADER
    # ==========================================================================
    lines.append(f"# {feature_name}\n\n")

    # One-liner
    one_liner = overview.get("one_liner", "")
    if one_liner:
        lines.append(f"> {one_liner}\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # OVERVIEW
    # ==========================================================================
    lines.append("## Overview\n\n")

    # Problem Statement
    problem = overview.get("problem_statement", "")
    if problem:
        lines.append("### Problem Statement\n\n")
        lines.append(f"{problem}\n\n")

    # Solution Summary
    solution = overview.get("solution_summary", "")
    if solution:
        lines.append("### Solution Summary\n\n")
        lines.append(f"{solution}\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # GOALS
    # ==========================================================================
    lines.append("## Goals\n\n")

    # Primary Goals
    primary_goals = goals.get("primary", [])
    if primary_goals:
        lines.append("### Primary Goals\n\n")
        for goal in primary_goals:
            lines.append(f"- {goal}\n")
        lines.append("\n")

    # Secondary Goals
    secondary_goals = goals.get("secondary", [])
    if secondary_goals:
        lines.append("### Secondary Goals\n\n")
        for goal in secondary_goals:
            lines.append(f"- {goal}\n")
        lines.append("\n")

    # Success Metrics
    success_metrics = goals.get("success_metrics", [])
    if success_metrics:
        lines.append("### Success Metrics\n\n")
        lines.append("| Metric | Target | How to Measure |\n")
        lines.append("|--------|--------|----------------|\n")
        for metric in success_metrics:
            if isinstance(metric, dict):
                name = metric.get("metric", "")
                target = metric.get("target", "")
                measurement = metric.get("measurement", "")
                lines.append(f"| {name} | {target} | {measurement} |\n")
            else:
                lines.append(f"| {metric} | - | - |\n")
        lines.append("\n")

    lines.append("---\n\n")

    # ==========================================================================
    # USERS
    # ==========================================================================
    lines.append("## Users\n\n")

    # Primary Users
    primary_users = users.get("primary", [])
    if primary_users:
        lines.append("### Primary Users\n\n")
        for user in primary_users:
            if isinstance(user, dict):
                role = user.get("role", "User")
                description = user.get("description", "")
                needs = user.get("needs", [])

                lines.append(f"#### {role}\n\n")
                if description:
                    lines.append(f"{description}\n\n")
                if needs:
                    lines.append("**Needs:**\n")
                    for need in needs:
                        lines.append(f"- {need}\n")
                    lines.append("\n")
            else:
                lines.append(f"- {user}\n")
        lines.append("\n")

    # Secondary Users
    secondary_users = users.get("secondary", [])
    if secondary_users:
        lines.append("### Secondary Users\n\n")
        for user in secondary_users:
            if isinstance(user, dict):
                role = user.get("role", "User")
                description = user.get("description", "")
                lines.append(f"- **{role}**: {description}\n")
            else:
                lines.append(f"- {user}\n")
        lines.append("\n")

    lines.append("---\n\n")

    # ==========================================================================
    # USER STORIES
    # ==========================================================================
    lines.append("## User Stories\n\n")

    if user_stories:
        for story in user_stories:
            if not isinstance(story, dict):
                continue

            story_id = story.get("id", "US-001")
            role = story.get("role", "user")
            want = story.get("want", "")
            benefit = story.get("benefit", "")
            priority = story.get("priority", "should")
            acceptance_criteria = story.get("acceptance_criteria", [])

            lines.append(f"### {story_id}\n\n")
            lines.append(f"**As a** {role},  \n")
            lines.append(f"**I want** {want},  \n")
            lines.append(f"**So that** {benefit}.\n\n")
            lines.append(f"**Priority**: {priority.upper()}\n\n")

            if acceptance_criteria:
                lines.append("**Acceptance Criteria:**\n")
                for criterion in acceptance_criteria:
                    lines.append(f"- [ ] {criterion}\n")
                lines.append("\n")

            lines.append("---\n\n")
    else:
        lines.append("*No user stories defined yet.*\n\n")

    # ==========================================================================
    # SCOPE
    # ==========================================================================
    lines.append("## Scope\n\n")

    # In Scope
    in_scope = scope.get("in_scope", [])
    if in_scope:
        lines.append("### In Scope\n\n")
        for item in in_scope:
            lines.append(f"- ✅ {item}\n")
        lines.append("\n")

    # Out of Scope
    out_of_scope = scope.get("out_of_scope", [])
    if out_of_scope:
        lines.append("### Out of Scope\n\n")
        for item in out_of_scope:
            lines.append(f"- ❌ {item}\n")
        lines.append("\n")

    # Dependencies
    dependencies = scope.get("dependencies", [])
    if dependencies:
        lines.append("### Dependencies\n\n")
        for dep in dependencies:
            lines.append(f"- {dep}\n")
        lines.append("\n")

    lines.append("---\n\n")

    # ==========================================================================
    # ASSUMPTIONS
    # ==========================================================================
    if assumptions:
        lines.append("## Assumptions\n\n")
        for assumption in assumptions:
            lines.append(f"- {assumption}\n")
        lines.append("\n---\n\n")

    # ==========================================================================
    # CONSTRAINTS
    # ==========================================================================
    if constraints:
        lines.append("## Constraints\n\n")

        technical = constraints.get("technical", [])
        if technical:
            lines.append("### Technical Constraints\n\n")
            for constraint in technical:
                lines.append(f"- {constraint}\n")
            lines.append("\n")

        business = constraints.get("business", [])
        if business:
            lines.append("### Business Constraints\n\n")
            for constraint in business:
                lines.append(f"- {constraint}\n")
            lines.append("\n")

        lines.append("---\n\n")

    # ==========================================================================
    # RISKS
    # ==========================================================================
    if risks:
        lines.append("## Risks\n\n")
        lines.append("| Risk | Impact | Probability | Mitigation |\n")
        lines.append("|------|--------|-------------|------------|\n")

        for risk in risks:
            if isinstance(risk, dict):
                description = risk.get("description", "")
                impact = risk.get("impact", "medium")
                probability = risk.get("probability", "medium")
                mitigation = risk.get("mitigation", "")
                lines.append(f"| {description} | {impact} | {probability} | {mitigation} |\n")
            else:
                lines.append(f"| {risk} | - | - | - |\n")

        lines.append("\n---\n\n")

    # ==========================================================================
    # OPEN QUESTIONS
    # ==========================================================================
    if open_questions:
        lines.append("## Open Questions\n\n")
        for question in open_questions:
            lines.append(f"- [ ] {question}\n")
        lines.append("\n---\n\n")

    # ==========================================================================
    # RELATED DOCUMENTS
    # ==========================================================================
    lines.append("## Related Documents\n\n")
    lines.append(f"- [Requirements](../requirements/REQ-{spec_id.replace(' ', '-').lower()}.md)\n")
    lines.append(f"- [Design](../designs/{spec_id.replace(' ', '-').lower()}.md)\n")
    lines.append(f"- [Tasks](../tasks/index.md)\n\n")

    lines.append("---\n\n")

    lines.append("## Revision History\n\n")
    lines.append("| Version | Date | Author | Changes |\n")
    lines.append("|---------|------|--------|--------|\n")
    lines.append(f"| 1.0 | {created_date} | spec-sandbox | Initial PRD |\n")

    return "".join(lines)


# =============================================================================
# DESIGN MARKDOWN - Matches design_template.md
# =============================================================================


def generate_design_markdown(
    output: Dict[str, Any],
    spec_id: str,
    spec_title: str,
    created_date: str,
    explore_output: Optional[Dict[str, Any]] = None,
    requirements_output: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate design markdown matching design_template.md.

    Includes architecture diagrams, database schemas, API specs,
    integration flows, and implementation details.
    """
    components = output.get("components", [])
    data_models = output.get("data_models", [])
    api_endpoints = output.get("api_endpoints", [])
    architecture = output.get("architecture", {})
    architecture_overview = architecture.get("flow", []) if isinstance(architecture, dict) else output.get("architecture_overview", "")
    testing_strategy = output.get("testing_strategy", "")
    integration_points = output.get("integration_points", [])
    configuration = output.get("configuration", {})

    # Extract requirement IDs
    requirement_ids = []
    if requirements_output:
        for req in requirements_output.get("requirements", []):
            if isinstance(req, dict) and req.get("id"):
                requirement_ids.append(req["id"])

    # Build frontmatter
    frontmatter = {
        "id": f"DESIGN-{spec_id.upper()}-001",
        "title": f"{spec_title} Design",
        "feature": spec_id,
        "created": created_date,
        "updated": created_date,
        "status": "draft",
        "requirements": requirement_ids[:10] if requirement_ids else [],
    }

    lines = [_yaml_frontmatter(frontmatter)]

    # ==========================================================================
    # DOCUMENT HEADER
    # ==========================================================================
    lines.append(f"# {spec_title} - Product Design Document\n\n")

    lines.append("## Document Overview\n\n")

    # Architecture overview
    if isinstance(architecture_overview, list):
        for step in architecture_overview:
            lines.append(f"{step}\n\n")
    elif architecture_overview:
        lines.append(f"{architecture_overview}\n\n")

    # Purpose & Scope
    lines.append("- **Purpose & Scope**\n")
    if explore_output:
        feature_summary = explore_output.get("feature_summary", {})
        scope = feature_summary.get("scope", {})
        if scope.get("in_scope"):
            for item in scope["in_scope"]:
                lines.append(f"  - {item}\n")
        if scope.get("out_of_scope"):
            lines.append("  - Non-goals:\n")
            for item in scope["out_of_scope"]:
                lines.append(f"    - {item}\n")
    else:
        lines.append("  - Implementation of core feature functionality\n")
        lines.append("  - Integration with existing services\n")
    lines.append("\n")

    # Target Audience
    lines.append("- **Target Audience**\n")
    lines.append("  - Implementation teams\n")
    lines.append("  - System architects\n")
    lines.append("  - Code reviewers\n\n")

    # Related Documents
    lines.append("- **Related Documents**\n")
    lines.append(f"  - Requirements: `requirements/{spec_id}.md`\n")
    lines.append(f"  - Design: `designs/{spec_id}.md`\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # ARCHITECTURE OVERVIEW
    # ==========================================================================
    lines.append("## Architecture Overview\n\n")

    # High-Level Architecture Diagram
    lines.append("### High-Level Architecture\n\n")
    lines.append("```mermaid\n")
    lines.append("flowchart TD\n")

    # Group components by layer
    by_layer: Dict[str, List[Dict[str, Any]]] = {}
    for comp in components:
        if not isinstance(comp, dict):
            continue
        layer = comp.get("layer", comp.get("type", "component"))
        if layer not in by_layer:
            by_layer[layer] = []
        by_layer[layer].append(comp)

    # Create subgraphs
    for layer, comps in by_layer.items():
        safe_layer = layer.replace(" ", "_").replace("-", "_")
        lines.append(f"    subgraph {safe_layer}[{layer.title()}]\n")
        for comp in comps:
            name = comp.get("name", "Unknown")
            safe_name = name.replace(" ", "_").replace("-", "_")
            lines.append(f"        {safe_name}[{name}]\n")
        lines.append("    end\n\n")

    # External systems
    if integration_points:
        lines.append("    subgraph External[External Systems]\n")
        for i, point in enumerate(integration_points[:5]):
            if isinstance(point, dict):
                ext_name = point.get("system", f"External{i+1}")
            else:
                ext_name = str(point).split()[0] if point else f"External{i+1}"
            safe_ext = ext_name.replace(" ", "_").replace("-", "_")
            lines.append(f"        E{i}[{ext_name}]\n")
        lines.append("    end\n\n")

    # Dependencies
    for comp in components:
        if not isinstance(comp, dict):
            continue
        name = comp.get("name", "").replace(" ", "_").replace("-", "_")
        deps = comp.get("dependencies", [])
        for dep in deps:
            safe_dep = dep.replace(" ", "_").replace("-", "_")
            lines.append(f"    {name} -->|calls| {safe_dep}\n")

    lines.append("```\n\n")

    # Component Responsibilities Table
    if components:
        lines.append("### Component Responsibilities\n\n")
        lines.append("| Component | Layer | Responsibilities |\n")
        lines.append("|-----------|-------|------------------|\n")
        for comp in components:
            if not isinstance(comp, dict):
                continue
            name = comp.get("name", "Unknown")
            layer = comp.get("layer", comp.get("type", "component"))
            resp = comp.get("responsibilities", [])
            resp_str = ", ".join(resp[:2]) if isinstance(resp, list) else str(resp)[:60]
            lines.append(f"| {name} | {layer} | {resp_str} |\n")
        lines.append("\n")

    # System Boundaries
    lines.append("### System Boundaries\n\n")
    if explore_output:
        feature_summary = explore_output.get("feature_summary", {})
        scope = feature_summary.get("scope", {})
        if scope.get("in_scope"):
            lines.append(f"- **Within scope of {spec_title}**:\n")
            for item in scope["in_scope"]:
                lines.append(f"  - {item}\n")
            lines.append("\n")
        if scope.get("out_of_scope"):
            lines.append("- **Out of scope (delegated)**:\n")
            for item in scope["out_of_scope"]:
                lines.append(f"  - {item}\n")
            lines.append("\n")
    else:
        lines.append(f"- **Within scope of {spec_title}**:\n")
        lines.append("  - Core feature implementation\n")
        lines.append("  - API endpoints and validation\n\n")
        lines.append("- **Out of scope (delegated)**:\n")
        lines.append("  - Authentication/authorization\n")
        lines.append("  - Infrastructure provisioning\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # COMPONENT DETAILS
    # ==========================================================================
    if components:
        lines.append("## Component Details\n\n")

        for comp in components:
            if not isinstance(comp, dict):
                continue

            name = comp.get("name", "Unknown")
            responsibilities = comp.get("responsibilities", [])
            deps = comp.get("dependencies", [])
            file_path = comp.get("file", comp.get("file_path", ""))

            lines.append(f"### {name}\n\n")

            lines.append("#### Responsibilities\n")
            if isinstance(responsibilities, list):
                for resp in responsibilities:
                    lines.append(f"- {resp}\n")
            else:
                lines.append(f"- {responsibilities}\n")
            lines.append("\n")

            lines.append("#### Key Interfaces\n")
            interfaces = comp.get("interfaces", [])
            if interfaces:
                for iface in interfaces:
                    if isinstance(iface, dict):
                        method = iface.get("method", "method")
                        lines.append(f"- `{method}()`\n")
                    else:
                        lines.append(f"- `{iface}()`\n")
            else:
                lines.append("- *To be defined during implementation*\n")
            lines.append("\n")

            lines.append("#### Implementation Notes\n")
            if file_path:
                lines.append(f"Target file: `{file_path}`\n")
            if deps:
                lines.append(f"Dependencies: {', '.join(deps)}\n")
            lines.append("\n---\n\n")

    # ==========================================================================
    # DATA MODELS
    # ==========================================================================
    if data_models:
        lines.append("## Data Models\n\n")

        # Database Schema
        lines.append("### Database Schema\n\n")
        lines.append("```sql\n")

        for model in data_models:
            if not isinstance(model, dict):
                continue
            name = model.get("name", "Entity")
            table_name = model.get("table_name", name.lower() + "s")
            fields = model.get("fields", [])
            indexes = model.get("indexes", [])

            lines.append(f"-- {name} table\n")
            lines.append(f"CREATE TABLE {table_name} (\n")

            field_lines = []

            # Handle both dict and list formats for fields
            if isinstance(fields, dict):
                for field_name, field_type in fields.items():
                    sql_type = _python_type_to_sql(field_type)
                    constraint = "PRIMARY KEY DEFAULT gen_random_uuid()" if field_name == "id" else ""
                    field_lines.append(f"    {field_name} {sql_type} {constraint}".rstrip())
            elif isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "field")
                        field_type = field.get("type", "string")
                        nullable = "NOT NULL" if not field.get("nullable", True) else ""
                        pk = "PRIMARY KEY" if field.get("primary_key") else ""
                        fk = f"REFERENCES {field['foreign_key']}" if field.get("foreign_key") else ""
                        default = f"DEFAULT {field['default']}" if field.get("default") else ""
                        sql_type = _python_type_to_sql(field_type)
                        field_lines.append(f"    {field_name} {sql_type} {nullable} {pk} {fk} {default}".rstrip())

            # Standard timestamps
            field_lines.append("    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
            field_lines.append("    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")

            lines.append(",\n".join(field_lines))
            lines.append("\n);\n\n")

            # Indexes
            for idx in indexes:
                if isinstance(idx, dict):
                    idx_name = idx.get("name", f"idx_{table_name}")
                    columns = idx.get("columns", [])
                    lines.append(f"CREATE INDEX {idx_name} ON {table_name}({', '.join(columns)});\n")

            lines.append("\n")

        lines.append("```\n\n")

        # Pydantic Models
        lines.append("### Pydantic Models\n\n")
        lines.append("```python\n")
        lines.append("from __future__ import annotations\n")
        lines.append("from datetime import datetime\n")
        lines.append("from enum import Enum\n")
        lines.append("from typing import Dict, List, Optional, Any\n")
        lines.append("from pydantic import BaseModel, Field\n\n\n")

        for model in data_models:
            if not isinstance(model, dict):
                continue
            name = model.get("name", "Entity")
            description = model.get("description", model.get("purpose", ""))
            fields = model.get("fields", [])

            # Main model
            lines.append(f"class {name}(BaseModel):\n")
            if description:
                lines.append(f'    """{description}"""\n\n')

            if isinstance(fields, dict):
                for field_name, field_type in fields.items():
                    py_type = _normalize_python_type(field_type)
                    lines.append(f"    {field_name}: {py_type}\n")
            elif isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "field")
                        field_type = field.get("type", "str")
                        nullable = field.get("nullable", False)
                        py_type = _normalize_python_type(field_type)
                        if nullable:
                            py_type = f"Optional[{py_type}]"
                        default = f' = {field["default"]}' if field.get("default") else ""
                        lines.append(f"    {field_name}: {py_type}{default}\n")

            lines.append("    created_at: datetime\n")
            lines.append("    updated_at: datetime\n\n\n")

            # Create model
            lines.append(f"class {name}Create(BaseModel):\n")
            if isinstance(fields, dict):
                for field_name, field_type in fields.items():
                    if field_name not in ("id", "created_at", "updated_at"):
                        py_type = _normalize_python_type(field_type)
                        lines.append(f"    {field_name}: {py_type}\n")
            elif isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "field")
                        if field_name not in ("id", "created_at", "updated_at") and not field.get("primary_key"):
                            py_type = _normalize_python_type(field.get("type", "str"))
                            lines.append(f"    {field_name}: {py_type}\n")
            lines.append("\n\n")

            # Update model
            lines.append(f"class {name}Update(BaseModel):\n")
            if isinstance(fields, dict):
                for field_name, field_type in fields.items():
                    if field_name not in ("id", "created_at", "updated_at"):
                        py_type = _normalize_python_type(field_type)
                        lines.append(f"    {field_name}: Optional[{py_type}] = None\n")
            elif isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        field_name = field.get("name", "field")
                        if field_name not in ("id", "created_at", "updated_at") and not field.get("primary_key"):
                            py_type = _normalize_python_type(field.get("type", "str"))
                            lines.append(f"    {field_name}: Optional[{py_type}] = None\n")
            lines.append("```\n\n")

        lines.append("---\n\n")

    # ==========================================================================
    # API SPECIFICATIONS
    # ==========================================================================
    if api_endpoints:
        lines.append("## API Specifications\n\n")

        # REST Endpoints Table
        lines.append("### REST Endpoints\n\n")
        lines.append("| Method | Path | Purpose | Request | Response |\n")
        lines.append("|--------|------|---------|---------|----------|\n")

        for endpoint in api_endpoints:
            if not isinstance(endpoint, dict):
                continue
            method = endpoint.get("method", "GET")
            path = endpoint.get("path", "/")
            desc = endpoint.get("description", endpoint.get("purpose", ""))[:40]
            req_schema = endpoint.get("request_schema", "-")
            resp_schema = endpoint.get("response_schema", "-")
            lines.append(f"| {method} | `{path}` | {desc} | `{req_schema}` | `{resp_schema}` |\n")

        lines.append("\n")

        # Request/Response Models
        lines.append("### Request/Response Models\n\n")
        lines.append("```python\n")

        for endpoint in api_endpoints[:3]:  # Show first 3
            if not isinstance(endpoint, dict):
                continue
            method = endpoint.get("method", "GET")
            path = endpoint.get("path", "/").replace("/", "_").replace("{", "").replace("}", "")
            req_example = endpoint.get("request_example", {})
            resp_example = endpoint.get("response_example", {})

            if req_example:
                lines.append(f"# {method} {endpoint.get('path', '/')} Request\n")
                lines.append(f"request_example = {json.dumps(req_example, indent=4)}\n\n")
            if resp_example:
                lines.append(f"# {method} {endpoint.get('path', '/')} Response\n")
                lines.append(f"response_example = {json.dumps(resp_example, indent=4)}\n\n")

        lines.append("```\n\n")

        # Error Handling
        lines.append("### Error Handling\n\n")
        lines.append("| Status Code | Error Code | Description |\n")
        lines.append("|-------------|------------|-------------|\n")
        lines.append("| 400 | `INVALID_INPUT` | Request validation failed |\n")
        lines.append("| 404 | `NOT_FOUND` | Resource not found |\n")
        lines.append("| 409 | `CONFLICT` | Resource conflict (duplicate, etc.) |\n")
        lines.append("| 500 | `INTERNAL_ERROR` | Internal server error |\n\n")

        lines.append("---\n\n")

    # ==========================================================================
    # INTEGRATION POINTS
    # ==========================================================================
    if integration_points:
        lines.append("## Integration Points\n\n")

        for point in integration_points:
            if isinstance(point, dict):
                system = point.get("system", "External System")
                purpose = point.get("purpose", "")
                protocol = point.get("protocol", "REST")
                int_type = point.get("type", "external")

                lines.append(f"### {system} Integration\n\n")
                lines.append(f"- **Purpose**: {purpose}\n")
                lines.append(f"- **Protocol**: {protocol}\n")
                lines.append(f"- **Type**: {int_type}\n\n")
            else:
                lines.append(f"### {point}\n\n")
                lines.append(f"- **Purpose**: {point}\n")
                lines.append("- **Protocol**: REST/HTTP\n\n")

        # Integration Flow Diagram
        lines.append("#### Integration Flow\n\n")
        lines.append("```mermaid\n")
        lines.append("sequenceDiagram\n")
        lines.append("    participant Our as Our System\n")
        lines.append("    participant Ext as External System\n\n")
        lines.append("    Our->>Ext: Request\n")
        lines.append("    Ext-->>Our: Response\n")
        lines.append("```\n\n")

        # Event Contracts
        event_contracts = output.get("event_contracts", [])
        if event_contracts:
            lines.append("### Event Contracts\n\n")
            lines.append("| Event | When Emitted | Payload |\n")
            lines.append("|-------|--------------|--------|\n")
            for event in event_contracts:
                if isinstance(event, dict):
                    name = event.get("name", "event")
                    when = event.get("when", "On action")
                    payload = event.get("payload", {})
                    payload_str = ", ".join(f"{k}" for k in payload.keys()) if payload else "-"
                    lines.append(f"| `{name}` | {when} | `{{{payload_str}}}` |\n")
            lines.append("\n")

        lines.append("---\n\n")

    # ==========================================================================
    # IMPLEMENTATION DETAILS
    # ==========================================================================
    lines.append("## Implementation Details\n\n")

    # Core Algorithm (if provided)
    core_algorithm = output.get("core_algorithm", "")
    if core_algorithm:
        lines.append("### Core Algorithm\n\n")
        lines.append("```python\n")
        lines.append(core_algorithm)
        lines.append("\n```\n\n")

    # Operation Flow
    lines.append("### Operation Flow\n\n")
    lines.append("```mermaid\n")
    lines.append("sequenceDiagram\n")
    lines.append("    participant Client\n")
    lines.append("    participant API\n")
    lines.append("    participant Service\n")
    lines.append("    participant Store\n")

    if integration_points:
        lines.append("    participant External\n")

    lines.append("\n")
    lines.append("    Client->>API: Request\n")
    lines.append("    API->>Service: process(request)\n")
    lines.append("    Service->>Store: persist(data)\n")
    lines.append("    Store-->>Service: result\n")

    if integration_points:
        lines.append("    Service->>External: notify(event)\n")
        lines.append("    External-->>Service: ack\n")

    lines.append("    Service-->>API: response\n")
    lines.append("    API-->>Client: Response\n")
    lines.append("```\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # CONFIGURATION
    # ==========================================================================
    lines.append("## Configuration\n\n")
    lines.append("| Parameter | Default | Range | Description |\n")
    lines.append("|-----------|---------|-------|-------------|\n")

    if isinstance(configuration, dict) and configuration:
        for param, config in configuration.items():
            if isinstance(config, dict):
                default = config.get("default", "-")
                range_val = config.get("range", "-")
                desc = config.get("description", "")
                lines.append(f"| `{param}` | {default} | {range_val} | {desc} |\n")
            else:
                lines.append(f"| `{param}` | {config} | - | - |\n")
    else:
        lines.append("| `timeout_seconds` | 30 | 5-60 | Operation timeout |\n")
        lines.append("| `max_retries` | 3 | 0-10 | Maximum retry attempts |\n")
        lines.append("| `batch_size` | 100 | 1-1000 | Batch processing size |\n")

    lines.append("\n---\n\n")

    # ==========================================================================
    # PERFORMANCE CONSIDERATIONS
    # ==========================================================================
    lines.append("## Performance Considerations\n\n")

    lines.append("### Database Indexing\n")
    lines.append("- Primary key indexes on all ID fields\n")
    lines.append("- Index on status and frequently queried fields\n\n")

    lines.append("### Caching Strategy\n")
    lines.append("- Cache frequently accessed read-only data\n")
    lines.append("- TTL-based expiration\n")
    lines.append("- Invalidation on write\n\n")

    lines.append("### Batch Processing\n")
    lines.append("- Use batch operations for bulk updates\n")
    lines.append("- Chunk large datasets\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # SECURITY CONSIDERATIONS
    # ==========================================================================
    lines.append("## Security Considerations\n\n")

    lines.append("### Authentication\n")
    lines.append("- JWT-based authentication for API endpoints\n\n")

    lines.append("### Authorization\n")
    lines.append("- Role-based access control (RBAC)\n\n")

    lines.append("### Data Protection\n")
    lines.append("- Encrypt sensitive data at rest\n")
    lines.append("- HTTPS for all communications\n")
    lines.append("- Input sanitization\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # RELATED DOCUMENTS & QUALITY CHECKLIST
    # ==========================================================================
    lines.append("## Related Documents\n\n")
    lines.append(f"- **Requirements**: `requirements/{spec_id}.md`\n")
    lines.append(f"- **Design**: `designs/{spec_id}.md`\n\n")

    lines.append("---\n\n")

    lines.append("## Quality Checklist\n\n")
    lines.append("- [ ] All requirements addressed\n")
    lines.append("- [ ] Architecture diagram included\n")
    lines.append("- [ ] API specifications complete\n")
    lines.append("- [ ] Database schemas defined\n")
    lines.append("- [ ] Integration points documented\n")
    lines.append("- [ ] Error handling specified\n")
    lines.append("- [ ] Security considerations addressed\n\n")

    lines.append("---\n\n")

    lines.append("## Revision History\n\n")
    lines.append("| Version | Date | Author | Changes |\n")
    lines.append("|---------|------|--------|--------|\n")
    lines.append(f"| 1.0 | {created_date} | spec-sandbox | Initial design |\n")

    return "".join(lines)


# =============================================================================
# TASK MARKDOWN - Matches task_template.md
# =============================================================================


def generate_task_markdown(
    task: Dict[str, Any],
    spec_id: str,
    created_date: str,
    design_output: Optional[Dict[str, Any]] = None,
) -> str:
    """Generate individual task markdown matching task_template.md.

    Includes objective, deliverables, implementation notes,
    acceptance criteria, and testing requirements.
    """
    task_id = task.get("id", "TSK-001")
    title = task.get("title", "Untitled Task")
    description = task.get("description", "")
    task_type = task.get("type", "implementation")
    parent_ticket = task.get("parent_ticket", f"TKT-{spec_id}")
    deliverables = task.get("deliverables", [])
    files_to_modify = task.get("files_to_modify", [])
    files_to_create = task.get("files_to_create", [])
    dependencies = task.get("dependencies", {})
    acceptance_criteria = task.get("acceptance_criteria", [])
    estimated_hours = task.get("estimated_hours", task.get("estimate", 0))
    priority = task.get("priority", "MEDIUM")

    # Handle dependencies format (can be list or dict)
    depends_on = []
    blocks = []
    if isinstance(dependencies, dict):
        depends_on = dependencies.get("depends_on", [])
        blocks = dependencies.get("blocks", [])
    elif isinstance(dependencies, list):
        depends_on = dependencies

    # Map hours/estimate to t-shirt size
    if isinstance(estimated_hours, str):
        estimate_size = estimated_hours.upper() if estimated_hours.upper() in ("S", "M", "L") else "M"
    elif isinstance(estimated_hours, (int, float)):
        if estimated_hours <= 2:
            estimate_size = "S"
        elif estimated_hours <= 4:
            estimate_size = "M"
        else:
            estimate_size = "L"
    else:
        estimate_size = "M"

    # Build frontmatter
    frontmatter = {
        "id": task_id,
        "title": title,
        "status": "pending",
        "parent_ticket": parent_ticket,
        "estimate": estimate_size,
        "created": created_date,
        "assignee": None,
        "dependencies": {
            "depends_on": depends_on,
            "blocks": blocks,
        },
    }

    lines = [_yaml_frontmatter(frontmatter)]

    # ==========================================================================
    # TASK HEADER
    # ==========================================================================
    lines.append(f"# {task_id}: {title}\n\n")

    lines.append("## Objective\n\n")
    lines.append(f"{description}\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # DELIVERABLES
    # ==========================================================================
    lines.append("## Deliverables\n\n")

    # Use explicit deliverables if provided
    if deliverables:
        for d in deliverables:
            lines.append(f"- [ ] `{d}` - Implementation file\n")
    else:
        # Fall back to files_to_create and files_to_modify
        if files_to_create:
            for f in files_to_create:
                lines.append(f"- [ ] `{f}` - Create new file\n")
        if files_to_modify:
            for f in files_to_modify:
                lines.append(f"- [ ] `{f}` - Modify existing file\n")

    if not deliverables and not files_to_create and not files_to_modify:
        lines.append("- [ ] *Deliverables to be determined*\n")

    lines.append("\n---\n\n")

    # ==========================================================================
    # IMPLEMENTATION NOTES
    # ==========================================================================
    lines.append("## Implementation Notes\n\n")

    lines.append("### Approach\n")
    impl_approach = task.get("implementation_approach", [])
    if impl_approach:
        for i, step in enumerate(impl_approach):
            lines.append(f"{i+1}. {step}\n")
    else:
        lines.append("1. Review existing code and dependencies\n")
        lines.append("2. Implement core functionality\n")
        lines.append("3. Add tests and documentation\n")
    lines.append("\n")

    lines.append("### Code Patterns\n")
    code_patterns = task.get("code_patterns", "")
    if code_patterns:
        lines.append(f"{code_patterns}\n\n")
    else:
        lines.append("Follow existing project conventions and patterns.\n\n")

    lines.append("### References\n")
    references = task.get("references", [])
    if references:
        for ref in references:
            lines.append(f"- {ref}\n")
    else:
        lines.append(f"- Design document: `../designs/{spec_id}.md`\n")
        lines.append(f"- Requirements: `../requirements/{spec_id}.md`\n")
    lines.append("\n")

    lines.append("---\n\n")

    # ==========================================================================
    # ACCEPTANCE CRITERIA
    # ==========================================================================
    lines.append("## Acceptance Criteria\n\n")

    if acceptance_criteria:
        for criterion in acceptance_criteria:
            lines.append(f"- [ ] {criterion}\n")
    else:
        lines.append("- [ ] Implementation complete\n")
        lines.append("- [ ] Tests pass\n")
        lines.append("- [ ] No linting errors\n")

    lines.append("- [ ] All tests pass\n")
    lines.append("- [ ] No linting errors\n")
    lines.append("- [ ] Type hints complete\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # TESTING REQUIREMENTS
    # ==========================================================================
    lines.append("## Testing Requirements\n\n")

    lines.append("### Unit Tests\n")
    lines.append("```python\n")
    lines.append("# Expected test cases\n")
    safe_title = title.lower().replace(" ", "_").replace("-", "_")[:30]
    lines.append(f"def test_{safe_title}_basic():\n")
    lines.append("    # Test basic functionality\n")
    lines.append("    pass\n\n")
    lines.append(f"def test_{safe_title}_edge_cases():\n")
    lines.append("    # Test edge cases\n")
    lines.append("    pass\n")
    lines.append("```\n\n")

    lines.append("### Edge Cases\n")
    edge_cases = task.get("edge_cases", [])
    if edge_cases:
        for case in edge_cases:
            lines.append(f"- {case}\n")
    else:
        lines.append("- Empty input handling\n")
        lines.append("- Error conditions\n")
        lines.append("- Boundary values\n")
    lines.append("\n")

    lines.append("---\n\n")

    # ==========================================================================
    # DEPENDENCIES & NOTES
    # ==========================================================================
    if depends_on:
        lines.append("## Dependencies\n\n")
        lines.append("**Must complete first:**\n")
        for dep in depends_on:
            lines.append(f"- [{dep}](./{dep}.md)\n")
        lines.append("\n")

    if blocks:
        lines.append("**Blocks:**\n")
        for blocked in blocks:
            lines.append(f"- [{blocked}](./{blocked}.md)\n")
        lines.append("\n")

    lines.append("## Notes\n\n")
    notes = task.get("notes", "")
    if notes:
        lines.append(f"{notes}\n")
    else:
        lines.append("*Additional notes will be added during implementation.*\n")

    return "".join(lines)


# =============================================================================
# TICKET MARKDOWN - Matches ticket_template.md
# =============================================================================


def generate_ticket_markdown(
    ticket: Dict[str, Any],
    spec_id: str,
    spec_title: str,
    created_date: str,
) -> str:
    """Generate ticket markdown matching ticket_template.md.

    Tickets are parent items containing multiple tasks.
    """
    ticket_id = ticket.get("id", "TKT-001")
    title = ticket.get("title", "Untitled Ticket")
    description = ticket.get("description", "")
    status = ticket.get("status", "backlog")
    priority = ticket.get("priority", "MEDIUM")
    estimate = ticket.get("estimate", "M")
    requirements = ticket.get("requirements", [])
    design_components = ticket.get("design_components", [])
    tasks = ticket.get("tasks", [])
    dependencies = ticket.get("dependencies", {})
    acceptance_criteria = ticket.get("acceptance_criteria", [])

    # Build frontmatter
    frontmatter = {
        "id": ticket_id,
        "title": title,
        "status": status,
        "priority": priority,
        "estimate": estimate,
        "created": created_date,
        "updated": created_date,
        "feature": spec_id,
        "requirements": requirements,
        "design_ref": f"designs/{spec_id}.md",
        "tasks": tasks,
        "dependencies": dependencies,
    }

    lines = [_yaml_frontmatter(frontmatter)]

    # ==========================================================================
    # TICKET HEADER
    # ==========================================================================
    lines.append(f"# {ticket_id}: {title}\n\n")

    lines.append("## Description\n\n")
    lines.append(f"{description}\n\n")

    # Context
    lines.append("### Context\n")
    context = ticket.get("context", f"Part of {spec_title} implementation.")
    lines.append(f"{context}\n\n")

    # Goals
    goals = ticket.get("goals", [])
    if goals:
        lines.append("### Goals\n")
        for goal in goals:
            lines.append(f"- {goal}\n")
        lines.append("\n")

    # Non-Goals
    non_goals = ticket.get("non_goals", [])
    if non_goals:
        lines.append("### Non-Goals\n")
        for ng in non_goals:
            lines.append(f"- {ng}\n")
        lines.append("\n")

    lines.append("---\n\n")

    # ==========================================================================
    # ACCEPTANCE CRITERIA
    # ==========================================================================
    lines.append("## Acceptance Criteria\n\n")

    if acceptance_criteria:
        for criterion in acceptance_criteria:
            lines.append(f"- [ ] {criterion}\n")
    else:
        lines.append("- [ ] All tasks completed\n")
        lines.append("- [ ] All unit tests pass\n")
        lines.append("- [ ] Integration tests pass\n")
        lines.append("- [ ] Documentation updated\n")

    lines.append("\n---\n\n")

    # ==========================================================================
    # TECHNICAL NOTES
    # ==========================================================================
    lines.append("## Technical Notes\n\n")

    lines.append("### Implementation Approach\n")
    impl_approach = ticket.get("implementation_approach", "Follow design document specifications.")
    lines.append(f"{impl_approach}\n\n")

    # Key Files
    if design_components:
        lines.append("### Key Components\n")
        for comp in design_components:
            lines.append(f"- `{comp}`\n")
        lines.append("\n")

    # Requirements covered
    if requirements:
        lines.append("### Requirements Covered\n")
        for req in requirements:
            lines.append(f"- {req}\n")
        lines.append("\n")

    lines.append("---\n\n")

    # ==========================================================================
    # TESTING STRATEGY
    # ==========================================================================
    lines.append("## Testing Strategy\n\n")

    lines.append("### Unit Tests\n")
    lines.append("- Test individual components in isolation\n\n")

    lines.append("### Integration Tests\n")
    lines.append("- Test component interactions\n\n")

    lines.append("### Manual Testing\n")
    lines.append("- Verify end-to-end functionality\n\n")

    lines.append("---\n\n")

    # ==========================================================================
    # TASKS & NOTES
    # ==========================================================================
    if tasks:
        lines.append("## Tasks\n\n")
        for task_id in tasks:
            lines.append(f"- [{task_id}](../tasks/{task_id}.md)\n")
        lines.append("\n")

    lines.append("## Notes\n\n")
    notes = ticket.get("notes", "")
    if notes:
        lines.append(f"{notes}\n")
    else:
        lines.append("*Additional notes will be added during implementation.*\n")

    return "".join(lines)


# =============================================================================
# TASKS INDEX MARKDOWN
# =============================================================================


def generate_tasks_index_markdown(
    output: Dict[str, Any],
    spec_id: str,
    spec_title: str,
    created_date: str,
) -> str:
    """Generate tasks index markdown with overview and dependency graph."""
    tasks = output.get("tasks", [])
    tickets = output.get("tickets", [])
    critical_path = output.get("critical_path", [])
    total_hours = output.get("total_estimated_hours", 0)
    execution_order = output.get("execution_order", [])
    summary = output.get("summary", {})

    # Build frontmatter
    frontmatter = {
        "id": f"TASKS-{spec_id}",
        "title": f"{spec_title} Tasks",
        "spec_id": spec_id,
        "created": created_date,
        "updated": created_date,
        "status": "pending",
        "total_tasks": len(tasks),
        "total_tickets": len(tickets),
        "total_estimated_hours": total_hours,
        "critical_path": critical_path,
    }

    lines = [_yaml_frontmatter(frontmatter)]

    lines.append(f"# {spec_title} - Task Breakdown\n\n")

    # ==========================================================================
    # SUMMARY
    # ==========================================================================
    lines.append("## Summary\n\n")
    lines.append(f"- **Total Tickets**: {len(tickets)}\n")
    lines.append(f"- **Total Tasks**: {len(tasks)}\n")
    lines.append(f"- **Total Estimated Hours**: {total_hours}\n")
    lines.append(f"- **Critical Path**: {' → '.join(critical_path) if critical_path else 'N/A'}\n\n")

    # Estimate breakdown
    if summary.get("estimated_effort"):
        effort = summary["estimated_effort"]
        lines.append("### Effort Breakdown\n")
        lines.append(f"- **Small (S)**: {effort.get('S', 0)} tasks\n")
        lines.append(f"- **Medium (M)**: {effort.get('M', 0)} tasks\n")
        lines.append(f"- **Large (L)**: {effort.get('L', 0)} tasks\n\n")

    # Ready to start
    if summary.get("ready_to_start"):
        lines.append("### Ready to Start\n")
        for task_id in summary["ready_to_start"]:
            lines.append(f"- [{task_id}](./{task_id}.md)\n")
        lines.append("\n")

    # ==========================================================================
    # DEPENDENCY GRAPH
    # ==========================================================================
    if tasks:
        lines.append("## Dependency Graph\n\n")
        lines.append("```mermaid\n")
        lines.append("flowchart LR\n")

        # Define nodes
        for task in tasks:
            if not isinstance(task, dict):
                continue
            task_id = task.get("id", "???")
            title = task.get("title", "")[:15]
            safe_id = task_id.replace("-", "_")
            lines.append(f"    {safe_id}[{task_id}]\n")

        lines.append("\n")

        # Define edges from dependency graph or task dependencies
        dep_graph = output.get("dependency_graph", {})
        if dep_graph:
            for task_id, deps in dep_graph.items():
                safe_id = task_id.replace("-", "_")
                for dep in deps:
                    safe_dep = dep.replace("-", "_")
                    lines.append(f"    {safe_dep} --> {safe_id}\n")
        else:
            for task in tasks:
                if not isinstance(task, dict):
                    continue
                task_id = task.get("id", "")
                safe_id = task_id.replace("-", "_")
                deps = task.get("dependencies", {})
                if isinstance(deps, dict):
                    depends_on = deps.get("depends_on", [])
                elif isinstance(deps, list):
                    depends_on = deps
                else:
                    depends_on = []
                for dep in depends_on:
                    safe_dep = dep.replace("-", "_")
                    lines.append(f"    {safe_dep} --> {safe_id}\n")

        lines.append("```\n\n")

    # ==========================================================================
    # EXECUTION ORDER
    # ==========================================================================
    if execution_order:
        lines.append("## Execution Order\n\n")
        for phase in execution_order:
            if isinstance(phase, dict):
                phase_num = phase.get("phase", "?")
                phase_tasks = phase.get("tasks", [])
                parallel = phase.get("parallel", False)
                par_str = " (parallel)" if parallel else ""
                lines.append(f"**Phase {phase_num}**{par_str}: {', '.join(phase_tasks)}\n\n")

    # ==========================================================================
    # TICKETS
    # ==========================================================================
    if tickets:
        lines.append("## Tickets\n\n")
        lines.append("| ID | Title | Priority | Tasks | Status |\n")
        lines.append("|----|-------|----------|-------|--------|\n")

        for ticket in tickets:
            if not isinstance(ticket, dict):
                continue
            tid = ticket.get("id", "???")
            title = ticket.get("title", "")[:30]
            priority = ticket.get("priority", "MEDIUM")
            task_count = len(ticket.get("tasks", []))
            status = ticket.get("status", "backlog")
            lines.append(f"| [{tid}](../tickets/{tid}.md) | {title} | {priority} | {task_count} | {status} |\n")

        lines.append("\n")

    # ==========================================================================
    # ALL TASKS
    # ==========================================================================
    lines.append("## All Tasks\n\n")
    lines.append("| ID | Title | Type | Estimate | Dependencies |\n")
    lines.append("|----|-------|------|----------|---------------|\n")

    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = task.get("id", "???")
        title = task.get("title", "")[:30]
        task_type = task.get("type", "implementation")
        estimate = task.get("estimate", "M")
        deps = task.get("dependencies", {})

        if isinstance(deps, dict):
            depends_on = deps.get("depends_on", [])
        elif isinstance(deps, list):
            depends_on = deps
        else:
            depends_on = []

        deps_str = ", ".join(depends_on) if depends_on else "-"
        lines.append(f"| [{task_id}](./{task_id}.md) | {title} | {task_type} | {estimate} | {deps_str} |\n")

    lines.append("\n")

    return "".join(lines)


# =============================================================================
# SPEC SUMMARY MARKDOWN
# =============================================================================


def generate_spec_summary_markdown(
    sync_output: Dict[str, Any],
    requirements_output: Optional[Dict[str, Any]] = None,
    design_output: Optional[Dict[str, Any]] = None,
    tasks_output: Optional[Dict[str, Any]] = None,
    spec_id: str = "",
    spec_title: str = "",
    created_date: str = "",
) -> str:
    """Generate spec summary markdown with validation results and coverage."""
    validation = sync_output.get("validation_results", {})
    coverage = sync_output.get("coverage_matrix", [])
    summary = sync_output.get("spec_summary", {})
    ready = sync_output.get("ready_for_execution", False)
    blockers = sync_output.get("blockers", [])

    # Build frontmatter
    frontmatter = {
        "id": f"SPEC-{spec_id}",
        "title": f"{spec_title} Spec Summary",
        "spec_id": spec_id,
        "created": created_date,
        "updated": created_date,
        "ready_for_execution": ready,
        "total_requirements": summary.get("total_requirements", 0),
        "total_tasks": summary.get("total_tasks", 0),
        "total_estimated_hours": summary.get("total_estimated_hours", 0),
    }

    lines = [_yaml_frontmatter(frontmatter)]

    lines.append(f"# {spec_title} - Spec Summary\n\n")

    # Status
    status_emoji = "✅" if ready else "⚠️"
    lines.append(f"## Status: {status_emoji} {'Ready for Execution' if ready else 'Not Ready'}\n\n")

    # Summary stats
    lines.append("## Summary\n\n")
    lines.append("| Metric | Count |\n")
    lines.append("|--------|-------|\n")
    lines.append(f"| Requirements | {summary.get('total_requirements', 0)} |\n")
    lines.append(f"| Tasks | {summary.get('total_tasks', 0)} |\n")
    lines.append(f"| Estimated Hours | {summary.get('total_estimated_hours', 0)} |\n")
    lines.append(f"| Files to Modify | {summary.get('files_to_modify', 0)} |\n")
    lines.append(f"| Files to Create | {summary.get('files_to_create', 0)} |\n")
    lines.append("\n")

    # Validation Results
    lines.append("## Validation Results\n\n")
    if validation:
        all_reqs = validation.get("all_requirements_covered", False)
        all_comps = validation.get("all_components_have_tasks", False)
        deps_valid = validation.get("dependency_order_valid", False)
        issues = validation.get("issues_found", [])

        lines.append(f"- Requirements Coverage: {'✅' if all_reqs else '❌'}\n")
        lines.append(f"- Components Have Tasks: {'✅' if all_comps else '❌'}\n")
        lines.append(f"- Dependency Order Valid: {'✅' if deps_valid else '❌'}\n")

        if issues:
            lines.append("\n**Issues Found:**\n\n")
            for issue in issues:
                lines.append(f"- ⚠️ {issue}\n")
        lines.append("\n")

    # Coverage Matrix
    if coverage:
        lines.append("## Coverage Matrix\n\n")
        lines.append("| Requirement | Tasks | Status |\n")
        lines.append("|-------------|-------|--------|\n")

        for item in coverage:
            if not isinstance(item, dict):
                continue
            req_id = item.get("requirement_id", "???")
            tasks = item.get("covered_by_tasks", [])
            status = item.get("status", "unknown")

            status_emoji = {
                "fully_covered": "✅",
                "partially_covered": "⚠️",
                "not_covered": "❌",
            }.get(status, "❓")

            lines.append(f"| {req_id} | {', '.join(tasks)} | {status_emoji} {status} |\n")

        lines.append("\n")

    # Blockers
    if blockers:
        lines.append("## Blockers\n\n")
        for blocker in blockers:
            lines.append(f"- 🚫 {blocker}\n")
        lines.append("\n")

    # Generated Artifacts
    lines.append("## Generated Artifacts\n\n")
    lines.append("- [Requirements](./requirements.md)\n")
    lines.append("- [Design](./design.md)\n")
    lines.append("- [Tasks](./tasks/index.md)\n")
    lines.append("\n")

    return "".join(lines)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _python_type_to_sql(py_type: str) -> str:
    """Convert Python type hint to SQL type."""
    # Handle complex types
    if isinstance(py_type, dict):
        return "JSONB"

    py_type_str = str(py_type).lower()

    type_map = {
        "str": "VARCHAR(255)",
        "string": "VARCHAR(255)",
        "int": "INTEGER",
        "integer": "INTEGER",
        "float": "FLOAT",
        "bool": "BOOLEAN",
        "boolean": "BOOLEAN",
        "datetime": "TIMESTAMPTZ",
        "timestamp": "TIMESTAMPTZ",
        "date": "DATE",
        "uuid": "UUID",
        "dict": "JSONB",
        "list": "JSONB",
        "json": "JSONB",
        "jsonb": "JSONB",
        "text": "TEXT",
        "enum": "VARCHAR(50)",
    }

    # Check for string patterns
    if "string(" in py_type_str:
        # Extract length e.g., "string(2048)" -> "VARCHAR(2048)"
        import re
        match = re.search(r"string\((\d+)\)", py_type_str)
        if match:
            return f"VARCHAR({match.group(1)})"

    return type_map.get(py_type_str, "VARCHAR(255)")


def _normalize_python_type(py_type: str) -> str:
    """Normalize type string to valid Python type."""
    # Handle complex types
    if isinstance(py_type, dict):
        return "Dict[str, Any]"

    py_type_str = str(py_type).lower()

    type_map = {
        "string": "str",
        "integer": "int",
        "boolean": "bool",
        "uuid": "str",
        "json": "Dict[str, Any]",
        "jsonb": "Dict[str, Any]",
        "text": "str",
        "timestamp": "datetime",
        "timestamptz": "datetime",
    }

    # Check for string patterns
    if "string(" in py_type_str:
        return "str"

    return type_map.get(py_type_str, py_type)
