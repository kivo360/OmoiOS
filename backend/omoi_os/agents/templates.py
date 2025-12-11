"""Agent Templates for OmoiOS.

Provides pre-configured agent types with phase-appropriate tools, prompts, and capabilities.
Each template defines what tools an agent has access to and how it should behave.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentType(str, Enum):
    """Agent type identifiers."""
    
    PLANNER = "planner"           # Read-only analysis, creates tasks
    IMPLEMENTER = "implementer"   # Full execution, writes code
    VALIDATOR = "validator"       # Reviews work, runs tests
    DIAGNOSTICIAN = "diagnostician"  # Analyzes stuck workflows
    COORDINATOR = "coordinator"   # Orchestrates other agents


@dataclass
class ToolSet:
    """Collection of tools for an agent."""
    
    # OpenHands SDK tools (built-in)
    terminal: bool = True
    file_editor: bool = True
    grep: bool = True
    glob: bool = True
    task_tracker: bool = False  # For planning mode
    
    # MCP tools (by category)
    mcp_tickets: bool = True       # Create, update, resolve tickets
    mcp_tasks: bool = True         # Create, update tasks
    mcp_collaboration: bool = True # Send messages, request handoffs
    mcp_history: bool = True       # Get trajectories, phase history
    mcp_discovery: bool = True     # Record discoveries, branch workflows
    
    def get_sdk_tools(self) -> List[str]:
        """Get list of SDK tool names to enable."""
        tools = []
        if self.terminal:
            tools.append("terminal")
        if self.file_editor:
            tools.append("file_editor")
        if self.grep:
            tools.append("grep")
        if self.glob:
            tools.append("glob")
        if self.task_tracker:
            tools.append("task_tracker")
        return tools
    
    def get_mcp_categories(self) -> List[str]:
        """Get list of MCP tool categories to enable."""
        categories = []
        if self.mcp_tickets:
            categories.append("tickets")
        if self.mcp_tasks:
            categories.append("tasks")
        if self.mcp_collaboration:
            categories.append("collaboration")
        if self.mcp_history:
            categories.append("history")
        if self.mcp_discovery:
            categories.append("discovery")
        return categories


@dataclass
class AgentTemplate:
    """Template for creating agents with specific capabilities."""
    
    agent_type: AgentType
    name: str
    description: str
    
    # Tool configuration
    tools: ToolSet = field(default_factory=ToolSet)
    
    # Prompt configuration
    system_prompt_prefix: str = ""  # Added before phase prompt
    system_prompt_suffix: str = ""  # Added after phase prompt
    
    # Behavior configuration
    read_only: bool = False          # If True, can't modify files
    max_iterations: int = 50         # Max agent loop iterations
    require_approval: bool = False   # Require human approval for actions
    
    # Phase restrictions (None = all phases allowed)
    allowed_phases: Optional[List[str]] = None
    
    # Additional context to inject
    context_injections: Dict[str, Any] = field(default_factory=dict)
    
    def build_system_prompt(self, phase_prompt: Optional[str] = None) -> str:
        """Build complete system prompt with template + phase instructions."""
        parts = []
        
        if self.system_prompt_prefix:
            parts.append(self.system_prompt_prefix)
        
        if phase_prompt:
            parts.append(phase_prompt)
        
        if self.system_prompt_suffix:
            parts.append(self.system_prompt_suffix)
        
        return "\n\n---\n\n".join(parts) if parts else ""


# =============================================================================
# Pre-defined Agent Templates
# =============================================================================

PLANNER_TEMPLATE = AgentTemplate(
    agent_type=AgentType.PLANNER,
    name="Planner Agent",
    description="Analyzes requirements and creates implementation tasks",
    tools=ToolSet(
        terminal=True,
        file_editor=False,  # Read-only
        grep=True,
        glob=True,
        task_tracker=True,  # For tracking planning progress
        mcp_tickets=True,
        mcp_tasks=True,
        mcp_collaboration=True,
        mcp_history=True,
        mcp_discovery=True,
    ),
    system_prompt_prefix="""YOU ARE A PLANNING AGENT

Your role is to ANALYZE and CREATE TASKS, not implement them.

CAPABILITIES:
- Read and analyze code, documentation, and requirements
- Create tickets and tasks for implementation work
- Send messages to coordinate with other agents
- Record discoveries when you find issues or opportunities

RESTRICTIONS:
- You CANNOT modify files (read-only access)
- You CANNOT run code that modifies state
- You must delegate implementation to Implementer agents

WORKFLOW:
1. Analyze the task/ticket requirements
2. Break down into specific, actionable sub-tasks
3. Create tasks for each component (use mcp__create_task)
4. Document dependencies between tasks
5. Mark your planning task as complete
""",
    read_only=True,
    allowed_phases=["PHASE_REQUIREMENTS", "PHASE_DESIGN"],
)


IMPLEMENTER_TEMPLATE = AgentTemplate(
    agent_type=AgentType.IMPLEMENTER,
    name="Implementer Agent",
    description="Writes code and implements features",
    tools=ToolSet(
        terminal=True,
        file_editor=True,
        grep=True,
        glob=True,
        task_tracker=False,
        mcp_tickets=True,
        mcp_tasks=True,
        mcp_collaboration=True,
        mcp_history=True,
        mcp_discovery=True,
    ),
    system_prompt_prefix="""YOU ARE AN IMPLEMENTATION AGENT

Your role is to WRITE CODE and IMPLEMENT features.

CAPABILITIES:
- Full file editing and creation
- Terminal access for running tests and commands
- Create sub-tasks when you discover new work needed
- Record discoveries (bugs, optimizations, issues)

WORKFLOW:
1. Read task requirements thoroughly
2. Design the implementation approach
3. Write the code
4. Write tests (minimum 3 test cases)
5. Run tests and ensure they pass
6. If bugs found: record_discovery_and_branch → continue working
7. Update task status and create validation task
""",
    system_prompt_suffix="""IMPORTANT RULES:
- Always run tests before marking task complete
- Use discovery service for spawning related work (don't stop your work)
- Include ticket ID in all spawned task descriptions
- Follow the phase's done_definitions exactly
""",
    read_only=False,
    allowed_phases=["PHASE_IMPLEMENTATION"],
)


VALIDATOR_TEMPLATE = AgentTemplate(
    agent_type=AgentType.VALIDATOR,
    name="Validator Agent",
    description="Reviews code and runs validation tests",
    tools=ToolSet(
        terminal=True,
        file_editor=False,  # Read-only for validation
        grep=True,
        glob=True,
        task_tracker=False,
        mcp_tickets=True,
        mcp_tasks=True,
        mcp_collaboration=True,
        mcp_history=True,
        mcp_discovery=True,
    ),
    system_prompt_prefix="""YOU ARE A VALIDATION AGENT

Your role is to VERIFY and TEST implementations.

CAPABILITIES:
- Run tests and integration checks
- Review code for quality and correctness
- Spawn fix tasks when issues found (loops back to implementation)
- Approve implementations that pass all checks

WORKFLOW:
1. Review the implementation code
2. Run all tests (unit, integration)
3. Validate against requirements
4. IF PASS: Approve and create deployment task
5. IF FAIL: Spawn fix task via discovery_and_branch (feedback loop)
""",
    system_prompt_suffix="""CRITICAL RULES:
- NEVER approve buggy code - spawn fix tasks instead
- Feedback loop: validate → fix → re-validate until passing
- Use priority_boost=True for critical bugs
- Security issues get CRITICAL priority
""",
    read_only=True,
    require_approval=False,
    allowed_phases=["PHASE_TESTING"],
)


DIAGNOSTICIAN_TEMPLATE = AgentTemplate(
    agent_type=AgentType.DIAGNOSTICIAN,
    name="Diagnostician Agent",
    description="Analyzes stuck workflows and spawns recovery tasks",
    tools=ToolSet(
        terminal=True,
        file_editor=False,
        grep=True,
        glob=True,
        task_tracker=False,
        mcp_tickets=True,
        mcp_tasks=True,
        mcp_collaboration=True,
        mcp_history=True,
        mcp_discovery=True,
    ),
    system_prompt_prefix="""YOU ARE A DIAGNOSTIC AGENT

Your role is to ANALYZE stuck workflows and SPAWN recovery tasks.

CAPABILITIES:
- Analyze agent trajectories and task histories
- Identify blockers and root causes
- Spawn targeted recovery tasks
- Coordinate with other agents to resolve issues

DIAGNOSTIC PROCESS:
1. Analyze the stuck workflow's history
2. Review agent trajectories for anomalies
3. Identify the root cause (blocker, bug, unclear requirements, etc.)
4. Spawn appropriate recovery task(s) via discovery service
5. Notify relevant agents about the diagnosis
""",
    read_only=True,
    allowed_phases=None,  # Can operate in any phase
)


COORDINATOR_TEMPLATE = AgentTemplate(
    agent_type=AgentType.COORDINATOR,
    name="Coordinator Agent",
    description="Orchestrates workflows and manages agent assignments",
    tools=ToolSet(
        terminal=False,
        file_editor=False,
        grep=False,
        glob=False,
        task_tracker=True,
        mcp_tickets=True,
        mcp_tasks=True,
        mcp_collaboration=True,
        mcp_history=True,
        mcp_discovery=True,
    ),
    system_prompt_prefix="""YOU ARE A COORDINATOR AGENT

Your role is to ORCHESTRATE workflows and COORDINATE agents.

CAPABILITIES:
- Create and manage tickets/tasks
- Assign work to specialist agents
- Monitor workflow progress
- Resolve coordination conflicts
- Make decisions about resource allocation

WORKFLOW:
1. Receive high-level work requests
2. Break into tickets and tasks
3. Assign to appropriate agent types
4. Monitor progress via task/ticket status
5. Intervene when agents are stuck
6. Ensure workflow completion
""",
    read_only=True,
    allowed_phases=None,  # Can operate at any level
)


# =============================================================================
# Template Registry
# =============================================================================

AGENT_TEMPLATES: Dict[AgentType, AgentTemplate] = {
    AgentType.PLANNER: PLANNER_TEMPLATE,
    AgentType.IMPLEMENTER: IMPLEMENTER_TEMPLATE,
    AgentType.VALIDATOR: VALIDATOR_TEMPLATE,
    AgentType.DIAGNOSTICIAN: DIAGNOSTICIAN_TEMPLATE,
    AgentType.COORDINATOR: COORDINATOR_TEMPLATE,
}


def get_template(agent_type: AgentType | str) -> AgentTemplate:
    """Get agent template by type.
    
    Args:
        agent_type: AgentType enum or string identifier
        
    Returns:
        AgentTemplate for the specified type
        
    Raises:
        ValueError: If agent type not found
    """
    if isinstance(agent_type, str):
        agent_type = AgentType(agent_type)
    
    if agent_type not in AGENT_TEMPLATES:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    return AGENT_TEMPLATES[agent_type]


def get_template_for_phase(phase_id: str) -> AgentTemplate:
    """Get the default agent template for a phase.
    
    Args:
        phase_id: Phase identifier (e.g., PHASE_IMPLEMENTATION)
        
    Returns:
        Appropriate AgentTemplate for the phase
    """
    phase_to_template = {
        "PHASE_REQUIREMENTS": AgentType.PLANNER,
        "PHASE_DESIGN": AgentType.PLANNER,
        "PHASE_IMPLEMENTATION": AgentType.IMPLEMENTER,
        "PHASE_TESTING": AgentType.VALIDATOR,
        "PHASE_DEPLOYMENT": AgentType.IMPLEMENTER,
        "PHASE_DONE": AgentType.COORDINATOR,
        "PHASE_BLOCKED": AgentType.DIAGNOSTICIAN,
    }
    
    agent_type = phase_to_template.get(phase_id, AgentType.IMPLEMENTER)
    return get_template(agent_type)


def list_templates() -> List[AgentTemplate]:
    """List all available agent templates."""
    return list(AGENT_TEMPLATES.values())

