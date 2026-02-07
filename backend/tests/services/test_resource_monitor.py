"""Tests for ResourceMonitorService."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from omoi_os.services.resource_monitor import (
    ResourceMonitorService,
    ResourceAllocation,
    ResourceUsage,
)
from omoi_os.models.sandbox_resource import SandboxResource, SandboxResourceMetrics


@pytest.fixture
def mock_db():
    """Create a mock database service."""
    db = MagicMock()
    db.session = MagicMock()
    return db


@pytest.fixture
def resource_monitor(mock_db):
    """Create a ResourceMonitorService instance."""
    return ResourceMonitorService(db=mock_db)


class TestResourceMonitorService:
    """Tests for ResourceMonitorService."""

    def test_init_without_db(self):
        """Test service initialization without database."""
        service = ResourceMonitorService(db=None)
        assert service.db is None

    def test_init_with_db(self, mock_db):
        """Test service initialization with database."""
        service = ResourceMonitorService(db=mock_db)
        assert service.db == mock_db

    @pytest.mark.asyncio
    async def test_register_sandbox_without_db(self):
        """Test sandbox registration returns None without database."""
        service = ResourceMonitorService(db=None)
        result = await service.register_sandbox(
            sandbox_id="sb-test-123",
            cpu_cores=2,
            memory_gb=4,
            disk_gb=8,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_metrics_without_db(self):
        """Test update_metrics returns None without database."""
        service = ResourceMonitorService(db=None)
        result = await service.update_metrics(
            sandbox_id="sb-test-123",
            cpu_percent=50.0,
            memory_percent=60.0,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_allocation_without_db(self):
        """Test update_allocation returns None without database."""
        service = ResourceMonitorService(db=None)
        result = await service.update_allocation(
            sandbox_id="sb-test-123",
            cpu_cores=4,
            memory_gb=8,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_sandbox_without_db(self):
        """Test get_sandbox returns None without database."""
        service = ResourceMonitorService(db=None)
        result = await service.get_sandbox("sb-test-123")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_active_sandboxes_without_db(self):
        """Test get_active_sandboxes returns empty list without database."""
        service = ResourceMonitorService(db=None)
        result = await service.get_active_sandboxes()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_metrics_history_without_db(self):
        """Test get_metrics_history returns empty list without database."""
        service = ResourceMonitorService(db=None)
        result = await service.get_metrics_history("sb-test-123")
        assert result == []

    @pytest.mark.asyncio
    async def test_delete_sandbox_without_db(self):
        """Test delete_sandbox returns False without database."""
        service = ResourceMonitorService(db=None)
        result = await service.delete_sandbox("sb-test-123")
        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_old_metrics_without_db(self):
        """Test cleanup_old_metrics returns 0 without database."""
        service = ResourceMonitorService(db=None)
        result = await service.cleanup_old_metrics(days=7)
        assert result == 0

    @pytest.mark.asyncio
    async def test_get_resource_summary_without_db(self):
        """Test get_resource_summary returns empty dict without database."""
        service = ResourceMonitorService(db=None)
        result = await service.get_resource_summary()
        assert result == {}


class TestResourceAllocationDataclass:
    """Tests for ResourceAllocation dataclass."""

    def test_resource_allocation_creation(self):
        """Test ResourceAllocation dataclass creation."""
        allocation = ResourceAllocation(
            cpu_cores=2,
            memory_gb=4,
            disk_gb=8,
        )
        assert allocation.cpu_cores == 2
        assert allocation.memory_gb == 4
        assert allocation.disk_gb == 8


class TestResourceUsageDataclass:
    """Tests for ResourceUsage dataclass."""

    def test_resource_usage_creation(self):
        """Test ResourceUsage dataclass creation."""
        usage = ResourceUsage(
            cpu_usage_percent=45.5,
            memory_usage_percent=62.3,
            memory_used_mb=2540.0,
            disk_usage_percent=35.0,
            disk_used_gb=2.8,
        )
        assert usage.cpu_usage_percent == 45.5
        assert usage.memory_usage_percent == 62.3
        assert usage.memory_used_mb == 2540.0
        assert usage.disk_usage_percent == 35.0
        assert usage.disk_used_gb == 2.8


class TestSandboxResourceModel:
    """Tests for SandboxResource model."""

    def test_sandbox_resource_creation(self):
        """Test SandboxResource model creation."""
        resource = SandboxResource(
            id=str(uuid4()),
            sandbox_id="sb-test-123",
            task_id="task-456",
            agent_id="agent-789",
            allocated_cpu_cores=2,
            allocated_memory_gb=4,
            allocated_disk_gb=8,
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
            memory_used_mb=2400.0,
            disk_usage_percent=30.0,
            disk_used_gb=2.4,
            status="running",
        )
        assert resource.sandbox_id == "sb-test-123"
        assert resource.allocated_cpu_cores == 2
        assert resource.cpu_usage_percent == 50.0

    def test_sandbox_resource_repr(self):
        """Test SandboxResource __repr__ method."""
        resource = SandboxResource(
            id=str(uuid4()),
            sandbox_id="sb-test-123",
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
        )
        repr_str = repr(resource)
        assert "sb-test-123" in repr_str
        assert "50.0%" in repr_str


class TestSandboxResourceMetricsModel:
    """Tests for SandboxResourceMetrics model."""

    def test_sandbox_resource_metrics_creation(self):
        """Test SandboxResourceMetrics model creation."""
        metrics = SandboxResourceMetrics(
            id=str(uuid4()),
            sandbox_id="sb-test-123",
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
            memory_used_mb=2400.0,
            disk_usage_percent=30.0,
            disk_used_gb=2.4,
        )
        assert metrics.sandbox_id == "sb-test-123"
        assert metrics.cpu_usage_percent == 50.0

    def test_sandbox_resource_metrics_repr(self):
        """Test SandboxResourceMetrics __repr__ method."""
        metrics = SandboxResourceMetrics(
            id=str(uuid4()),
            sandbox_id="sb-test-123",
            cpu_usage_percent=50.0,
            memory_usage_percent=60.0,
            memory_used_mb=0.0,
            disk_usage_percent=0.0,
            disk_used_gb=0.0,
        )
        repr_str = repr(metrics)
        assert "sb-test-123" in repr_str
        assert "50.0%" in repr_str
