"""Pydantic schemas for structured LLM outputs."""

from omoi_os.schemas.memory_analysis import MemoryClassification, PatternExtraction
from omoi_os.schemas.diagnostic_analysis import (
    DiagnosticAnalysis,
    Hypothesis,
    Recommendation,
)
from omoi_os.schemas.quality_analysis import QualityPrediction, QualityRecommendation
from omoi_os.schemas.validation_analysis import BlockingIssue, ValidationResult
from omoi_os.schemas.context_analysis import ContextSummary, Decision, Risk
from omoi_os.schemas.blocker_analysis import BlockerAnalysis, UnblockingStep
from omoi_os.schemas.quality_metrics_analysis import (
    LintError,
    QualityMetricsExtraction,
)
from omoi_os.schemas.spec_generation import (
    # Enums
    SpecPhase,
    SpecStatus,
    RequirementCategory,
    Priority,
    TicketStatus,
    TaskStatus,
    TaskType,
    Estimate,
    # Exploration Phase
    CodebasePattern,
    ExistingComponent,
    DatabaseSchema,
    ExplorationContext,
    # Requirements Phase
    AcceptanceCriterion,
    Requirement,
    RequirementsOutput,
    # Design Phase
    ApiEndpoint,
    DataModelField,
    DataModel,
    DesignOutput,
    # Tasks Phase
    TicketDependencies,
    TaskDependencies,
    Task,
    Ticket,
    TasksOutput,
    # State Machine
    PhaseResult,
    SpecGenerationState,
    EvaluationResult,
)

__all__ = [
    # Memory Analysis
    "MemoryClassification",
    "PatternExtraction",
    # Diagnostic Analysis
    "DiagnosticAnalysis",
    "Hypothesis",
    "Recommendation",
    # Quality Analysis
    "QualityPrediction",
    "QualityRecommendation",
    # Validation Analysis
    "ValidationResult",
    "BlockingIssue",
    # Context Analysis
    "ContextSummary",
    "Decision",
    "Risk",
    # Blocker Analysis
    "BlockerAnalysis",
    "UnblockingStep",
    # Quality Metrics
    "QualityMetricsExtraction",
    "LintError",
    # Spec Generation - Enums
    "SpecPhase",
    "SpecStatus",
    "RequirementCategory",
    "Priority",
    "TicketStatus",
    "TaskStatus",
    "TaskType",
    "Estimate",
    # Spec Generation - Exploration Phase
    "CodebasePattern",
    "ExistingComponent",
    "DatabaseSchema",
    "ExplorationContext",
    # Spec Generation - Requirements Phase
    "AcceptanceCriterion",
    "Requirement",
    "RequirementsOutput",
    # Spec Generation - Design Phase
    "ApiEndpoint",
    "DataModelField",
    "DataModel",
    "DesignOutput",
    # Spec Generation - Tasks Phase
    "TicketDependencies",
    "TaskDependencies",
    "Task",
    "Ticket",
    "TasksOutput",
    # Spec Generation - State Machine
    "PhaseResult",
    "SpecGenerationState",
    "EvaluationResult",
]

