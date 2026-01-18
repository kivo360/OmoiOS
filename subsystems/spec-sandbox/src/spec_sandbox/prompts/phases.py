"""Phase-specific prompts for spec-driven development.

Each phase has a specific prompt that guides the Claude Agent to produce
structured output for that phase of the development workflow.

Phases:
- EXPLORE: Analyze the codebase to understand architecture, patterns, and key files
- REQUIREMENTS: Generate structured requirements from the spec description
- DESIGN: Create architecture design based on requirements
- TASKS: Break down design into discrete, actionable tasks
- SYNC: Synchronize generated artifacts with the project
"""

from spec_sandbox.schemas.spec import SpecPhase

# =============================================================================
# EXPLORE PHASE - Codebase Analysis
# =============================================================================

EXPLORE_PROMPT = """You are analyzing a codebase to understand its structure and patterns.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Your Task
Explore the codebase to understand:
1. **Project Structure**: Directory layout, main entry points, configuration files
2. **Architecture Patterns**: How code is organized (MVC, microservices, monolith, etc.)
3. **Key Dependencies**: Major libraries and frameworks used
4. **Relevant Files**: Files most relevant to the spec requirements
5. **Existing Patterns**: Coding patterns, naming conventions, test structure

## Instructions
- Use the Read, Glob, and Grep tools to explore the codebase
- Focus on understanding patterns that will inform implementation
- Identify files that will need modification for this spec
- Note any existing similar functionality that can be reused

## Required Output Format
When complete, you MUST write a JSON file with this structure:
{{
    "codebase_summary": "Brief overview of the codebase architecture",
    "project_type": "Type of project (web app, library, service, etc.)",
    "tech_stack": ["list", "of", "technologies"],
    "key_files": [
        {{"path": "relative/path/to/file", "purpose": "Why this file matters"}}
    ],
    "relevant_patterns": [
        {{"pattern": "Pattern name", "description": "How it's used", "files": ["example/files"]}}
    ],
    "entry_points": ["main entry point files"],
    "test_structure": "How tests are organized",
    "notes": "Any important observations for implementation"
}}

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# REQUIREMENTS PHASE - Structured Requirements Generation
# =============================================================================

REQUIREMENTS_PROMPT = """You are generating structured requirements from a spec description.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Codebase Context (from Explore phase)
{explore_context}

## Your Task
Generate structured requirements using the EARS (Easy Approach to Requirements Syntax) format:
- WHEN [trigger] THE SYSTEM SHALL [action]
- IF [condition] THEN THE SYSTEM SHALL [action]
- THE SYSTEM SHALL [action]

## Instructions
- Break down the spec into discrete, testable requirements
- Each requirement should be independently verifiable
- Include both functional and non-functional requirements
- Reference existing patterns from the codebase where applicable
- Consider edge cases and error handling

## Required Output Format
When complete, you MUST write a JSON file with this structure:
{{
    "requirements": [
        {{
            "id": "REQ-001",
            "type": "functional|non_functional|constraint",
            "category": "Category (e.g., API, UI, Data, Security)",
            "text": "EARS-format requirement text",
            "priority": "must|should|could|wont",
            "acceptance_criteria": ["Testable criterion 1", "Testable criterion 2"],
            "dependencies": ["REQ-XXX"]
        }}
    ],
    "assumptions": ["List of assumptions made"],
    "out_of_scope": ["Items explicitly not covered"],
    "open_questions": ["Questions needing clarification"]
}}

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# DESIGN PHASE - Architecture Design
# =============================================================================

DESIGN_PROMPT = """You are creating an architecture design based on requirements.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Codebase Context (from Explore phase)
{explore_context}

## Requirements (from Requirements phase)
{requirements_context}

## Your Task
Design the architecture to satisfy all requirements while:
- Following existing codebase patterns
- Minimizing changes to existing code
- Maintaining separation of concerns
- Ensuring testability

## Instructions
- Define components and their responsibilities
- Specify interfaces between components
- Design data models if needed
- Plan error handling strategy
- Consider performance implications

## Required Output Format
When complete, you MUST write a JSON file with this structure:
{{
    "architecture_overview": "High-level description of the design",
    "components": [
        {{
            "name": "ComponentName",
            "type": "service|repository|controller|model|util",
            "responsibility": "What this component does",
            "file_path": "Where it should live",
            "interfaces": [
                {{"method": "method_name", "inputs": {{}}, "outputs": {{}}, "description": ""}}
            ],
            "dependencies": ["Other components it depends on"]
        }}
    ],
    "data_models": [
        {{
            "name": "ModelName",
            "fields": {{"field_name": "type"}},
            "purpose": "What this model represents"
        }}
    ],
    "api_endpoints": [
        {{
            "method": "GET|POST|PUT|DELETE",
            "path": "/api/path",
            "purpose": "What it does",
            "request_schema": {{}},
            "response_schema": {{}}
        }}
    ],
    "integration_points": ["How this integrates with existing code"],
    "error_handling": "Strategy for error handling",
    "testing_strategy": "How this should be tested",
    "migration_plan": "If data migration is needed"
}}

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# TASKS PHASE - Ticket and Task Breakdown
# =============================================================================

TASKS_PROMPT = """You are breaking down a design into tickets (grouped work items) and tasks (discrete units of work).

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Codebase Context (from Explore phase)
{explore_context}

## Requirements (from Requirements phase)
{requirements_context}

## Design (from Design phase)
{design_context}

## Your Task
Create tickets that represent logical groupings of work, then break each ticket into small, discrete tasks that:
- Can each be completed in 1-4 hours
- Are independently verifiable
- Have clear acceptance criteria
- Follow a logical dependency order

## Instructions
1. **Create Tickets** - Logical groupings of related work (e.g., "User Authentication", "Data Export Feature")
   - Each ticket should represent a coherent piece of functionality
   - Tickets are what appear on the project board
   - Assign priority: CRITICAL, HIGH, MEDIUM, LOW

2. **Break Down into Tasks** - Each ticket contains multiple tasks
   - Tasks are the actual units of work (1-4 hours each)
   - Order tasks by dependency (foundations first)
   - Include tasks for tests and documentation
   - Link each task to its parent ticket

3. **Define Dependencies** - Both between tickets and between tasks
   - Ticket-level dependencies for high-level ordering
   - Task-level dependencies for execution sequence

## Required Output Format
When complete, you MUST write a JSON file with this structure:
{{
    "tickets": [
        {{
            "id": "TKT-001",
            "title": "Ticket title - logical work grouping",
            "description": "Full description of what this ticket covers and why",
            "priority": "HIGH|MEDIUM|LOW|CRITICAL",
            "requirements": ["REQ-001", "REQ-002"],
            "tasks": ["TSK-001", "TSK-002", "TSK-003"],
            "dependencies": ["TKT-XXX"]
        }}
    ],
    "tasks": [
        {{
            "id": "TSK-001",
            "title": "Short, descriptive title",
            "description": "Detailed description of what to implement",
            "parent_ticket": "TKT-001",
            "type": "implementation|test|documentation|configuration",
            "priority": "HIGH|MEDIUM|LOW|CRITICAL",
            "files_to_modify": ["path/to/file1.py", "path/to/file2.py"],
            "files_to_create": ["path/to/new_file.py"],
            "dependencies": {{"depends_on": ["TSK-XXX"]}},
            "requirements_addressed": ["REQ-001", "REQ-002"],
            "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            "estimated_hours": 2
        }}
    ],
    "total_estimated_hours": 20,
    "critical_path": ["TSK-001", "TSK-003", "TSK-005"]
}}

Use the Write tool to create this JSON file at the path specified in your instructions.
"""

# =============================================================================
# SYNC PHASE - Artifact Synchronization
# =============================================================================

SYNC_PROMPT = """You are synchronizing generated artifacts with the project.

## Spec Context
Title: {spec_title}
Description: {spec_description}

## Generated Artifacts
- Requirements: {requirements_context}
- Design: {design_context}
- Tasks: {tasks_context}

## Your Task
Verify and finalize all generated artifacts:
1. Validate consistency between requirements, design, and tasks
2. Check that all requirements are covered by tasks
3. Verify file paths are correct for the codebase
4. Check for circular dependencies in task graph
5. Generate traceability statistics
6. Generate a final summary

## Instructions
- Cross-reference requirements to tasks using requirements_addressed field
- Verify design components map to tasks
- Check for any gaps or inconsistencies
- Detect circular dependencies using task dependency graph
- Calculate requirement coverage percentage
- Produce a final spec document with traceability stats

## Required Output Format
When complete, you MUST write a JSON file with this structure:
{{
    "validation_results": {{
        "all_requirements_covered": true,
        "all_components_have_tasks": true,
        "dependency_order_valid": true,
        "no_circular_dependencies": true,
        "issues_found": []
    }},
    "coverage_matrix": [
        {{
            "requirement_id": "REQ-001",
            "covered_by_tasks": ["TASK-001", "TASK-002"],
            "status": "fully_covered|partially_covered|not_covered"
        }}
    ],
    "traceability_stats": {{
        "requirements": {{
            "total": 10,
            "linked": 9,
            "coverage": 90.0
        }},
        "tasks": {{
            "total": 15,
            "done": 0,
            "in_progress": 0,
            "pending": 15
        }},
        "orphans": {{
            "requirements": ["REQ-XXX"]
        }}
    }},
    "spec_summary": {{
        "total_requirements": 10,
        "total_tasks": 15,
        "total_estimated_hours": 30,
        "files_to_modify": 8,
        "files_to_create": 3,
        "requirement_coverage_percent": 90.0
    }},
    "ready_for_execution": true,
    "blockers": []
}}

Use the Write tool to create this JSON file at the path specified in your instructions.
"""


def get_phase_prompt(phase: SpecPhase) -> str:
    """Get the prompt template for a specific phase.

    Args:
        phase: The spec phase to get prompt for

    Returns:
        The prompt template string with placeholders

    Raises:
        ValueError: If phase is not recognized
    """
    prompts = {
        SpecPhase.EXPLORE: EXPLORE_PROMPT,
        SpecPhase.REQUIREMENTS: REQUIREMENTS_PROMPT,
        SpecPhase.DESIGN: DESIGN_PROMPT,
        SpecPhase.TASKS: TASKS_PROMPT,
        SpecPhase.SYNC: SYNC_PROMPT,
    }

    if phase not in prompts:
        raise ValueError(f"Unknown phase: {phase}")

    return prompts[phase]
