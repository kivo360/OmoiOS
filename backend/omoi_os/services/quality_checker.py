"""Quality checker service for code quality validation."""

from typing import List, Dict, Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from omoi_os.models.quality_metric import QualityMetric, MetricType
from omoi_os.models.quality_gate import QualityGate
from omoi_os.models.task import Task
from omoi_os.services.event_bus import EventBusService, SystemEvent
from omoi_os.services.llm_service import get_llm_service
from omoi_os.schemas.quality_metrics_analysis import QualityMetricsExtraction
from omoi_os.utils.datetime import utc_now


class QualityCheckerService:
    """
    Service for checking code quality metrics.

    Validates test coverage, lint scores, complexity, and other
    quality indicators against defined thresholds.
    """

    def __init__(
        self,
        event_bus: Optional[EventBusService] = None,
    ):
        """
        Initialize quality checker service.

        Args:
            event_bus: Optional event bus for publishing quality events.
        """
        self.event_bus = event_bus

    def record_metric(
        self,
        session: Session,
        task_id: str,
        metric_type: str,
        metric_name: str,
        value: float,
        threshold: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QualityMetric:
        """
        Record a quality metric for a task.

        Args:
            session: Database session.
            task_id: Task being measured.
            metric_type: Type of metric (coverage, lint, complexity, etc.).
            metric_name: Specific metric name.
            value: Measured value.
            threshold: Optional threshold requirement.
            metadata: Additional measurement context.

        Returns:
            Created quality metric record.
        """
        # Verify task exists
        task = session.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Determine if threshold passed
        passed = True
        if threshold is not None:
            # For most metrics, higher is better (coverage, etc.)
            # For some metrics, lower is better (lint errors, complexity)
            if metric_type in [MetricType.LINT, MetricType.COMPLEXITY]:
                passed = value <= threshold
            else:
                passed = value >= threshold

        # Create metric record
        metric = QualityMetric(
            task_id=task_id,
            metric_type=metric_type,
            metric_name=metric_name,
            value=value,
            threshold=threshold,
            passed=passed,
            measured_at=utc_now(),
            measurement_metadata=metadata,
        )

        session.add(metric)
        session.flush()

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="quality.metric.recorded",
                    entity_type="quality_metric",
                    entity_id=str(metric.id),
                    payload={
                        "task_id": task_id,
                        "metric_type": metric_type,
                        "metric_name": metric_name,
                        "value": value,
                        "passed": passed,
                    },
                )
            )

        return metric

    async def check_code_quality(
        self, session: Session, task_id: str, task_result: Dict[str, Any]
    ) -> List[QualityMetric]:
        """
        Check code quality from task result using PydanticAI for extraction.

        Extracts quality metrics from task execution results and records them.

        Args:
            session: Database session.
            task_id: Task to check.
            task_result: Task result dictionary (may contain coverage, lint data).

        Returns:
            List of quality metrics recorded.
        """
        import json

        # Convert task result to JSON for analysis
        task_result_str = json.dumps(task_result, indent=2, default=str)

        # Build prompt using template
        from omoi_os.services.template_service import get_template_service

        template_service = get_template_service()
        prompt = template_service.render(
            "prompts/quality_metrics.md.j2",
            task_result_json=task_result_str,
        )

        system_prompt = template_service.render_system_prompt("system/quality_metrics.md.j2")

        try:
            # Run extraction using LLM service
            llm = get_llm_service()
            extraction = await llm.structured_output(
                prompt,
                output_type=QualityMetricsExtraction,
                system_prompt=system_prompt,
            )

            # Record metrics from structured extraction
            metrics = []

            # Test coverage
            if extraction.test_coverage is not None:
                metric = self.record_metric(
                    session=session,
                    task_id=task_id,
                    metric_type=MetricType.COVERAGE,
                    metric_name="test_coverage_percentage",
                    value=extraction.test_coverage,
                    threshold=80.0,
                )
                metrics.append(metric)

            # Lint errors
            for lint_error in extraction.lint_errors:
                metric = self.record_metric(
                    session=session,
                    task_id=task_id,
                    metric_type=MetricType.LINT,
                    metric_name=f"lint_{lint_error.error_type}",
                    value=1.0,  # Count as 1 error
                    threshold=0.0,
                    metadata={
                        "file_path": lint_error.file_path,
                        "line_number": lint_error.line_number,
                        "message": lint_error.message,
                        "severity": lint_error.severity,
                    },
                )
                metrics.append(metric)

            # Complexity
            if extraction.complexity_score is not None:
                metric = self.record_metric(
                    session=session,
                    task_id=task_id,
                    metric_type=MetricType.COMPLEXITY,
                    metric_name="cyclomatic_complexity",
                    value=extraction.complexity_score,
                    threshold=10.0,
                )
                metrics.append(metric)

            # Overall quality score
            metric = self.record_metric(
                session=session,
                task_id=task_id,
                metric_type="overall",
                metric_name="code_quality_score",
                value=extraction.code_quality_score,
                threshold=0.7,  # 70% minimum
            )
            metrics.append(metric)

            return metrics

        except Exception:
            # Fallback to basic extraction
            return self.check_code_quality_sync(session, task_id, task_result)

    def check_code_quality_sync(
        self, session: Session, task_id: str, task_result: Dict[str, Any]
    ) -> List[QualityMetric]:
        """
        Synchronous fallback for code quality checking (basic extraction).

        Args:
            session: Database session.
            task_id: Task to check.
            task_result: Task result dictionary.

        Returns:
            List of quality metrics recorded.
        """
        metrics = []

        # Extract coverage if available
        if "test_coverage" in task_result:
            coverage = task_result["test_coverage"]
            metric = self.record_metric(
                session=session,
                task_id=task_id,
                metric_type=MetricType.COVERAGE,
                metric_name="test_coverage_percentage",
                value=coverage,
                threshold=80.0,
            )
            metrics.append(metric)

        # Extract lint errors if available
        if "lint_errors" in task_result:
            lint_errors = task_result["lint_errors"]
            metric = self.record_metric(
                session=session,
                task_id=task_id,
                metric_type=MetricType.LINT,
                metric_name="lint_error_count",
                value=float(lint_errors),
                threshold=0.0,
            )
            metrics.append(metric)

        # Extract complexity if available
        if "complexity_score" in task_result:
            complexity = task_result["complexity_score"]
            metric = self.record_metric(
                session=session,
                task_id=task_id,
                metric_type=MetricType.COMPLEXITY,
                metric_name="cyclomatic_complexity",
                value=complexity,
                threshold=10.0,
            )
            metrics.append(metric)

        return metrics

    def evaluate_gate(
        self, session: Session, task_id: str, gate_id: str
    ) -> Dict[str, Any]:
        """
        Evaluate a quality gate for a task.

        Args:
            session: Database session.
            task_id: Task to evaluate.
            gate_id: Quality gate to apply.

        Returns:
            Evaluation result with pass/fail and details.
        """
        # Get gate
        gate = session.get(QualityGate, gate_id)
        if not gate:
            raise ValueError(f"Quality gate {gate_id} not found")

        if not gate.enabled:
            return {"gate_id": gate_id, "passed": True, "skipped": True}

        # Get metrics for task
        metrics_query = select(QualityMetric).where(QualityMetric.task_id == task_id)
        metrics = list(session.execute(metrics_query).scalars().all())

        # Check requirements
        requirements_met = []
        requirements_failed = []

        for req_key, req_value in gate.requirements.items():
            # Find matching metric
            metric = next(
                (m for m in metrics if req_key in m.metric_name.lower()), None
            )

            if metric:
                if metric.passed:
                    requirements_met.append(
                        {
                            "requirement": req_key,
                            "expected": req_value,
                            "actual": metric.value,
                            "status": "pass",
                        }
                    )
                else:
                    requirements_failed.append(
                        {
                            "requirement": req_key,
                            "expected": req_value,
                            "actual": metric.value,
                            "status": "fail",
                        }
                    )
            else:
                requirements_failed.append(
                    {
                        "requirement": req_key,
                        "expected": req_value,
                        "actual": None,
                        "status": "missing",
                    }
                )

        passed = len(requirements_failed) == 0
        result = {
            "gate_id": gate_id,
            "gate_name": gate.name,
            "passed": passed,
            "requirements_met": requirements_met,
            "requirements_failed": requirements_failed,
            "failure_action": gate.failure_action if not passed else None,
        }

        # Publish event
        if self.event_bus:
            self.event_bus.publish(
                SystemEvent(
                    event_type="quality.gate.evaluated",
                    entity_type="quality_gate",
                    entity_id=gate_id,
                    payload={
                        "task_id": task_id,
                        "passed": passed,
                        "failed_count": len(requirements_failed),
                    },
                )
            )

        return result

    def get_task_quality_summary(
        self, session: Session, task_id: str
    ) -> Dict[str, Any]:
        """
        Get quality summary for a task.

        Args:
            session: Database session.
            task_id: Task to summarize.

        Returns:
            Quality summary with all metrics and overall pass/fail.
        """
        metrics_query = select(QualityMetric).where(QualityMetric.task_id == task_id)
        metrics = list(session.execute(metrics_query).scalars().all())

        if not metrics:
            return {
                "task_id": task_id,
                "metrics_count": 0,
                "overall_passed": None,
                "metrics": [],
            }

        passed_count = sum(1 for m in metrics if m.passed)
        overall_passed = passed_count == len(metrics)

        return {
            "task_id": task_id,
            "metrics_count": len(metrics),
            "passed_count": passed_count,
            "failed_count": len(metrics) - passed_count,
            "overall_passed": overall_passed,
            "metrics": [m.to_dict() for m in metrics],
        }

