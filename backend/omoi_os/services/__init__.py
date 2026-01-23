"""Core services for OmoiOS."""

# NOTE: AgentExecutor removed from top-level imports due to openhands.sdk compatibility issues.
# Import directly from omoi_os.services.agent_executor if needed (legacy code only).
# The new Claude sandbox workers don't use AgentExecutor.

from omoi_os.services.agent_health import AgentHealthService
from omoi_os.services.repository_service import (
    GitHubAPIError,
    RepositoryService,
    RepositoryServiceError,
)
from omoi_os.services.agent_registry import AgentRegistryService
from omoi_os.services.agent_status_manager import AgentStatusManager
from omoi_os.services.ace_engine import ACEEngine
from omoi_os.services.ace_executor import Executor
from omoi_os.services.ace_reflector import Reflector
from omoi_os.services.ace_curator import Curator
from omoi_os.services.approval import ApprovalService
from omoi_os.services.baseline_learner import BaselineLearner
from omoi_os.services.branch_workflow import BranchWorkflowService
from omoi_os.services.collaboration import CollaborationService
from omoi_os.services.composite_anomaly_scorer import CompositeAnomalyScorer
from omoi_os.services.context_service import ContextService
from omoi_os.services.coordination import CoordinationService
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.heartbeat_protocol import HeartbeatProtocolService
from omoi_os.services.message_queue import (
    RedisMessageQueue,
    InMemoryMessageQueue,
    get_message_queue,
)
from omoi_os.services.phase_gate import PhaseGateService
from omoi_os.services.phase_manager import PhaseManager, get_phase_manager
from omoi_os.services.resource_lock import ResourceLockService
from omoi_os.services.restart_orchestrator import RestartOrchestrator
from omoi_os.services.task_queue import TaskQueueService
from omoi_os.services.task_scorer import TaskScorer
from omoi_os.services.ticket_workflow import TicketWorkflowOrchestrator
from omoi_os.services.validation_agent import ValidationAgent
from omoi_os.services.llm_service import LLMService, get_llm_service
from omoi_os.services.spec_driven_settings import (
    SpecDrivenSettings,
    SpecDrivenSettingsService,
    get_spec_driven_settings_service,
)

__all__ = [
    "ACEEngine",
    "Executor",
    "Reflector",
    "Curator",
    # "AgentExecutor",  # Removed - import directly if needed (legacy)
    "AgentHealthService",
    "AgentRegistryService",
    "AgentStatusManager",
    "ApprovalService",
    "BaselineLearner",
    "BranchWorkflowService",
    "CollaborationService",
    "CompositeAnomalyScorer",
    "ContextService",
    "CoordinationService",
    "DatabaseService",
    "EventBusService",
    "HeartbeatProtocolService",
    "InMemoryMessageQueue",
    "LLMService",
    "PhaseGateService",
    "PhaseManager",
    "get_phase_manager",
    "RedisMessageQueue",
    "ResourceLockService",
    "RestartOrchestrator",
    "SystemEvent",
    "TaskQueueService",
    "TaskScorer",
    "TicketWorkflowOrchestrator",
    "ValidationAgent",
    "get_llm_service",
    "get_message_queue",
    "get_spec_driven_settings_service",
    "GitHubAPIError",
    "RepositoryService",
    "RepositoryServiceError",
    "SpecDrivenSettings",
    "SpecDrivenSettingsService",
]
