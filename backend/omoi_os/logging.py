"""Centralized structlog configuration with comprehensive error tracking.

Features:
- File, line, function, module for every log
- Exception type and value classification
- Full structured stack traces with local variables
- Request/trace ID propagation via contextvars
- Rich console output in development
- JSON output with orjson in production

Usage:
    # At application startup (main.py, workers)
    from omoi_os.logging import configure_logging
    configure_logging(env="development")  # or "production"

    # In any module
    from omoi_os.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Task started", task_id="abc123")

    # For errors - automatically captures full stack trace with locals
    try:
        process_task(task)
    except Exception:
        logger.exception("Task failed", task_id=task.id)
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any, Literal

import structlog
from structlog.processors import CallsiteParameter, CallsiteParameterAdder
from structlog.tracebacks import ExceptionDictTransformer

if TYPE_CHECKING:
    from structlog.typing import EventDict, WrappedLogger

# Track if logging has been configured
_logging_configured = False


def configure_logging(
    env: Literal["development", "production", "test"] = "development",
    log_level: int | None = None,
    json_logs: bool | None = None,
    show_locals: bool = True,
    locals_max_length: int = 10,
    locals_max_string: int = 80,
    max_frames: int = 50,
) -> None:
    """Configure structlog globally with comprehensive error tracking.

    This should be called once at application startup, before any logging occurs.

    Args:
        env: Environment determines default formatting:
            - "development": Rich colored console output with pretty tracebacks
            - "production": JSON output with structured exception data
            - "test": Minimal output, WARNING level by default
        log_level: Minimum log level. Defaults based on env:
            - development: DEBUG
            - production: INFO
            - test: WARNING
        json_logs: Force JSON output (None = auto-detect from env)
        show_locals: Include local variables in exception stack traces
        locals_max_length: Max length for collection locals (lists, dicts)
        locals_max_string: Max string length for local variable values
        max_frames: Maximum number of stack frames to capture

    Example:
        >>> from omoi_os.logging import configure_logging
        >>> configure_logging(env="development")
    """
    global _logging_configured

    # Prevent double configuration
    if _logging_configured:
        return

    # Set defaults based on environment
    if log_level is None:
        log_level = {
            "development": logging.DEBUG,
            "production": logging.INFO,
            "test": logging.WARNING,
        }.get(env, logging.INFO)

    if json_logs is None:
        json_logs = env == "production"

    # Exception transformer for structured exception data
    exception_transformer = ExceptionDictTransformer(
        show_locals=show_locals,
        locals_max_length=locals_max_length,
        locals_max_string=locals_max_string,
        locals_hide_dunder=True,
        locals_hide_sunder=False,
        max_frames=max_frames,
        use_rich=not json_logs,  # Use rich formatting in dev mode
        suppress=(
            "structlog",
            "logging",
        ),
    )

    # Shared processors for all log entries
    shared_processors: list[structlog.types.Processor] = [
        # Merge request_id, user_id, etc. from contextvars
        structlog.contextvars.merge_contextvars,
        # Add log level (info, error, debug, etc.)
        structlog.stdlib.add_log_level,
        # Add logger name (module path like omoi_os.services.task_queue)
        structlog.stdlib.add_logger_name,
        # Add file, line, function, module info
        CallsiteParameterAdder(
            [
                CallsiteParameter.FILENAME,
                CallsiteParameter.LINENO,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.MODULE,
                CallsiteParameter.PATHNAME,
            ],
            additional_ignores=["uvicorn", "starlette", "fastapi"],
        ),
        # Handle stack_info=True parameter
        structlog.processors.StackInfoRenderer(),
        # Auto-set exc_info=True for logger.exception() calls
        structlog.dev.set_exc_info,
        # Add ISO timestamp
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Decode bytes to strings
        structlog.processors.UnicodeDecoder(),
        # Add error classification for exceptions
        _add_error_classification,
    ]

    if json_logs:
        # Production: Structured JSON with full exception details
        try:
            import orjson

            def json_serializer(obj: Any, **_kwargs: Any) -> str:
                # orjson.dumps returns bytes, decode to str for proper log output
                return orjson.dumps(obj).decode("utf-8")
        except ImportError:
            import json

            def json_serializer(obj: Any, **_kwargs: Any) -> str:
                return json.dumps(obj)

        shared_processors.append(
            structlog.processors.ExceptionRenderer(
                exception_formatter=exception_transformer
            )
        )
        final_processors: list[structlog.types.Processor] = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(serializer=json_serializer),
        ]
    else:
        # Development: Rich console with pretty exceptions
        shared_processors.append(structlog.processors.format_exc_info)
        final_processors = [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.dev.ConsoleRenderer(
                colors=True,
                exception_formatter=structlog.dev.RichTracebackFormatter(
                    show_locals=show_locals,
                    max_frames=max_frames,
                    locals_max_length=locals_max_length,
                    locals_max_string=locals_max_string,
                ),
            ),
        ]

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to also use structlog formatting
    # This ensures third-party libraries also get structured output
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=final_processors,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Silence noisy third-party loggers
    noisy_loggers = [
        "httpx",
        "httpcore",
        "uvicorn.access",
        "asyncio",
        "urllib3",
        "requests",
        "PIL",
        "fsevents",
    ]
    for noisy_logger in noisy_loggers:
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)

    _logging_configured = True


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger with the given name.

    Args:
        name: Logger name, typically __name__ for the current module.
              If None, returns unnamed logger.

    Returns:
        Configured bound logger with all processors applied.

    Example:
        >>> from omoi_os.logging import get_logger
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing started", task_id="abc123")
    """
    return structlog.get_logger(name)


# === Context helpers for request/task tracking ===


def bind_context(**context: Any) -> None:
    """Bind context that propagates to all subsequent log calls.

    Use this to add request IDs, user IDs, task IDs, etc. that should
    appear in all log entries within the current context (async task/thread).

    Args:
        **context: Key-value pairs to bind to logging context.

    Example:
        >>> bind_context(request_id="req-123", user_id="user-456")
        >>> logger.info("Processing")  # Includes request_id and user_id
    """
    # Filter out None values
    filtered_context = {k: v for k, v in context.items() if v is not None}
    if filtered_context:
        structlog.contextvars.bind_contextvars(**filtered_context)


def unbind_context(*keys: str) -> None:
    """Remove specific keys from the logging context.

    Args:
        *keys: Keys to remove from context.

    Example:
        >>> unbind_context("user_id", "request_id")
    """
    structlog.contextvars.unbind_contextvars(*keys)


def clear_context() -> None:
    """Clear all bound context (call at end of request/task)."""
    structlog.contextvars.clear_contextvars()


def get_context() -> dict[str, Any]:
    """Get the current logging context as a dictionary.

    Returns:
        Dict of currently bound context variables.
    """
    return structlog.contextvars.get_contextvars()


# === Error classification processor ===


def _add_error_classification(
    _logger: WrappedLogger,
    _method_name: str,
    event_dict: EventDict,
) -> EventDict:
    """Add error classification based on exception type.

    Adds to event_dict:
    - error_category: "validation", "database", "network", "auth", "timeout", "internal"
    - is_retryable: bool indicating if the error might succeed on retry
    - error_code: Optional error code if available
    """
    exc_info = event_dict.get("exc_info")
    if not exc_info:
        return event_dict

    # Get exception type
    exc_type: type[BaseException] | None = None
    exc_instance: BaseException | None = None

    if isinstance(exc_info, tuple) and len(exc_info) >= 2:
        exc_type = exc_info[0]
        exc_instance = exc_info[1]
    elif isinstance(exc_info, BaseException):
        exc_type = type(exc_info)
        exc_instance = exc_info

    if exc_type is None:
        return event_dict

    exc_name = exc_type.__name__

    # Classification rules
    validation_errors = {
        "ValueError",
        "TypeError",
        "ValidationError",
        "RequestValidationError",
        "JSONDecodeError",
        "KeyError",
        "IndexError",
        "AttributeError",
    }

    database_errors = {
        "DatabaseError",
        "IntegrityError",
        "OperationalError",
        "ProgrammingError",
        "DataError",
        "InterfaceError",
        "InternalError",
        "NotSupportedError",
        "UniqueViolationError",
        "ForeignKeyViolationError",
    }

    network_errors = {
        "ConnectionError",
        "ConnectionRefusedError",
        "ConnectionResetError",
        "BrokenPipeError",
        "ConnectTimeout",
        "ReadTimeout",
        "WriteTimeout",
        "HTTPError",
        "SSLError",
        "ProxyError",
    }

    timeout_errors = {
        "TimeoutError",
        "asyncio.TimeoutError",
        "ConnectTimeout",
        "ReadTimeout",
        "WriteTimeout",
        "PoolTimeout",
    }

    auth_errors = {
        "AuthenticationError",
        "PermissionError",
        "AuthorizationError",
        "InvalidTokenError",
        "ExpiredTokenError",
    }

    # Classify
    if exc_name in validation_errors:
        event_dict["error_category"] = "validation"
        event_dict["is_retryable"] = False
    elif exc_name in database_errors:
        event_dict["error_category"] = "database"
        # OperationalError often means connection issues - retryable
        event_dict["is_retryable"] = exc_name in {
            "OperationalError",
            "InterfaceError",
        }
    elif exc_name in timeout_errors:
        event_dict["error_category"] = "timeout"
        event_dict["is_retryable"] = True
    elif exc_name in network_errors:
        event_dict["error_category"] = "network"
        event_dict["is_retryable"] = True
    elif exc_name in auth_errors:
        event_dict["error_category"] = "auth"
        event_dict["is_retryable"] = False
    else:
        event_dict["error_category"] = "internal"
        event_dict["is_retryable"] = False

    # Extract error code if available (e.g., HTTP status codes)
    if exc_instance is not None:
        # Check for status_code attribute (FastAPI HTTPException, httpx responses)
        if hasattr(exc_instance, "status_code"):
            event_dict["error_code"] = getattr(exc_instance, "status_code")
        # Check for errno (OS-level errors)
        elif hasattr(exc_instance, "errno") and exc_instance.errno is not None:
            event_dict["error_code"] = exc_instance.errno
        # Check for code attribute (various libraries)
        elif hasattr(exc_instance, "code"):
            event_dict["error_code"] = getattr(exc_instance, "code")

    return event_dict


# === Convenience aliases ===

# For compatibility with existing code patterns
getLogger = get_logger
