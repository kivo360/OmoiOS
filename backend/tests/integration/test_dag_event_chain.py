"""Integration test for the full DAG event chain wiring.

Verifies that the three-service pipeline works end-to-end:
  CoordinationService → SynthesisService → ConvergenceMergeService

Event flow tested:
  1. CoordinationService.join_tasks() publishes coordination.join.created
  2. SynthesisService receives it, tracks the join
  3. When all source tasks complete (TASK_COMPLETED events), SynthesisService
     merges results and publishes coordination.synthesis.completed
  4. ConvergenceMergeService receives the synthesis event

This test uses a LocalEventBus that dispatches synchronously, so we can
verify the full chain without Redis. This matches what happens in production
when all three services are initialized in orchestrator_worker.py.
"""

import pytest
from typing import Any, Callable, Dict, List
from uuid import uuid4

from omoi_os.models.task import Task
from omoi_os.models.ticket import Ticket
from omoi_os.services.coordination import CoordinationService
from omoi_os.services.convergence_merge_service import (
    ConvergenceMergeService,
    ConvergenceMergeConfig,
    reset_convergence_merge_service,
)
from omoi_os.services.database import DatabaseService
from omoi_os.services.event_bus import SystemEvent
from omoi_os.services.synthesis_service import (
    SynthesisService,
    reset_synthesis_service,
)
from omoi_os.services.task_queue import TaskQueueService

# =============================================================================
# LOCAL EVENT BUS (synchronous dispatch for testing)
# =============================================================================


class LocalEventBus:
    """In-process event bus that dispatches callbacks synchronously.

    Replaces Redis pub/sub for testing so we can verify the full event chain
    without external dependencies. Callbacks fire immediately on publish().
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self.published_events: List[SystemEvent] = []

    def subscribe(self, event_type: str, callback: Callable) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def publish(self, event: SystemEvent) -> None:
        self.published_events.append(event)
        callbacks = self._subscribers.get(event.event_type, [])
        for cb in callbacks:
            cb(event)

    def close(self) -> None:
        pass

    def get_events_of_type(self, event_type: str) -> List[SystemEvent]:
        return [e for e in self.published_events if e.event_type == event_type]


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def local_event_bus() -> LocalEventBus:
    """Create a local synchronous event bus."""
    return LocalEventBus()


@pytest.fixture
def task_queue(
    db_service: DatabaseService, local_event_bus: LocalEventBus
) -> TaskQueueService:
    """TaskQueueService with local event bus."""
    return TaskQueueService(db_service, event_bus=local_event_bus)


@pytest.fixture
def coordination(
    db_service: DatabaseService,
    task_queue: TaskQueueService,
    local_event_bus: LocalEventBus,
) -> CoordinationService:
    """CoordinationService wired to local event bus."""
    return CoordinationService(db_service, task_queue, local_event_bus)


@pytest.fixture
def synthesis(
    db_service: DatabaseService,
    local_event_bus: LocalEventBus,
) -> SynthesisService:
    """SynthesisService subscribed to local event bus."""
    reset_synthesis_service()
    svc = SynthesisService(db=db_service, event_bus=local_event_bus)
    svc.subscribe_to_events()
    return svc


@pytest.fixture
def convergence_merge(
    db_service: DatabaseService,
    local_event_bus: LocalEventBus,
) -> ConvergenceMergeService:
    """ConvergenceMergeService subscribed to local event bus."""
    reset_convergence_merge_service()
    svc = ConvergenceMergeService(
        db=db_service,
        event_bus=local_event_bus,
        config=ConvergenceMergeConfig(
            max_conflicts_auto_resolve=10,
            enable_auto_push=False,
        ),
    )
    svc.subscribe_to_events()
    return svc


@pytest.fixture
def parallel_tasks_completed(db_service: DatabaseService) -> Dict[str, Any]:
    """Create a ticket with parallel source tasks already completed.

    Returns dict with ticket, source tasks (completed), and continuation task (pending).
    Use this for tests that verify immediate synthesis on already-completed sources.
    """
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Parallel Workflow (completed)",
            description="Ticket for DAG event chain test - sources completed",
            phase_id="PHASE_IMPLEMENTATION",
            status="in_progress",
            priority="MEDIUM",
        )
        session.add(ticket)
        session.flush()

        source_1 = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Source task 1 - implement service",
            status="completed",
            priority="MEDIUM",
            result={
                "output": "service implemented",
                "files_changed": ["src/service.py"],
            },
        )
        source_2 = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Source task 2 - implement tests",
            status="completed",
            priority="MEDIUM",
            result={
                "output": "tests implemented",
                "files_changed": ["tests/test_service.py"],
            },
        )
        continuation = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="integrate_feature",
            description="Continuation task - integrate parallel results",
            status="pending",
            priority="MEDIUM",
        )

        session.add_all([source_1, source_2, continuation])
        session.commit()

        for obj in [ticket, source_1, source_2, continuation]:
            session.refresh(obj)
            session.expunge(obj)

        return {
            "ticket": ticket,
            "source_1": source_1,
            "source_2": source_2,
            "continuation": continuation,
        }


@pytest.fixture
def parallel_tasks_running(db_service: DatabaseService) -> Dict[str, Any]:
    """Create a ticket with parallel source tasks still running.

    Returns dict with ticket, source tasks (running), and continuation task (pending).
    Use this for tests that need to control when tasks complete via events.
    """
    with db_service.get_session() as session:
        ticket = Ticket(
            title="Test Parallel Workflow (running)",
            description="Ticket for DAG event chain test - sources running",
            phase_id="PHASE_IMPLEMENTATION",
            status="in_progress",
            priority="MEDIUM",
        )
        session.add(ticket)
        session.flush()

        source_1 = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Source task 1 - implement service",
            status="running",
            priority="MEDIUM",
        )
        source_2 = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="implement_feature",
            description="Source task 2 - implement tests",
            status="running",
            priority="MEDIUM",
        )
        continuation = Task(
            ticket_id=ticket.id,
            phase_id="PHASE_IMPLEMENTATION",
            task_type="integrate_feature",
            description="Continuation task - integrate parallel results",
            status="pending",
            priority="MEDIUM",
        )

        session.add_all([source_1, source_2, continuation])
        session.commit()

        for obj in [ticket, source_1, source_2, continuation]:
            session.refresh(obj)
            session.expunge(obj)

        return {
            "ticket": ticket,
            "source_1": source_1,
            "source_2": source_2,
            "continuation": continuation,
        }


# =============================================================================
# WIRING VERIFICATION TESTS
# =============================================================================


class TestDAGEventChainWiring:
    """Tests that verify the three-service event chain is properly wired."""

    def test_coordination_publishes_join_event(
        self,
        coordination: CoordinationService,
        local_event_bus: LocalEventBus,
        parallel_tasks_completed: Dict[str, Any],
    ):
        """CoordinationService.register_join() should publish coordination.join.created."""
        source_ids = [
            str(parallel_tasks_completed["source_1"].id),
            str(parallel_tasks_completed["source_2"].id),
        ]
        continuation_id = str(parallel_tasks_completed["continuation"].id)

        coordination.register_join(
            join_id=f"join-{uuid4().hex[:8]}",
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        join_events = local_event_bus.get_events_of_type("coordination.join.created")
        assert len(join_events) == 1
        assert join_events[0].payload["source_task_ids"] == source_ids
        assert join_events[0].payload["continuation_task_id"] == continuation_id

    def test_synthesis_receives_join_event(
        self,
        coordination: CoordinationService,
        synthesis: SynthesisService,
        local_event_bus: LocalEventBus,
        parallel_tasks_running: Dict[str, Any],
    ):
        """SynthesisService should register the join when it receives the event."""
        source_ids = [
            str(parallel_tasks_running["source_1"].id),
            str(parallel_tasks_running["source_2"].id),
        ]
        continuation_id = str(parallel_tasks_running["continuation"].id)
        join_id = f"join-{uuid4().hex[:8]}"

        # CoordinationService publishes → SynthesisService receives (synchronous)
        coordination.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Verify SynthesisService tracked the join
        assert join_id in synthesis._pending_joins
        pending = synthesis._pending_joins[join_id]
        assert set(pending.source_task_ids) == set(source_ids)
        assert pending.continuation_task_id == continuation_id

    def test_synthesis_triggers_on_task_completion(
        self,
        db_service: DatabaseService,
        coordination: CoordinationService,
        synthesis: SynthesisService,
        local_event_bus: LocalEventBus,
        parallel_tasks_running: Dict[str, Any],
    ):
        """SynthesisService should trigger merge when all sources complete."""
        source_ids = [
            str(parallel_tasks_running["source_1"].id),
            str(parallel_tasks_running["source_2"].id),
        ]
        continuation_id = str(parallel_tasks_running["continuation"].id)
        join_id = f"join-{uuid4().hex[:8]}"

        # Step 1: Register join via coordination event
        coordination.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Step 2: Complete source 1 in DB, then fire event
        with db_service.get_session() as session:
            task = session.query(Task).filter(Task.id == source_ids[0]).first()
            task.status = "completed"
            task.result = {
                "output": "service implemented",
                "files_changed": ["src/service.py"],
            }
            session.commit()

        local_event_bus.publish(
            SystemEvent(
                event_type="TASK_COMPLETED",
                entity_type="task",
                entity_id=source_ids[0],
                payload={"task_id": source_ids[0]},
            )
        )

        # Not ready yet — still waiting for source 2
        synthesis_events = local_event_bus.get_events_of_type(
            "coordination.synthesis.completed"
        )
        assert len(synthesis_events) == 0

        # Step 3: Complete source 2 in DB, then fire event
        with db_service.get_session() as session:
            task = session.query(Task).filter(Task.id == source_ids[1]).first()
            task.status = "completed"
            task.result = {
                "output": "tests implemented",
                "files_changed": ["tests/test_service.py"],
            }
            session.commit()

        local_event_bus.publish(
            SystemEvent(
                event_type="TASK_COMPLETED",
                entity_type="task",
                entity_id=source_ids[1],
                payload={"task_id": source_ids[1]},
            )
        )

        # Now synthesis should have triggered
        synthesis_events = local_event_bus.get_events_of_type(
            "coordination.synthesis.completed"
        )
        assert len(synthesis_events) == 1
        assert synthesis_events[0].payload["join_id"] == join_id
        assert synthesis_events[0].payload["continuation_task_id"] == continuation_id

    def test_convergence_merge_receives_synthesis_event(
        self,
        coordination: CoordinationService,
        synthesis: SynthesisService,
        convergence_merge: ConvergenceMergeService,
        local_event_bus: LocalEventBus,
        parallel_tasks_completed: Dict[str, Any],
    ):
        """ConvergenceMergeService should receive coordination.synthesis.completed.

        This is the critical test — it verifies the full 3-service chain:
        Coordination → Synthesis → ConvergenceMerge
        """
        source_ids = [
            str(parallel_tasks_completed["source_1"].id),
            str(parallel_tasks_completed["source_2"].id),
        ]
        continuation_id = str(parallel_tasks_completed["continuation"].id)
        join_id = f"join-{uuid4().hex[:8]}"

        # Track whether ConvergenceMergeService received the event
        received_events = []
        original_handler = convergence_merge._handle_synthesis_completed

        def tracking_handler(event_data):
            received_events.append(event_data)
            original_handler(event_data)

        convergence_merge._handle_synthesis_completed = tracking_handler

        # Re-subscribe with tracking handler
        local_event_bus._subscribers["coordination.synthesis.completed"] = [
            tracking_handler
        ]

        # Step 1: Register join
        coordination.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # Step 2: Complete both source tasks
        for sid in source_ids:
            local_event_bus.publish(
                SystemEvent(
                    event_type="TASK_COMPLETED",
                    entity_type="task",
                    entity_id=sid,
                    payload={"task_id": sid},
                )
            )

        # Step 3: Verify ConvergenceMergeService received the event
        assert len(received_events) == 1
        event = received_events[0]
        assert event.payload["continuation_task_id"] == continuation_id
        assert set(event.payload["source_task_ids"]) == set(source_ids)


class TestDAGEventChainWithPreCompleted:
    """Tests for edge cases where tasks complete before joins are registered."""

    def test_already_completed_sources_trigger_immediate_synthesis(
        self,
        coordination: CoordinationService,
        synthesis: SynthesisService,
        local_event_bus: LocalEventBus,
        parallel_tasks_completed: Dict[str, Any],
    ):
        """If source tasks are already completed when join is registered,
        synthesis should trigger immediately."""
        source_ids = [
            str(parallel_tasks_completed["source_1"].id),  # already status=completed
            str(parallel_tasks_completed["source_2"].id),  # already status=completed
        ]
        continuation_id = str(parallel_tasks_completed["continuation"].id)
        join_id = f"join-{uuid4().hex[:8]}"

        # Register join — sources are already completed in DB
        coordination.register_join(
            join_id=join_id,
            source_task_ids=source_ids,
            continuation_task_id=continuation_id,
        )

        # SynthesisService checks DB on registration and should find them completed
        synthesis_events = local_event_bus.get_events_of_type(
            "coordination.synthesis.completed"
        )
        assert len(synthesis_events) == 1
        assert synthesis_events[0].payload["join_id"] == join_id


class TestOrchestratorWorkerInitOrder:
    """Tests that verify the init_services() function wires services correctly."""

    def test_init_services_imports_all_dag_services(self):
        """Verify that orchestrator_worker.init_services references all DAG services.

        This is a static analysis test — it reads the source code and checks
        that the required imports and initializations are present.
        """
        import inspect
        from omoi_os.workers import orchestrator_worker

        source = inspect.getsource(orchestrator_worker.init_services)

        # Verify CoordinationService is imported and initialized
        assert (
            "CoordinationService" in source
        ), "CoordinationService not found in init_services()"

        # Verify ConvergenceMergeService is imported and initialized
        assert (
            "get_convergence_merge_service" in source
        ), "get_convergence_merge_service not found in init_services()"
        assert (
            "subscribe_to_events" in source
        ), "subscribe_to_events() not called in init_services()"

        # Verify OwnershipValidationService is imported and initialized
        assert (
            "get_ownership_validation_service" in source
        ), "get_ownership_validation_service not found in init_services()"

        # Verify AgentConflictResolver is imported
        assert (
            "AgentConflictResolver" in source
        ), "AgentConflictResolver not found in init_services()"

    def test_init_services_order_is_correct(self):
        """Verify services are initialized in dependency order.

        Required order:
        1. DatabaseService, EventBusService, TaskQueueService (core)
        2. SynthesisService (must subscribe before CoordinationService publishes)
        3. CoordinationService (publishes events SynthesisService listens to)
        4. ConvergenceMergeService (subscribes to synthesis events)
        """
        import inspect
        from omoi_os.workers import orchestrator_worker

        source = inspect.getsource(orchestrator_worker.init_services)

        # Find positions of key initializations
        synthesis_pos = source.find("SynthesisService")
        coordination_pos = source.find("CoordinationService")
        convergence_pos = source.find("get_convergence_merge_service")

        assert (
            synthesis_pos < coordination_pos
        ), "SynthesisService must be initialized before CoordinationService"
        assert (
            coordination_pos < convergence_pos
        ), "CoordinationService must be initialized before ConvergenceMergeService"
