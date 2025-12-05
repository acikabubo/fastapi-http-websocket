"""Custom filters for uvicorn access logging."""

import logging


class ExcludeMetricsFilter(logging.Filter):
    """
    Logging filter to exclude monitoring endpoint requests from access logs.

    This filter prevents excessive log noise from health checks and
    Prometheus scraping. Requests to paths like /metrics and /health
    will not appear in uvicorn's access logs.

    Note: This class is imported by uvicorn's logging config before the app
    starts, so it must not depend on app.settings to avoid requiring
    environment variables at logging initialization time.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Determine if the log record should be logged.

        Args:
            record: The log record to evaluate.

        Returns:
            False if the request path is in excluded paths, True otherwise.
        """
        message = record.getMessage()

        # Lazy import to avoid circular dependency and env var requirements
        # Only import when actually filtering, not at class load time
        try:
            from app.settings import app_settings

            excluded_paths = app_settings.LOG_EXCLUDED_PATHS
        except Exception:
            # Fallback to hardcoded paths if settings can't be loaded
            excluded_paths = ["/metrics", "/health"]

        # Check if any excluded path appears in the log message
        return not any(path in message for path in excluded_paths)
