"""
Comprehensive WebSocket connection and message handling tests.

This module tests WebSocket connection lifecycle, authentication,
message routing, handler dispatch, and error handling.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.authentication import UnauthenticatedUser

from {{cookiecutter.module_name}}.api.ws.constants import PkgID, RSPCode
from {{cookiecutter.module_name}}.api.ws.consumers.web import Web
from {{cookiecutter.module_name}}.api.ws.websocket import (
    PackageAuthWebSocketEndpoint,
)
from {{cookiecutter.module_name}}.managers.websocket_connection_manager import (
    connection_manager,
)
from {{cookiecutter.module_name}}.routing import pkg_router
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.schemas.response import (
    BroadcastDataModel,
    ResponseModel,
)
from {{cookiecutter.module_name}}.schemas.user import UserModel


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
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()

        # Mock Redis connection
        with patch(
            "{{cookiecutter.module_name}}.api.ws.websocket.get_auth_redis_connection"
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
        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()

        # Mock Redis connection and connection manager
        mock_redis = AsyncMock()
        mock_redis.add_kc_user_session = AsyncMock()

        with patch(
            "{{cookiecutter.module_name}}.api.ws.websocket.get_auth_redis_connection",
            return_value=mock_redis,
        ), patch(
            "{{cookiecutter.module_name}}.api.ws.websocket.connection_manager"
        ) as mock_cm, patch(
            "{{cookiecutter.module_name}}.api.ws.websocket.ws_clients", {}
        ):
            mock_cm.connect = MagicMock()

            # Call on_connect
            await endpoint.on_connect(mock_websocket)

            # Verify websocket was NOT closed
            mock_websocket.close.assert_not_called()

            # Verify user session was added to Redis
            mock_redis.add_kc_user_session.assert_called_once_with(user)

            # Verify connection was registered
            mock_cm.connect.assert_called_once_with(mock_websocket)

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

        mock_websocket = MagicMock()

        with patch(
            "{{cookiecutter.module_name}}.api.ws.websocket.connection_manager"
        ) as mock_cm:
            mock_cm.disconnect = MagicMock()

            # Call on_disconnect
            await endpoint.on_disconnect(mock_websocket, 1000)

            # Verify connection was removed
            mock_cm.disconnect.assert_called_once_with(mock_websocket)


class TestWebSocketMessageHandling:
    """Test WebSocket message routing and handler dispatch."""

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
        mock_websocket = MagicMock()
        mock_websocket.close = AsyncMock()

        # Create Web endpoint instance
        scope = {"type": "websocket", "user": mock_user}
        web = Web(scope=scope, receive=None, send=None)  # type: ignore
        web.user = mock_user

        # Call on_receive with invalid data
        await web.on_receive(mock_websocket, invalid_data)

        # Verify connection was closed due to validation error
        mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_valid_websocket_message_with_mock_handler(
        self, mock_user
    ):
        """
        Test handling of valid WebSocket messages with mock handler.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        request_data = {
            "pkg_id": PkgID.TEST_HANDLER,
            "req_id": str(uuid.uuid4()),
            "data": {},
        }

        # Mock the websocket
        mock_websocket = MagicMock()
        mock_websocket.send_response = AsyncMock()

        # Create Web endpoint instance
        scope = {"type": "websocket", "user": mock_user}
        web = Web(scope=scope, receive=None, send=None)  # type: ignore
        web.user = mock_user

        # Mock the package router to return a success response
        mock_response = ResponseModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=uuid.UUID(request_data["req_id"]),
            status_code=RSPCode.OK,
            data={"message": "success"},
        )

        with patch.object(
            pkg_router, "handle_request", return_value=mock_response
        ):
            # Call on_receive
            await web.on_receive(mock_websocket, request_data)

            # Verify response was sent
            mock_websocket.send_response.assert_called_once()

            # Get the response that was sent
            sent_response = mock_websocket.send_response.call_args[0][0]

            assert sent_response.status_code == RSPCode.OK
            assert sent_response.pkg_id == PkgID.TEST_HANDLER
            assert str(sent_response.req_id) == request_data["req_id"]


class TestPackageRouter:
    """Test PackageRouter request handling and validation."""

    @pytest.mark.asyncio
    async def test_handler_not_found(self, mock_user):
        """
        Test response when no handler is registered for pkg_id.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        # TEST_HANDLER exists but has no handler registered by default
        request = RequestModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=str(uuid.uuid4()),
            data={},
        )

        response = await pkg_router.handle_request(mock_user, request)

        assert response.status_code == RSPCode.ERROR
        assert "No handler found" in response.data.get("msg", "")

    @pytest.mark.asyncio
    async def test_handler_with_registered_mock(self, mock_user):
        """
        Test handler execution with dynamically registered mock handler.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        # Create a mock handler
        async def mock_handler(
            _request: RequestModel,
        ) -> ResponseModel:
            return ResponseModel(
                pkg_id=_request.pkg_id,
                req_id=_request.req_id,
                data={"result": "ok"},
            )

        # Temporarily register the handler directly in the registry
        pkg_router.handlers_registry[PkgID.TEST_HANDLER] = mock_handler
        pkg_router.validators_registry[PkgID.TEST_HANDLER] = (None, None)

        try:
            request = RequestModel(
                pkg_id=PkgID.TEST_HANDLER,
                req_id=str(uuid.uuid4()),
                data={},
            )

            response = await pkg_router.handle_request(mock_user, request)

            assert response.status_code == RSPCode.OK
            assert response.pkg_id == PkgID.TEST_HANDLER
            assert response.data.get("result") == "ok"
        finally:
            # Cleanup: remove the handler
            if PkgID.TEST_HANDLER in pkg_router.handlers_registry:
                del pkg_router.handlers_registry[PkgID.TEST_HANDLER]
            if PkgID.TEST_HANDLER in pkg_router.validators_registry:
                del pkg_router.validators_registry[PkgID.TEST_HANDLER]

    @pytest.mark.asyncio
    async def test_handler_permission_denied(self, limited_user_data):
        """
        Test that handler respects permission checks.

        Args:
            limited_user_data: Fixture providing limited user data
        """
        limited_user = UserModel(**limited_user_data)

        # Create a mock handler that requires permissions
        async def mock_handler(
            _request: RequestModel,
        ) -> ResponseModel:
            return ResponseModel(
                pkg_id=_request.pkg_id,
                req_id=_request.req_id,
                data={"result": "ok"},
            )

        # Temporarily register the handler directly in the registry
        pkg_router.handlers_registry[PkgID.TEST_HANDLER] = mock_handler
        pkg_router.validators_registry[PkgID.TEST_HANDLER] = (None, None)

        try:
            request = RequestModel(
                pkg_id=PkgID.TEST_HANDLER,
                req_id=str(uuid.uuid4()),
                data={},
            )

            # Mock RBAC check to return False
            with patch.object(pkg_router, "_check_permission", return_value=False):
                response = await pkg_router.handle_request(
                    limited_user, request
                )

                assert response.status_code == RSPCode.PERMISSION_DENIED
        finally:
            # Cleanup
            if PkgID.TEST_HANDLER in pkg_router.handlers_registry:
                del pkg_router.handlers_registry[PkgID.TEST_HANDLER]
            if PkgID.TEST_HANDLER in pkg_router.validators_registry:
                del pkg_router.validators_registry[PkgID.TEST_HANDLER]

    @pytest.mark.asyncio
    async def test_handler_exception_handling(self, mock_user):
        """
        Test that handler exceptions are properly caught and reported.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        # Create a handler that raises an exception
        async def failing_handler(
            _request: RequestModel,
        ) -> ResponseModel:
            raise ValueError("Test error")

        # Temporarily register the failing handler directly in the registry
        pkg_router.handlers_registry[PkgID.TEST_HANDLER] = failing_handler
        pkg_router.validators_registry[PkgID.TEST_HANDLER] = (None, None)

        try:
            request = RequestModel(
                pkg_id=PkgID.TEST_HANDLER,
                req_id=str(uuid.uuid4()),
                data={},
            )

            # The handler will raise an exception, which should propagate
            # (PackageRouter doesn't catch exceptions from handlers)
            with pytest.raises(ValueError, match="Test error"):
                await pkg_router.handle_request(mock_user, request)
        finally:
            # Cleanup
            if PkgID.TEST_HANDLER in pkg_router.handlers_registry:
                del pkg_router.handlers_registry[PkgID.TEST_HANDLER]
            if PkgID.TEST_HANDLER in pkg_router.validators_registry:
                del pkg_router.validators_registry[PkgID.TEST_HANDLER]


class TestWebSocketBroadcast:
    """Test WebSocket broadcast functionality."""

    @pytest.mark.asyncio
    async def test_connection_manager_broadcast(self):
        """Test that connection manager can broadcast to all connections."""
        # Create mock websockets
        mock_ws1 = MagicMock()
        mock_ws1.send_json = AsyncMock()

        mock_ws2 = MagicMock()
        mock_ws2.send_json = AsyncMock()

        # Connect mock websockets
        connection_manager.connect(mock_ws1)
        connection_manager.connect(mock_ws2)

        try:
            # Create a broadcast message
            broadcast_msg = BroadcastDataModel(
                pkg_id=PkgID.TEST_HANDLER,
                req_id=uuid.uuid4(),
                data={"message": "test broadcast"},
            )

            # Broadcast message
            await connection_manager.broadcast(broadcast_msg)

            # Verify both websockets received the message (as serialized dict)
            expected_data = broadcast_msg.model_dump(mode="json")
            mock_ws1.send_json.assert_called_once_with(expected_data)
            mock_ws2.send_json.assert_called_once_with(expected_data)
        finally:
            # Cleanup
            connection_manager.disconnect(mock_ws1)
            connection_manager.disconnect(mock_ws2)


class TestWebSocketEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.mark.asyncio
    async def test_websocket_with_null_user(self):
        """Test WebSocket behavior when user is None."""
        scope = {"type": "websocket", "user": None}
        endpoint = PackageAuthWebSocketEndpoint(
            scope=scope, receive=None, send=None
        )  # type: ignore

        mock_websocket = MagicMock()
        mock_websocket.accept = AsyncMock()
        mock_websocket.close = AsyncMock()

        with patch(
            "{{cookiecutter.module_name}}.api.ws.websocket.get_auth_redis_connection"
        ) as mock_redis:
            mock_redis.return_value = AsyncMock()

            await endpoint.on_connect(mock_websocket)

            # Should close connection for None user
            mock_websocket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_model_validation(self):
        """Test RequestModel validates required fields."""
        # Valid request
        valid_request = RequestModel(
            pkg_id=PkgID.TEST_HANDLER,
            req_id=str(uuid.uuid4()),
            data={},
        )
        assert valid_request.pkg_id == PkgID.TEST_HANDLER
        assert isinstance(valid_request.req_id, uuid.UUID)

        # Test that missing required fields raises validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            RequestModel(req_id=str(uuid.uuid4()), data={})  # type: ignore

        # Test that missing req_id raises validation error
        with pytest.raises(Exception):  # Pydantic ValidationError
            RequestModel(pkg_id=PkgID.TEST_HANDLER, data={})  # type: ignore

    @pytest.mark.asyncio
    async def test_response_model_construction(self):
        """Test ResponseModel direct construction."""
        req_id = uuid.uuid4()
        data = {"test": "data"}

        response = ResponseModel(
            pkg_id=PkgID.TEST_HANDLER, req_id=req_id, data=data
        )

        assert response.pkg_id == PkgID.TEST_HANDLER
        assert response.req_id == req_id
        assert response.status_code == RSPCode.OK
        assert response.data == data

    @pytest.mark.asyncio
    async def test_response_model_error_helper(self):
        """Test ResponseModel.err_msg() helper method."""
        req_id = uuid.uuid4()
        error_msg = "Test error"

        response = ResponseModel.err_msg(
            PkgID.TEST_HANDLER,
            req_id,
            msg=error_msg,
            status_code=RSPCode.ERROR,
        )

        assert response.pkg_id == PkgID.TEST_HANDLER
        assert response.req_id == req_id
        assert response.status_code == RSPCode.ERROR
        assert response.data.get("msg") == error_msg
