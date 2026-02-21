"""
Comprehensive tests for AuthBackend.authenticate() method.

This module tests the authentication integration including:
- Token decoding via the injected manager
- WebSocket authentication success scenarios
- Edge cases (missing/malformed tokens)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from jwcrypto.jwt import JWTExpired
from keycloak.exceptions import KeycloakAuthenticationError

from fastapi_keycloak_rbac.backend import AuthBackend
from fastapi_keycloak_rbac.exceptions import AuthenticationError
from tests.mocks.auth_mocks import create_mock_keycloak_manager


class TestAuthBackendTokenDecoding:
    """Test token decoding behaviour in authenticate() method."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user(self, mock_user_data):
        """Test that a valid token is decoded and returns a UserModel."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(return_value=mock_user_data)

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer valid_token"

        result = await auth_backend.authenticate(request)

        assert result is not None
        _, user = result
        assert user.username == mock_user_data["preferred_username"]
        mock_manager.decode_token.assert_called_once_with("valid_token")

    @pytest.mark.asyncio
    async def test_token_decoded_once_per_request(self, mock_user_data):
        """Test that decode_token is called exactly once per request."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(return_value=mock_user_data)

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer some_token"

        await auth_backend.authenticate(request)

        mock_manager.decode_token.assert_called_once_with("some_token")


class TestAuthBackendWebSocketSuccess:
    """Test successful WebSocket authentication scenarios."""

    @pytest.mark.asyncio
    async def test_websocket_auth_with_query_param(self, mock_user_data):
        """Test WebSocket authentication with token in query parameter."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(return_value=mock_user_data)

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"Authorization=Bearer%20ws_valid_token",
        }

        result = await auth_backend.authenticate(request)

        assert result is not None
        _, user = result
        assert user.username == mock_user_data["preferred_username"]
        assert user.id == mock_user_data["sub"]
        mock_manager.decode_token.assert_called_once_with("ws_valid_token")

    @pytest.mark.asyncio
    async def test_websocket_auth_url_encoded_token(self, mock_user_data):
        """Test WebSocket authentication handles URL-encoded tokens."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(return_value=mock_user_data)

        auth_backend = AuthBackend(manager=mock_manager)

        # Token with special characters that need URL encoding
        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"Authorization=Bearer%20token%2Bwith%2Bplus",
        }

        result = await auth_backend.authenticate(request)

        assert result is not None
        mock_manager.decode_token.assert_called_once_with("token+with+plus")


class TestAuthBackendEdgeCases:
    """Test edge cases in authentication."""

    @pytest.mark.asyncio
    async def test_missing_authorization_header(self):
        """Test authentication with missing Authorization header."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid token")
        )

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = ""  # No Authorization header

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_backend.authenticate(request)

        assert "invalid_credentials" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_malformed_authorization_header_no_bearer(self):
        """Test authentication with malformed header (missing Bearer prefix)."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid token")
        )

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "just_token_no_bearer"

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_backend.authenticate(request)

        assert "invalid_credentials" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_websocket_missing_authorization_query_param(self):
        """Test WebSocket authentication with missing Authorization query param."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid token")
        )

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"other_param=value",  # No Authorization
        }

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_backend.authenticate(request)

        assert "invalid_credentials" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_empty_query_string_websocket(self):
        """Test WebSocket authentication with empty query string."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid token")
        )

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {"type": "websocket", "query_string": b""}

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_backend.authenticate(request)

        assert "invalid_credentials" in exc_info.value.message


class TestAuthBackendRequestTypeDifferentiation:
    """Test that HTTP and WebSocket requests are properly differentiated."""

    @pytest.mark.asyncio
    async def test_http_request_extracts_from_header(self, mock_user_data):
        """Test that HTTP requests extract token from Authorization header."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(return_value=mock_user_data)

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer http_token"

        await auth_backend.authenticate(request)

        mock_manager.decode_token.assert_called_once_with("http_token")

    @pytest.mark.asyncio
    async def test_websocket_request_extracts_from_query_string(
        self, mock_user_data
    ):
        """Test that WebSocket requests extract token from query string."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(return_value=mock_user_data)

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"Authorization=Bearer%20ws_token",
        }

        await auth_backend.authenticate(request)

        mock_manager.decode_token.assert_called_once_with("ws_token")

    @pytest.mark.asyncio
    async def test_expired_token_raises_authentication_error(self):
        """Test that expired JWT token raises AuthenticationError."""
        mock_manager = create_mock_keycloak_manager()
        mock_manager.decode_token = AsyncMock(
            side_effect=JWTExpired("Token expired")
        )

        auth_backend = AuthBackend(manager=mock_manager)

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer expired_token"

        with pytest.raises(AuthenticationError) as exc_info:
            await auth_backend.authenticate(request)

        assert "token_expired" in exc_info.value.message
