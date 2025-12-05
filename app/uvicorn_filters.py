"""Custom filters for uvicorn access logging."""

import logging

from app.settings import app_settings


class ExcludeMetricsFilter(logging.Filter):
    """
    Logging filter to exclude monitoring endpoint requests from access logs.

    This filter prevents excessive log noise from health checks and
    Prometheus scraping. Requests to paths like /metrics and /health
    will not appear in uvicorn's access logs.

    The excluded paths are configurable via the LOG_EXCLUDED_PATHS
    setting in app.settings.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the log record should be logged.

        Args:
            record: The log record to evaluate.

        Returns:
            False if the request path is in LOG_EXCLUDED_PATHS, True otherwise.
        """
        message = record.getMessage()
        # Check if any excluded path appears in the log message
        return not any(
            path in message for path in app_settings.LOG_EXCLUDED_PATHS
        )
