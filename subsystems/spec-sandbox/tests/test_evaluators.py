"""Tests for phase evaluators."""

import pytest

from spec_sandbox.evaluators.phases import (
    PRDEvaluator,
    ExploreEvaluator,
    RequirementsEvaluator,
    DesignEvaluator,
    TasksEvaluator,
    SyncEvaluator,
    get_evaluator,
)
from spec_sandbox.schemas.spec import SpecPhase


class TestGetEvaluator:
    """Tests for evaluator factory function."""

    def test_returns_correct_evaluator_for_each_phase(self):
        """Should return the correct evaluator type for each phase."""
        assert isinstance(get_evaluator("explore"), ExploreEvaluator)
        assert isinstance(get_evaluator("prd"), PRDEvaluator)
        assert isinstance(get_evaluator("requirements"), RequirementsEvaluator)
        assert isinstance(get_evaluator("design"), DesignEvaluator)
        assert isinstance(get_evaluator("tasks"), TasksEvaluator)
        assert isinstance(get_evaluator("sync"), SyncEvaluator)

    def test_raises_for_unknown_phase(self):
        """Should raise ValueError for unknown phase."""
        with pytest.raises(ValueError, match="Unknown phase"):
            get_evaluator("unknown_phase")


class TestPRDEvaluator:
    """Tests for PRD phase evaluator."""

    @pytest.fixture
    def evaluator(self):
        return PRDEvaluator()

    @pytest.fixture
    def valid_prd_output(self):
        """Complete valid PRD output that should pass evaluation."""
        return {
            "overview": {
                "feature_name": "webhook-notifications",
                "one_liner": "Enable real-time event notifications via webhooks",
                "problem_statement": "Users need real-time updates when events occur",
                "solution_summary": "Implement a webhook delivery system with retry logic",
            },
            "goals": {
                "primary": ["Enable real-time event delivery"],
                "secondary": ["Reduce API polling load"],
                "success_metrics": [
                    {
                        "metric": "Delivery success rate",
                        "target": ">99%",
                        "measurement": "Successful/Total deliveries",
                    }
                ],
            },
            "users": {
                "primary": [
                    {
                        "role": "Integration Developer",
                        "description": "Builds integrations with our platform",
                        "needs": ["Real-time notifications", "Reliable delivery"],
                    }
                ],
                "secondary": [
                    {
                        "role": "Platform Admin",
                        "description": "Manages webhook configurations",
                        "needs": ["Monitor delivery health"],
                    }
                ],
            },
            "user_stories": [
                {
                    "id": "US-001",
                    "role": "Integration Developer",
                    "want": "register a webhook endpoint",
                    "benefit": "receive real-time event notifications",
                    "priority": "must",
                    "acceptance_criteria": [
                        "Can specify endpoint URL",
                        "Can select event types",
                        "Webhook is validated",
                    ],
                },
                {
                    "id": "US-002",
                    "role": "Integration Developer",
                    "want": "receive events in consistent format",
                    "benefit": "parse all events with same code",
                    "priority": "must",
                    "acceptance_criteria": [
                        "Events have timestamp",
                        "Events have event_type",
                    ],
                },
            ],
            "scope": {
                "in_scope": ["Webhook registration", "Event delivery", "Retry logic"],
                "out_of_scope": ["Mobile notifications", "Email notifications"],
                "dependencies": ["EventBusService", "PostgreSQL"],
            },
            "assumptions": [
                "External endpoints respond within 30 seconds",
                "Event volume under 10,000/minute initially",
            ],
            "constraints": {
                "technical": ["Must use existing EventBusService", "Must use PostgreSQL"],
                "business": ["Must launch Q1", "Cannot break existing APIs"],
            },
            "risks": [
                {
                    "description": "Webhook endpoints are slow",
                    "impact": "high",
                    "mitigation": "Implement timeouts and circuit breaker",
                },
                {
                    "description": "Event volume exceeds capacity",
                    "impact": "medium",
                    "mitigation": "Design for horizontal scaling",
                },
            ],
            "open_questions": [
                "Should we support webhook batching?",
                "What's the maximum payload size?",
            ],
        }

    @pytest.mark.asyncio
    async def test_valid_prd_passes_evaluation(self, evaluator, valid_prd_output):
        """Valid PRD output should pass evaluation with high score."""
        result = await evaluator.evaluate(valid_prd_output, {})

        assert result.passed is True
        assert result.score >= 0.7
        assert result.feedback is None or result.feedback == ""

    @pytest.mark.asyncio
    async def test_missing_overview_fails(self, evaluator):
        """PRD without overview should fail."""
        output = {
            "goals": {"primary": [], "secondary": [], "success_metrics": []},
            "users": {"primary": [], "secondary": []},
            "user_stories": [],
            "scope": {"in_scope": [], "out_of_scope": [], "dependencies": []},
        }

        result = await evaluator.evaluate(output, {})
        assert result.passed is False
        # Check feedback or details mention missing overview
        assert result.details.get("overview", 1.0) < 1.0

    @pytest.mark.asyncio
    async def test_missing_goals_reduces_score(self, evaluator, valid_prd_output):
        """PRD without goals should reduce score (but may still pass if rest is complete)."""
        del valid_prd_output["goals"]

        result = await evaluator.evaluate(valid_prd_output, {})
        # goals detail key should show 0 score
        assert "goals" in result.details
        assert result.details["goals"] == 0.0
        # Overall score should be reduced
        assert result.score < 1.0

    @pytest.mark.asyncio
    async def test_missing_user_stories_fails(self, evaluator, valid_prd_output):
        """PRD without user stories should fail."""
        valid_prd_output["user_stories"] = []

        result = await evaluator.evaluate(valid_prd_output, {})
        assert result.passed is False
        # user_stories_structure should be 0 when empty
        assert result.details.get("user_stories_structure", 1.0) == 0.0

    @pytest.mark.asyncio
    async def test_user_story_missing_id_reduces_score(self, evaluator, valid_prd_output):
        """User stories without proper IDs should reduce score."""
        valid_prd_output["user_stories"] = [
            {
                "id": "story-1",  # Invalid format - should be US-NNN
                "role": "User",
                "want": "do something",
                "benefit": "achieve goal",
                "priority": "must",
                "acceptance_criteria": ["Works"],
            }
        ]

        result = await evaluator.evaluate(valid_prd_output, {})
        # Should still have some issues or lower score
        assert result.score < 1.0

    @pytest.mark.asyncio
    async def test_user_story_with_valid_id_format(self, evaluator, valid_prd_output):
        """User stories with US-NNN format should be valid."""
        valid_prd_output["user_stories"] = [
            {
                "id": "US-001",
                "role": "User",
                "want": "do something",
                "benefit": "achieve goal",
                "priority": "must",
                "acceptance_criteria": ["Works"],
            }
        ]

        result = await evaluator.evaluate(valid_prd_output, {})
        # Should have valid ID format (full score for user_stories_id_format)
        assert result.details.get("user_stories_id_format", 0.0) == 1.0

    @pytest.mark.asyncio
    async def test_missing_scope_reduces_score(self, evaluator, valid_prd_output):
        """PRD without scope should reduce score (but may still pass if rest is complete)."""
        del valid_prd_output["scope"]

        result = await evaluator.evaluate(valid_prd_output, {})
        # scope detail key should show reduced score
        assert "scope" in result.details
        assert result.details["scope"] < 1.0
        # Overall score should be reduced
        assert result.score < 1.0

    @pytest.mark.asyncio
    async def test_empty_output_fails(self, evaluator):
        """Empty output should fail evaluation."""
        result = await evaluator.evaluate({}, {})

        assert result.passed is False
        assert result.score < 0.5

    @pytest.mark.asyncio
    async def test_partial_output_has_reduced_score(self, evaluator):
        """Partial output should have reduced score but provide feedback."""
        output = {
            "overview": {
                "feature_name": "test",
                "one_liner": "A test",
                "problem_statement": "Problem",
                "solution_summary": "Solution",
            },
            "goals": {"primary": ["Goal 1"], "secondary": [], "success_metrics": []},
            # Missing users, user_stories, scope, etc.
        }

        result = await evaluator.evaluate(output, {})
        # Should have reduced score due to missing sections
        assert result.score < 0.7
        assert result.passed is False


class TestExploreEvaluator:
    """Tests for EXPLORE phase evaluator."""

    @pytest.fixture
    def evaluator(self):
        return ExploreEvaluator()

    @pytest.mark.asyncio
    async def test_valid_explore_output_passes(self, evaluator):
        """Valid explore output should pass."""
        output = {
            "codebase_summary": "A Python web application using FastAPI with modern patterns and comprehensive testing",
            "project_type": "web_application",
            "tech_stack": ["Python", "FastAPI", "PostgreSQL"],
            "key_files": [
                {"path": "src/main.py", "purpose": "Entry point"},
                {"path": "src/api/routes.py", "purpose": "API routes"},
                {"path": "src/services/core.py", "purpose": "Core services"},
            ],
            "relevant_patterns": [{"pattern": "Repository", "description": "Data access"}],
            "entry_points": ["src/main.py"],
            "test_structure": "pytest in tests/",
            "structure": {"api": ["src/api/"], "services": ["src/services/"]},
            "discovery_questions": {
                "problem_value": ["What problem does this solve?"],
                "users_journeys": ["Who uses this?"],
                "scope_boundaries": ["What is out of scope?"],
                "technical_context": ["What systems to integrate?"],
                "risks_tradeoffs": ["What are the risks?"],
            },
            "feature_summary": {
                "name": "feature",
                "scope_in": ["A"],
                "scope_out": ["B"],
            },
            "conventions": {
                "naming": "snake_case",
                "testing": "pytest",
                "patterns": ["Repository"],
            },
        }

        result = await evaluator.evaluate(output, {})
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_missing_codebase_summary_fails(self, evaluator):
        """Explore without codebase_summary should fail."""
        output = {"tech_stack": ["Python"]}

        result = await evaluator.evaluate(output, {})
        assert result.passed is False


class TestRequirementsEvaluator:
    """Tests for REQUIREMENTS phase evaluator."""

    @pytest.fixture
    def evaluator(self):
        return RequirementsEvaluator()

    @pytest.mark.asyncio
    async def test_valid_requirements_output_passes(self, evaluator):
        """Valid requirements output should pass."""
        output = {
            "requirements": [
                {
                    "id": "REQ-FEAT-FUNC-001",
                    "type": "functional",
                    "category": "Core",
                    "text": "THE SYSTEM SHALL validate user input data before processing to ensure data integrity",
                    "priority": "must",
                    "acceptance_criteria": ["Input validated according to schema", "Invalid input rejected with error message"],
                    "rationale": "Ensures data integrity and system reliability",
                },
                {
                    "id": "REQ-FEAT-FUNC-002",
                    "type": "functional",
                    "category": "Core",
                    "text": "THE SYSTEM SHALL log all authentication attempts for security auditing",
                    "priority": "must",
                    "acceptance_criteria": ["Auth attempts logged", "Log includes timestamp and result"],
                    "rationale": "Required for security compliance",
                },
            ],
            "assumptions": ["Users have valid authentication credentials", "Network connectivity is available"],
            "traceability": {
                "REQ-FEAT-FUNC-001": {"source": "PRD", "user_stories": ["US-001"]},
                "REQ-FEAT-FUNC-002": {"source": "PRD", "user_stories": ["US-002"]},
            },
            "dependencies": ["Authentication service must be available"],
        }

        result = await evaluator.evaluate(output, {})
        # Should pass with score >= 0.7
        assert result.score >= 0.7
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_empty_requirements_fails(self, evaluator):
        """Empty requirements list should fail."""
        output = {"requirements": []}

        result = await evaluator.evaluate(output, {})
        assert result.passed is False


class TestDesignEvaluator:
    """Tests for DESIGN phase evaluator."""

    @pytest.fixture
    def evaluator(self):
        return DesignEvaluator()

    @pytest.mark.asyncio
    async def test_valid_design_output_passes(self, evaluator):
        """Valid design output should pass."""
        output = {
            "feature_name": "webhook-notifications",
            "architecture_overview": "Layered architecture with API gateway, service layer for business logic, and PostgreSQL data layer for persistent storage. The system follows microservices principles with clear boundaries.",
            "components": [
                {
                    "name": "WebhookService",
                    "type": "service",
                    "responsibility": "Handle webhook delivery with retry logic and circuit breaker pattern",
                    "interfaces": [
                        {
                            "method": "deliver",
                            "inputs": {"webhook_id": "uuid", "payload": "dict"},
                            "outputs": {"success": "bool", "delivery_id": "uuid"},
                        }
                    ],
                    "dependencies": ["DatabaseService", "HttpClient"],
                }
            ],
            "data_models": [
                {
                    "name": "Webhook",
                    "table_name": "webhooks",
                    "fields": {"id": "uuid", "url": "string", "events": "list[string]", "created_at": "datetime"},
                    "indexes": ["id", "created_at"],
                }
            ],
            "api_endpoints": [
                {
                    "method": "POST",
                    "path": "/webhooks",
                    "purpose": "Create a new webhook subscription",
                    "auth_required": True,
                    "response_schema": {"id": "uuid", "url": "string", "events": "list"},
                }
            ],
            "testing_strategy": "Unit tests for service logic, integration tests for API endpoints, and contract tests for webhook delivery",
            "error_handling": "Circuit breaker pattern for external calls with exponential backoff retry",
            "security_considerations": ["Webhook signature verification", "Rate limiting per client", "URL validation"],
            "integration_points": ["EventBus for event subscription", "PostgreSQL for persistence"],
        }

        result = await evaluator.evaluate(output, {})
        # Should pass with score >= 0.7
        assert result.score >= 0.7
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_missing_architecture_overview_fails(self, evaluator):
        """Design without architecture_overview should fail."""
        output = {"components": []}

        result = await evaluator.evaluate(output, {})
        assert result.passed is False


class TestTasksEvaluator:
    """Tests for TASKS phase evaluator."""

    @pytest.fixture
    def evaluator(self):
        return TasksEvaluator()

    @pytest.mark.asyncio
    async def test_valid_tasks_output_passes(self, evaluator):
        """Valid tasks output should pass."""
        output = {
            "tickets": [
                {
                    "id": "TKT-001",
                    "title": "Implement webhooks",
                    "tasks": ["TSK-001"],
                }
            ],
            "tasks": [
                {
                    "id": "TSK-001",
                    "title": "Create webhook model",
                    "description": "Define SQLAlchemy model",
                    "type": "implementation",
                    "parent_ticket": "TKT-001",
                    "estimated_hours": 2,
                    "acceptance_criteria": ["Model created"],
                }
            ],
            "total_estimated_hours": 2,
            "critical_path": ["TSK-001"],
        }

        result = await evaluator.evaluate(output, {})
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_empty_tasks_fails(self, evaluator):
        """Empty tasks list should fail."""
        output = {"tasks": [], "total_estimated_hours": 0}

        result = await evaluator.evaluate(output, {})
        assert result.passed is False


class TestSyncEvaluator:
    """Tests for SYNC phase evaluator."""

    @pytest.fixture
    def evaluator(self):
        return SyncEvaluator()

    @pytest.mark.asyncio
    async def test_valid_sync_output_passes(self, evaluator):
        """Valid sync output should pass."""
        output = {
            "validation_results": {
                "all_requirements_covered": True,
                "all_components_have_tasks": True,
                "dependency_order_valid": True,
            },
            "coverage_matrix": [
                {"requirement_id": "REQ-001", "covered_by_tasks": ["TSK-001"], "status": "fully_covered"}
            ],
            "traceability_stats": {
                "requirements": {"total": 1, "linked": 1, "coverage": 100.0},
                "tasks": {"total": 1, "done": 0, "in_progress": 0, "pending": 1},
            },
            "dependency_analysis": {
                "task_dependencies": {"TSK-001": []},
                "task_dependency_graph": {"nodes": ["TSK-001"], "edges": []},
                "critical_path": ["TSK-001"],
                "blocking_tasks": [],
                "parallel_groups": [["TSK-001"]],
            },
            "spec_summary": {
                "total_requirements": 1,
                "total_tasks": 1,
                "requirement_coverage_percent": 100.0,
            },
            "ready_for_execution": True,
            "recommendations": ["Start with TSK-001 as it has no dependencies"],
        }

        result = await evaluator.evaluate(output, {})
        # Should pass with score >= 0.7
        assert result.score >= 0.7
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_not_ready_for_execution_fails(self, evaluator):
        """Sync with ready_for_execution=False should fail."""
        output = {
            "validation_results": {"all_requirements_covered": False},
            "coverage_matrix": [],
            "spec_summary": {},
            "ready_for_execution": False,
            "blockers": ["Requirements not covered"],
        }

        result = await evaluator.evaluate(output, {})
        assert result.passed is False
