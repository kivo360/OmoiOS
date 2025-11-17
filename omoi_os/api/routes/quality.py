"""API routes for quality gates and metrics."""

from typing import List, Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from omoi_os.api.dependencies import get_db
from omoi_os.services.quality_checker import QualityCheckerService
from omoi_os.services.quality_predictor import QualityPredictorService
from omoi_os.services.memory import MemoryService
from omoi_os.services.embedding import EmbeddingService, EmbeddingProvider
from omoi_os.services.event_bus import EventBusService

router = APIRouter(prefix="/quality", tags=["quality"])


# Request/Response Models
class RecordMetricRequest(BaseModel):
    """Request to record a quality metric."""

    task_id: str
    metric_type: str
    metric_name: str
    value: float
    threshold: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class PredictQualityRequest(BaseModel):
    """Request to predict quality for a task."""

    task_description: str
    task_type: Optional[str] = None


class QualityPredictionResponse(BaseModel):
    """Quality prediction response."""

    predicted_quality_score: float
    confidence: float
    similar_task_count: int
    pattern_count: int
    recommendations: List[str]
    risk_level: str


# Dependencies
def get_quality_checker() -> QualityCheckerService:
    """Get quality checker service."""
    event_bus = EventBusService()
    return QualityCheckerService(event_bus=event_bus)


def get_quality_predictor() -> QualityPredictorService:
    """Get quality predictor service."""
    embedding_service = EmbeddingService(provider=EmbeddingProvider.LOCAL)
    event_bus = EventBusService()
    memory_service = MemoryService(
        embedding_service=embedding_service, event_bus=event_bus
    )
    return QualityPredictorService(memory_service=memory_service, event_bus=event_bus)


@router.post("/metrics/record", status_code=201)
def record_quality_metric(
    request: RecordMetricRequest,
    db: Session = Depends(get_db),
    checker: QualityCheckerService = Depends(get_quality_checker),
) -> Dict[str, Any]:
    """Record a quality metric for a task."""
    try:
        metric = checker.record_metric(
            session=db,
            task_id=request.task_id,
            metric_type=request.metric_type,
            metric_name=request.metric_name,
            value=request.value,
            threshold=request.threshold,
            metadata=request.metadata,
        )
        db.commit()
        return metric.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Failed to record metric: {str(e)}"
        )


@router.get("/metrics/{task_id}")
def get_task_metrics(
    task_id: str,
    db: Session = Depends(get_db),
    checker: QualityCheckerService = Depends(get_quality_checker),
) -> Dict[str, Any]:
    """Get all quality metrics for a task."""
    try:
        summary = checker.get_task_quality_summary(session=db, task_id=task_id)
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/predict", response_model=QualityPredictionResponse)
def predict_quality(
    request: PredictQualityRequest,
    db: Session = Depends(get_db),
    predictor: QualityPredictorService = Depends(get_quality_predictor),
) -> QualityPredictionResponse:
    """
    Predict quality score for a planned task using Memory patterns.

    Uses similarity to past successful tasks and learned patterns
    to estimate quality and provide recommendations.
    """
    try:
        prediction = predictor.predict_quality(
            session=db,
            task_description=request.task_description,
            task_type=request.task_type,
        )
        db.commit()  # Commit any reuse counter updates
        return QualityPredictionResponse(**prediction)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.get("/trends")
def get_quality_trends(
    phase_id: Optional[str] = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    predictor: QualityPredictorService = Depends(get_quality_predictor),
) -> Dict[str, Any]:
    """Get quality trends across tasks."""
    try:
        trends = predictor.get_quality_trends(
            session=db, phase_id=phase_id, limit=limit
        )
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get trends: {str(e)}")


@router.post("/gates/{gate_id}/evaluate")
def evaluate_quality_gate(
    gate_id: str,
    task_id: str,
    db: Session = Depends(get_db),
    checker: QualityCheckerService = Depends(get_quality_checker),
) -> Dict[str, Any]:
    """Evaluate a quality gate for a task."""
    try:
        result = checker.evaluate_gate(session=db, task_id=task_id, gate_id=gate_id)
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {str(e)}")
