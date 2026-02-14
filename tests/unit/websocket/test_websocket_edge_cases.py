"""
Comprehensive edge case tests for WebSocket consumers.

This module tests critical edge cases and error conditions in WebSocket
message handling, including malformed data, size limits, connection drops,
and concurrent operations.
"""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette import status

from app.api.ws.constants import PkgID, RSPCode
from app.api.ws.consumers.web import Web
from app.schemas.proto import Request as ProtoRequest
from tests.mocks.websocket_mocks import create_mock_websocket


class TestMalformedMessages:
    """Test handling of malformed and invalid messages."""

    @pytest.mark.asyncio
    async def test_malformed_json_message(self, mock_user):
        """
        Test handling of invalid JSON syntax.

        Verifies that the consumer closes the connection when receiving
        unparsable JSON data.
        """
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        # Invalid JSON - missing required fields and wrong types
        invalid_data = {
            "invalid_field": "invalid_value",
            # Missing pkg_id, req_id
        }

        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            await consumer.on_receive(websocket, invalid_data)

            # Should close connection due to validation error
            websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_malformed_protobuf_message(self, mock_user):
        """
        Test handling of invalid Protobuf data.

        DecodeError from protobuf should be caught and connection closed gracefully.
        """
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        # Corrupted protobuf bytes
        invalid_protobuf = b"\x00\xff\xfe\xfd invalid protobuf"

        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            # DecodeError should be caught, connection closed gracefully
            await consumer.on_receive(websocket, invalid_protobuf)

            # Should close connection due to decode error
            websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_missing_required_field_pkg_id(self, mock_user):
        """Test message missing pkg_id field."""
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        # Missing pkg_id
        invalid_data = {"req_id": str(uuid.uuid4()), "data": {}}

        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            await consumer.on_receive(websocket, invalid_data)

            websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_missing_required_field_req_id(self, mock_user):
        """Test message missing req_id field."""
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        # Missing req_id
        invalid_data = {"pkg_id": PkgID.GET_AUTHORS, "data": {}}

        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            await consumer.on_receive(websocket, invalid_data)

            websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_message_with_invalid_pkg_id_type(self, mock_user):
        """Test message with pkg_id as string instead of int."""
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        # pkg_id as string
        invalid_data = {
            "pkg_id": "not_an_int",
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            await consumer.on_receive(websocket, invalid_data)

            websocket.close.assert_called_once()


class TestMessageSizeLimits:
    """Test message size limit enforcement."""

    @pytest.mark.asyncio
    async def test_oversized_json_data_field(self, mock_user):
        """
        Test handling of excessively large data field.

        Note: WebSocket frame size limits are typically enforced by the
        WebSocket server layer, but we test application-level handling.
        """
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        # Create very large data payload (1MB+)
        large_data = {"large_field": "x" * (1024 * 1024)}  # 1MB of 'x'

        request_data = {
            "pkg_id": PkgID.GET_AUTHORS,
            "req_id": str(uuid.uuid4()),
            "data": large_data,
        }

        with (
            patch(
                "app.api.ws.consumers.web.rate_limiter"
            ) as mock_rate_limiter,
            patch("app.api.ws.consumers.web.pkg_router") as mock_router,
        ):
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            # Should still process (no hard size limit in app layer)
            # But we can verify it gets to the router
            mock_router.handle_request = AsyncMock(
                return_value=MagicMock(
                    status_code=RSPCode.OK,
                    pkg_id=PkgID.GET_AUTHORS,
                    req_id=request_data["req_id"],
                    data={},
                )
            )

            await consumer.on_receive(websocket, request_data)

            # Should attempt to process (router handles validation)
            mock_router.handle_request.assert_called_once()


class TestConcurrentMessageHandling:
    """Test concurrent message processing and race conditions."""

    @pytest.mark.asyncio
    async def test_concurrent_messages_from_single_connection(self, mock_user):
        """
        Test handling of multiple concurrent messages.

        Simulates a client sending multiple messages rapidly before
        the first one completes processing.
        """
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        # Create multiple concurrent requests
        requests = [
            {
                "pkg_id": PkgID.GET_AUTHORS,
                "req_id": str(uuid.uuid4()),
                "data": {},
            }
            for _ in range(10)
        ]

        with (
            patch(
                "app.api.ws.consumers.web.rate_limiter"
            ) as mock_rate_limiter,
            patch(
                "app.repositories.author_repository.AuthorRepository.get_all"
            ) as mock_get_all,
        ):
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )
            mock_get_all.return_value = []

            # Send all messages concurrently
            tasks = [consumer.on_receive(websocket, req) for req in requests]
            await asyncio.gather(*tasks)

            # All messages should be processed
            assert websocket.send_response.call_count == 10

    @pytest.mark.asyncio
    async def test_message_processing_during_disconnect(self, mock_user):
        """
        Test message processing when connection drops mid-processing.

        RuntimeError from send_response should be caught and handled gracefully.
        """
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        request_data = {
            "pkg_id": PkgID.GET_AUTHORS,
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        async def slow_handler(*args, **kwargs):
            """Simulate slow handler that takes time to process."""
            await asyncio.sleep(0.1)
            return MagicMock(
                status_code=RSPCode.OK,
                pkg_id=PkgID.GET_AUTHORS,
                req_id=request_data["req_id"],
                data=[],
            )

        with (
            patch(
                "app.api.ws.consumers.web.rate_limiter"
            ) as mock_rate_limiter,
            patch("app.api.ws.consumers.web.pkg_router") as mock_router,
        ):
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )
            mock_router.handle_request = slow_handler

            # Simulate send_response failing (connection closed)
            websocket.send_response.side_effect = RuntimeError(
                "Connection closed"
            )

            # RuntimeError should be caught and handled gracefully
            await consumer.on_receive(websocket, request_data)

            # Connection error should be logged but not raise exception


class TestRateLimitEdgeCases:
    """Test rate limiting edge cases for WebSocket messages."""

    @pytest.mark.asyncio
    async def test_message_rate_limit_exceeded(self, mock_user):
        """Test that rate limit exceeded closes connection."""
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        request_data = {
            "pkg_id": PkgID.GET_AUTHORS,
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            # Simulate rate limit exceeded
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(False, 0)
            )

            await consumer.on_receive(websocket, request_data)

            # Should close connection with policy violation
            websocket.close.assert_called_once_with(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Message rate limit exceeded",
            )

    @pytest.mark.asyncio
    async def test_rate_limiter_failure_allows_message(self, mock_user):
        """
        Test fail-open behavior when rate limiter fails.

        Rate limiter exceptions should be caught and message allowed through (fail-open).
        """
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        request_data = {
            "pkg_id": PkgID.GET_AUTHORS,
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        with (
            patch(
                "app.api.ws.consumers.web.rate_limiter"
            ) as mock_rate_limiter,
            patch("app.api.ws.consumers.web.pkg_router") as mock_router,
        ):
            # Simulate Redis failure
            mock_rate_limiter.check_rate_limit = AsyncMock(
                side_effect=Exception("Redis connection failed")
            )

            # Mock successful handler response
            mock_router.handle_request = AsyncMock(
                return_value=MagicMock(
                    status_code=RSPCode.OK,
                    pkg_id=PkgID.GET_AUTHORS,
                    req_id=request_data["req_id"],
                    data=[],
                )
            )

            # Should fail-open: allow message through despite rate limiter error
            await consumer.on_receive(websocket, request_data)

            # Handler should have been called (fail-open behavior)
            mock_router.handle_request.assert_called_once()


class TestProtobufEdgeCases:
    """Test Protocol Buffers format edge cases."""

    @pytest.mark.asyncio
    async def test_empty_protobuf_message(self, mock_user):
        """
        Test handling of empty protobuf bytes.

        Empty protobuf parses but creates invalid PkgID=0 which should be caught.
        """
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            # Empty bytes parse but create invalid PkgID=0, ValueError should be caught
            await consumer.on_receive(websocket, b"")

            # Should close connection due to ValueError
            websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_valid_protobuf_message_processing(self, mock_user):
        """Test successful protobuf message processing."""
        # Include format=protobuf in query string for strategy selection
        consumer = Web(
            scope={
                "type": "websocket",
                "user": mock_user,
                "query_string": b"format=protobuf",
            },
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        # Create valid protobuf message
        proto_request = ProtoRequest()
        proto_request.pkg_id = PkgID.GET_AUTHORS
        proto_request.req_id = str(uuid.uuid4())
        proto_request.data_json = json.dumps({})

        protobuf_bytes = proto_request.SerializeToString()

        with (
            patch(
                "app.api.ws.consumers.web.rate_limiter"
            ) as mock_rate_limiter,
            patch(
                "app.repositories.author_repository.AuthorRepository.get_all"
            ) as mock_get_all,
        ):
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )
            mock_get_all.return_value = []

            await consumer.on_receive(websocket, protobuf_bytes)

            # Should send protobuf response
            websocket.send_bytes.assert_called_once()


class TestAuditLoggingEdgeCases:
    """Test audit logging during WebSocket message handling."""

    @pytest.mark.asyncio
    async def test_audit_log_on_successful_message(self, mock_user):
        """Test that successful messages are audit logged."""
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        request_data = {
            "pkg_id": PkgID.GET_AUTHORS,
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        with (
            patch(
                "app.api.ws.consumers.web.rate_limiter"
            ) as mock_rate_limiter,
            patch(
                "app.repositories.author_repository.AuthorRepository.get_all"
            ) as mock_get_all,
            patch(
                "app.api.ws.consumers.web.log_user_action"
            ) as mock_log_action,
        ):
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )
            mock_get_all.return_value = []

            await consumer.on_receive(websocket, request_data)

            # Audit log should be called
            mock_log_action.assert_called_once()
            call_kwargs = mock_log_action.call_args[1]
            assert call_kwargs["username"] == mock_user.username
            assert call_kwargs["outcome"] == "success"

    @pytest.mark.asyncio
    async def test_audit_log_on_error_message(self, mock_user):
        """
        Test that failed messages are audit logged with error outcome.

        Handler exceptions should be caught, audit logged, and connection closed.
        """
        consumer = Web(
            scope={"type": "websocket", "user": mock_user},
            receive=None,
            send=None,
        )
        consumer.user = mock_user
        consumer.correlation_id = "test-1234"

        websocket = create_mock_websocket()

        request_data = {
            "pkg_id": PkgID.GET_AUTHORS,
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        with (
            patch(
                "app.api.ws.consumers.web.rate_limiter"
            ) as mock_rate_limiter,
            patch("app.api.ws.consumers.web.pkg_router") as mock_router,
            patch(
                "app.api.ws.consumers.web.log_user_action"
            ) as mock_log_action,
        ):
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            # Simulate handler exception
            mock_router.handle_request = AsyncMock(
                side_effect=Exception("Database error")
            )

            # Handler exception should be caught and audit logged
            await consumer.on_receive(websocket, request_data)

            # Should close connection after error
            websocket.close.assert_called_once()

            # Should audit log the error
            mock_log_action.assert_called_once()
            call_kwargs = mock_log_action.call_args[1]
            assert call_kwargs["outcome"] == "error"
            assert "Database error" in call_kwargs["error_message"]
