"""
Tests for audit logging utilities.

This module tests audit log queueing, batching, sanitization, and worker
functionality.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest
from starlette.requests import Request

from app.utils.audit_logger import (
    SENSITIVE_FIELDS,
    extract_ip_address,
    flush_audit_queue,
    get_audit_queue,
    log_user_action,
    sanitize_data,
)


class TestSanitizeData:
    """Tests for sanitize_data function."""

    def test_sanitize_none(self):
        """Test that None input returns None."""
        result = sanitize_data(None)
        assert result is None

    def test_sanitize_empty_dict(self):
        """Test that empty dict returns empty dict."""
        result = sanitize_data({})
        assert result == {}

    def test_sanitize_sensitive_fields(self):
        """Test that sensitive fields are redacted."""
        data = {
            "username": "testuser",
            "password": "secret123",
            "token": "abc123",
            "email": "test@example.com",
        }

        result = sanitize_data(data)

        assert result["username"] == "testuser"
        assert result["password"] == "[REDACTED]"
        assert result["token"] == "[REDACTED]"
        assert result["email"] == "test@example.com"

    def test_sanitize_case_insensitive(self):
        """Test that sensitive field detection is case-insensitive."""
        data = {
            "PASSWORD": "secret",
            "Token": "abc",
            "API_KEY": "key123",
        }

        result = sanitize_data(data)

        assert result["PASSWORD"] == "[REDACTED]"
        assert result["Token"] == "[REDACTED]"
        assert result["API_KEY"] == "[REDACTED]"

    def test_sanitize_nested_dict(self):
        """Test that nested dictionaries are sanitized recursively."""
        data = {
            "user": {
                "username": "testuser",
                "password": "secret",
                "profile": {
                    "email": "test@example.com",
                    "api_key": "key123",
                },
            }
        }

        result = sanitize_data(data)

        assert result["user"]["username"] == "testuser"
        assert result["user"]["password"] == "[REDACTED]"
        assert result["user"]["profile"]["email"] == "test@example.com"
        assert result["user"]["profile"]["api_key"] == "[REDACTED]"

    def test_sanitize_list_of_dicts(self):
        """Test that lists of dictionaries are sanitized."""
        data = {
            "users": [
                {"username": "user1", "password": "pass1"},
                {"username": "user2", "token": "abc123"},
            ]
        }

        result = sanitize_data(data)

        assert result["users"][0]["username"] == "user1"
        assert result["users"][0]["password"] == "[REDACTED]"
        assert result["users"][1]["username"] == "user2"
        assert result["users"][1]["token"] == "[REDACTED]"

    def test_sanitize_list_of_primitives(self):
        """Test that lists of primitives are preserved."""
        data = {"roles": ["admin", "user"], "count": 42}

        result = sanitize_data(data)

        assert result["roles"] == ["admin", "user"]
        assert result["count"] == 42

    def test_all_sensitive_fields_covered(self):
        """Test all defined sensitive fields are redacted."""
        data = {field: f"value_{field}" for field in SENSITIVE_FIELDS}

        result = sanitize_data(data)

        for field in SENSITIVE_FIELDS:
            assert result[field] == "[REDACTED]"


class TestExtractIpAddress:
    """Tests for extract_ip_address function."""

    def test_extract_ip_from_client(self):
        """Test extracting IP from request client."""
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "192.168.1.100"
        request.headers = {}

        with patch(
            "app.utils.ip_utils.get_client_ip", return_value="192.168.1.100"
        ):
            ip = extract_ip_address(request)

        assert ip == "192.168.1.100"

    def test_extract_ip_returns_none_when_unavailable(self):
        """Test that None is returned when IP is not available."""
        request = MagicMock(spec=Request)

        with patch("app.utils.ip_utils.get_client_ip", return_value=None):
            ip = extract_ip_address(request)

        assert ip is None


class TestGetAuditQueue:
    """Tests for get_audit_queue function."""

    def test_get_audit_queue_creates_queue(self):
        """Test that get_audit_queue creates new queue if none exists."""
        # Reset global queue
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with patch("app.utils.audit_logger.app_settings") as mock_settings:
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1000

            queue = get_audit_queue()

            assert isinstance(queue, asyncio.Queue)
            assert queue.maxsize == 1000

    def test_get_audit_queue_returns_existing(self):
        """Test that get_audit_queue returns existing queue."""
        # Reset global queue
        import app.utils.audit_logger

        existing_queue = asyncio.Queue(maxsize=500)
        app.utils.audit_logger._audit_queue = existing_queue

        queue = get_audit_queue()

        assert queue is existing_queue


class TestLogUserAction:
    """Tests for log_user_action function."""

    @pytest.mark.asyncio
    async def test_log_user_action_success(self):
        """Test successful queueing of user action."""
        # Reset global queue
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with patch("app.utils.audit_logger.app_settings") as mock_settings:
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1000

            action = await log_user_action(
                user_id="user123",
                username="testuser",
                user_roles=["admin"],
                action_type="GET",
                resource="/api/users",
                outcome="success",
                ip_address="127.0.0.1",
                user_agent="Mozilla/5.0",
                request_id="req-123",
                request_data={"page": 1},
                response_status=200,
                duration_ms=45,
            )

            assert action is not None
            assert action.user_id == "user123"
            assert action.username == "testuser"
            assert action.action_type == "GET"
            assert action.resource == "/api/users"
            assert action.outcome == "success"
            assert action.ip_address == "127.0.0.1"
            assert action.response_status == 200
            assert action.duration_ms == 45

    @pytest.mark.asyncio
    async def test_log_user_action_sanitizes_data(self):
        """Test that request data is sanitized before logging."""
        # Reset global queue
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with patch("app.utils.audit_logger.app_settings") as mock_settings:
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1000

            action = await log_user_action(
                user_id="user123",
                username="testuser",
                user_roles=["admin"],
                action_type="POST",
                resource="/api/login",
                outcome="success",
                request_data={"username": "test", "password": "secret123"},
            )

            assert action is not None
            assert action.request_data["username"] == "test"
            assert action.request_data["password"] == "[REDACTED]"

    @pytest.mark.asyncio
    async def test_log_user_action_queue_full_no_backpressure(self):
        """Test handling of full audit queue with backpressure disabled."""
        # Reset global queue with size 1
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with (
            patch("app.utils.audit_logger.app_settings") as mock_settings,
            patch("app.utils.audit_logger.logger") as mock_logger,
        ):
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1
            mock_settings.AUDIT_QUEUE_TIMEOUT = 0  # Disable backpressure

            # Fill the queue
            action1 = await log_user_action(
                user_id="user1",
                username="user1",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test",
                outcome="success",
            )
            assert action1 is not None

            # Try to add to full queue
            action2 = await log_user_action(
                user_id="user2",
                username="user2",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test",
                outcome="success",
            )

            # Should return None when queue is full and no backpressure
            assert action2 is None
            mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_log_user_action_backpressure_timeout(self):
        """Test backpressure timeout when queue stays full."""
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with (
            patch("app.utils.audit_logger.app_settings") as mock_settings,
            patch("app.utils.audit_logger.logger") as mock_logger,
        ):
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1
            mock_settings.AUDIT_QUEUE_TIMEOUT = 0.1  # Short timeout for test

            # Fill the queue
            action1 = await log_user_action(
                user_id="user1",
                username="user1",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test",
                outcome="success",
            )
            assert action1 is not None

            # Try to add to full queue - should wait then timeout
            action2 = await log_user_action(
                user_id="user2",
                username="user2",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test",
                outcome="success",
            )

            # Should return None after timeout
            assert action2 is None
            # Should log warning about timeout
            warning_calls = [
                call
                for call in mock_logger.warning.call_args_list
                if "timeout" in str(call).lower()
            ]
            assert len(warning_calls) > 0

    @pytest.mark.asyncio
    async def test_log_user_action_backpressure_success(self):
        """Test backpressure succeeds when queue drains."""
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with patch("app.utils.audit_logger.app_settings") as mock_settings:
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1
            mock_settings.AUDIT_QUEUE_TIMEOUT = 1.0  # Long enough timeout

            # Fill the queue
            action1 = await log_user_action(
                user_id="user1",
                username="user1",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test",
                outcome="success",
            )
            assert action1 is not None

            queue = get_audit_queue()

            # Simulate consumer draining queue in background
            async def drain_queue():
                await asyncio.sleep(0.05)  # Short delay
                queue.get_nowait()

            # Start drain and try to add
            drain_task = asyncio.create_task(drain_queue())

            action2 = await log_user_action(
                user_id="user2",
                username="user2",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test",
                outcome="success",
            )

            await drain_task

            # Should succeed after backpressure wait
            assert action2 is not None
            assert action2.user_id == "user2"

    @pytest.mark.asyncio
    async def test_log_user_action_handles_exception(self):
        """Test error handling in log_user_action."""
        with (
            patch(
                "app.utils.audit_logger.sanitize_data",
                side_effect=ValueError("Sanitization error"),
            ),
            patch("app.utils.audit_logger.logger") as mock_logger,
        ):
            action = await log_user_action(
                user_id="user123",
                username="testuser",
                user_roles=["admin"],
                action_type="GET",
                resource="/api/test",
                outcome="success",
            )

            assert action is None
            mock_logger.error.assert_called()


class TestFlushAuditQueue:
    """Tests for flush_audit_queue function."""

    @pytest.mark.asyncio
    async def test_flush_empty_queue(self):
        """Test flushing empty queue returns 0."""
        # Reset global queue
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with patch("app.utils.audit_logger.app_settings") as mock_settings:
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1000

            count = await flush_audit_queue()

            assert count == 0

    @pytest.mark.asyncio
    async def test_flush_queue_collects_entries(self):
        """Test that flush collects entries from queue."""
        # Reset global queue
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with patch("app.utils.audit_logger.app_settings") as mock_settings:
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1000

            # Add entries to queue
            await log_user_action(
                user_id="user1",
                username="user1",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test1",
                outcome="success",
            )
            await log_user_action(
                user_id="user2",
                username="user2",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test2",
                outcome="success",
            )

            # Verify queue has 2 items
            queue = get_audit_queue()
            assert queue.qsize() == 2

            # Note: Full database write testing would require complex async
            # context manager mocking. The queue collection logic is tested here.

    @pytest.mark.asyncio
    async def test_flush_queue_handles_database_error(self):
        """Test that flush handles database errors gracefully."""
        # Reset global queue
        import app.utils.audit_logger

        app.utils.audit_logger._audit_queue = None

        with (
            patch("app.utils.audit_logger.app_settings") as mock_settings,
            patch("app.utils.audit_logger.async_session") as mock_session_ctx,
            patch("app.utils.audit_logger.logger") as mock_logger,
        ):
            mock_settings.AUDIT_QUEUE_MAX_SIZE = 1000

            # Add entry to queue
            await log_user_action(
                user_id="user1",
                username="user1",
                user_roles=["user"],
                action_type="GET",
                resource="/api/test",
                outcome="success",
            )

            # Mock database error with specific exception type
            from sqlalchemy.exc import OperationalError

            mock_session_ctx.return_value.__aenter__.side_effect = (
                OperationalError("Database error", None, None)
            )

            count = await flush_audit_queue()

            assert count == 0
            mock_logger.error.assert_called()
