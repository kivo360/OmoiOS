"""MCP Circuit Breaker for failure protection per server+tool."""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from omoi_os.models.mcp_server import CircuitBreakerState
from omoi_os.services.database import DatabaseService
from omoi_os.utils.datetime import utc_now


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "CLOSED"  # Normal operation
    OPEN = "OPEN"  # Failing, reject requests
    HALF_OPEN = "HALF_OPEN"  # Testing if recovered


class CircuitOpenError(Exception):
    """Circuit breaker is open."""

    def __init__(self, message: str, opened_at: Optional[datetime] = None):
        super().__init__(message)
        self.opened_at = opened_at


class CircuitBreakerMetrics:
    """Circuit breaker metrics."""

    def __init__(
        self,
        state: CircuitState,
        failure_count: int,
        last_failure_time: Optional[datetime],
        opened_at: Optional[datetime],
    ):
        self.state = state
        self.failure_count = failure_count
        self.last_failure_time = last_failure_time
        self.opened_at = opened_at


class MCPCircuitBreaker:
    """
    Circuit breaker per server+tool combination.
    
    REQ-MCP-CALL-005: Circuit Breaker
    """

    def __init__(
        self,
        circuit_key: str,
        db: DatabaseService,
        failure_threshold: int = 5,
        cooldown_seconds: int = 60,
        half_open_max_requests: int = 3,
    ):
        """
        Initialize circuit breaker.

        Args:
            circuit_key: Unique key (server_id:tool_name)
            db: DatabaseService for state persistence
            failure_threshold: Errors before opening circuit
            cooldown_seconds: Cooldown period before half-open
            half_open_max_requests: Max requests in half-open state
        """
        self.circuit_key = circuit_key
        self.db = db
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.half_open_max_requests = half_open_max_requests

        # Load state from database
        self._load_state()

    def _load_state(self) -> None:
        """Load circuit breaker state from database."""
        with self.db.get_session() as session:
            state_record = (
                session.query(CircuitBreakerState)
                .filter_by(circuit_key=self.circuit_key)
                .first()
            )

            if state_record:
                self.state = CircuitState(state_record.state)
                self.failure_count = state_record.failure_count
                self.success_count = state_record.success_count
                self.last_failure_time = state_record.last_failure_time
                self.opened_at = state_record.opened_at
                self.half_open_requests = 0  # Reset on load
            else:
                # Initialize new circuit breaker
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.last_failure_time = None
                self.opened_at = None
                self.half_open_requests = 0

    def _save_state(self) -> None:
        """Save circuit breaker state to database."""
        with self.db.get_session() as session:
            state_record = (
                session.query(CircuitBreakerState)
                .filter_by(circuit_key=self.circuit_key)
                .first()
            )

            if state_record:
                state_record.state = self.state.value
                state_record.failure_count = self.failure_count
                state_record.success_count = self.success_count
                state_record.last_failure_time = self.last_failure_time
                state_record.opened_at = self.opened_at
                state_record.updated_at = utc_now()
            else:
                state_record = CircuitBreakerState(
                    circuit_key=self.circuit_key,
                    state=self.state.value,
                    failure_count=self.failure_count,
                    success_count=self.success_count,
                    last_failure_time=self.last_failure_time,
                    opened_at=self.opened_at,
                )
                session.add(state_record)

            session.commit()

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
        """
        # Check if circuit should transition
        self._check_state_transition()

        # Reject if open
        if self.state == CircuitState.OPEN:
            raise CircuitOpenError(
                f"Circuit is OPEN for {self.cooldown_seconds}s", opened_at=self.opened_at
            )

        # Execute function
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception as e:
            self._on_failure()
            raise

    def _check_state_transition(self) -> None:
        """Check if circuit should transition states."""
        if self.state == CircuitState.OPEN:
            # Check if cooldown period has passed
            if self.opened_at:
                elapsed = (utc_now() - self.opened_at).total_seconds()
                if elapsed >= self.cooldown_seconds:
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_requests = 0
                    self.success_count = 0
                    self._save_state()

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            self.half_open_requests += 1

            # If enough successes, close circuit
            if self.success_count >= self.half_open_max_requests:
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
                self.half_open_requests = 0
        else:
            # Reset failure count on success
            if self.failure_count > 0:
                self.failure_count = 0

        self._save_state()

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = utc_now()

        if self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open immediately opens circuit
            self.state = CircuitState.OPEN
            self.opened_at = utc_now()
            self.half_open_requests = 0
        elif self.failure_count >= self.failure_threshold:
            # Open circuit after threshold failures
            self.state = CircuitState.OPEN
            self.opened_at = utc_now()

        self._save_state()

    def get_metrics(self) -> CircuitBreakerMetrics:
        """
        Get current circuit breaker metrics.

        Returns:
            CircuitBreakerMetrics object
        """
        return CircuitBreakerMetrics(
            state=self.state,
            failure_count=self.failure_count,
            last_failure_time=self.last_failure_time,
            opened_at=self.opened_at,
        )

