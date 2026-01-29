"""Tests for structured logging functionality."""

import json
import logging
from unittest.mock import patch


from app.logging import (
    HumanReadableFormatter,
    StructuredJSONFormatter,
    clear_log_context,
    get_correlation_id,
    get_log_context,
    logger,
    set_log_context,
    setup_logging,
)


class TestLogContext:
    """Test log context management."""

    def test_set_log_context_adds_fields(self):
        """Test that set_log_context adds fields to log context."""
        clear_log_context()  # Start clean
        set_log_context(user_id="user123", request_id="req456")

        context = get_log_context()

        assert context["user_id"] == "user123"
        assert context["request_id"] == "req456"

        clear_log_context()

    def test_set_log_context_updates_existing_fields(self):
        """Test that set_log_context updates existing context."""
        clear_log_context()
        set_log_context(user_id="user123")
        set_log_context(request_id="req456")

        context = get_log_context()

        assert context["user_id"] == "user123"
        assert context["request_id"] == "req456"

        clear_log_context()

    def test_clear_log_context_removes_fields(self):
        """Test that clear_log_context removes all fields."""
        set_log_context(user_id="user123", request_id="req456")
        clear_log_context()

        context = get_log_context()

        assert context == {}

    def test_get_log_context_returns_empty_dict_initially(self):
        """Test that get_log_context returns empty dict by default."""
        clear_log_context()

        context = get_log_context()

        assert context == {}


class TestGetCorrelationId:
    """Test correlation ID retrieval."""

    def test_get_correlation_id_returns_string(self):
        """Test correlation ID returns string."""
        correlation_id = get_correlation_id()

        assert isinstance(correlation_id, str)

    def test_get_correlation_id_returns_empty_string_on_runtime_error(
        self,
    ):
        """Test fallback when correlation ID context not initialized."""
        with patch(
            "app.middlewares.correlation_id.get_correlation_id",
            side_effect=RuntimeError("Context not initialized"),
        ):
            correlation_id = get_correlation_id()

            assert correlation_id == ""

    def test_get_correlation_id_returns_id_when_available(self):
        """Test correlation ID retrieval when available."""
        with patch(
            "app.middlewares.correlation_id.get_correlation_id",
            return_value="correlation-123",
        ):
            correlation_id = get_correlation_id()

            assert correlation_id == "correlation-123"


class TestStructuredJSONFormatter:
    """Test JSON formatter for structured logging."""

    def test_format_includes_standard_fields(self):
        """Test that JSON formatter includes standard fields."""
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/test/test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "timestamp" in log_data
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["line"] == 10

    def test_format_includes_correlation_id_when_available(self):
        """Test that correlation ID is included when available."""
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        with patch(
            "app.logging.get_correlation_id",
            return_value="correlation-123",
        ):
            formatted = formatter.format(record)
            log_data = json.loads(formatted)

            assert log_data["request_id"] == "correlation-123"

    def test_format_includes_log_context(self):
        """Test that log context fields are included."""
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )

        set_log_context(user_id="user123", endpoint="/api/test")

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["user_id"] == "user123"
        assert log_data["endpoint"] == "/api/test"

        clear_log_context()

    def test_format_includes_exception_info(self):
        """Test that exception information is included."""
        formatter = StructuredJSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys

            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert "exception" in log_data
        assert "ValueError: Test error" in log_data["exception"]

    def test_format_truncates_long_messages(self):
        """Test that very long messages are truncated for Loki."""
        formatter = StructuredJSONFormatter()

        # Create a very long message that exceeds Loki limit
        long_message = "x" * 300000  # 300KB message

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg=long_message,
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        # Message should be truncated
        assert "[TRUNCATED]" in log_data["message"]
        assert len(formatted) < 300000


class TestHumanReadableFormatter:
    """Test human-readable formatter for console output."""

    def test_format_includes_correlation_id(self):
        """Test that correlation ID is included in formatted output."""
        formatter = HumanReadableFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch(
            "app.logging.get_correlation_id",
            return_value="correlation-123",
        ):
            formatted = formatter.format(record)

            assert "correlation-123" in formatted

    def test_format_uses_dash_when_no_correlation_id(self):
        """Test that '-' is used when no correlation ID available."""
        formatter = HumanReadableFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        with patch("app.logging.get_correlation_id", return_value=""):
            formatted = formatter.format(record)

            assert "[-]" in formatted


class TestSetupLogging:
    """Test logging setup function."""

    def test_setup_logging_creates_logger(self):
        """Test that setup_logging creates and configures logger."""
        test_logger = setup_logging()

        assert test_logger is not None
        assert isinstance(test_logger, logging.Logger)

    def test_setup_logging_adds_console_handler(self):
        """Test that console handler is added."""
        test_logger = setup_logging()

        # Should have at least console handler
        assert len(test_logger.handlers) > 0

    def test_setup_logging_handles_file_handler_errors(self):
        """Test that file handler errors are handled gracefully."""
        with patch(
            "app.logging.logging.FileHandler",
            side_effect=PermissionError("No write permission"),
        ):
            # Should not raise exception
            test_logger = setup_logging()

            assert test_logger is not None


class TestLoggerIntegration:
    """Integration tests for logger usage."""

    def test_logger_instance_exists(self):
        """Test that logger instance is created."""
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_logger_with_context_fields(self, caplog):
        """Test logging with context fields."""
        clear_log_context()
        set_log_context(user_id="user123", endpoint="/api/test")

        with caplog.at_level(logging.INFO):
            logger.info("Test message with context")

        clear_log_context()

        # caplog should capture the log record
        assert len(caplog.records) > 0

    def test_logger_with_exception(self, caplog):
        """Test logging exceptions."""
        try:
            raise ValueError("Test error")
        except ValueError:
            with caplog.at_level(logging.ERROR):
                logger.error("Error occurred", exc_info=True)

        # Should have error log
        assert any(r.levelname == "ERROR" for r in caplog.records)
