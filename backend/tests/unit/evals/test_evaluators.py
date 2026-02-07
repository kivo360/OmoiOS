"""Unit tests for spec-driven development evaluators.

Tests the evaluator classes that validate phase outputs in the state machine.
"""

import pytest

from omoi_os.evals import (
    EvalResult,
    ExplorationEvaluator,
    RequirementEvaluator,
    DesignEvaluator,
    TaskEvaluator,
)


class TestEvalResult:
    """Tests for EvalResult dataclass."""

    def test_default_values(self):
        """Test EvalResult has correct defaults."""
        result = EvalResult(passed=True, score=0.8)
        assert result.passed is True
        assert result.score == 0.8
        assert result.failures == []
        assert result.warnings == []
        assert result.details == {}
        assert result.feedback_for_retry == ""

    def test_with_failures(self):
        """Test EvalResult with failures."""
        result = EvalResult(
            passed=False,
            score=0.3,
            failures=["Missing field X", "Invalid format Y"],
            details={"has_x": False, "valid_y": False},
        )
        assert result.passed is False
        assert len(result.failures) == 2


class TestExplorationEvaluator:
    """Tests for ExplorationEvaluator."""

    @pytest.fixture
    def evaluator(self):
        return ExplorationEvaluator()

    def test_empty_context_fails(self, evaluator):
        """Empty context should fail evaluation."""
        result = evaluator.evaluate(None)
        assert result.passed is False
        assert result.score == 0.0
        assert any("No exploration" in f for f in result.failures)

    def test_minimal_valid_context(self, evaluator):
        """Minimal valid context should pass."""
        context = {
            "project_type": "web_application",
            "structure": {"directories": ["src", "tests"], "files": ["main.py"]},
            "existing_models": [
                {
                    "name": "User",
                    "file": "models/user.py",
                    "fields": ["id", "email", "name"],
                },
            ],
            "conventions": {
                "naming": "snake_case",
                "testing": "pytest",
            },
            "tech_stack": ["python", "fastapi", "postgresql"],
            "explored_files": ["main.py", "models.py"],
        }
        result = evaluator.evaluate(context)
        assert result.passed is True
        assert result.score >= 0.7

    def test_missing_project_type_fails(self, evaluator):
        """Missing project_type should reduce score."""
        context = {
            "structure": {"directories": ["src"]},
            "existing_models": [{"name": "User", "fields": ["id"]}],
            "conventions": {"naming": "snake_case"},
            "tech_stack": ["python"],
            "explored_files": ["main.py"],
        }
        result = evaluator.evaluate(context)
        assert (
            "has_project_type" not in result.details
            or result.details["has_project_type"] is False
        )

    def test_incomplete_models_generate_warning(self, evaluator):
        """Models without fields should generate a warning."""
        context = {
            "project_type": "web_app",
            "structure": {"directories": ["src"]},
            "existing_models": [{"name": "User"}],  # No fields
            "conventions": {"naming": "snake_case"},
            "tech_stack": ["python"],
            "explored_files": ["main.py"],
        }
        result = evaluator.evaluate(context)
        # Should have warning about incomplete models
        assert result.details.get("models_complete") is False


class TestRequirementEvaluator:
    """Tests for RequirementEvaluator."""

    @pytest.fixture
    def evaluator(self):
        return RequirementEvaluator()

    def test_empty_requirements_fails(self, evaluator):
        """Empty requirements should fail."""
        result = evaluator.evaluate(None)
        assert result.passed is False
        assert "No requirements" in result.failures[0]

    def test_valid_ears_requirements(self, evaluator):
        """Valid EARS format requirements should pass."""
        requirements = [
            {
                "title": "User Authentication",
                "condition": "WHEN a user provides valid credentials",
                "action": "THE SYSTEM SHALL authenticate the user and create a session",
                "criteria": [
                    "System should return a JWT token on successful login",
                    "System must reject invalid credentials with 401 error",
                    "Session should expire after 24 hours",
                ],
                "priority": "high",
            },
            {
                "title": "User Registration",
                "condition": "WHEN a new user submits registration form",
                "action": "THE SYSTEM SHALL create a new user account",
                "criteria": [
                    "Email validation should pass before account creation",
                    "Password must be hashed before storing",
                ],
                "priority": "high",
            },
        ]
        result = evaluator.evaluate(requirements)
        assert result.passed is True
        assert result.score >= 0.7

    def test_missing_ears_condition_fails(self, evaluator):
        """Requirements without WHEN condition should fail EARS check."""
        requirements = [
            {
                "title": "User Auth",
                "condition": "A user logs in",  # Missing WHEN
                "action": "Create session",
                "criteria": ["Should work", "Must be fast"],
                "priority": "high",
            },
        ]
        result = evaluator.evaluate(requirements)
        assert result.details.get("ears_format") is False
        assert "EARS format" in (result.feedback_for_retry or "")

    def test_insufficient_criteria_fails(self, evaluator):
        """Requirements with less than 2 criteria should fail."""
        requirements = [
            {
                "title": "User Auth",
                "condition": "WHEN user logs in",
                "action": "Create session",
                "criteria": ["Only one criterion"],
                "priority": "high",
            },
        ]
        result = evaluator.evaluate(requirements)
        assert result.details.get("has_criteria") is False

    def test_dict_format_requirements(self, evaluator):
        """RequirementsOutput dict format should work."""
        requirements = {
            "requirements": [
                {
                    "title": "Test Req",
                    "condition": "WHEN something happens",
                    "action": "THE SYSTEM SHALL do something",
                    "criteria": ["Should work", "Must validate"],
                    "priority": "medium",
                },
            ]
        }
        result = evaluator.evaluate(requirements)
        assert result.passed is True


class TestDesignEvaluator:
    """Tests for DesignEvaluator."""

    @pytest.fixture
    def evaluator(self):
        return DesignEvaluator()

    def test_empty_design_fails(self, evaluator):
        """Empty design should fail."""
        result = evaluator.evaluate(None)
        assert result.passed is False
        assert "No design provided" in result.failures

    def test_valid_design(self, evaluator):
        """Valid complete design should pass."""
        design = {
            "architecture": (
                "The system uses a layered architecture with FastAPI for the API layer, "
                "SQLAlchemy for ORM, and PostgreSQL for persistence. The frontend is a "
                "React SPA that communicates via REST API."
            ),
            "data_models": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "UUID", "primary_key": True},
                        {"name": "email", "type": "String"},
                        {"name": "password_hash", "type": "String"},
                    ],
                },
            ],
            "api_endpoints": [
                {
                    "method": "POST",
                    "path": "/api/v1/auth/login",
                    "description": "Authenticate user and return JWT token",
                },
                {
                    "method": "GET",
                    "path": "/api/v1/users/me",
                    "description": "Get current user profile",
                },
            ],
            "error_handling": (
                "All errors return consistent JSON format with error code and message. "
                "Database errors are caught and logged, returning 500 to client."
            ),
        }
        result = evaluator.evaluate(design)
        assert result.passed is True
        assert result.score >= 0.7

    def test_brief_architecture_fails(self, evaluator):
        """Architecture that's too brief should fail."""
        design = {
            "architecture": "Use FastAPI",  # Too short
            "data_models": [{"name": "User", "fields": [{"name": "id"}]}],
            "api_endpoints": [
                {"method": "GET", "path": "/api/test", "description": "Test endpoint"},
            ],
        }
        result = evaluator.evaluate(design)
        assert result.details.get("architecture_substantive") is False
        assert "Architecture description is too brief" in (
            result.feedback_for_retry or ""
        )

    def test_incomplete_endpoints_fails(self, evaluator):
        """Endpoints missing required fields should fail."""
        design = {
            "architecture": "A" * 150,  # Long enough
            "data_models": [{"name": "User", "fields": [{"name": "id"}]}],
            "api_endpoints": [
                {"method": "GET", "path": "/api/test"},  # Missing description
            ],
        }
        result = evaluator.evaluate(design)
        assert result.details.get("endpoints_complete") is False

    def test_invalid_http_method_fails(self, evaluator):
        """Invalid HTTP methods should be flagged."""
        design = {
            "architecture": "A" * 150,
            "data_models": [{"name": "User", "fields": [{"name": "id"}]}],
            "api_endpoints": [
                {
                    "method": "FETCH",
                    "path": "/api/test",
                    "description": "Test",
                },  # Invalid
            ],
        }
        result = evaluator.evaluate(design)
        assert result.details.get("valid_methods") is False

    def test_missing_optional_fields_generates_warnings(self, evaluator):
        """Missing optional fields should generate warnings."""
        design = {
            "architecture": "A" * 150,
            "data_models": [{"name": "User", "fields": [{"name": "id"}]}],
            "api_endpoints": [
                {"method": "GET", "path": "/api/test", "description": "Test"},
            ],
        }
        result = evaluator.evaluate(design)
        # Should have warnings for missing error_handling, security, testing
        assert len(result.warnings) > 0


class TestTaskEvaluator:
    """Tests for TaskEvaluator."""

    @pytest.fixture
    def evaluator(self):
        return TaskEvaluator()

    def test_empty_tasks_fails(self, evaluator):
        """Empty task list should fail."""
        result = evaluator.evaluate(None)
        assert result.passed is False
        assert "No tasks" in result.failures[0]

    def test_valid_tasks(self, evaluator):
        """Valid tasks should pass."""
        tasks = [
            {
                "id": "task-1",
                "title": "Implement User Model",
                "description": "Create SQLAlchemy User model with fields",
                "phase": "backend",
                "priority": "high",
                "dependencies": [],
                "acceptance_criteria": ["Model created", "Fields match spec"],
            },
            {
                "id": "task-2",
                "title": "Create Auth Endpoints",
                "description": "Implement login/logout endpoints",
                "phase": "backend",
                "priority": "high",
                "dependencies": ["task-1"],
                "acceptance_criteria": ["Login works", "JWT returned"],
            },
        ]
        result = evaluator.evaluate(tasks)
        assert result.passed is True
        assert result.score >= 0.7

    def test_invalid_priority_fails(self, evaluator):
        """Invalid priority should fail check."""
        tasks = [
            {
                "title": "Test Task",
                "description": "Test description",
                "phase": "backend",
                "priority": "super_important",  # Invalid
                "acceptance_criteria": ["Done"],
            },
        ]
        result = evaluator.evaluate(tasks)
        assert result.details.get("valid_priorities") is False

    def test_invalid_phase_generates_warning(self, evaluator):
        """Invalid phase should generate warning."""
        tasks = [
            {
                "title": "Test Task",
                "description": "Test",
                "phase": "unknown_phase",  # Invalid
                "priority": "high",
                "acceptance_criteria": ["Done"],
            },
        ]
        result = evaluator.evaluate(tasks)
        assert result.details.get("valid_phases") is False
        # Should have warning about valid phases
        assert any("phases" in w.lower() for w in result.warnings)

    def test_duplicate_titles_fails(self, evaluator):
        """Duplicate task titles should fail."""
        tasks = [
            {
                "title": "Same Title",
                "description": "Task 1",
                "phase": "backend",
                "priority": "high",
                "acceptance_criteria": ["Done"],
            },
            {
                "title": "Same Title",  # Duplicate
                "description": "Task 2",
                "phase": "backend",
                "priority": "medium",
                "acceptance_criteria": ["Done"],
            },
        ]
        result = evaluator.evaluate(tasks)
        assert result.details.get("no_duplicates") is False

    def test_invalid_dependency_fails(self, evaluator):
        """Dependencies referencing non-existent tasks should fail."""
        tasks = [
            {
                "id": "task-1",
                "title": "Task One",
                "description": "Description",
                "phase": "backend",
                "priority": "high",
                "dependencies": ["non-existent-task"],  # Invalid reference
                "acceptance_criteria": ["Done"],
            },
        ]
        result = evaluator.evaluate(tasks)
        assert result.details.get("valid_dependencies") is False
        assert "dependencies reference non-existent" in (
            result.feedback_for_retry or ""
        )

    def test_circular_dependency_fails(self, evaluator):
        """Circular dependencies should fail."""
        tasks = [
            {
                "id": "task-1",
                "title": "Task One",
                "description": "Description",
                "phase": "backend",
                "priority": "high",
                "dependencies": ["task-2"],
                "acceptance_criteria": ["Done"],
            },
            {
                "id": "task-2",
                "title": "Task Two",
                "description": "Description",
                "phase": "backend",
                "priority": "high",
                "dependencies": ["task-1"],  # Circular!
                "acceptance_criteria": ["Done"],
            },
        ]
        result = evaluator.evaluate(tasks)
        assert result.details.get("no_circular_deps") is False
        assert "Circular dependencies" in (result.feedback_for_retry or "")

    def test_self_dependency_fails(self, evaluator):
        """Task depending on itself should fail."""
        tasks = [
            {
                "id": "task-1",
                "title": "Task One",
                "description": "Description",
                "phase": "backend",
                "priority": "high",
                "dependencies": ["task-1"],  # Self-reference!
                "acceptance_criteria": ["Done"],
            },
        ]
        result = evaluator.evaluate(tasks)
        assert result.details.get("no_self_dependencies") is False

    def test_tasks_output_format(self, evaluator):
        """TasksOutput format with tickets should work."""
        tasks_output = {
            "tickets": [
                {
                    "title": "Ticket 1",
                    "tasks": [
                        {
                            "id": "task-1",
                            "title": "Task One",
                            "description": "Description",
                            "phase": "backend",
                            "priority": "high",
                            "dependencies": [],
                            "acceptance_criteria": ["Done"],
                        },
                    ],
                },
            ]
        }
        result = evaluator.evaluate(tasks_output)
        assert result.passed is True

    def test_transitive_circular_dependency_fails(self, evaluator):
        """Transitive circular dependencies (A->B->C->A) should fail."""
        tasks = [
            {
                "id": "task-1",
                "title": "Task One",
                "description": "D",
                "phase": "backend",
                "priority": "high",
                "dependencies": ["task-2"],
                "acceptance_criteria": ["Done"],
            },
            {
                "id": "task-2",
                "title": "Task Two",
                "description": "D",
                "phase": "backend",
                "priority": "high",
                "dependencies": ["task-3"],
                "acceptance_criteria": ["Done"],
            },
            {
                "id": "task-3",
                "title": "Task Three",
                "description": "D",
                "phase": "backend",
                "priority": "high",
                "dependencies": ["task-1"],  # Creates cycle: 1->2->3->1
                "acceptance_criteria": ["Done"],
            },
        ]
        result = evaluator.evaluate(tasks)
        assert result.details.get("no_circular_deps") is False


class TestBaseEvaluator:
    """Tests for BaseEvaluator helper methods."""

    def test_make_result_all_pass(self):
        """All passing checks should result in score 1.0."""
        evaluator = ExplorationEvaluator()
        checks = [
            ("check_1", True),
            ("check_2", True),
            ("check_3", True),
        ]
        result = evaluator._make_result(checks)
        assert result.passed is True
        assert result.score == 1.0
        assert len(result.failures) == 0

    def test_make_result_some_fail(self):
        """Some failing checks should reduce score."""
        evaluator = ExplorationEvaluator()
        checks = [
            ("check_1", True),
            ("check_2", False),
            ("check_3", True),
        ]
        result = evaluator._make_result(checks)
        # 2/3 passed = 0.666..., below 0.7 threshold
        assert result.passed is False
        assert abs(result.score - (2 / 3)) < 0.01
        # Failure message includes the check name in a human-readable format
        assert any(
            "check_2" in f.lower() or "check 2" in f.lower() for f in result.failures
        )

    def test_custom_min_score(self):
        """Custom min_score threshold should be respected."""
        evaluator = ExplorationEvaluator()
        evaluator.min_score = 0.5  # Lower threshold
        checks = [
            ("check_1", True),
            ("check_2", False),
            ("check_3", True),
        ]
        result = evaluator._make_result(checks)
        # 2/3 = 0.666, above 0.5 threshold BUT has failures, so passed=False
        # The _make_result condition is: score >= min_score AND len(failures) == 0
        # Since check_2 failed, passed will be False regardless of score
        assert result.passed is False
        # But if all pass:
        all_pass_checks = [
            ("check_1", True),
            ("check_2", True),
            ("check_3", True),
        ]
        result_all_pass = evaluator._make_result(all_pass_checks)
        # Now it should pass since score=1.0 >= 0.5 and no failures
        assert result_all_pass.passed is True
