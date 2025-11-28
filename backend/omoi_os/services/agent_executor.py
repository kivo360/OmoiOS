"""Agent executor service wrapping OpenHands SDK for task execution."""

import asyncio
from typing import Dict, Any, Optional

# Ensure an event loop exists for libraries that expect one at import time
try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from openhands.sdk import Agent, Conversation, LLM
from openhands.sdk.context.condenser import LLMSummarizingCondenser
from openhands.sdk.tool import Tool
from openhands.tools.preset.default import get_default_tools, register_default_tools
from openhands.tools.preset.planning import (
    get_planning_tools,
    format_plan_structure,
    register_planning_tools,
)

from omoi_os.config import load_llm_settings
from omoi_os.models.phase import PhaseModel
from omoi_os.services.database import DatabaseService

# Import OmoiOS native tools
from omoi_os.tools import register_omoi_tools
from omoi_os.tools.task_tools import initialize_task_tool_services
from omoi_os.tools.collaboration_tools import initialize_collaboration_tool_services
from omoi_os.tools.planning_tools import initialize_planning_tool_services

# Import tool classes for getting their names
from omoi_os.tools.task_tools import (
    CreateTaskTool,
    UpdateTaskStatusTool,
    GetTaskTool,
    GetTaskDiscoveriesTool,
    GetWorkflowGraphTool,
    ListPendingTasksTool,
)
from omoi_os.tools.collaboration_tools import (
    BroadcastMessageTool,
    SendMessageTool,
    GetMessagesTool,
    RequestHandoffTool,
    MarkMessageReadTool,
)
from omoi_os.tools.planning_tools import (
    GetTicketDetailsTool,
    GetPhaseContextTool,
    SearchSimilarTasksTool,
    GetLearnedPatternsTool,
    GetDependencyGraphTool,
    AnalyzeBlockersTool,
    GetProjectStructureTool,
    SearchCodebaseTool,
    AnalyzeRequirementsTool,
)

# Flag to track if tools are registered
_tools_registered = False


class AgentExecutor:
    """Wraps OpenHands Agent for task execution.

    Supports two modes:
    - **Planning Mode**: Read-only agent that analyzes tasks and creates plans
    - **Execution Mode**: Full agent that implements plans with editing capabilities

    Both modes include OmoiOS tools for task management and collaboration.
    """

    def __init__(
        self,
        phase_id: str,
        workspace_dir: str,
        db: Optional[DatabaseService] = None,
        planning_mode: bool = False,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ):
        """
        Initialize agent executor.

        Args:
            phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")
            workspace_dir: Directory path for workspace operations
            db: Optional database service for loading phase context
            planning_mode: If True, creates a read-only planning agent.
                          If False (default), creates a full execution agent.
            project_id: Optional project ID for project-scoped workspace isolation
            task_id: Optional task ID for task-specific workspace subdirectory
        """
        self.phase_id = phase_id
        self.workspace_dir = workspace_dir
        self.db = db
        self.planning_mode = planning_mode
        self.project_id = project_id
        self.task_id = task_id
        self._openhands_workspace = None

        # Load phase context for instructions
        phase_context = self._load_phase_context()
        phase_instructions = self._build_phase_instructions(phase_context)

        llm_settings = load_llm_settings()
        if not llm_settings.api_key:
            raise ValueError("LLM_API_KEY (or equivalent) must be configured")

        # Create OpenHands LLM and Agent
        self.llm = LLM(
            model=llm_settings.model,
            api_key=llm_settings.api_key,
            base_url=llm_settings.base_url,
        )

        # Initialize and register OmoiOS native tools (once per process)
        global _tools_registered
        if not _tools_registered:
            self._initialize_native_tools()
            _tools_registered = True

        # Build system prompt kwargs
        system_prompt_kwargs = {"cli_mode": True}
        if phase_instructions:
            # Add phase instructions to system prompt
            system_prompt_kwargs["phase_instructions"] = phase_instructions

        # Create planning or execution agent based on mode
        if planning_mode:
            # Planning agent: read-only + OmoiOS tools
            register_planning_tools()
            base_tools = get_planning_tools()
            omoi_tools = self._get_planning_tool_specs()

            self.agent = Agent(
                llm=self.llm,
                tools=base_tools + omoi_tools,
                system_prompt_filename="system_prompt_planning.j2",
                system_prompt_kwargs={
                    "plan_structure": format_plan_structure(),
                    **(
                        {"phase_instructions": phase_instructions}
                        if phase_instructions
                        else {}
                    ),
                },
                condenser=LLMSummarizingCondenser(
                    llm=self.llm.model_copy(update={"usage_id": "planning_condenser"}),
                    max_size=100,
                    keep_first=6,
                ),
            )
        else:
            # Execution agent: full editing capabilities + OmoiOS tools
            register_default_tools(enable_browser=False)
            base_tools = get_default_tools(enable_browser=False)
            omoi_tools = self._get_execution_tool_specs()

            self.agent = Agent(
                llm=self.llm,
                tools=base_tools + omoi_tools,
                system_prompt_kwargs=system_prompt_kwargs,
                condenser=LLMSummarizingCondenser(
                    llm=self.llm.model_copy(update={"usage_id": "condenser"}),
                    max_size=80,
                    keep_first=4,
                ),
            )
        self.phase_instructions = phase_instructions

    @classmethod
    def create_planning_executor(
        cls,
        phase_id: str,
        workspace_dir: str,
        db: Optional[DatabaseService] = None,
    ) -> "AgentExecutor":
        """Create a planning-mode executor for task breakdown.

        The planning agent can:
        - Read files and analyze code
        - Create tasks via OmoiOS tools (omoi__create_task)
        - Track discoveries (omoi__create_task with discovery_type)
        - Write PLAN.md files

        But cannot:
        - Edit existing files
        - Execute destructive commands

        Usage:
            executor = AgentExecutor.create_planning_executor(
                phase_id="PHASE_REQUIREMENTS",
                workspace_dir="/path/to/project",
            )
            result = executor.execute_task(
                "Analyze this codebase and create implementation tasks for adding OAuth"
            )
        """
        return cls(
            phase_id=phase_id,
            workspace_dir=workspace_dir,
            db=db,
            planning_mode=True,
        )

    @classmethod
    def create_execution_executor(
        cls,
        phase_id: str,
        workspace_dir: str,
        db: Optional[DatabaseService] = None,
    ) -> "AgentExecutor":
        """Create an execution-mode executor for implementing tasks.

        The execution agent can:
        - Read and edit files
        - Execute terminal commands
        - Update task status via OmoiOS tools (omoi__update_task_status)
        - Create subtasks as discoveries arise

        Usage:
            executor = AgentExecutor.create_execution_executor(
                phase_id="PHASE_IMPLEMENTATION",
                workspace_dir="/path/to/project",
            )
            result = executor.execute_task(
                "Implement the OAuth login feature as specified in PLAN.md"
            )
        """
        return cls(
            phase_id=phase_id,
            workspace_dir=workspace_dir,
            db=db,
            planning_mode=False,
        )

    @classmethod
    def create_for_project(
        cls,
        project_id: str,
        phase_id: str,
        task_id: Optional[str] = None,
        db: Optional[DatabaseService] = None,
        planning_mode: bool = False,
    ) -> "AgentExecutor":
        """Create an executor with project-scoped workspace isolation.

        Uses OpenHandsWorkspaceFactory to create isolated workspaces:
        - local mode: Direct filesystem at /workspaces/{project_id}/
        - docker mode: Isolated Docker container with mounted workspace
        - remote mode: Connect to external OpenHands agent server

        Args:
            project_id: Project identifier for workspace isolation
            phase_id: Phase identifier (e.g., "PHASE_IMPLEMENTATION")
            task_id: Optional task ID for task-specific subdirectory
            db: Optional database service
            planning_mode: If True, creates read-only planning agent

        Returns:
            AgentExecutor configured for project workspace

        Example:
            executor = AgentExecutor.create_for_project(
                project_id="proj-123",
                phase_id="PHASE_REQUIREMENTS",
                planning_mode=True,
            )
        """
        from omoi_os.services.workspace_manager import get_workspace_factory

        factory = get_workspace_factory()
        workspace_path = factory.get_project_workspace_path(project_id)

        # Create workspace directory if needed
        if task_id:
            workspace_path = workspace_path / task_id
        workspace_path.mkdir(parents=True, exist_ok=True)

        return cls(
            phase_id=phase_id,
            workspace_dir=str(workspace_path),
            db=db,
            planning_mode=planning_mode,
            project_id=project_id,
            task_id=task_id,
        )

    @property
    def openhands_workspace(self):
        """Lazily create OpenHands workspace based on configuration.

        Returns LocalWorkspace, DockerWorkspace, or RemoteWorkspace
        depending on WORKSPACE_MODE setting.
        """
        if self._openhands_workspace is None:
            if self.project_id:
                from omoi_os.services.workspace_manager import get_workspace_factory

                factory = get_workspace_factory()
                self._openhands_workspace = factory.create_for_project(
                    project_id=self.project_id,
                    task_id=self.task_id,
                )
            else:
                # Fallback to LocalWorkspace for non-project executors
                from openhands.sdk.workspace import LocalWorkspace

                self._openhands_workspace = LocalWorkspace(
                    working_dir=self.workspace_dir
                )
        return self._openhands_workspace

    def _initialize_native_tools(self) -> None:
        """Initialize OmoiOS native tools with required services."""
        from omoi_os.services.task_queue import TaskQueueService
        from omoi_os.services.collaboration import CollaborationService
        from omoi_os.services.discovery import DiscoveryService
        from omoi_os.services.event_bus import EventBusService

        # Get or create database instance
        if self.db is None:
            from omoi_os.config import get_app_settings

            app_settings = get_app_settings()
            self.db = DatabaseService(connection_string=app_settings.database.url)

        # Initialize task queue and related services
        task_queue = TaskQueueService(self.db)

        # Initialize discovery service for tracking task spawning
        try:
            discovery_service = DiscoveryService(self.db)
        except Exception:
            discovery_service = None

        # Initialize event bus for real-time updates
        try:
            event_bus = EventBusService()
        except Exception:
            event_bus = None

        # Initialize tool services
        initialize_task_tool_services(
            db=self.db,
            task_queue=task_queue,
            discovery_service=discovery_service,
            event_bus=event_bus,
        )

        # Initialize collaboration services
        try:
            collab_service = CollaborationService(self.db)
            initialize_collaboration_tool_services(collab_service)
        except Exception:
            # Collaboration is optional
            pass

        # Initialize planning tools with context services
        try:
            from omoi_os.services.context_service import ContextService
            from omoi_os.services.dependency_graph import DependencyGraphService
            from omoi_os.services.embedding import EmbeddingService
            from omoi_os.services.memory import MemoryService

            context_service = ContextService(self.db)
            dependency_service = DependencyGraphService(self.db)

            # Memory service requires embedding service (optional)
            memory_service = None
            try:
                embedding_service = EmbeddingService()
                memory_service = MemoryService(embedding_service, event_bus)
            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Memory service not available (search_similar_tasks, get_learned_patterns will be disabled). "
                    f"To enable: set EMBEDDING_OPENAI_API_KEY or install fastembed. Error: {e}"
                )

            initialize_planning_tool_services(
                db=self.db,
                memory_service=memory_service,
                context_service=context_service,
                dependency_service=dependency_service,
                discovery_service=discovery_service,
                event_bus=event_bus,
            )
        except Exception:
            # Planning services are optional; fallbacks exist in tool implementations
            pass

        # Register all OmoiOS tools with OpenHands
        register_omoi_tools()

    def _get_planning_tool_specs(self) -> list[Tool]:
        """Get Tool specs for planning mode (task creation + planning tools)."""
        return [
            # Task tools (planning can create tasks)
            Tool(name=CreateTaskTool.name),
            Tool(name=GetTaskTool.name),
            Tool(name=GetTaskDiscoveriesTool.name),
            Tool(name=GetWorkflowGraphTool.name),
            Tool(name=ListPendingTasksTool.name),
            # Collaboration tools (can broadcast discoveries)
            Tool(name=BroadcastMessageTool.name),
            Tool(name=SendMessageTool.name),
            Tool(name=GetMessagesTool.name),
            # Planning-specific tools
            Tool(name=GetTicketDetailsTool.name),
            Tool(name=GetPhaseContextTool.name),
            Tool(name=SearchSimilarTasksTool.name),
            Tool(name=GetLearnedPatternsTool.name),
            Tool(name=GetDependencyGraphTool.name),
            Tool(name=AnalyzeBlockersTool.name),
            Tool(name=GetProjectStructureTool.name),
            Tool(name=SearchCodebaseTool.name),
            Tool(name=AnalyzeRequirementsTool.name),
        ]

    def _get_execution_tool_specs(self) -> list[Tool]:
        """Get Tool specs for execution mode (task management + collaboration)."""
        return [
            # Task tools (full CRUD)
            Tool(name=CreateTaskTool.name),
            Tool(name=UpdateTaskStatusTool.name),
            Tool(name=GetTaskTool.name),
            Tool(name=GetTaskDiscoveriesTool.name),
            Tool(name=GetWorkflowGraphTool.name),
            Tool(name=ListPendingTasksTool.name),
            # Collaboration tools
            Tool(name=BroadcastMessageTool.name),
            Tool(name=SendMessageTool.name),
            Tool(name=GetMessagesTool.name),
            Tool(name=RequestHandoffTool.name),
            Tool(name=MarkMessageReadTool.name),
        ]

    def prepare_conversation(self, task_id: str | None = None) -> Dict[str, str]:
        """
        Prepare conversation with persistence and return metadata.

        This allows storing conversation_id and persistence_dir in the database
        before execution starts, enabling Guardian to send interventions during execution.

        Args:
            task_id: Optional task ID to use as conversation_id for persistence

        Returns:
            Dictionary with:
            - conversation_id: OpenHands conversation ID
            - persistence_dir: Conversation persistence directory
        """
        import os

        # Set up persistence directory for conversation resumption
        persistence_dir = os.path.join(self.workspace_dir, "conversation")
        os.makedirs(persistence_dir, exist_ok=True)

        # Use task_id as conversation_id if provided, otherwise let OpenHands generate one
        conversation_id = str(task_id) if task_id else None

        # Create conversation with persistence enabled
        conversation = Conversation(
            agent=self.agent,
            workspace=self.workspace_dir,
            persistence_dir=persistence_dir,
            conversation_id=conversation_id,
        )

        return {
            "conversation_id": conversation.state.id,
            "persistence_dir": persistence_dir,
            "_conversation": conversation,  # Internal: store for execute_task
        }

    def execute_task(
        self,
        task_description: str,
        task_id: str | None = None,
        conversation_metadata: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """
        Execute a task using OpenHands agent.

        Args:
            task_description: Description of the task to execute
            task_id: Optional task ID to use as conversation_id for persistence
            conversation_metadata: Optional pre-prepared conversation metadata from prepare_conversation()

        Returns:
            Dictionary with execution results:
            - status: Execution status
            - event_count: Number of events generated
            - cost: LLM API cost
            - conversation_id: OpenHands conversation ID
            - persistence_dir: Conversation persistence directory
        """
        import os

        # Use pre-prepared conversation if provided, otherwise create new one
        if conversation_metadata and "_conversation" in conversation_metadata:
            conversation = conversation_metadata["_conversation"]
            conversation_id = conversation_metadata["conversation_id"]
            persistence_dir = conversation_metadata["persistence_dir"]
        else:
            # Set up persistence directory for conversation resumption
            persistence_dir = os.path.join(self.workspace_dir, "conversation")
            os.makedirs(persistence_dir, exist_ok=True)

            # Use task_id as conversation_id if provided, otherwise let OpenHands generate one
            conversation_id = str(task_id) if task_id else None

            # Create conversation with persistence enabled
            conversation = Conversation(
                agent=self.agent,
                workspace=self.workspace_dir,
                persistence_dir=persistence_dir,
                conversation_id=conversation_id,
            )

        try:
            # Build task message with phase instructions if not already in system prompt
            # (If agent_context was used, instructions are already in system prompt)
            task_message = task_description
            if self.phase_instructions and not hasattr(
                self.agent, "_phase_instructions_in_system"
            ):
                # Prepend phase instructions to task message if not in system prompt
                task_message = f"{self.phase_instructions}\n\n---\n\n{task_description}"

            # Send task message
            conversation.send_message(task_message)

            # Run agent
            conversation.run()

            # Extract result with conversation metadata
            result = {
                "status": conversation.state.execution_status,
                "event_count": len(conversation.state.events),
                "cost": conversation.conversation_stats.get_combined_metrics().accumulated_cost,
                "conversation_id": conversation.state.id,
                "persistence_dir": persistence_dir,
            }

            return result
        finally:
            # Always close conversation, even on error
            conversation.close()

    def _load_phase_context(self) -> Optional[Dict[str, Any]]:
        """Load phase context from database.

        Returns:
            Phase context dictionary or None if phase not found
        """
        if not self.db or not self.phase_id:
            return None

        try:
            with self.db.get_session() as session:
                phase = session.query(PhaseModel).filter_by(id=self.phase_id).first()
                if phase:
                    return phase.to_dict()
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to load phase context for {self.phase_id}: {e}")

        return None

    def _build_phase_instructions(
        self, phase_context: Optional[Dict[str, Any]]
    ) -> Optional[str]:
        """Build phase instructions string from phase context.

        Args:
            phase_context: Phase context dictionary from database

        Returns:
            Formatted phase instructions string or None
        """
        if not phase_context:
            return None

        instructions_parts = []

        # Add phase name and description
        phase_name = phase_context.get("name", self.phase_id)
        phase_desc = phase_context.get("description")
        if phase_desc:
            instructions_parts.append(f"# Phase: {phase_name}\n{phase_desc}\n")
        else:
            instructions_parts.append(f"# Phase: {phase_name}\n")

        # Add phase prompt (main instructions)
        phase_prompt = phase_context.get("phase_prompt")
        if phase_prompt:
            instructions_parts.append(f"## Phase Instructions\n{phase_prompt}\n")

        # Add done definitions (completion criteria)
        done_definitions = phase_context.get("done_definitions")
        if done_definitions:
            instructions_parts.append("## Completion Criteria\n")
            instructions_parts.append(
                "You must complete ALL of the following before marking this task as done:\n"
            )
            for i, criterion in enumerate(done_definitions, 1):
                instructions_parts.append(f"{i}. {criterion}\n")
            instructions_parts.append(
                "\n⚠️ IMPORTANT: Do not claim the task is done until ALL criteria above are met.\n"
            )

        # Add expected outputs
        expected_outputs = phase_context.get("expected_outputs")
        if expected_outputs:
            instructions_parts.append("## Expected Outputs\n")
            for output in expected_outputs:
                output_type = output.get("type", "unknown")
                pattern = output.get("pattern") or output.get("name", "N/A")
                required = output.get("required", False)
                required_str = " (REQUIRED)" if required else " (optional)"
                instructions_parts.append(f"- {output_type}: {pattern}{required_str}\n")
            instructions_parts.append("\n")

        if not instructions_parts:
            return None

        return "\n".join(instructions_parts).strip()
