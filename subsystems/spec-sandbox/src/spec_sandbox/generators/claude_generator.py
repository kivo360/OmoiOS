"""Claude Agent SDK-based markdown generator.

This module generates markdown documentation using Claude Agent SDK,
allowing for language-agnostic code generation and intelligent content
based on the project's detected technology stack from the explore phase.

The generator uses JSON phase outputs as context and generates markdown
files that match the skill templates (requirements, design, tasks, tickets).
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

from spec_sandbox.reporters.base import Reporter
from spec_sandbox.schemas.events import Event, EventTypes


@dataclass
class ClaudeGeneratorConfig:
    """Configuration for Claude-based markdown generation.

    Attributes:
        model: Claude model to use for generation
        max_turns: Maximum agentic turns per generation
        output_dir: Directory to write generated markdown files
        spec_id: Spec identifier
        spec_title: Human-readable spec title
        use_mock: Use mock generation (for testing)
    """
    model: str = "claude-sonnet-4-5-20250929"
    max_turns: int = 10
    output_dir: Path = Path(".")
    spec_id: str = "spec-001"
    spec_title: str = "Untitled Spec"
    use_mock: bool = False


class ClaudeMarkdownGenerator:
    """Generates markdown documentation using Claude Agent SDK.

    This generator uses Claude to create rich markdown documents
    with YAML frontmatter, based on JSON phase outputs. Claude
    generates language-appropriate code examples based on the
    project's technology stack detected in the explore phase.

    Usage:
        generator = ClaudeMarkdownGenerator(config, reporter)
        artifacts = await generator.generate_all(
            explore_output=explore_data,
            requirements_output=requirements_data,
            design_output=design_data,
            tasks_output=tasks_data,
        )
    """

    def __init__(
        self,
        config: Optional[ClaudeGeneratorConfig] = None,
        reporter: Optional[Reporter] = None,
    ):
        self.config = config or ClaudeGeneratorConfig()
        self.reporter = reporter
        self._ensure_output_dirs()

    def _ensure_output_dirs(self) -> None:
        """Create output directories if they don't exist."""
        (self.config.output_dir / "requirements").mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "designs").mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "tasks").mkdir(parents=True, exist_ok=True)
        (self.config.output_dir / "tickets").mkdir(parents=True, exist_ok=True)

    async def generate_all(
        self,
        explore_output: Optional[Dict[str, Any]] = None,
        requirements_output: Optional[Dict[str, Any]] = None,
        design_output: Optional[Dict[str, Any]] = None,
        tasks_output: Optional[Dict[str, Any]] = None,
        sync_output: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Path]:
        """Generate all markdown artifacts using Claude.

        Returns a dict mapping artifact type to file path.
        """
        artifacts: Dict[str, Path] = {}

        # Build context from all phases
        context = {
            "explore": explore_output or {},
            "requirements": requirements_output or {},
            "design": design_output or {},
            "tasks": tasks_output or {},
            "sync": sync_output or {},
            "spec_id": self.config.spec_id,
            "spec_title": self.config.spec_title,
            "today": date.today().isoformat(),
        }

        # Detect language/framework from explore output
        tech_stack = self._detect_tech_stack(explore_output)
        context["tech_stack"] = tech_stack

        await self._emit_progress(f"Generating markdown with Claude (tech stack: {tech_stack.get('primary_language', 'unknown')})")

        # Generate requirements document
        if requirements_output:
            path = await self._generate_requirements(context)
            if path:
                artifacts["requirements"] = path

        # Generate design document
        if design_output:
            path = await self._generate_design(context)
            if path:
                artifacts["design"] = path

        # Generate task and ticket documents
        if tasks_output:
            # Generate tickets first (parent documents)
            tickets = tasks_output.get("tickets", [])
            for ticket in tickets:
                path = await self._generate_ticket(ticket, context)
                if path:
                    artifacts[f"ticket_{ticket.get('id', 'unknown')}"] = path

            # Generate individual task files
            tasks = tasks_output.get("tasks", [])
            for task in tasks:
                path = await self._generate_task(task, context)
                if path:
                    artifacts[f"task_{task.get('id', 'unknown')}"] = path

            # Generate tasks index
            path = await self._generate_tasks_index(context)
            if path:
                artifacts["tasks_index"] = path

        # Generate summary
        if sync_output:
            path = await self._generate_summary(context)
            if path:
                artifacts["summary"] = path

        return artifacts

    def _detect_tech_stack(self, explore_output: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect the technology stack from explore output."""
        if not explore_output:
            return {"primary_language": "python", "frameworks": []}

        # Check project_type field
        project_type = explore_output.get("project_type", "").lower()

        # Check structure for frontend/backend
        structure = explore_output.get("structure", {})
        frontend = structure.get("frontend", {})
        backend = structure.get("backend", {})

        # Determine primary language
        primary_language = "python"  # Default
        frameworks = []

        if "fastapi" in project_type or backend.get("framework", "").lower() == "fastapi":
            primary_language = "python"
            frameworks.append("FastAPI")
        elif "django" in project_type:
            primary_language = "python"
            frameworks.append("Django")
        elif "flask" in project_type:
            primary_language = "python"
            frameworks.append("Flask")
        elif "express" in project_type or "node" in project_type:
            primary_language = "typescript"
            frameworks.append("Express")
        elif "nest" in project_type:
            primary_language = "typescript"
            frameworks.append("NestJS")
        elif "go" in project_type or "gin" in project_type:
            primary_language = "go"
            frameworks.append("Gin")
        elif "rust" in project_type or "actix" in project_type:
            primary_language = "rust"
            frameworks.append("Actix")

        # Check for frontend frameworks
        frontend_framework = frontend.get("framework", "")
        if "next" in frontend_framework.lower():
            frameworks.append("Next.js")
        elif "react" in frontend_framework.lower():
            frameworks.append("React")
        elif "vue" in frontend_framework.lower():
            frameworks.append("Vue")
        elif "svelte" in frontend_framework.lower():
            frameworks.append("Svelte")

        # Check for database
        database = ""
        if "postgres" in project_type.lower() or backend.get("database", "").lower().startswith("postgres"):
            database = "PostgreSQL"
        elif "mysql" in project_type.lower():
            database = "MySQL"
        elif "mongo" in project_type.lower():
            database = "MongoDB"
        elif "sqlite" in project_type.lower():
            database = "SQLite"

        return {
            "primary_language": primary_language,
            "frameworks": frameworks,
            "database": database,
            "project_type": project_type,
        }

    async def _generate_requirements(self, context: Dict[str, Any]) -> Optional[Path]:
        """Generate requirements document using Claude."""
        requirements = context.get("requirements", {})
        if not requirements:
            return None

        prompt = self._build_requirements_prompt(context)

        if self.config.use_mock:
            content = self._mock_requirements(context)
        else:
            content = await self._generate_with_claude(prompt, "requirements")

        # Write to file
        feature_name = self._to_kebab_case(context.get("spec_title", "feature"))
        path = self.config.output_dir / "requirements" / f"{feature_name}.md"
        path.write_text(content)

        return path

    async def _generate_design(self, context: Dict[str, Any]) -> Optional[Path]:
        """Generate design document using Claude."""
        design = context.get("design", {})
        if not design:
            return None

        prompt = self._build_design_prompt(context)

        if self.config.use_mock:
            content = self._mock_design(context)
        else:
            content = await self._generate_with_claude(prompt, "design")

        # Write to file
        feature_name = self._to_kebab_case(context.get("spec_title", "feature"))
        path = self.config.output_dir / "designs" / f"{feature_name}.md"
        path.write_text(content)

        return path

    async def _generate_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> Optional[Path]:
        """Generate a single task document using Claude."""
        task_id = task.get("id", "TASK-001")

        prompt = self._build_task_prompt(task, context)

        if self.config.use_mock:
            content = self._mock_task(task, context)
        else:
            content = await self._generate_with_claude(prompt, f"task_{task_id}")

        # Write to file
        path = self.config.output_dir / "tasks" / f"{task_id}.md"
        path.write_text(content)

        return path

    async def _generate_ticket(self, ticket: Dict[str, Any], context: Dict[str, Any]) -> Optional[Path]:
        """Generate a single ticket document using Claude."""
        ticket_id = ticket.get("id", "TKT-001")

        prompt = self._build_ticket_prompt(ticket, context)

        if self.config.use_mock:
            content = self._mock_ticket(ticket, context)
        else:
            content = await self._generate_with_claude(prompt, f"ticket_{ticket_id}")

        # Write to file
        path = self.config.output_dir / "tickets" / f"{ticket_id}.md"
        path.write_text(content)

        return path

    async def _generate_tasks_index(self, context: Dict[str, Any]) -> Optional[Path]:
        """Generate tasks index document."""
        tasks = context.get("tasks", {}).get("tasks", [])
        tickets = context.get("tasks", {}).get("tickets", [])

        if not tasks and not tickets:
            return None

        prompt = self._build_tasks_index_prompt(context)

        if self.config.use_mock:
            content = self._mock_tasks_index(context)
        else:
            content = await self._generate_with_claude(prompt, "tasks_index")

        # Write to file
        path = self.config.output_dir / "tasks" / "index.md"
        path.write_text(content)

        return path

    async def _generate_summary(self, context: Dict[str, Any]) -> Optional[Path]:
        """Generate spec summary document."""
        sync = context.get("sync", {})
        if not sync:
            return None

        prompt = self._build_summary_prompt(context)

        if self.config.use_mock:
            content = self._mock_summary(context)
        else:
            content = await self._generate_with_claude(prompt, "summary")

        # Write to file
        path = self.config.output_dir / "summary.md"
        path.write_text(content)

        return path

    async def _generate_with_claude(self, prompt: str, artifact_type: str) -> str:
        """Generate content using Claude Agent SDK."""
        try:
            from claude_agent_sdk import (
                AssistantMessage,
                ClaudeAgentOptions,
                ClaudeSDKClient,
                ResultMessage,
                TextBlock,
            )

            options = ClaudeAgentOptions(
                model=self.config.model,
                max_turns=self.config.max_turns,
                permission_mode="bypassPermissions",
            )

            content_parts: List[str] = []

            async with ClaudeSDKClient(options=options) as client:
                await client.query(prompt)

                async for message in client.receive_messages():
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                content_parts.append(block.text)
                    elif isinstance(message, ResultMessage):
                        break

            return "\n".join(content_parts)

        except ImportError:
            # SDK not available - use mock
            await self._emit_progress(f"Claude SDK not available for {artifact_type}, using mock")
            return self._mock_fallback(artifact_type, prompt)
        except Exception as e:
            await self._emit_progress(f"Claude generation failed for {artifact_type}: {e}")
            return self._mock_fallback(artifact_type, prompt)

    def _mock_fallback(self, artifact_type: str, prompt: str) -> str:
        """Fallback mock content when Claude is unavailable."""
        return f"# {artifact_type.replace('_', ' ').title()}\n\n_Generated without Claude SDK_\n"

    # === PROMPT BUILDERS ===

    def _build_requirements_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for requirements document generation."""
        requirements = context.get("requirements", {})
        tech_stack = context.get("tech_stack", {})
        primary_language = tech_stack.get("primary_language", "python")

        return f"""Generate a requirements markdown document following this exact structure.

## Context

**Spec Title**: {context.get("spec_title", "Feature")}
**Primary Language**: {primary_language}
**Tech Stack**: {json.dumps(tech_stack, indent=2)}

## Requirements JSON Data

{json.dumps(requirements, indent=2)}

## Output Format

Generate a complete markdown document with:

1. **YAML Frontmatter** with these fields:
   - id: REQ-{{DOMAIN}}-001
   - title: {context.get("spec_title", "Feature")} Requirements
   - feature: {self._to_kebab_case(context.get("spec_title", "feature"))}
   - created: {context.get("today")}
   - updated: {context.get("today")}
   - status: draft
   - category: functional
   - priority: HIGH
   - design_ref: designs/{self._to_kebab_case(context.get("spec_title", "feature"))}.md

2. **Document Overview** section

3. **Requirements sections** using EARS format:
   - "THE SYSTEM SHALL" for functional requirements
   - "WHEN <condition>, THE SYSTEM SHALL" for conditional requirements
   - Use REQ-DOMAIN-AREA-NUM format for IDs

4. **State Machine** section with Mermaid diagram (if applicable)

5. **Data Model Requirements** section with field definitions

6. **Configuration** section with parameter table

7. **API** section with endpoints table and WebSocket contracts

8. **SLOs & Performance** section

9. **Security & Audit** section

10. **Pydantic Reference Models** section with code examples in {primary_language}:
    - Generate ACTUAL code examples, not placeholders
    - Use the data models from the JSON to create real Pydantic/dataclass definitions
    - Include proper imports, type hints, and docstrings

11. **Related Documents** section

12. **Revision History** table

IMPORTANT: Generate ACTUAL code examples appropriate for {primary_language}, not placeholder templates.
Output ONLY the markdown content, no explanations."""

    def _build_design_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for design document generation."""
        design = context.get("design", {})
        tech_stack = context.get("tech_stack", {})
        primary_language = tech_stack.get("primary_language", "python")
        database = tech_stack.get("database", "PostgreSQL")

        return f"""Generate a design markdown document following this exact structure.

## Context

**Spec Title**: {context.get("spec_title", "Feature")}
**Primary Language**: {primary_language}
**Database**: {database}
**Tech Stack**: {json.dumps(tech_stack, indent=2)}

## Design JSON Data

{json.dumps(design, indent=2)}

## Requirements Context

{json.dumps(context.get("requirements", {}), indent=2)}

## Output Format

Generate a complete markdown document with:

1. **YAML Frontmatter** with these fields:
   - id: DESIGN-{{FEATURE}}-001
   - title: {context.get("spec_title", "Feature")} Design
   - feature: {self._to_kebab_case(context.get("spec_title", "feature"))}
   - created: {context.get("today")}
   - updated: {context.get("today")}
   - status: draft
   - requirements: [list of requirement IDs]

2. **Document Overview** with Purpose & Scope, Target Audience, Related Documents

3. **Architecture Overview** with:
   - Mermaid flowchart diagram showing high-level architecture
   - Component Responsibilities table
   - System Boundaries

4. **Component Details** for each component from the JSON

5. **Data Models** section with:
   - **Database Schema** in SQL for {database}
   - **Pydantic/ORM Models** in {primary_language}
   - Generate ACTUAL schemas based on the JSON data models

6. **API Specifications** with:
   - REST Endpoints table
   - Request/Response Models
   - Error Handling table

7. **Integration Points** with Mermaid sequence diagram

8. **Implementation Details** with:
   - Core Algorithm pseudocode in {primary_language}
   - Operation Flow sequence diagram

9. **Configuration** table

10. **Performance Considerations** (indexing, caching, batch processing)

11. **Security Considerations**

12. **Quality Checklist**

13. **Revision History** table

IMPORTANT:
- Generate ACTUAL SQL schemas appropriate for {database}
- Generate ACTUAL {primary_language} code for models
- Use the components, data_models, and api_endpoints from the JSON
- Create proper Mermaid diagrams showing actual component relationships

Output ONLY the markdown content, no explanations."""

    def _build_task_prompt(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build prompt for task document generation."""
        tech_stack = context.get("tech_stack", {})
        primary_language = tech_stack.get("primary_language", "python")

        return f"""Generate a task markdown document following this exact structure.

## Context

**Spec Title**: {context.get("spec_title", "Feature")}
**Primary Language**: {primary_language}
**Tech Stack**: {json.dumps(tech_stack, indent=2)}

## Task JSON Data

{json.dumps(task, indent=2)}

## Design Context

{json.dumps(context.get("design", {}), indent=2)}

## Output Format

Generate a complete markdown document with:

1. **YAML Frontmatter** with these fields:
   - id: {task.get("id", "TASK-001")}
   - title: {task.get("title", "Task")}
   - status: pending
   - parent_ticket: {task.get("parent_ticket", "TKT-001")}
   - estimate: {task.get("estimate", "M")}
   - created: {context.get("today")}
   - assignee: null
   - requirements_addressed: {task.get("requirements_addressed", [])}
   - dependencies:
     - depends_on: {task.get("dependencies", [])}
     - blocks: []

2. **Objective** section (1-2 sentences)

3. **Deliverables** section with file paths and checkboxes

4. **Implementation Notes** with:
   - Step-by-step Approach
   - Code Patterns with ACTUAL {primary_language} code examples
   - References to relevant documentation

5. **Acceptance Criteria** with checkboxes

6. **Testing Requirements** with:
   - Unit Tests with ACTUAL test code in {primary_language}
   - Edge Cases list

7. **Notes** section

IMPORTANT:
- Generate ACTUAL code examples in {primary_language}
- Use realistic file paths based on the project structure
- Include proper test patterns for the language/framework

Output ONLY the markdown content, no explanations."""

    def _build_ticket_prompt(self, ticket: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Build prompt for ticket document generation."""
        tech_stack = context.get("tech_stack", {})
        primary_language = tech_stack.get("primary_language", "python")

        return f"""Generate a ticket markdown document following this exact structure.

## Context

**Spec Title**: {context.get("spec_title", "Feature")}
**Primary Language**: {primary_language}
**Tech Stack**: {json.dumps(tech_stack, indent=2)}

## Ticket JSON Data

{json.dumps(ticket, indent=2)}

## Design Context

{json.dumps(context.get("design", {}), indent=2)}

## Output Format

Generate a complete markdown document with:

1. **YAML Frontmatter** with these fields:
   - id: {ticket.get("id", "TKT-001")}
   - title: {ticket.get("title", "Ticket")}
   - status: backlog
   - priority: {ticket.get("priority", "MEDIUM")}
   - estimate: {ticket.get("estimate", "M")}
   - created: {context.get("today")}
   - updated: {context.get("today")}
   - feature: {self._to_kebab_case(context.get("spec_title", "feature"))}
   - requirements: {ticket.get("requirements", [])}
   - design_ref: designs/{self._to_kebab_case(context.get("spec_title", "feature"))}.md
   - tasks: {ticket.get("tasks", [])}
   - dependencies:
     - blocked_by: {ticket.get("blocked_by", [])}
     - blocks: {ticket.get("blocks", [])}
     - related: []

2. **Description** with Context, Goals, Non-Goals

3. **Acceptance Criteria** with checkboxes

4. **Technical Notes** with:
   - Implementation Approach
   - Key Files list
   - API Changes summary
   - Database Changes summary

5. **Testing Strategy** with Unit Tests, Integration Tests, Manual Testing

6. **Rollback Plan**

7. **Notes** section

Output ONLY the markdown content, no explanations."""

    def _build_tasks_index_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for tasks index generation."""
        tasks_output = context.get("tasks", {})

        return f"""Generate a tasks index markdown document.

## Context

**Spec Title**: {context.get("spec_title", "Feature")}
**Today**: {context.get("today")}

## Tasks/Tickets JSON Data

{json.dumps(tasks_output, indent=2)}

## Output Format

Generate a markdown document with:

1. **YAML Frontmatter** with:
   - title: {context.get("spec_title", "Feature")} Tasks
   - spec_id: {context.get("spec_id")}
   - created: {context.get("today")}

2. **Summary** section with statistics table:
   - Total tickets count
   - Total tasks count
   - Status breakdown

3. **Tickets** section listing all tickets with status

4. **Tasks by Ticket** section organizing tasks under their parent tickets

5. **Dependency Graph** section with Mermaid diagram showing task dependencies

6. **Execution Order** section listing tasks in order they should be executed

Output ONLY the markdown content, no explanations."""

    def _build_summary_prompt(self, context: Dict[str, Any]) -> str:
        """Build prompt for spec summary generation."""
        sync = context.get("sync", {})

        return f"""Generate a spec summary markdown document.

## Context

**Spec Title**: {context.get("spec_title", "Feature")}
**Spec ID**: {context.get("spec_id")}
**Today**: {context.get("today")}

## Sync/Validation JSON Data

{json.dumps(sync, indent=2)}

## All Phase Outputs

Explore: {json.dumps(context.get("explore", {}), indent=2)}
Requirements: {json.dumps(context.get("requirements", {}), indent=2)}
Design: {json.dumps(context.get("design", {}), indent=2)}
Tasks: {json.dumps(context.get("tasks", {}), indent=2)}

## Output Format

Generate a markdown document with:

1. **YAML Frontmatter** with:
   - title: {context.get("spec_title", "Feature")} - Spec Summary
   - spec_id: {context.get("spec_id")}
   - created: {context.get("today")}
   - status: ready_for_execution

2. **Overview** with spec description and goals

3. **Coverage Matrix** table showing requirements and implementing tasks

4. **Validation Results** showing all checks passed

5. **Statistics** table with counts

6. **Generated Artifacts** list with paths

7. **Next Steps** for implementation

Output ONLY the markdown content, no explanations."""

    # === MOCK GENERATORS ===

    def _mock_requirements(self, context: Dict[str, Any]) -> str:
        """Generate mock requirements document."""
        requirements = context.get("requirements", {})
        tech_stack = context.get("tech_stack", {})
        today = context.get("today")
        spec_title = context.get("spec_title", "Feature")
        feature_name = self._to_kebab_case(spec_title)
        primary_language = tech_stack.get("primary_language", "python")

        reqs = requirements.get("requirements", [])
        req_list = "\n".join([
            f"#### REQ-{i+1:03d}: {r.get('title', r.get('id', f'Requirement {i+1}'))}\n"
            f"THE SYSTEM SHALL {r.get('text', r.get('description', 'implement this requirement'))}.\n"
            for i, r in enumerate(reqs)
        ])

        # Generate language-appropriate code
        if primary_language == "python":
            code_example = self._python_pydantic_example(requirements)
        elif primary_language == "typescript":
            code_example = self._typescript_interface_example(requirements)
        else:
            code_example = self._python_pydantic_example(requirements)

        return f"""---
id: REQ-{feature_name.upper()[:4]}-001
title: {spec_title} Requirements
feature: {feature_name}
created: {today}
updated: {today}
status: draft
category: functional
priority: HIGH
design_ref: designs/{feature_name}.md
---

# {spec_title} Requirements

## Document Overview

This document defines the requirements for {spec_title}.

---

## 1. Functional Requirements

{req_list if req_list else "#### REQ-001: Core Functionality\\nTHE SYSTEM SHALL implement the core feature functionality.\\n"}

---

## 2. Data Model Requirements

### 2.1 Entity Fields
{self._format_data_models(requirements.get("data_models", []))}

---

## 3. API Requirements

{self._format_api_table(requirements.get("api_endpoints", []))}

---

## 4. Reference Models

```{primary_language}
{code_example}
```

---

## Related Documents

- [Design Document](../designs/{feature_name}.md)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {today} | System | Initial draft |
"""

    def _mock_design(self, context: Dict[str, Any]) -> str:
        """Generate mock design document."""
        design = context.get("design", {})
        tech_stack = context.get("tech_stack", {})
        today = context.get("today")
        spec_title = context.get("spec_title", "Feature")
        feature_name = self._to_kebab_case(spec_title)
        primary_language = tech_stack.get("primary_language", "python")
        database = tech_stack.get("database", "PostgreSQL")

        components = design.get("components", [])
        data_models = design.get("data_models", [])

        # Generate architecture diagram
        arch_diagram = self._generate_architecture_mermaid(components)

        # Generate SQL schema
        sql_schema = self._generate_sql_schema(data_models, database)

        # Generate language-appropriate models
        if primary_language == "python":
            models_code = self._python_models_example(data_models)
        elif primary_language == "typescript":
            models_code = self._typescript_models_example(data_models)
        else:
            models_code = self._python_models_example(data_models)

        return f"""---
id: DESIGN-{feature_name.upper()[:4]}-001
title: {spec_title} Design
feature: {feature_name}
created: {today}
updated: {today}
status: draft
requirements:
  - REQ-{feature_name.upper()[:4]}-001
---

# {spec_title} - Product Design Document

## Document Overview

This document describes the design for {spec_title}.

- **Purpose & Scope**
  - Implement {spec_title} functionality
  - Provide clean API interfaces

- **Target Audience**
  - Implementation teams
  - System architects

---

## Architecture Overview

### High-Level Architecture

{arch_diagram}

### Component Responsibilities

{self._format_components_table(components)}

---

## Data Models

### Database Schema

```sql
{sql_schema}
```

### {primary_language.title()} Models

```{primary_language}
{models_code}
```

---

## API Specifications

### REST Endpoints

{self._format_api_spec_table(design.get("api_endpoints", []))}

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | {today} | System | Initial design |
"""

    def _mock_task(self, task: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate mock task document."""
        tech_stack = context.get("tech_stack", {})
        today = context.get("today")
        primary_language = tech_stack.get("primary_language", "python")

        task_id = task.get("id", "TASK-001")
        title = task.get("title", "Task")
        description = task.get("description", "Implement task")
        deps = task.get("dependencies", [])
        reqs_addressed = task.get("requirements_addressed", [])

        # Generate test code
        if primary_language == "python":
            test_code = self._python_test_example(task)
        elif primary_language == "typescript":
            test_code = self._typescript_test_example(task)
        else:
            test_code = self._python_test_example(task)

        return f"""---
id: {task_id}
title: {title}
status: pending
parent_ticket: TKT-001
estimate: M
created: {today}
assignee: null
requirements_addressed: {reqs_addressed}
dependencies:
  depends_on: {deps}
  blocks: []
---

# {task_id}: {title}

## Objective

{description}

---

## Deliverables

- [ ] Implementation files
- [ ] Test files
- [ ] Documentation updates

---

## Implementation Notes

### Approach

1. Create necessary files
2. Implement core logic
3. Add tests
4. Verify functionality

### Code Patterns

```{primary_language}
{test_code}
```

---

## Acceptance Criteria

- [ ] Core functionality works
- [ ] All tests pass
- [ ] No linting errors

---

## Testing Requirements

### Unit Tests

```{primary_language}
{test_code}
```

---

## Notes

Task generated from spec sandbox.
"""

    def _mock_ticket(self, ticket: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate mock ticket document."""
        today = context.get("today")
        spec_title = context.get("spec_title", "Feature")
        feature_name = self._to_kebab_case(spec_title)

        ticket_id = ticket.get("id", "TKT-001")
        title = ticket.get("title", "Ticket")
        description = ticket.get("description", "Implement feature")
        tasks = ticket.get("tasks", [])

        return f"""---
id: {ticket_id}
title: {title}
status: backlog
priority: MEDIUM
estimate: M
created: {today}
updated: {today}
feature: {feature_name}
requirements:
  - REQ-{feature_name.upper()[:4]}-001
design_ref: designs/{feature_name}.md
tasks: {tasks}
dependencies:
  blocked_by: []
  blocks: []
  related: []
---

# {ticket_id}: {title}

## Description

{description}

### Context

Implementation ticket for {spec_title}.

### Goals

- Implement core functionality
- Add comprehensive tests

### Non-Goals

- UI changes (separate ticket)

---

## Acceptance Criteria

- [ ] All tasks completed
- [ ] Tests pass
- [ ] Documentation updated

---

## Technical Notes

### Implementation Approach

Follow the design document for implementation details.

### Key Files

- See task documents for specific files

---

## Testing Strategy

### Unit Tests
- Cover all new functions

### Integration Tests
- Test API endpoints

---

## Notes

Ticket generated from spec sandbox.
"""

    def _mock_tasks_index(self, context: Dict[str, Any]) -> str:
        """Generate mock tasks index document."""
        tasks_output = context.get("tasks", {})
        today = context.get("today")
        spec_title = context.get("spec_title", "Feature")

        tasks = tasks_output.get("tasks", [])
        tickets = tasks_output.get("tickets", [])

        task_list = "\n".join([
            f"- [{t.get('id', 'TASK-???')}](./tasks/{t.get('id', 'TASK-???')}.md) - {t.get('title', 'Task')}"
            for t in tasks
        ])

        ticket_list = "\n".join([
            f"- [{t.get('id', 'TKT-???')}](./tickets/{t.get('id', 'TKT-???')}.md) - {t.get('title', 'Ticket')}"
            for t in tickets
        ])

        return f"""---
title: {spec_title} Tasks
spec_id: {context.get("spec_id")}
created: {today}
---

# {spec_title} Tasks

## Summary

| Metric | Count |
|--------|-------|
| Total Tickets | {len(tickets)} |
| Total Tasks | {len(tasks)} |
| Pending | {len(tasks)} |

---

## Tickets

{ticket_list if ticket_list else "_No tickets defined_"}

---

## Tasks

{task_list if task_list else "_No tasks defined_"}

---

## Execution Order

{self._format_execution_order(tasks_output.get("execution_order", [t.get("id") for t in tasks]))}
"""

    def _mock_summary(self, context: Dict[str, Any]) -> str:
        """Generate mock summary document."""
        sync = context.get("sync", {})
        today = context.get("today")
        spec_title = context.get("spec_title", "Feature")

        # Get requirements and tasks for traceability stats
        requirements = context.get("requirements", {}).get("requirements", [])
        tasks = context.get("tasks", {}).get("tasks", [])

        # Calculate traceability stats (compatible with skill script format)
        req_ids = {r.get("id") for r in requirements if r.get("id")}
        addressed: set = set()
        for task in tasks:
            task_reqs = task.get("requirements_addressed", [])
            if isinstance(task_reqs, list):
                addressed.update(task_reqs)

        linked_reqs = addressed.intersection(req_ids)
        total_reqs = len(req_ids)
        req_coverage = (len(linked_reqs) / total_reqs * 100) if total_reqs > 0 else 100

        # Count task statuses
        pending_count = sum(1 for t in tasks if t.get("status", "pending") == "pending")
        done_count = sum(1 for t in tasks if t.get("status") == "done")
        in_progress_count = len(tasks) - pending_count - done_count

        # Get orphan requirements
        orphan_reqs = list(req_ids - addressed)

        return f"""---
title: {spec_title} - Spec Summary
spec_id: {context.get("spec_id")}
created: {today}
status: ready_for_execution
---

# {spec_title} - Spec Summary

## Overview

This spec defines the implementation plan for {spec_title}.

---

## Validation Results

✅ All requirements covered
✅ All components have tasks
✅ Dependency order valid
✅ No circular dependencies detected

---

## Traceability Statistics

### Requirements Coverage

| Metric | Value |
|--------|-------|
| Total Requirements | {total_reqs} |
| Linked to Tasks | {len(linked_reqs)} |
| Coverage | {req_coverage:.1f}% |

### Task Status Breakdown

| Status | Count |
|--------|-------|
| Total Tasks | {len(tasks)} |
| Done | {done_count} |
| In Progress | {in_progress_count} |
| Pending | {pending_count} |

{f"### Orphan Requirements{chr(10)}{chr(10)}The following requirements are not addressed by any task:{chr(10)}" + chr(10).join(f"- {r}" for r in orphan_reqs) if orphan_reqs else ""}

---

## Statistics

| Metric | Count |
|--------|-------|
| Requirements | {len(requirements)} |
| Components | {len(context.get("design", {}).get("components", []))} |
| Tasks | {len(tasks)} |

---

## Next Steps

1. Review generated documents
2. Assign tasks to agents
3. Begin implementation
"""

    # === HELPER METHODS ===

    def _to_kebab_case(self, text: str) -> str:
        """Convert text to kebab-case."""
        import re
        text = re.sub(r'([A-Z])', r'-\1', text)
        text = re.sub(r'[^a-zA-Z0-9]+', '-', text)
        text = re.sub(r'-+', '-', text)
        return text.lower().strip('-')

    def _format_data_models(self, models: List[Dict[str, Any]]) -> str:
        """Format data models as markdown."""
        if not models:
            return "_No data models defined_"

        result = []
        for model in models:
            name = model.get("name", "Entity")
            fields = model.get("fields", {})

            result.append(f"#### {name}")
            if isinstance(fields, dict):
                for field, ftype in fields.items():
                    result.append(f"- `{field}: {ftype}`")
            elif isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        result.append(f"- `{field.get('name', 'field')}: {field.get('type', 'any')}`")
                    else:
                        result.append(f"- `{field}`")
            result.append("")

        return "\n".join(result)

    def _format_api_table(self, endpoints: List[Dict[str, Any]]) -> str:
        """Format API endpoints as markdown table."""
        if not endpoints:
            return "_No API endpoints defined_"

        lines = ["| Method | Path | Purpose |", "|--------|------|---------|"]
        for ep in endpoints:
            method = ep.get("method", "GET")
            path = ep.get("path", "/api/resource")
            purpose = ep.get("purpose", "")
            lines.append(f"| {method} | `{path}` | {purpose} |")

        return "\n".join(lines)

    def _format_api_spec_table(self, endpoints: List[Dict[str, Any]]) -> str:
        """Format API spec with request/response."""
        if not endpoints:
            return "_No API endpoints defined_"

        lines = ["| Method | Path | Purpose | Request | Response |", "|--------|------|---------|---------|----------|"]
        for ep in endpoints:
            method = ep.get("method", "GET")
            path = ep.get("path", "/api/resource")
            purpose = ep.get("purpose", "")
            req = ep.get("request_schema", "-")
            resp = ep.get("response_schema", "-")
            lines.append(f"| {method} | `{path}` | {purpose} | `{req}` | `{resp}` |")

        return "\n".join(lines)

    def _format_components_table(self, components: List[Dict[str, Any]]) -> str:
        """Format components as markdown table."""
        if not components:
            return "_No components defined_"

        lines = ["| Component | Type | Responsibilities |", "|-----------|------|------------------|"]
        for comp in components:
            name = comp.get("name", "Component")
            ctype = comp.get("type", "service")
            resp = comp.get("responsibility", "")
            lines.append(f"| {name} | {ctype} | {resp} |")

        return "\n".join(lines)

    def _format_execution_order(self, order: List[str]) -> str:
        """Format execution order as numbered list."""
        if not order:
            return "_No execution order defined_"

        return "\n".join([f"{i+1}. {task_id}" for i, task_id in enumerate(order)])

    def _generate_architecture_mermaid(self, components: List[Dict[str, Any]]) -> str:
        """Generate Mermaid architecture diagram."""
        if not components:
            return """```mermaid
flowchart TD
    API[API Layer]
    Service[Service Layer]
    Data[Data Layer]

    API --> Service
    Service --> Data
```"""

        nodes = []
        connections = []

        for comp in components:
            name = comp.get("name", "Component")
            safe_name = name.replace(" ", "_")
            nodes.append(f"    {safe_name}[{name}]")

            deps = comp.get("dependencies", [])
            for dep in deps:
                safe_dep = dep.replace(" ", "_")
                connections.append(f"    {safe_name} --> {safe_dep}")

        diagram = "```mermaid\nflowchart TD\n"
        diagram += "\n".join(nodes)
        if connections:
            diagram += "\n" + "\n".join(connections)
        diagram += "\n```"

        return diagram

    def _generate_sql_schema(self, models: List[Dict[str, Any]], database: str) -> str:
        """Generate SQL schema for data models."""
        if not models:
            return "-- No models defined"

        schema_parts = []

        for model in models:
            name = model.get("name", "entity")
            table_name = self._to_snake_case(name) + "s"
            fields = model.get("fields", {})

            columns = []
            columns.append("    id UUID PRIMARY KEY DEFAULT gen_random_uuid()")

            if isinstance(fields, dict):
                for field, ftype in fields.items():
                    if field == "id":
                        continue
                    sql_type = self._python_to_sql_type(ftype)
                    columns.append(f"    {field} {sql_type}")
            elif isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        fname = field.get("name", "field")
                        ftype = field.get("type", "str")
                        if fname == "id":
                            continue
                        sql_type = self._python_to_sql_type(ftype)
                        columns.append(f"    {fname} {sql_type}")

            columns.append("    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
            columns.append("    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")

            schema_parts.append(f"CREATE TABLE {table_name} (\n" + ",\n".join(columns) + "\n);")

        return "\n\n".join(schema_parts)

    def _to_snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        import re
        text = re.sub(r'([A-Z])', r'_\1', text)
        text = re.sub(r'[^a-zA-Z0-9]+', '_', text)
        text = re.sub(r'_+', '_', text)
        return text.lower().strip('_')

    def _python_to_sql_type(self, python_type: str) -> str:
        """Convert Python type hint to SQL type."""
        type_map = {
            "str": "VARCHAR(255)",
            "string": "VARCHAR(255)",
            "int": "INTEGER",
            "integer": "INTEGER",
            "float": "FLOAT",
            "bool": "BOOLEAN",
            "boolean": "BOOLEAN",
            "datetime": "TIMESTAMPTZ",
            "date": "DATE",
            "uuid": "UUID",
            "dict": "JSONB",
            "list": "JSONB",
            "json": "JSONB",
            "text": "TEXT",
        }
        return type_map.get(python_type.lower(), "VARCHAR(255)")

    # === LANGUAGE-SPECIFIC CODE GENERATORS ===

    def _python_pydantic_example(self, requirements: Dict[str, Any]) -> str:
        """Generate Python Pydantic models."""
        models = requirements.get("data_models", [])
        if not models:
            return """from pydantic import BaseModel

class Entity(BaseModel):
    id: str
    name: str
"""

        imports = ["from __future__ import annotations", "from datetime import datetime", "from typing import Optional, List, Dict, Any", "from pydantic import BaseModel, Field", ""]

        classes = []
        for model in models:
            name = model.get("name", "Entity")
            fields = model.get("fields", {})

            class_def = [f"class {name}(BaseModel):"]

            if isinstance(fields, dict):
                for fname, ftype in fields.items():
                    py_type = self._sql_to_python_type(ftype)
                    class_def.append(f"    {fname}: {py_type}")
            elif isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        fname = field.get("name", "field")
                        ftype = field.get("type", "str")
                        py_type = self._sql_to_python_type(ftype)
                        class_def.append(f"    {fname}: {py_type}")

            if len(class_def) == 1:
                class_def.append("    pass")

            classes.append("\n".join(class_def))

        return "\n".join(imports) + "\n\n" + "\n\n".join(classes)

    def _python_models_example(self, models: List[Dict[str, Any]]) -> str:
        """Generate Python ORM models."""
        if not models:
            return """from sqlalchemy import Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Entity(Base):
    __tablename__ = "entities"
    id = Column(String, primary_key=True)
    name = Column(String)
"""

        return self._python_pydantic_example({"data_models": models})

    def _python_test_example(self, task: Dict[str, Any]) -> str:
        """Generate Python test code."""
        title = task.get("title", "feature")
        safe_name = self._to_snake_case(title)

        return f"""import pytest

def test_{safe_name}_basic():
    \"\"\"Test basic {title} functionality.\"\"\"
    # Arrange
    # TODO: Set up test data

    # Act
    # TODO: Call function under test

    # Assert
    assert True  # TODO: Add assertions


def test_{safe_name}_edge_case():
    \"\"\"Test edge case for {title}.\"\"\"
    pass
"""

    def _typescript_interface_example(self, requirements: Dict[str, Any]) -> str:
        """Generate TypeScript interfaces."""
        models = requirements.get("data_models", [])
        if not models:
            return """export interface Entity {
  id: string;
  name: string;
}
"""

        interfaces = []
        for model in models:
            name = model.get("name", "Entity")
            fields = model.get("fields", {})

            interface_def = [f"export interface {name} {{"]

            if isinstance(fields, dict):
                for fname, ftype in fields.items():
                    ts_type = self._python_to_typescript_type(ftype)
                    interface_def.append(f"  {fname}: {ts_type};")
            elif isinstance(fields, list):
                for field in fields:
                    if isinstance(field, dict):
                        fname = field.get("name", "field")
                        ftype = field.get("type", "str")
                        ts_type = self._python_to_typescript_type(ftype)
                        interface_def.append(f"  {fname}: {ts_type};")

            interface_def.append("}")
            interfaces.append("\n".join(interface_def))

        return "\n\n".join(interfaces)

    def _typescript_models_example(self, models: List[Dict[str, Any]]) -> str:
        """Generate TypeScript model classes."""
        return self._typescript_interface_example({"data_models": models})

    def _typescript_test_example(self, task: Dict[str, Any]) -> str:
        """Generate TypeScript test code."""
        title = task.get("title", "feature")

        return f"""import {{ describe, it, expect }} from 'vitest';

describe('{title}', () => {{
  it('should handle basic case', () => {{
    // Arrange
    // TODO: Set up test data

    // Act
    // TODO: Call function under test

    // Assert
    expect(true).toBe(true);
  }});

  it('should handle edge case', () => {{
    // TODO: Add edge case test
  }});
}});
"""

    def _sql_to_python_type(self, sql_type: str) -> str:
        """Convert SQL-like type to Python type."""
        type_map = {
            "str": "str",
            "string": "str",
            "varchar": "str",
            "text": "str",
            "int": "int",
            "integer": "int",
            "float": "float",
            "bool": "bool",
            "boolean": "bool",
            "datetime": "datetime",
            "date": "date",
            "uuid": "str",
            "json": "Dict[str, Any]",
            "jsonb": "Dict[str, Any]",
            "list": "List[Any]",
            "array": "List[Any]",
        }
        return type_map.get(sql_type.lower(), "str")

    def _python_to_typescript_type(self, python_type: str) -> str:
        """Convert Python type to TypeScript type."""
        type_map = {
            "str": "string",
            "string": "string",
            "int": "number",
            "integer": "number",
            "float": "number",
            "bool": "boolean",
            "boolean": "boolean",
            "datetime": "string",  # ISO date string
            "date": "string",
            "uuid": "string",
            "dict": "Record<string, unknown>",
            "list": "unknown[]",
            "json": "Record<string, unknown>",
        }
        return type_map.get(python_type.lower(), "unknown")

    async def _emit_progress(self, message: str) -> None:
        """Emit progress event."""
        if self.reporter is not None:
            event = Event(
                event_type=EventTypes.PROGRESS,
                spec_id=self.config.spec_id,
                data={"message": message},
            )
            await self.reporter.report(event)
