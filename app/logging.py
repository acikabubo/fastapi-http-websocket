"""
Structured logging configuration with Loki integration.

This module provides JSON-formatted structured logging with support for:
- Correlation ID tracking
- Contextual fields (user_id, endpoint, method, etc.)
- Loki integration for centralized log aggregation
- Multiple log handlers (console, file, Loki)

Log formatters and context helpers are provided by the fastapi-correlation package.
"""

import logging
import sys

from fastapi_correlation import (
    HumanReadableFormatter,
    StructuredJSONFormatter,
    clear_log_context,
    get_correlation_id,
    get_log_context,
    set_log_context,
)

from app.settings import app_settings

# Re-export for backward compatibility — existing imports of these names from
# app.logging continue to work unchanged.
__all__ = [
    "StructuredJSONFormatter",
    "HumanReadableFormatter",
    "set_log_context",
    "get_log_context",
    "clear_log_context",
    "get_correlation_id",
    "setup_logging",
    "logger",
]


def setup_logging() -> logging.Logger:
    """
    Configure logging with structured JSON output and Loki integration.

    This function sets up:
    - Console handler with human-readable format (for development)
    - File handler for errors (JSON format)

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
