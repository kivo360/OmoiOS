"""Phase gate validation service."""

from __future__ import annotations

from typing import Any

from omoi_os.models.phase_gate_artifact import PhaseGateArtifact
from omoi_os.models.phase_gate_result import PhaseGateResult
from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.database import DatabaseService


PHASE_GATE_REQUIREMENTS: dict[str, dict[str, Any]] = {
    "PHASE_REQUIREMENTS": {
        "required_artifacts": ["requirements_document"],
        "required_tasks_completed": True,
        "validation_criteria": {
            "requirements_document": {
                "min_length": 500,
                "required_sections": ["scope", "acceptance_criteria"],
            }
        },
    },
    "PHASE_IMPLEMENTATION": {
        "required_artifacts": ["code_changes", "test_coverage"],
        "required_tasks_completed": True,
        "validation_criteria": {
            "test_coverage": {"min_percentage": 80},
            "code_changes": {"must_have_tests": True},
        },
    },
    "PHASE_TESTING": {
        "required_artifacts": ["test_results", "test_evidence"],
        "required_tasks_completed": True,
        "validation_criteria": {
            "test_results": {"all_passed": True},
        },
    },
}


class PhaseGateService:
    """Validates phase gates before transitions."""

    def __init__(self, db: DatabaseService):
        self.db = db

    def check_gate_requirements(self, ticket_id: str, phase_id: str) -> dict[str, Any]:
        """
        Check if gate requirements are met for a ticket and phase.

        Returns:
            Dictionary containing requirements status, missing artifacts, and validation state.
        """
        config = PHASE_GATE_REQUIREMENTS.get(phase_id)
        if not config:
            return {
                "requirements_met": True,
                "missing_artifacts": [],
                "validation_status": "not_configured",
            }

        with self.db.get_session() as session:
            artifacts = (
                session.query(PhaseGateArtifact)
                .filter(
                    PhaseGateArtifact.ticket_id == ticket_id,
                    PhaseGateArtifact.phase_id == phase_id,
                )
                .all()
            )
            artifact_types = {artifact.artifact_type for artifact in artifacts}
            required_artifacts: list[str] = config.get("required_artifacts", [])
            missing_artifacts = [
                artifact_type
                for artifact_type in required_artifacts
                if artifact_type not in artifact_types
            ]

            tasks_complete = True
            if config.get("required_tasks_completed"):
                tasks = (
                    session.query(Task)
                    .filter(Task.ticket_id == ticket_id, Task.phase_id == phase_id)
                    .all()
                )
                tasks_complete = bool(tasks) and all(task.status == "completed" for task in tasks)

        requirements_met = not missing_artifacts and tasks_complete
        if not missing_artifacts and not tasks_complete:
            validation_status = "waiting_tasks"
        elif missing_artifacts:
            validation_status = "blocked"
        else:
            validation_status = "ready"

        return {
            "requirements_met": requirements_met,
            "missing_artifacts": missing_artifacts,
            "validation_status": validation_status,
        }

    def validate_gate(self, ticket_id: str, phase_id: str) -> PhaseGateResult:
        """
        Run full gate validation and persist result.

        Returns:
            PhaseGateResult representing validation outcome.
        """
        # Ensure latest artifacts are captured before validation
        self.collect_artifacts(ticket_id, phase_id)

        requirements = self.check_gate_requirements(ticket_id, phase_id)
        blocking_reasons: list[str] = []
        validation_passed = requirements["requirements_met"]

        if not requirements["requirements_met"]:
            missing = requirements.get("missing_artifacts") or []
            if missing:
                blocking_reasons.append(
                    f"Missing required artifacts: {', '.join(missing)}"
                )
            if requirements.get("validation_status") == "waiting_tasks":
                blocking_reasons.append("Phase tasks not yet completed")
        else:
            validation_passed, criteria_reasons = self._evaluate_validation_criteria(
                ticket_id, phase_id
            )
            if criteria_reasons:
                blocking_reasons.extend(criteria_reasons)

        gate_status = "passed" if validation_passed and not blocking_reasons else "failed"

        with self.db.get_session() as session:
            result = PhaseGateResult(
                ticket_id=ticket_id,
                phase_id=phase_id,
                gate_status=gate_status,
                validation_result={
                    "requirements": requirements,
                    "blocking_reasons": blocking_reasons,
                },
                blocking_reasons=blocking_reasons or None,
                validated_by="phase-gate-service",
            )
            session.add(result)
            session.flush()
            session.refresh(result)
            session.expunge(result)
            return result

    def collect_artifacts(self, ticket_id: str, phase_id: str) -> list[PhaseGateArtifact]:
        """Collect artifacts from completed tasks for a ticket and phase."""
        collected: list[PhaseGateArtifact] = []

        with self.db.get_session() as session:
            existing = (
                session.query(PhaseGateArtifact)
                .filter(
                    PhaseGateArtifact.ticket_id == ticket_id,
                    PhaseGateArtifact.phase_id == phase_id,
                )
                .all()
            )
            existing_keys = {
                (artifact.artifact_type, artifact.artifact_path) for artifact in existing
            }

            tasks = (
                session.query(Task)
                .filter(
                    Task.ticket_id == ticket_id,
                    Task.phase_id == phase_id,
                    Task.status == "completed",
                )
                .all()
            )

            for task in tasks:
                task_result = task.result or {}
                artifacts_payload = task_result.get("artifacts", [])
                for payload in artifacts_payload:
                    artifact_type = payload.get("type")
                    if not artifact_type:
                        continue

                    artifact_path = payload.get("path")
                    key = (artifact_type, artifact_path)
                    if key in existing_keys:
                        continue

                    artifact = PhaseGateArtifact(
                        ticket_id=ticket_id,
                        phase_id=phase_id,
                        artifact_type=artifact_type,
                        artifact_path=artifact_path,
                        artifact_content=payload.get("content"),
                        collected_by=payload.get("collected_by", "system"),
                    )
                    session.add(artifact)
                    session.flush()
                    session.refresh(artifact)
                    session.expunge(artifact)
                    collected.append(artifact)
                    existing_keys.add(key)

        return collected

    def can_transition(self, ticket_id: str, to_phase: str) -> tuple[bool, list[str]]:
        """
        Determine whether a ticket can transition out of its current phase.

        Returns:
            Tuple containing boolean flag and blocking reasons.
        """
        del to_phase  # Placeholder for future use when downstream phase requirements added

        with self.db.get_session() as session:
            ticket = session.get(Ticket, ticket_id)
            if not ticket:
                raise ValueError(f"Ticket {ticket_id} not found")
            current_phase = ticket.phase_id

        result = self.validate_gate(ticket_id, current_phase)
        can_transition = result.gate_status == "passed"
        blocking = result.blocking_reasons or []
        return can_transition, (blocking if not can_transition else [])

    def _evaluate_validation_criteria(
        self, ticket_id: str, phase_id: str
    ) -> tuple[bool, list[str]]:
        """Validate artifacts against configured criteria."""
        config = PHASE_GATE_REQUIREMENTS.get(phase_id, {})
        criteria = config.get("validation_criteria", {})
        if not criteria:
            return True, []

        with self.db.get_session() as session:
            artifacts = (
                session.query(PhaseGateArtifact)
                .filter(
                    PhaseGateArtifact.ticket_id == ticket_id,
                    PhaseGateArtifact.phase_id == phase_id,
                )
                .all()
            )
            artifact_map = {artifact.artifact_type: artifact for artifact in artifacts}

        blocking_reasons: list[str] = []
        for artifact_type, rules in criteria.items():
            artifact = artifact_map.get(artifact_type)
            if not artifact:
                blocking_reasons.append(f"Missing artifact for validation: {artifact_type}")
                continue

            content = artifact.artifact_content or {}
            if not isinstance(content, dict):
                blocking_reasons.append(f"Artifact {artifact_type} missing structured content")
                continue

            min_length = rules.get("min_length")
            if min_length is not None:
                length_value = content.get("length")
                if length_value is None and isinstance(content.get("content"), str):
                    length_value = len(content["content"])
                if (length_value or 0) < min_length:
                    blocking_reasons.append(
                        f"Artifact {artifact_type} length {length_value or 0} below minimum {min_length}"
                    )

            required_sections = rules.get("required_sections")
            if required_sections:
                sections = content.get("sections") or []
                missing_sections = [
                    section for section in required_sections if section not in sections
                ]
                if missing_sections:
                    blocking_reasons.append(
                        f"Artifact {artifact_type} missing sections: {', '.join(missing_sections)}"
                    )

            min_percentage = rules.get("min_percentage")
            if min_percentage is not None:
                percentage = content.get("percentage", 0)
                if percentage < min_percentage:
                    blocking_reasons.append(
                        f"Artifact {artifact_type} coverage {percentage}% below {min_percentage}%"
                    )

            if rules.get("must_have_tests"):
                has_tests = content.get("has_tests")
                if not has_tests:
                    blocking_reasons.append(
                        f"Artifact {artifact_type} must include associated tests"
                    )

            if rules.get("all_passed"):
                all_passed = content.get("all_passed")
                if not all_passed:
                    blocking_reasons.append(
                        f"Artifact {artifact_type} indicates failing tests"
                    )

        return (not blocking_reasons), blocking_reasons
