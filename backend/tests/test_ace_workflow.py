"""Tests for ACE workflow (REQ-MEM-ACE-001, REQ-MEM-ACE-002, REQ-MEM-ACE-003, REQ-MEM-ACE-004)."""

import pytest
from unittest.mock import Mock

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.models.task_memory import TaskMemory
from omoi_os.models.playbook_entry import PlaybookEntry
from omoi_os.models.memory_type import MemoryType
from omoi_os.services.ace_executor import Executor, ExecutorResult
from omoi_os.services.ace_reflector import Reflector, ReflectorResult, Insight
from omoi_os.services.ace_curator import Curator, DeltaOperation, PlaybookDelta
from omoi_os.services.ace_engine import ACEEngine, ACEResult
from omoi_os.services.memory import MemoryService
from omoi_os.services.embedding import EmbeddingService
from omoi_os.services.event_bus import EventBusService
from omoi_os.utils.datetime import utc_now


@pytest.fixture
def embedding_service():
    """Embedding service for tests."""
    from omoi_os.services.embedding import EmbeddingProvider

    return EmbeddingService(provider=EmbeddingProvider.LOCAL)


@pytest.fixture
def memory_service(embedding_service):
    """Memory service for testing."""
    return MemoryService(embedding_service=embedding_service, event_bus=None)


@pytest.fixture
def event_bus_service():
    """Mock event bus service."""
    return Mock(spec=EventBusService)


@pytest.fixture
def test_ticket(db_service):
    """Create a test ticket."""
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Ticket",
            description="Test description",
            phase_id="PHASE_IMPLEMENTATION",
            status="backlog",
            priority="MEDIUM",
        )
        session.add(ticket)
        session.commit()
        session.refresh(ticket)
        ticket_id = ticket.id
        session.expunge(ticket)
    return ticket_id


@pytest.fixture
def test_task(db_service, test_ticket):
    """Create a test task."""
    with db_service.get_session() as session:
        task = Task(
            ticket_id=test_ticket,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Implement user authentication",
            priority="MEDIUM",
            status="completed",
        )
        session.add(task)
        session.commit()
        session.refresh(task)
        task_id = task.id
        session.expunge(task)
    return task_id


class TestExecutor:
    """Tests for Executor service (REQ-MEM-ACE-001)."""

    def test_execute_creates_memory(
        self, db_service, memory_service, embedding_service, test_task
    ):
        """Test that Executor creates memory record (REQ-MEM-ACE-001)."""
        executor = Executor(memory_service, embedding_service)

        goal = "Implement user authentication with JWT tokens"
        result = "Successfully implemented JWT authentication middleware"
        tool_usage = [
            {"tool_name": "file_read", "arguments": {"path": "src/auth.py"}},
            {"tool_name": "file_edit", "arguments": {"path": "src/auth.py"}},
        ]
        feedback = "Tests passed: 15/15"

        with db_service.get_session() as session:
            result_obj = executor.execute(
                session=session,
                task_id=test_task,
                goal=goal,
                result=result,
                tool_usage=tool_usage,
                feedback=feedback,
            )
            session.commit()

            # Verify memory was created
            memory = session.get(TaskMemory, result_obj.memory_id)
            assert memory is not None
            assert memory.goal == goal
            assert memory.result == result
            assert memory.feedback == feedback
            assert memory.tool_usage == {"tools": tool_usage}
            assert memory.memory_type in MemoryType.all_types()
            assert memory.context_embedding is not None
            # Note: Embedding dimensions may vary, just check it exists
            assert len(memory.context_embedding) > 0

    def test_extract_file_paths(self, memory_service, embedding_service):
        """Test file path extraction from tool usage (REQ-MEM-ACE-001)."""
        executor = Executor(memory_service, embedding_service)

        tool_usage = [
            {"tool_name": "file_read", "arguments": {"path": "src/auth.py"}},
            {"tool_name": "file_edit", "arguments": {"file_path": "src/middleware.py"}},
            {"tool_name": "file_create", "arguments": {"file": "tests/test_auth.py"}},
            {"tool_name": "bash", "arguments": {"command": "npm install"}},
        ]

        files = executor.extract_file_paths(tool_usage)
        assert "src/auth.py" in files
        assert "src/middleware.py" in files
        assert "tests/test_auth.py" in files
        assert len(files) == 3

    def test_extract_tags(self, memory_service, embedding_service):
        """Test tag extraction from goal and result."""
        executor = Executor(memory_service, embedding_service)

        goal = "Implement JWT authentication for API"
        result = "Created authentication middleware and tests"

        tags = executor.extract_tags(goal, result)
        assert "authentication" in tags or "api" in tags


class TestReflector:
    """Tests for Reflector service (REQ-MEM-ACE-002)."""

    def test_identify_errors(self, embedding_service):
        """Test error identification from feedback (REQ-MEM-ACE-002)."""
        reflector = Reflector(embedding_service)

        feedback = """
        Traceback (most recent call last):
          File "test.py", line 5, in <module>
            import nonexistent
        ImportError: No module named 'nonexistent'
        """

        errors = reflector.identify_errors(feedback)
        assert len(errors) > 0
        assert any(e.error_type == "ImportError" for e in errors)

    def test_search_playbook_entries(self, db_service, embedding_service, test_ticket):
        """Test playbook entry search (REQ-MEM-ACE-002)."""
        reflector = Reflector(embedding_service)

        # Create a playbook entry
        with db_service.get_session() as session:
            entry = PlaybookEntry(
                ticket_id=test_ticket,
                content="Always use JWT tokens for authentication",
                category="best_practices",
                embedding=embedding_service.generate_embedding(
                    "Always use JWT tokens for authentication"
                ),
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(entry)
            session.commit()
            entry_id = entry.id
            session.expunge(entry)

        # Search for related entries
        with db_service.get_session() as session:
            results = reflector.search_playbook_entries(
                session=session,
                query_text="JWT authentication patterns",
                ticket_id=test_ticket,
                limit=5,
                similarity_threshold=0.5,
            )

            assert len(results) > 0
            assert any(r.id == entry_id for r in results)

    def test_extract_insights(self, embedding_service):
        """Test insight extraction (REQ-MEM-ACE-002)."""
        reflector = Reflector(embedding_service)

        goal = "Implement authentication"
        result = "Successfully implemented JWT middleware"
        feedback = "Make sure to always validate token expiration. Best practice: use middleware for JWT validation. Watch out for token leakage in logs."

        insights = reflector.extract_insights(goal, result, feedback)
        assert len(insights) > 0
        assert any(i.insight_type == "pattern" for i in insights)
        assert any(i.insight_type == "best_practice" for i in insights)
        assert any(i.insight_type == "gotcha" for i in insights)

    def test_analyze_tags_playbook_entries(
        self, db_service, embedding_service, test_ticket, test_task
    ):
        """Test that analyze tags related playbook entries (REQ-MEM-ACE-002)."""
        reflector = Reflector(embedding_service)

        # Create executor result
        executor_result = ExecutorResult(
            memory_id="test-memory-123",
            memory_type=MemoryType.DISCOVERY.value,
            files_linked=["src/auth.py"],
            tags=["authentication"],
        )

        # Create a playbook entry
        with db_service.get_session() as session:
            entry = PlaybookEntry(
                ticket_id=test_ticket,
                content="Always use JWT tokens for authentication",
                category="best_practices",
                embedding=embedding_service.generate_embedding(
                    "Always use JWT tokens for authentication"
                ),
                supporting_memory_ids=[],
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(entry)
            session.commit()
            entry_id = entry.id
            session.expunge(entry)

        # Analyze and tag
        with db_service.get_session() as session:
            result = reflector.analyze(
                session=session,
                executor_result=executor_result,
                memory_id="test-memory-123",
                feedback="Tests passed",
                ticket_id=test_ticket,
                goal="Implement authentication",
                result="Successfully implemented JWT",
            )
            session.commit()

            # Verify entry was tagged
            entry = session.get(PlaybookEntry, entry_id)
            assert "test-memory-123" in (entry.supporting_memory_ids or [])
            assert entry_id in result.tags_added


class TestCurator:
    """Tests for Curator service (REQ-MEM-ACE-003)."""

    def test_curate_creates_playbook_entry(
        self, db_service, embedding_service, test_ticket
    ):
        """Test that Curator creates playbook entries (REQ-MEM-ACE-003)."""
        curator = Curator(embedding_service)

        executor_result = ExecutorResult(
            memory_id="test-memory-123",
            memory_type=MemoryType.DISCOVERY.value,
            files_linked=["src/auth.py"],
            tags=["authentication"],
        )

        reflector_result = ReflectorResult(
            tags_added=[],
            insights_found=[
                Insight(
                    insight_type="best_practice",
                    content="Always validate JWT token expiration",
                    confidence=0.8,
                )
            ],
            errors_identified=[],
            related_playbook_entries=[],
        )

        with db_service.get_session() as session:
            result = curator.curate(
                session=session,
                executor_result=executor_result,
                reflector_result=reflector_result,
                ticket_id=test_ticket,
                memory_id="test-memory-123",
                agent_id="test-agent",
            )
            session.commit()

            # Verify playbook entry was created
            assert result.change_id is not None
            assert len(result.updated_bullets) > 0

            entry_id = result.updated_bullets[0].id
            entry = session.get(PlaybookEntry, entry_id)
            assert entry is not None
            assert "JWT" in entry.content
            assert entry.supporting_memory_ids == ["test-memory-123"]
            assert entry.category == "best_practices"

    def test_validate_delta_rejects_duplicates(
        self, db_service, embedding_service, test_ticket
    ):
        """Test that validate_delta rejects duplicate content (REQ-MEM-ACE-003)."""
        curator = Curator(embedding_service)

        # Create existing playbook entry
        with db_service.get_session() as session:
            existing = PlaybookEntry(
                ticket_id=test_ticket,
                content="Always validate JWT token expiration",
                category="best_practices",
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(existing)
            session.commit()
            existing_content = existing.content
            session.expunge(existing)

        # Try to add duplicate
        delta = PlaybookDelta(
            operations=[
                DeltaOperation(
                    operation="add",
                    content=existing_content,  # Duplicate content
                    category="best_practices",
                )
            ],
            summary="Test delta",
        )

        with db_service.get_session() as session:
            current_playbook = (
                session.query(PlaybookEntry)
                .filter(
                    PlaybookEntry.ticket_id == test_ticket,
                    PlaybookEntry.is_active == True,  # noqa: E712
                )
                .all()
            )

            is_valid = curator.validate_delta(delta, current_playbook)
            assert not is_valid  # Should reject duplicate

    def test_search_playbook_for_similar(
        self, db_service, embedding_service, test_ticket
    ):
        """Test playbook similarity search (REQ-MEM-ACE-003)."""
        curator = Curator(embedding_service)

        # Create playbook entry
        with db_service.get_session() as session:
            entry = PlaybookEntry(
                ticket_id=test_ticket,
                content="Always validate JWT token expiration",
                category="best_practices",
                embedding=embedding_service.generate_embedding(
                    "Always validate JWT token expiration"
                ),
                is_active=True,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
            session.add(entry)
            session.commit()
            session.expunge(entry)

        # Search for similar
        with db_service.get_session() as session:
            similar = curator.search_playbook_for_similar(
                session=session,
                content="JWT token validation is important",
                ticket_id=test_ticket,
                threshold=0.5,  # Lower threshold for test
            )

            assert similar is not None
            assert "JWT" in similar.content


class TestACEEngine:
    """Tests for ACE Engine orchestrator (REQ-MEM-ACE-004)."""

    def test_execute_workflow_complete_flow(
        self,
        db_service,
        memory_service,
        embedding_service,
        event_bus_service,
        test_task,
        test_ticket,
    ):
        """Test complete ACE workflow execution (REQ-MEM-ACE-004)."""
        engine = ACEEngine(
            db=db_service,
            memory_service=memory_service,
            embedding_service=embedding_service,
            event_bus=event_bus_service,
        )

        goal = "Implement user authentication with JWT tokens"
        result = "Successfully implemented JWT authentication middleware"
        tool_usage = [
            {"tool_name": "file_read", "arguments": {"path": "src/auth.py"}},
            {"tool_name": "file_edit", "arguments": {"path": "src/auth.py"}},
        ]
        feedback = "Make sure to always validate token expiration. Best practice: use middleware for JWT validation."
        agent_id = "test-agent-123"

        result_obj = engine.execute_workflow(
            task_id=test_task,
            goal=goal,
            result=result,
            tool_usage=tool_usage,
            feedback=feedback,
            agent_id=agent_id,
        )

        # Verify result structure (REQ-MEM-ACE-004)
        assert isinstance(result_obj, ACEResult)
        assert result_obj.memory_id is not None
        assert result_obj.memory_type in MemoryType.all_types()
        assert len(result_obj.files_linked) > 0
        assert isinstance(result_obj.insights_found, list)
        assert isinstance(result_obj.errors_identified, list)
        assert isinstance(result_obj.playbook_delta, dict)
        assert "operations" in result_obj.playbook_delta

        # Verify memory was created
        with db_service.get_session() as session:
            memory = session.get(TaskMemory, result_obj.memory_id)
            assert memory is not None
            assert memory.goal == goal
            assert memory.result == result

        # Verify event was published
        event_bus_service.publish.assert_called_once()
        call_args = event_bus_service.publish.call_args[0][0]
        assert call_args.event_type == "ace.workflow.completed"
        assert call_args.entity_id == result_obj.memory_id

    def test_execute_workflow_with_errors(
        self,
        db_service,
        memory_service,
        embedding_service,
        event_bus_service,
        test_task,
    ):
        """Test ACE workflow with error feedback (REQ-MEM-ACE-002)."""
        engine = ACEEngine(
            db=db_service,
            memory_service=memory_service,
            embedding_service=embedding_service,
            event_bus=event_bus_service,
        )

        goal = "Implement authentication"
        result = "Failed to implement due to import error"
        tool_usage = []
        feedback = "ImportError: No module named 'jwt'"
        agent_id = "test-agent-123"

        result_obj = engine.execute_workflow(
            task_id=test_task,
            goal=goal,
            result=result,
            tool_usage=tool_usage,
            feedback=feedback,
            agent_id=agent_id,
        )

        # Verify errors were identified
        assert len(result_obj.errors_identified) > 0
        assert any(
            e["error_type"] == "ImportError" for e in result_obj.errors_identified
        )

    def test_execute_workflow_creates_playbook_entry(
        self,
        db_service,
        memory_service,
        embedding_service,
        event_bus_service,
        test_task,
        test_ticket,
    ):
        """Test that ACE workflow creates playbook entries from insights (REQ-MEM-ACE-003)."""
        engine = ACEEngine(
            db=db_service,
            memory_service=memory_service,
            embedding_service=embedding_service,
            event_bus=event_bus_service,
        )

        goal = "Implement authentication"
        result = "Successfully implemented JWT"
        tool_usage = []
        feedback = "Best practice: always validate JWT token expiration. Watch out for token leakage."
        agent_id = "test-agent-123"

        result_obj = engine.execute_workflow(
            task_id=test_task,
            goal=goal,
            result=result,
            tool_usage=tool_usage,
            feedback=feedback,
            agent_id=agent_id,
        )

        # Verify playbook entries were created
        assert result_obj.change_id is not None
        assert len(result_obj.updated_bullets) > 0

        # Verify playbook entry exists
        with db_service.get_session() as session:
            entry = (
                session.query(PlaybookEntry)
                .filter(
                    PlaybookEntry.ticket_id == test_ticket,
                    PlaybookEntry.supporting_memory_ids.contains(
                        [result_obj.memory_id]
                    ),
                )
                .first()
            )

            assert entry is not None
            assert entry.content is not None
            assert len(entry.content) > 10


class TestACEAPI:
    """Tests for ACE API endpoint (REQ-MEM-API-001)."""

    def test_complete_task_endpoint(
        self,
        db_service,
        memory_service,
        embedding_service,
        event_bus_service,
        test_task,
    ):
        """Test ACE workflow via ACEEngine directly (REQ-MEM-API-001)."""
        engine = ACEEngine(
            db=db_service,
            memory_service=memory_service,
            embedding_service=embedding_service,
            event_bus=event_bus_service,
        )

        result = engine.execute_workflow(
            task_id=test_task,
            goal="Implement user authentication with JWT tokens",
            result="Successfully implemented JWT authentication middleware",
            tool_usage=[
                {
                    "tool_name": "file_read",
                    "arguments": {"path": "src/auth.py"},
                    "result": None,
                },
                {
                    "tool_name": "file_edit",
                    "arguments": {"path": "src/auth.py"},
                    "result": "File updated successfully",
                },
            ],
            feedback="Tests passed: 15/15",
            agent_id="test-agent-123",
        )

        # Verify result structure (REQ-MEM-API-001)
        assert result is not None
        assert result.memory_id is not None
        assert result.memory_type in MemoryType.all_types()
        assert isinstance(result.files_linked, list)
        assert isinstance(result.insights_found, list)
        assert isinstance(result.errors_identified, list)
        assert isinstance(result.playbook_delta, dict)
        assert "operations" in result.playbook_delta

    def test_complete_task_endpoint_invalid_task(
        self, db_service, memory_service, embedding_service, event_bus_service
    ):
        """Test ACE workflow with invalid task ID."""
        engine = ACEEngine(
            db=db_service,
            memory_service=memory_service,
            embedding_service=embedding_service,
            event_bus=event_bus_service,
        )

        with pytest.raises(ValueError, match="Task.*not found"):
            engine.execute_workflow(
                task_id="nonexistent-task",
                goal="Test goal",
                result="Test result",
                tool_usage=[{"tool_name": "test", "arguments": {}}],
                feedback="Test feedback",
                agent_id="test-agent",
            )
