"""
Tests for authentication error handling improvements.

This module tests the new AuthenticationError exception and its integration
with the AuthBackend authentication flow.
"""

import pytest
from unittest.mock import MagicMock, patch
from jwcrypto.jwt import JWTExpired
from keycloak.exceptions import KeycloakAuthenticationError

from app.auth import AuthBackend
from app.exceptions import AuthenticationError
from tests.mocks.auth_mocks import create_mock_keycloak_manager


@pytest.fixture
def mock_kc_manager():
    """Provide a mock Keycloak manager for tests."""
    return create_mock_keycloak_manager()


class TestAuthenticationError:
    """Test the AuthenticationError exception class."""

    def test_authentication_error_creation(self):
        """Test creating AuthenticationError with message."""
        error = AuthenticationError("token_expired: JWT token has expired")

        assert error.message == "token_expired: JWT token has expired"
        assert str(error) == "token_expired: JWT token has expired"

    def test_authentication_error_different_types(self):
        """Test AuthenticationError with different error types."""
        error1 = AuthenticationError("invalid_credentials: User not found")
        error2 = AuthenticationError(
            "token_decode_error: Invalid token format"
        )

        assert "invalid_credentials" in error1.message
        assert "token_decode_error" in error2.message


class TestAuthBackendErrorHandling:
    """Test AuthBackend error handling with specific exceptions."""

    @pytest.mark.asyncio
    async def test_expired_token_raises_authentication_error(
        self, mock_request, mock_kc_manager
    ):
        """Test that expired JWT token raises AuthenticationError."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()

        # Mock request object
        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer expired_token"

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            # Simulate JWT expired exception using async method
            mock_kc_manager.openid.a_decode_token = AsyncMock(
                side_effect=JWTExpired("Token expired")
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            assert "token_expired" in exc_info.value.message
            assert "Token expired" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_invalid_credentials_raises_authentication_error(self):
        """Test that invalid credentials raise AuthenticationError."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer invalid_token"

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("Invalid credentials")
        )

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            assert "invalid_credentials" in exc_info.value.message
            assert "Invalid credentials" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_token_decode_error_raises_authentication_error(self):
        """Test that token decoding errors raise AuthenticationError."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer malformed_token"

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=ValueError("Malformed token")
        )

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            assert "token_decode_error" in exc_info.value.message
            assert "Malformed token" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_websocket_expired_token_raises_authentication_error(
        self,
    ):
        """Test expired token raises AuthenticationError for WebSocket."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()

        # Mock WebSocket request
        request = MagicMock()
        request.scope = {
            "type": "websocket",
            "query_string": b"Authorization=Bearer%20expired_token",
        }

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=JWTExpired("Token expired")
        )

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            assert "token_expired" in exc_info.value.message

    @pytest.mark.asyncio
    async def test_successful_authentication_no_error(self):
        """Test that successful authentication doesn't raise errors."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer valid_token"

        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            return_value={
                "sub": "user-id-123",
                "exp": 1700000000,
                "preferred_username": "testuser",
                "email": "test@example.com",
                "realm_access": {"roles": ["admin"]},
                "azp": "test-client",
                "resource_access": {"test-client": {"roles": ["admin"]}},
            }
        )

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            result = await auth_backend.authenticate(request)

            # Should return AuthCredentials and UserModel
            assert result is not None
            assert len(result) == 2
            credentials, user = result
            assert user.username == "testuser"
            assert user.id == "user-id-123"

    @pytest.mark.asyncio
    async def test_excluded_paths_no_error(self):
        """Test that excluded paths don't raise authentication errors."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/docs"  # Excluded path
        request.headers.get.return_value = ""

        # Should return None without raising error
        result = await auth_backend.authenticate(request)
        assert result is None


class TestErrorHandlingIntegration:
    """Integration tests for error handling in real scenarios."""

    @pytest.mark.asyncio
    async def test_error_contains_useful_debugging_info(self):
        """Test that errors contain useful information for debugging."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer test_token"

        mock_kc_manager = create_mock_keycloak_manager()
        error_message = "Detailed error: signature verification failed"
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=ValueError(error_message)
        )

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            # Error should contain the detailed message
            assert error_message in exc_info.value.message
            assert "token_decode_error" in exc_info.value.message

            # Error string representation should be helpful
            error_str = str(exc_info.value)
            assert "token_decode_error" in error_str
            assert error_message in error_str

    @pytest.mark.asyncio
    async def test_different_error_types_are_distinguishable(self):
        """Test that different error types can be distinguished."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()
        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer token"

        errors_caught = []

        # Test expired token
        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=JWTExpired("expired")
        )
        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            try:
                await auth_backend.authenticate(request)
            except AuthenticationError as e:
                errors_caught.append(e.message)

        # Test invalid credentials
        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=KeycloakAuthenticationError("invalid")
        )
        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            try:
                await auth_backend.authenticate(request)
            except AuthenticationError as e:
                errors_caught.append(e.message)

        # Test decode error
        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token = AsyncMock(
            side_effect=ValueError("decode error")
        )
        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            try:
                await auth_backend.authenticate(request)
            except AuthenticationError as e:
                errors_caught.append(e.message)

        # All three error types should be distinguishable
        assert any("token_expired" in msg for msg in errors_caught)
        assert any("invalid_credentials" in msg for msg in errors_caught)
        assert any("token_decode_error" in msg for msg in errors_caught)
        assert len(errors_caught) == 3  # All three caught
