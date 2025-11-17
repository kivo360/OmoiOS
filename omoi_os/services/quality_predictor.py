"""Quality predictor service using Memory patterns."""

from typing import Dict, Any, List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.learned_pattern import TaskPattern
from omoi_os.models.quality_metric import QualityMetric
from omoi_os.models.task import Task
from omoi_os.services.memory import MemoryService
from omoi_os.services.event_bus import EventBusService, SystemEvent


class QualityPredictorService:
    """
    Service for predicting quality based on learned patterns.

    Uses Memory Squad's pattern learning to predict quality issues
    before task execution.
    """

    def __init__(
        self,
        memory_service: MemoryService,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize quality predictor.

        Args:
            memory_service: Memory service for pattern retrieval.
            event_bus: Optional event bus for publishing predictions.
        """
        self.memory_service = memory_service
        self.event_bus = event_bus

    def predict_quality(
        self, session: Session, task_description: str, task_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Predict quality score for a planned task.

        Args:
            session: Database session.
            task_description: Description of the task.
            task_type: Optional task type filter.

        Returns:
            Prediction result with score, confidence, and recommendations.
        """
        # Get similar successful tasks
        similar_tasks = self.memory_service.search_similar(
            session=session,
            task_description=task_description,
            top_k=5,
            similarity_threshold=0.5,
            success_only=True,
        )

        # Get matching patterns
        patterns = self.memory_service.search_patterns(
            session=session, task_type=task_type, pattern_type="success", limit=5
        )

        # Calculate predicted quality score
        quality_score = self._calculate_quality_score(similar_tasks, patterns)

        # Generate recommendations
        recommendations = self._generate_recommendations(similar_tasks, patterns)

        # Determine confidence
        confidence = self._calculate_confidence(similar_tasks, patterns)

        prediction = {
            "predicted_quality_score": quality_score,
            "confidence": confidence,
            "similar_task_count": len(similar_tasks),
            "pattern_count": len(patterns),
            "recommendations": recommendations,
            "risk_level": self._assess_risk_level(quality_score, confidence),
        }

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="quality.prediction.generated",
                    entity_type="task",
                    entity_id="new",
                    payload={
                        "quality_score": quality_score,
                        "confidence": confidence,
                        "risk_level": prediction["risk_level"],
                    },
                )
            )

        return prediction

    def _calculate_quality_score(
        self, similar_tasks: List, patterns: List[TaskPattern]
    ) -> float:
        """
        Calculate predicted quality score (0.0 to 1.0).

        Based on:
        - Success rate of similar tasks
        - Pattern confidence scores
        - Number of success indicators
        """
        if not similar_tasks and not patterns:
            return 0.5  # Neutral score when no data

        score = 0.0
        weight_similar = 0.6
        weight_patterns = 0.4

        # Score from similar tasks
        if similar_tasks:
            success_rate = sum(1 for t in similar_tasks if t.success) / len(
                similar_tasks
            )
            avg_similarity = sum(t.similarity_score for t in similar_tasks) / len(
                similar_tasks
            )
            similar_score = success_rate * avg_similarity
            score += similar_score * weight_similar

        # Score from patterns
        if patterns:
            avg_confidence = sum(p.confidence_score for p in patterns) / len(patterns)
            indicator_strength = sum(len(p.success_indicators) for p in patterns) / max(
                len(patterns), 1
            )
            pattern_score = avg_confidence * min(indicator_strength / 5.0, 1.0)
            score += pattern_score * weight_patterns

        return min(max(score, 0.0), 1.0)  # Clamp to [0, 1]

    def _calculate_confidence(
        self, similar_tasks: List, patterns: List[TaskPattern]
    ) -> float:
        """Calculate confidence in the prediction."""
        # Confidence based on data availability
        task_confidence = min(len(similar_tasks) / 5.0, 1.0)  # Max at 5 tasks
        pattern_confidence = min(len(patterns) / 3.0, 1.0)  # Max at 3 patterns

        # Combined confidence
        if similar_tasks and patterns:
            return (task_confidence + pattern_confidence) / 2
        elif similar_tasks:
            return task_confidence * 0.7  # Slight penalty for missing patterns
        elif patterns:
            return pattern_confidence * 0.7
        else:
            return 0.1  # Very low confidence with no data

    def _generate_recommendations(
        self, similar_tasks: List, patterns: List[TaskPattern]
    ) -> List[str]:
        """Generate quality recommendations."""
        recommendations = []

        if similar_tasks:
            avg_similarity = sum(t.similarity_score for t in similar_tasks) / len(
                similar_tasks
            )
            if avg_similarity > 0.8:
                recommendations.append(
                    "High similarity to successful tasks. Follow established patterns."
                )

        if patterns:
            high_conf_patterns = [p for p in patterns if p.confidence_score > 0.7]
            if high_conf_patterns:
                indicators = []
                for p in high_conf_patterns:
                    indicators.extend(p.success_indicators)
                unique_indicators = list(set(indicators))
                recommendations.append(
                    f"Success indicators from patterns: {', '.join(unique_indicators[:3])}"
                )

        if not similar_tasks and not patterns:
            recommendations.append(
                "No historical data. Extra caution recommended. Consider adding tests early."
            )

        return recommendations

    def _assess_risk_level(self, quality_score: float, confidence: float) -> str:
        """Assess risk level based on predicted quality and confidence."""
        if quality_score > 0.8 and confidence > 0.7:
            return "low"
        elif quality_score > 0.6 and confidence > 0.5:
            return "medium"
        elif quality_score < 0.4 or confidence < 0.3:
            return "high"
        else:
            return "medium"

    def get_quality_trends(
        self, session: Session, phase_id: Optional[str] = None, limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get quality trends across tasks.

        Args:
            session: Database session.
            phase_id: Optional filter by phase.
            limit: Number of recent tasks to analyze.

        Returns:
            Quality trends and statistics.
        """
        # Build query
        query = select(QualityMetric).order_by(QualityMetric.measured_at.desc())

        if phase_id:
            query = query.join(Task).where(Task.phase_id == phase_id)

        metrics = list(session.execute(query.limit(limit * 10)).scalars().all())

        if not metrics:
            return {"trend": "no_data", "metrics_analyzed": 0}

        # Group by metric type
        by_type: Dict[str, List[QualityMetric]] = {}
        for metric in metrics:
            if metric.metric_type not in by_type:
                by_type[metric.metric_type] = []
            by_type[metric.metric_type].append(metric)

        # Calculate trends
        trends = {}
        for metric_type, type_metrics in by_type.items():
            avg_value = sum(m.value for m in type_metrics) / len(type_metrics)
            pass_rate = sum(1 for m in type_metrics if m.passed) / len(type_metrics)

            trends[metric_type] = {
                "average_value": avg_value,
                "pass_rate": pass_rate,
                "sample_count": len(type_metrics),
            }

        return {
            "trends": trends,
            "metrics_analyzed": len(metrics),
            "overall_pass_rate": sum(1 for m in metrics if m.passed) / len(metrics),
        }
