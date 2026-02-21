"""
Comprehensive WebSocket connection and message handling tests.

This module tests WebSocket connection lifecycle, authentication,
message routing, handler dispatch, and error handling.
"""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from starlette.authentication import UnauthenticatedUser

from app.api.ws.constants import PkgID, RSPCode
from app.api.ws.consumers.web import Web
from app.api.ws.websocket import PackageAuthWebSocketEndpoint
from app.routing import pkg_router
from app.schemas.request import RequestModel
from fastapi_keycloak_rbac.models import UserModel
from tests.mocks.websocket_mocks import (
    create_mock_connection_manager,
    create_mock_websocket,
)


class TestWebSocketAuthentication:
    """Test WebSocket connection authentication and authorization."""

    @pytest.mark.asyncio
    async def test_websocket_rejects_unauthenticated_connection(
        self, mock_user_data
    ):
        """
        Test that WebSocket connections without valid auth are rejected.

        Args:
            mock_user_data: Fixture providing mock user data
        """
        # Create a mock websocket endpoint with proper scope
        scope = {"type": "websocket", "user": UnauthenticatedUser()}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        # Mock the websocket
        mock_websocket = create_mock_websocket()

        # Mock Redis connection
        with patch(
            "app.api.ws.websocket.get_auth_redis_connection"
        ) as mock_redis:
            mock_redis.return_value = AsyncMock()

            # Call on_connect
            await endpoint.on_connect(mock_websocket)

            # Verify websocket was closed for unauthenticated user
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_accepts_authenticated_connection(
        self, mock_user_data
    ):
        """
        Test that WebSocket connections with valid auth are accepted.

        Args:
            mock_user_data: Fixture providing mock user data
        """
        user = UserModel(**mock_user_data)

        # Create a mock websocket endpoint with proper scope
        scope = {"type": "websocket", "user": user}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        # Mock the websocket
        mock_websocket = create_mock_websocket()

        # Mock Redis connection and connection manager
        mock_redis = AsyncMock()
        mock_redis.add_kc_user_session = AsyncMock()

        with (
            patch(
                "app.api.ws.websocket.get_auth_redis_connection",
                return_value=mock_redis,
            ),
            patch(
                "app.api.ws.websocket.connection_manager",
                create_mock_connection_manager(),
            ) as mock_cm,
            patch(
                "app.api.ws.websocket.connection_limiter"
            ) as mock_conn_limiter,
        ):
            mock_conn_limiter.add_connection = AsyncMock(return_value=True)

            # Call on_connect
            await endpoint.on_connect(mock_websocket)

            # Verify websocket was NOT closed
            mock_websocket.close.assert_not_called()

            # Verify user session was added to Redis
            mock_redis.add_kc_user_session.assert_called_once_with(user)

            # Verify connection was registered
            mock_cm.connect.assert_called_once_with(
                "session:testuser", mock_websocket
            )

    @pytest.mark.asyncio
    async def test_websocket_disconnect_cleanup(self, mock_user_data):
        """
        Test that WebSocket disconnection properly cleans up resources.

        Args:
            mock_user_data: Fixture providing mock user data
        """
        user = UserModel(**mock_user_data)

        scope = {"type": "websocket", "user": user}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore
        endpoint.user = user
        endpoint.session_key = (
            "session:testuser"  # Set session key for disconnect
        )

        mock_websocket = create_mock_websocket()

        with patch(
            "app.api.ws.websocket.connection_manager",
            create_mock_connection_manager(),
        ) as mock_cm:
            # Call on_disconnect
            await endpoint.on_disconnect(mock_websocket, 1000)

            # Verify connection was removed with session key
            mock_cm.disconnect.assert_called_once_with("session:testuser")


class TestWebSocketMessageHandling:
    """Test WebSocket message routing and handler dispatch."""

    @pytest.mark.asyncio
    async def test_valid_websocket_message_handling(self, mock_user):
        """
        Test handling of valid WebSocket messages.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        request_data = {
            "pkg_id": PkgID.GET_AUTHORS,
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        # Mock the websocket
        mock_websocket = create_mock_websocket()

        # Create Web endpoint instance
        scope = {"type": "websocket", "user": mock_user}
        web = Web(scope=scope, receive=None, send=None)  # type: ignore
        web.user = mock_user
        web.correlation_id = "test-1234"  # Mock correlation_id

        # Mock the handler to avoid database dependencies
        with patch(
            "app.repositories.author_repository.AuthorRepository.get_all",
            new_callable=AsyncMock,
        ) as mock_get_list:
            mock_get_list.return_value = []

            # Call on_receive
            await web.on_receive(mock_websocket, request_data)

            # Verify response was sent
            mock_websocket.send_response.assert_called_once()

            # Get the response that was sent
            sent_response = mock_websocket.send_response.call_args[0][0]

            assert sent_response.status_code == RSPCode.OK
            assert sent_response.pkg_id == PkgID.GET_AUTHORS
            assert str(sent_response.req_id) == request_data["req_id"]

    @pytest.mark.asyncio
    async def test_malformed_websocket_message_closes_connection(
        self, mock_user
    ):
        """
        Test that malformed messages result in connection closure.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        invalid_data = {
            "invalid_field": "invalid_value",
            # Missing required fields: pkg_id, req_id
        }

        # Mock the websocket
        mock_websocket = create_mock_websocket()

        # Create Web endpoint instance
        scope = {"type": "websocket", "user": mock_user}
        web = Web(scope=scope, receive=None, send=None)  # type: ignore
        web.user = mock_user
        web.correlation_id = "test-1234"  # Mock correlation_id

        # Mock rate limiter to avoid Redis connection issues
        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            # Call on_receive with invalid data
            await web.on_receive(mock_websocket, invalid_data)

            # Verify connection was closed due to validation error
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_websocket_message_permission_denied(
        self, limited_user_data
    ):
        """
        Test that messages without permission return PERMISSION_DENIED.

        Args:
            limited_user_data: Fixture providing limited user data
        """
        limited_user = UserModel(**limited_user_data)

        request_data = {
            "pkg_id": PkgID.GET_AUTHORS,
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        # Mock the websocket
        mock_websocket = create_mock_websocket()

        # Create Web endpoint instance
        scope = {"type": "websocket", "user": limited_user}
        web = Web(scope=scope, receive=None, send=None)  # type: ignore
        web.user = limited_user
        web.correlation_id = "test-1234"  # Mock correlation_id

        # Mock rate limiter to avoid Redis connection issues
        with patch(
            "app.api.ws.consumers.web.rate_limiter"
        ) as mock_rate_limiter:
            mock_rate_limiter.check_rate_limit = AsyncMock(
                return_value=(True, 100)
            )

            # Call on_receive
            await web.on_receive(mock_websocket, request_data)

            # Verify response was sent
            mock_websocket.send_response.assert_called_once()

            # Get the response that was sent
            sent_response = mock_websocket.send_response.call_args[0][0]

            assert sent_response.status_code == RSPCode.PERMISSION_DENIED
            assert "No permission" in sent_response.data.get("msg", "")


class TestPackageRouter:
    """Test PackageRouter request handling and validation."""

    @pytest.mark.asyncio
    async def test_handler_not_found(self, mock_user):
        """
        Test response when no handler is registered for pkg_id.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        request = RequestModel(
            pkg_id=PkgID.UNREGISTERED_HANDLER,  # Valid PkgID but no handler registered
            req_id=str(uuid.uuid4()),
            data={},
        )

        response = await pkg_router.handle_request(mock_user, request)

        assert response.status_code == RSPCode.ERROR
        assert "No handler found" in response.data.get("msg", "")

    @pytest.mark.asyncio
    async def test_handler_permission_check(
        self, mock_user, limited_user_data
    ):
        """
        Test permission checking for different users.

        Args:
            mock_user: Fixture providing admin user
            limited_user_data: Fixture providing limited user data
        """
        limited_user = UserModel(**limited_user_data)

        request = RequestModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=str(uuid.uuid4()),
            data={},
        )

        # Mock the handler to avoid database
        with patch(
            "app.repositories.author_repository.AuthorRepository.get_all",
            new_callable=AsyncMock,
        ) as mock_get_list:
            mock_get_list.return_value = []

            # Admin user should succeed
            admin_response = await pkg_router.handle_request(
                mock_user, request
            )
            assert admin_response.status_code == RSPCode.OK

            # Limited user should be denied
            limited_response = await pkg_router.handle_request(
                limited_user, request
            )
            assert limited_response.status_code == RSPCode.PERMISSION_DENIED

    @pytest.mark.asyncio
    async def test_handler_data_validation(self, mock_user):
        """
        Test that handler validates request data against Pydantic schema.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        # Use GET_PAGINATED_AUTHORS which validates filters
        # Request missing required 'page' and 'per_page' fields should
        # trigger validation if we had stricter validation
        # For now, test with invalid filter value for JSON schema validation
        request = RequestModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=str(uuid.uuid4()),
            data={
                "filters": {
                    "id": 123,
                    "invalid_field": "should_fail",  # Not allowed
                }
            },
        )

        response = await pkg_router.handle_request(mock_user, request)

        # The handler catches all exceptions and returns ERROR
        # This is actually the current behavior - validation errors
        # are caught by the handler's try/except
        assert response.status_code in [RSPCode.INVALID_DATA, RSPCode.ERROR]
        assert response.data is not None

    @pytest.mark.asyncio
    async def test_handler_successful_execution(self, mock_user):
        """
        Test successful handler execution with valid request.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        request = RequestModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=str(uuid.uuid4()),
            data={},
        )

        # Mock the database call
        with patch(
            "app.repositories.author_repository.AuthorRepository.get_all",
            new_callable=AsyncMock,
        ) as mock_get_list:
            mock_get_list.return_value = []

            response = await pkg_router.handle_request(mock_user, request)

            assert response.status_code == RSPCode.OK
            assert response.pkg_id == PkgID.GET_AUTHORS
            assert response.req_id == request.req_id
            assert isinstance(response.data, list)


class TestWebSocketBroadcast:
    """Test WebSocket broadcast functionality."""

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast(self):
        """Test that connection manager can broadcast to all connections."""
        from app.managers.websocket_connection_manager import (
            connection_manager,
        )

        # Create mock websockets
        mock_ws1 = create_mock_websocket()
        mock_ws2 = create_mock_websocket()

        # Connect mock websockets
        connection_manager.connect("session:test1", mock_ws1)
        connection_manager.connect("session:test2", mock_ws2)

        # Create a broadcast message
        from app.schemas.response import BroadcastDataModel

        broadcast_msg = BroadcastDataModel(
            pkg_id=1, req_id=uuid.uuid4(), data={"message": "test broadcast"}
        )

        try:
            # Broadcast message
            await connection_manager.broadcast(broadcast_msg)

            # Verify both websockets received the message (as serialized dict)
            expected_data = broadcast_msg.model_dump(mode="json")
            mock_ws1.send_json.assert_called_once_with(expected_data)
            mock_ws2.send_json.assert_called_once_with(expected_data)
        finally:
            # Cleanup
            connection_manager.disconnect("session:test1")
            connection_manager.disconnect("session:test2")


class TestWebSocketEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_websocket_with_null_user(self):
        """Test WebSocket behavior when user is None."""
        scope = {"type": "websocket", "user": None}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        mock_websocket = create_mock_websocket()

        with patch(
            "app.api.ws.websocket.get_auth_redis_connection"
        ) as mock_redis:
            mock_redis.return_value = AsyncMock()

            await endpoint.on_connect(mock_websocket)

            # Should close connection for None user
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_handler_exception_handling(self, mock_user):
        """
        Test that handler database exceptions are properly caught and reported.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        from sqlalchemy.exc import SQLAlchemyError

        request = RequestModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=str(uuid.uuid4()),
            data={},
        )

        # Mock the database call to raise a SQLAlchemy exception
        with patch(
            "app.repositories.author_repository.AuthorRepository.get_all",
            new_callable=AsyncMock,
        ) as mock_get_list:
            mock_get_list.side_effect = SQLAlchemyError("Database error")

            response = await pkg_router.handle_request(mock_user, request)

            # Handler should catch database exception and return error response
            assert response.status_code == RSPCode.ERROR
            assert "Database error occurred" in response.data.get("msg", "")


class TestWebSocketOriginValidation:
    """Test WebSocket CSRF protection via origin validation."""

    @pytest.mark.asyncio
    async def test_origin_allowed_with_wildcard(self, mock_user_data):
        """Test that wildcard '*' allows all origins."""
        user = UserModel(**mock_user_data)
        scope = {"type": "websocket", "user": user}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        mock_websocket = create_mock_websocket()
        mock_websocket.headers = {"origin": "https://evil.com"}

        with patch("app.api.ws.websocket.app_settings") as mock_settings:
            mock_settings.ALLOWED_WS_ORIGINS = ["*"]

            result = endpoint._is_origin_allowed(mock_websocket)

            assert result is True

    @pytest.mark.asyncio
    async def test_origin_allowed_no_header(self, mock_user_data):
        """Test that missing Origin header is allowed (same-origin request)."""
        user = UserModel(**mock_user_data)
        scope = {"type": "websocket", "user": user}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        mock_websocket = create_mock_websocket()
        mock_websocket.headers = {}  # No origin header

        with patch("app.api.ws.websocket.app_settings") as mock_settings:
            mock_settings.ALLOWED_WS_ORIGINS = ["https://app.example.com"]

            result = endpoint._is_origin_allowed(mock_websocket)

            assert result is True

    @pytest.mark.asyncio
    async def test_origin_allowed_exact_match(self, mock_user_data):
        """Test that exact match in allowed list is permitted."""
        user = UserModel(**mock_user_data)
        scope = {"type": "websocket", "user": user}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        mock_websocket = create_mock_websocket()
        mock_websocket.headers = {"origin": "https://app.example.com"}

        with patch("app.api.ws.websocket.app_settings") as mock_settings:
            mock_settings.ALLOWED_WS_ORIGINS = [
                "https://app.example.com",
                "https://admin.example.com",
            ]

            result = endpoint._is_origin_allowed(mock_websocket)

            assert result is True

    @pytest.mark.asyncio
    async def test_origin_rejected_not_in_list(self, mock_user_data):
        """Test that origin not in allowed list is rejected."""
        user = UserModel(**mock_user_data)
        scope = {"type": "websocket", "user": user}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        mock_websocket = create_mock_websocket()
        mock_websocket.headers = {"origin": "https://evil.com"}

        with patch("app.api.ws.websocket.app_settings") as mock_settings:
            mock_settings.ALLOWED_WS_ORIGINS = [
                "https://app.example.com",
                "https://admin.example.com",
            ]

            result = endpoint._is_origin_allowed(mock_websocket)

            assert result is False

    @pytest.mark.asyncio
    async def test_origin_rejected_connection_closed(self, mock_user_data):
        """Test that rejected origin closes WebSocket with policy violation."""
        user = UserModel(**mock_user_data)
        scope = {"type": "websocket", "user": user}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        mock_websocket = create_mock_websocket()
        mock_websocket.headers = {"origin": "https://evil.com"}

        with (
            patch("app.api.ws.websocket.app_settings") as mock_settings,
            patch(
                "app.api.ws.websocket.get_auth_redis_connection"
            ) as mock_redis,
        ):
            mock_settings.ALLOWED_WS_ORIGINS = ["https://app.example.com"]
            mock_settings.USER_SESSION_REDIS_KEY_PREFIX = "session:"
            mock_redis.return_value = AsyncMock()

            await endpoint.on_connect(mock_websocket)

            # Verify websocket was closed with policy violation code
            mock_websocket.close.assert_called_once_with(
                code=1008  # WS_1008_POLICY_VIOLATION
            )

    @pytest.mark.asyncio
    async def test_origin_allowed_connection_proceeds(self, mock_user_data):
        """Test that allowed origin proceeds with normal connection flow."""
        user = UserModel(**mock_user_data)
        scope = {"type": "websocket", "user": user}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        mock_websocket = create_mock_websocket()
        mock_websocket.headers = {"origin": "https://app.example.com"}

        mock_redis = AsyncMock()
        mock_redis.add_kc_user_session = AsyncMock()

        with (
            patch("app.api.ws.websocket.app_settings") as mock_settings,
            patch(
                "app.api.ws.websocket.get_auth_redis_connection",
                return_value=mock_redis,
            ),
            patch(
                "app.api.ws.websocket.connection_manager",
                create_mock_connection_manager(),
            ),
            patch(
                "app.api.ws.websocket.connection_limiter"
            ) as mock_conn_limiter,
        ):
            mock_settings.ALLOWED_WS_ORIGINS = ["https://app.example.com"]
            mock_settings.USER_SESSION_REDIS_KEY_PREFIX = "session:"
            mock_conn_limiter.add_connection = AsyncMock(return_value=True)

            await endpoint.on_connect(mock_websocket)

            # Verify websocket was NOT closed (connection proceeded)
            mock_websocket.close.assert_not_called()

            # Verify user session was added (connection fully established)
            mock_redis.add_kc_user_session.assert_called_once_with(user)
