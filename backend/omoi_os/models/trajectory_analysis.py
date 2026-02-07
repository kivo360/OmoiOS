"""Pydantic models for trajectory analysis and intelligent monitoring."""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class LLMTrajectoryAnalysisResponse(BaseModel):
    """Pydantic model for LLM trajectory analysis response.

    This model is used with structured_output to get properly typed
    analysis results directly from the LLM, without manual JSON parsing.
    """

    trajectory_aligned: bool = Field(
        default=True, description="Whether agent trajectory is aligned with phase goals"
    )
    alignment_score: float = Field(
        default=0.8, ge=0.0, le=1.0, description="Alignment score from 0.0 to 1.0"
    )
    needs_steering: bool = Field(
        default=False, description="Whether agent needs steering intervention"
    )
    steering_type: Optional[str] = Field(
        default=None, description="Type of steering needed (guidance, emergency, etc.)"
    )
    steering_recommendation: Optional[str] = Field(
        default=None, description="Recommended steering action"
    )
    trajectory_summary: str = Field(
        ..., description="Summary of agent's current trajectory and state"
    )
    last_claude_message_marker: Optional[str] = Field(
        default=None, description="Marker for last significant Claude message"
    )
    accumulated_goal: Optional[str] = Field(
        default=None, description="Accumulated goal from conversation context"
    )
    current_focus: str = Field(..., description="Agent's current focus area or task")
    session_duration: Optional[str] = Field(
        default=None, description="Session duration (will be converted to timedelta)"
    )
    conversation_length: int = Field(
        default=0, description="Length of conversation in messages"
    )
    details: Dict[str, Any] = Field(
        default_factory=dict, description="Additional analysis details"
    )


class ConversationEvent(BaseModel):
    """Model for conversation events in trajectory analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: str
    event_type: str
    content: str
    timestamp: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PersistentConstraint(BaseModel):
    """Model for persistent constraints in trajectory context."""

    model_config = ConfigDict(from_attributes=True)

    constraint_type: str = Field(..., description="Type of constraint")
    description: str = Field(..., description="Description of the constraint")
    source: str = Field(..., description="Source of the constraint")
    strength: float = Field(default=1.0, description="Strength of the constraint (0-1)")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AccumulatedContext(BaseModel):
    """Model for accumulated context in trajectory analysis."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    context_summary: str
    persistent_constraints: List[PersistentConstraint] = Field(default_factory=list)
    session_duration: Optional[timedelta] = None
    conversation_events: List[ConversationEvent] = Field(default_factory=list)
    task_completion_rate: float = Field(default=0.0)
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class TrajectoryContext(BaseModel):
    """Complete trajectory context for an agent."""

    model_config = ConfigDict(from_attributes=True)

    accumulated_context: AccumulatedContext
    current_phase: str
    current_focus: str
    accumulated_goal: Optional[str] = None
    conversation_length: int = Field(default=0)
    session_duration: Optional[timedelta] = None
    last_claude_message_marker: Optional[str] = None


class GuardianAnalysis(BaseModel):
    """Model for Guardian trajectory analysis results."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: str
    current_phase: str
    trajectory_aligned: bool = Field(default=True)
    alignment_score: float = Field(default=0.8, ge=0.0, le=1.0)
    needs_steering: bool = Field(default=False)
    steering_type: Optional[str] = None
    steering_recommendation: Optional[str] = None
    trajectory_summary: str
    last_claude_message_marker: Optional[str] = None
    accumulated_goal: Optional[str] = None
    current_focus: str
    session_duration: Optional[timedelta] = None
    conversation_length: int = Field(default=0)
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class SteeringIntervention(BaseModel):
    """Model for steering intervention records."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    agent_id: str
    steering_type: str = Field(..., description="Type of steering intervention")
    message: str = Field(..., description="Intervention message")
    actor_type: str = Field(..., description="Type of actor initiating intervention")
    actor_id: str = Field(..., description="ID of actor initiating intervention")
    reason: str = Field(..., description="Reason for intervention")
    created_at: datetime


class DetectedDuplicate(BaseModel):
    """Model for detected duplicate work."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    conductor_analysis_id: UUID
    agent1_id: str
    agent2_id: str
    similarity_score: float = Field(ge=0.0, le=1.0)
    work_description: Optional[str] = None
    resources: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ConductorAnalysis(BaseModel):
    """Model for Conductor system coherence analysis."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    cycle_id: UUID
    coherence_score: float = Field(ge=0.0, le=1.0)
    system_status: str = Field(..., description="Overall system status")
    num_agents: int = Field(ge=0)
    duplicate_count: int = Field(default=0, ge=0)
    termination_count: int = Field(default=0, ge=0)
    coordination_count: int = Field(default=0, ge=0)
    details: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class MonitoringVector(BaseModel):
    """Model for vector search entries (PGVector integration)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    entity_type: str = Field(..., description="Type of entity (agent, task, etc.)")
    entity_id: UUID
    embedding: List[float] = Field(..., description="Vector embedding")
    created_at: datetime


class MonitoringAuditLog(BaseModel):
    """Model for monitoring audit trail."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str = Field(..., description="Type of monitoring event")
    actor_type: str = Field(
        ..., description="Type of actor (guardian, conductor, etc.)"
    )
    actor_id: Optional[str] = None
    target_agent_ids: List[str] = Field(..., description="List of affected agent IDs")
    reason: str = Field(..., description="Reason for the monitoring action")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# Request/Response Models for API Endpoints


class TrajectoryAnalysisRequest(BaseModel):
    """Request model for trajectory analysis."""

    agent_id: str = Field(..., description="Agent ID to analyze")
    force_analysis: bool = Field(
        default=False, description="Skip cache and force fresh analysis"
    )


class TrajectoryAnalysisResponse(BaseModel):
    """Response model for trajectory analysis."""

    agent_id: str
    current_phase: str
    trajectory_aligned: bool
    alignment_score: float
    needs_steering: bool
    steering_type: Optional[str]
    steering_recommendation: Optional[str]
    trajectory_summary: str
    current_focus: str
    conversation_length: int
    session_duration: Optional[timedelta]
    health_score: float
    last_analysis: datetime


class SystemCoherenceRequest(BaseModel):
    """Request model for system coherence analysis."""

    cycle_id: Optional[UUID] = Field(None, description="Optional cycle ID for tracking")


class SystemCoherenceResponse(BaseModel):
    """Response model for system coherence analysis."""

    coherence_score: float
    system_status: str
    num_agents: int
    duplicate_count: int
    termination_count: int
    coordination_count: int
    detected_duplicates: List[Dict[str, Any]]
    recommendations: List[str]
    analysis_id: UUID


class SteeringInterventionRequest(BaseModel):
    """Request model for steering intervention."""

    agent_id: str = Field(..., description="Target agent ID")
    steering_type: str = Field(..., description="Type of steering intervention")
    message: str = Field(..., description="Intervention message")
    reason: str = Field(..., description="Reason for intervention")
    auto_execute: bool = Field(
        default=False, description="Whether to auto-execute the intervention"
    )


class SteeringInterventionResponse(BaseModel):
    """Response model for steering intervention."""

    intervention_id: UUID
    agent_id: str
    steering_type: str
    message: str
    executed: bool
    created_at: datetime


class SystemHealthResponse(BaseModel):
    """Response model for system health overview."""

    active_agents: int
    average_alignment: float
    agents_need_steering: int
    system_health: str
    phase_distribution: Dict[str, int]
    steering_types: Dict[str, int]
    recent_duplicates: int
    last_analysis: Optional[datetime] = None


class AgentHealthResponse(BaseModel):
    """Response model for individual agent health."""

    status: str
    agent_id: str
    health_score: Optional[float] = None
    alignment_score: Optional[float] = None
    trajectory_aligned: Optional[bool] = None
    needs_steering: Optional[bool] = None
    current_phase: Optional[str] = None
    current_focus: Optional[str] = None
    conversation_length: Optional[int] = None
    recent_interventions: Optional[int] = None
    last_analysis: Optional[datetime] = None
    error: Optional[str] = None
