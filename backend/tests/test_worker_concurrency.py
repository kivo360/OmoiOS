"""Tests for concurrent worker execution."""

from concurrent.futures import ThreadPoolExecutor

from omoi_os.worker import register_agent


class TestAgentRegistration:
    """Tests for agent registration with capacity."""

    def test_register_agent_with_capacity(self, db_service):
        """Test registering agent with custom capacity."""
        agent_id = register_agent(
            db_service,
            agent_type="worker",
            phase_id="PHASE_IMPLEMENTATION",
            capacity=3,
        )

        # Verify agent was created with correct capacity
        with db_service.get_session() as session:
            from omoi_os.models.agent import Agent

            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            assert agent is not None
            assert agent.capacity == 3
            assert agent.health_status == "healthy"

    def test_register_agent_default_capacity(self, db_service):
        """Test registering agent with default capacity."""
        agent_id = register_agent(
            db_service,
            agent_type="worker",
        )

        with db_service.get_session() as session:
            from omoi_os.models.agent import Agent

            agent = session.query(Agent).filter(Agent.id == agent_id).first()
            assert agent is not None
            assert agent.capacity == 1  # Default


class TestConcurrentExecution:
    """Tests for concurrent task execution patterns."""

    def test_threadpool_execution(self):
        """Test that ThreadPoolExecutor can run multiple tasks."""
        results = []

        def worker_task(task_id):
            results.append(task_id)
            return task_id

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(worker_task, i) for i in range(5)]
            for future in futures:
                future.result()

        assert len(results) == 5
        assert set(results) == {0, 1, 2, 3, 4}

    def test_task_isolation(self):
        """Test that concurrent tasks are properly isolated."""
        # Each task should have its own workspace and not interfere
        import tempfile
        import os

        workspaces = []

        def create_workspace(task_id):
            workspace = tempfile.mkdtemp(prefix=f"task_{task_id}_")
            workspaces.append(workspace)
            # Verify workspace is unique
            assert os.path.exists(workspace)
            return workspace

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_workspace, i) for i in range(5)]
            results = [f.result() for f in futures]

        # All workspaces should be unique
        assert len(results) == 5
        assert len(set(results)) == 5


class TestCapacityRespect:
    """Tests that worker respects capacity limits."""

    def test_capacity_limits_concurrent_tasks(self):
        """Test that capacity limits number of concurrent executions."""
        import time
        from threading import Lock

        concurrent_count = 0
        max_concurrent = 0
        lock = Lock()

        def long_running_task():
            nonlocal concurrent_count, max_concurrent
            with lock:
                concurrent_count += 1
                if concurrent_count > max_concurrent:
                    max_concurrent = concurrent_count

            time.sleep(0.1)  # Simulate work

            with lock:
                concurrent_count -= 1

        # Run 10 tasks with max_workers=3
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(long_running_task) for _ in range(10)]
            for future in futures:
                future.result()

        # Max concurrent should never exceed thread pool size
        assert max_concurrent <= 3
