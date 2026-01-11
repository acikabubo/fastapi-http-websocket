"""
Structured logging configuration with Loki integration.

This module provides JSON-formatted structured logging with support for:
- Correlation ID tracking
- Contextual fields (user_id, endpoint, method, etc.)
- Loki integration for centralized log aggregation
- Multiple log handlers (console, file, Loki)
"""

import json
import logging
import sys
from contextvars import ContextVar
from typing import Any

from {{cookiecutter.module_name}}.constants import LOKI_MAX_LOG_SIZE_BYTES
from {{cookiecutter.module_name}}.settings import app_settings

# Context variables for storing request-specific logging context
log_context: ContextVar[dict[str, Any]] = ContextVar("log_context", default={})


def get_correlation_id() -> str:
    """
    Get correlation ID from context, safe wrapper for logging.

    Returns:
        Correlation ID or empty string if not available.
    """
    try:
        from {{cookiecutter.module_name}}.middlewares.correlation_id import (
            get_correlation_id as _get_cid,
        )

        return _get_cid()
    except (ImportError, AttributeError, RuntimeError):
        # ImportError: Module not available
        # AttributeError: Function not found
        # RuntimeError: Correlation ID context not initialized
        return ""


def set_log_context(**kwargs: Any) -> None:
    """
    Set contextual fields for structured logging.

    This allows adding fields like user_id, endpoint, method, etc.
    to all log messages within the current request context.

    Args:
        **kwargs: Key-value pairs to add to log context.

    Example:
        >>> set_log_context(user_id=123, endpoint="/api/authors")
        >>> logger.info(
        ...     "Processing request"
        ... )  # Will include user_id and endpoint
    """
    current = log_context.get()
    current.update(kwargs)
    log_context.set(current)


def get_log_context() -> dict[str, Any]:
    """
    Get current log context.

    Returns:
        Dictionary of contextual log fields.
    """
    return log_context.get()


def clear_log_context() -> None:
    """Clear the log context (useful at end of request)."""
    log_context.set({})


class StructuredJSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    This formatter outputs logs in JSON format with:
    - Standard fields: timestamp, level, logger, message
    - Correlation ID from request context
    - Additional contextual fields from log_context
    - Exception information when present
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: The log record to format.

        Returns:
            JSON string with structured log data.
        """
        # Base log structure
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        correlation_id = get_correlation_id()
        if correlation_id:
            log_data["request_id"] = correlation_id

        # Add contextual fields from log_context
        context = get_log_context()
        if context:
            log_data.update(context)

        # Add environment
        log_data["environment"] = app_settings.ENV.value

        # Add exception information if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record (only JSON-serializable ones)
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "taskName",
            ]:
                # Only add JSON-serializable values
                try:
                    json.dumps(value)
                    log_data[key] = value
                except (TypeError, ValueError):
                    # Skip non-serializable fields
                    log_data[key] = str(value)

        # Truncate message if too long (for Loki compatibility)
        json_str = json.dumps(log_data)
        if len(json_str) > LOKI_MAX_LOG_SIZE_BYTES:
            message = log_data.get("message", "")
            if isinstance(message, str):
                log_data["message"] = (
                    message[: LOKI_MAX_LOG_SIZE_BYTES - 1000]
                    + "... [TRUNCATED]"
                )
            json_str = json.dumps(log_data)

        return json_str


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable formatter for console output (non-JSON).

    Uses different format strings based on log level for better readability
    during development.
    """

    INFO_FMT = "%(asctime)s - [%(correlation_id)s] %(levelname)s: %(message)s"
    ERROR_FMT = "%(asctime)s - [%(correlation_id)s] %(levelname)s: %(module)s.%(funcName)s:%(lineno)d - %(message)s"

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the formatter."""
        super().__init__(*args, **kwargs)
        self._formatters = {
            logging.INFO: logging.Formatter(
                self.INFO_FMT, datefmt="%Y-%m-%d %H:%M:%S"
            ),
            logging.WARNING: logging.Formatter(
                self.ERROR_FMT, datefmt="%Y-%m-%d %H:%M:%S"
            ),
            logging.ERROR: logging.Formatter(
                self.ERROR_FMT, datefmt="%Y-%m-%d %H:%M:%S"
            ),
            logging.DEBUG: logging.Formatter(
                self.ERROR_FMT, datefmt="%Y-%m-%d %H:%M:%S"
            ),
        }

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record with correlation ID.

        Args:
            record: The log record to format.

        Returns:
            Formatted log string.
        """
        # Inject correlation ID into record
        record.correlation_id = get_correlation_id() or "-"

        formatter = self._formatters.get(
            record.levelno, self._formatters[logging.INFO]
        )
        return formatter.format(record)


def setup_logging() -> logging.Logger:
    """
    Configure logging with structured JSON output and Loki integration.

    This function sets up:
    - Console handler with human-readable format (for development)
    - File handler for errors (JSON format)
    - Loki handler for centralized logging (if enabled)

    Returns:
        Configured logger instance.
    """
    # Get or create root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, app_settings.LOG_LEVEL.upper()))

    # Clear existing handlers to avoid duplicates
    logger.handlers.clear()

    # Console handler - format based on LOG_CONSOLE_FORMAT setting
    # 'json' for Grafana Alloy collection, 'human' for development readability
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    if app_settings.LOG_CONSOLE_FORMAT.lower() == "human":
        console_handler.setFormatter(HumanReadableFormatter())
    else:
        # Default to JSON format for Grafana Alloy collection
        console_handler.setFormatter(StructuredJSONFormatter())
    logger.addHandler(console_handler)

    # File handler (JSON format for errors)
    try:
        file_handler = logging.FileHandler(app_settings.LOG_FILE_PATH)
        file_handler.setLevel(logging.ERROR)
        file_handler.setFormatter(StructuredJSONFormatter())
        logger.addHandler(file_handler)
    except (OSError, PermissionError) as e:
        # OSError: File system errors (path doesn't exist, disk full)
        # PermissionError: No write permission for log directory
        logger.warning(f"Could not create file handler: {e}")

    # Note: We use Grafana Alloy to collect logs from Docker stdout and send to Loki
    # Alloy replaced deprecated Promtail (deprecated Feb 2025, EOL March 2026)
    # LokiHandler was removed to avoid duplicate logs and complexity
    # Alloy scrapes container logs and handles shipping to Loki

    # Disable logging during pytest runs
    if sys.argv[0].split("/")[-1] in ["pytest"]:
        logging.disable(logging.ERROR)

    return logger


# Create default logger instance
logger = setup_logging()
