"""API routes for memory and pattern learning."""

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from omoi_os.api.dependencies import get_db_service
from omoi_os.services.memory import MemoryService
from omoi_os.services.embedding import EmbeddingService, EmbeddingProvider
from omoi_os.services.event_bus import EventBusService

router = APIRouter(prefix="/memory", tags=["memory"])


# Request/Response Models
class StoreExecutionRequest(BaseModel):
    """Request to store task execution in memory."""

    task_id: str = Field(..., description="Task ID to remember")
    execution_summary: str = Field(..., description="Summary of task execution")
    success: bool = Field(..., description="Whether execution was successful")
    error_patterns: Optional[Dict[str, Any]] = Field(
        None, description="Error patterns if failed"
    )
    auto_extract_patterns: bool = Field(
        True, description="Auto-extract patterns from successful executions"
    )


class SimilarTaskResponse(BaseModel):
    """Response for similar task search."""

    task_id: str
    memory_id: str
    summary: str
    success: bool
    similarity_score: float
    reused_count: int


class SearchSimilarRequest(BaseModel):
    """Request to search for similar tasks."""

    task_description: str = Field(..., description="Description of the task")
    top_k: int = Field(5, ge=1, le=20, description="Number of results")
    similarity_threshold: float = Field(
        0.7, ge=0.0, le=1.0, description="Minimum similarity"
    )
    success_only: bool = Field(False, description="Only return successful tasks")


class TaskContextResponse(BaseModel):
    """Response with suggested context for a task."""

    similar_tasks: List[Dict[str, Any]]
    matching_patterns: List[Dict[str, Any]]
    recommendations: List[str]


class PatternResponse(BaseModel):
    """Response for learned pattern."""

    pattern_id: str
    pattern_type: str
    task_type_pattern: str
    success_indicators: List[str]
    failure_indicators: List[str]
    recommended_context: Dict[str, Any]
    confidence_score: float
    usage_count: int


class ExtractPatternRequest(BaseModel):
    """Request to extract a pattern."""

    task_type_pattern: str = Field(..., description="Regex pattern for matching tasks")
    pattern_type: str = Field(
        "success", description="Type: success, failure, optimization"
    )
    min_samples: int = Field(3, ge=2, le=10, description="Minimum sample count")


class PatternFeedbackRequest(BaseModel):
    """Feedback on a pattern's usefulness."""

    helpful: bool = Field(..., description="Whether pattern was helpful")
    confidence_adjustment: Optional[float] = Field(
        None, ge=-0.2, le=0.2, description="Confidence score adjustment"
    )


# Dependency: Get MemoryService
def get_memory_service(
    db: Session = Depends(get_db_service),
) -> MemoryService:
    """Get memory service with dependencies."""
    embedding_service = EmbeddingService(provider=EmbeddingProvider.LOCAL)
    event_bus = EventBusService()
    return MemoryService(embedding_service=embedding_service, event_bus=event_bus)


@router.post("/store", status_code=201)
def store_execution(
    request: StoreExecutionRequest,
    db: Session = Depends(get_db_service),
    memory_service: MemoryService = Depends(get_memory_service),
) -> Dict[str, str]:
    """
    Store task execution in memory with embedding.

    This endpoint records a task execution for future pattern learning and
    similarity search.
    """
    try:
        memory = memory_service.store_execution(
            session=db,
            task_id=request.task_id,
            execution_summary=request.execution_summary,
            success=request.success,
            error_patterns=request.error_patterns,
            auto_extract_patterns=request.auto_extract_patterns,
        )
        db.commit()
        return {"memory_id": memory.id, "status": "stored"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to store execution: {str(e)}"
        )


@router.post("/search", response_model=List[SimilarTaskResponse])
def search_similar(
    request: SearchSimilarRequest,
    db: Session = Depends(get_db_service),
    memory_service: MemoryService = Depends(get_memory_service),
) -> List[SimilarTaskResponse]:
    """
    Search for similar past tasks using embedding similarity.

    Returns tasks ordered by similarity score with the query description.
    """
    try:
        results = memory_service.search_similar(
            session=db,
            task_description=request.task_description,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
            success_only=request.success_only,
        )
        db.commit()  # Commit reuse counter updates
        return [
            SimilarTaskResponse(
                task_id=r.task_id,
                memory_id=r.memory_id,
                summary=r.summary,
                success=r.success,
                similarity_score=r.similarity_score,
                reused_count=r.reused_count,
            )
            for r in results
        ]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/tasks/{task_id}/context", response_model=TaskContextResponse)
def get_task_context(
    task_id: str,
    top_k: int = Query(3, ge=1, le=10, description="Number of similar tasks"),
    db: Session = Depends(get_db_service),
    memory_service: MemoryService = Depends(get_memory_service),
) -> TaskContextResponse:
    """
    Get suggested context for a task based on similar past tasks.

    Useful for providing context to agents before they start working on a task.
    """
    try:
        # Get task description
        from omoi_os.models.task import Task

        task = db.get(Task, task_id)
        if not task or not task.description:
            raise HTTPException(
                status_code=404,
                detail=f"Task {task_id} not found or has no description",
            )

        context = memory_service.get_task_context(
            session=db, task_description=task.description, top_k=top_k
        )
        db.commit()
        return TaskContextResponse(**context)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to get context: {str(e)}")


@router.get("/patterns", response_model=List[PatternResponse])
def list_patterns(
    task_type: Optional[str] = Query(None, description="Filter by task type pattern"),
    pattern_type: Optional[str] = Query(None, description="Filter by pattern type"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    db: Session = Depends(get_db_service),
    memory_service: MemoryService = Depends(get_memory_service),
) -> List[PatternResponse]:
    """
    List learned patterns.

    Patterns are ordered by confidence score and usage count.
    """
    try:
        patterns = memory_service.search_patterns(
            session=db, task_type=task_type, pattern_type=pattern_type, limit=limit
        )
        return [
            PatternResponse(
                pattern_id=p.pattern_id,
                pattern_type=p.pattern_type,
                task_type_pattern=p.task_type_pattern,
                success_indicators=p.success_indicators,
                failure_indicators=p.failure_indicators,
                recommended_context=p.recommended_context,
                confidence_score=p.confidence_score,
                usage_count=p.usage_count,
            )
            for p in patterns
        ]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to list patterns: {str(e)}"
        )


@router.post("/patterns/extract", status_code=201)
def extract_pattern(
    request: ExtractPatternRequest,
    db: Session = Depends(get_db_service),
    memory_service: MemoryService = Depends(get_memory_service),
) -> Dict[str, Any]:
    """
    Extract a pattern from completed tasks matching a regex.

    Requires minimum number of samples to extract a reliable pattern.
    """
    try:
        pattern = memory_service.extract_pattern(
            session=db,
            task_type_pattern=request.task_type_pattern,
            pattern_type=request.pattern_type,
            min_samples=request.min_samples,
        )

        if not pattern:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient samples (need {request.min_samples}) to extract pattern",
            )

        db.commit()
        return {
            "pattern_id": pattern.id,
            "confidence": pattern.confidence_score,
            "status": "extracted",
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to extract pattern: {str(e)}"
        )


@router.post("/patterns/{pattern_id}/feedback")
def provide_pattern_feedback(
    pattern_id: str,
    feedback: PatternFeedbackRequest,
    db: Session = Depends(get_db_service),
) -> Dict[str, str]:
    """
    Provide feedback on a pattern's usefulness.

    Helps improve pattern confidence scores over time based on real usage.
    """
    try:
        from omoi_os.models.learned_pattern import LearnedPattern

        pattern = db.get(LearnedPattern, pattern_id)
        if not pattern:
            raise HTTPException(
                status_code=404, detail=f"Pattern {pattern_id} not found"
            )

        # Adjust confidence if provided
        if feedback.confidence_adjustment is not None:
            new_confidence = pattern.confidence_score + feedback.confidence_adjustment
            new_confidence = max(0.0, min(1.0, new_confidence))  # Clamp to [0, 1]
            pattern.update_confidence(new_confidence)

        db.commit()
        return {
            "status": "feedback_recorded",
            "new_confidence": pattern.confidence_score,
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to record feedback: {str(e)}"
        )
