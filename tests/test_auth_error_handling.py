"""
Tests for authentication error handling improvements.

This module tests the new AuthenticationError exception and its integration
with the AuthBackend authentication flow.
"""

import pytest
from unittest.mock import MagicMock, patch
from jwcrypto.jwt import JWTExpired
from keycloak.exceptions import KeycloakAuthenticationError

from app.auth import AuthBackend, AuthenticationError
from tests.mocks.auth_mocks import create_mock_keycloak_manager


@pytest.fixture
def mock_kc_manager():
    """Provide a mock Keycloak manager for tests."""
    return create_mock_keycloak_manager()


class TestAuthenticationError:
    """Test the AuthenticationError exception class."""

    def test_authentication_error_creation(self):
        """Test creating AuthenticationError with reason and detail."""
        error = AuthenticationError("token_expired", "JWT token has expired")

        assert error.reason == "token_expired"
        assert error.detail == "JWT token has expired"
        assert str(error) == "token_expired: JWT token has expired"

    def test_authentication_error_different_reasons(self):
        """Test AuthenticationError with different reason codes."""
        error1 = AuthenticationError("invalid_credentials", "User not found")
        error2 = AuthenticationError(
            "token_decode_error", "Invalid token format"
        )

        assert error1.reason == "invalid_credentials"
        assert error2.reason == "token_decode_error"


class TestAuthBackendErrorHandling:
    """Test AuthBackend error handling with specific exceptions."""

    @pytest.mark.asyncio
    async def test_expired_token_raises_authentication_error(
        self, mock_request, mock_kc_manager
    ):
        """Test that expired JWT token raises AuthenticationError."""
        auth_backend = AuthBackend()

        # Mock request object
        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer expired_token"

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            # Simulate JWT expired exception using async method
            mock_kc_manager.openid.a_decode_token.side_effect = JWTExpired(
                "Token expired"
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            assert exc_info.value.reason == "token_expired"
            assert "Token expired" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_invalid_credentials_raises_authentication_error(self):
        """Test that invalid credentials raise AuthenticationError."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer invalid_token"

        with patch("app.auth.KeycloakManager") as mock_kc_manager_class:
            mock_kc_manager = MagicMock()
            mock_kc_manager_class.return_value = mock_kc_manager

            # Simulate Keycloak authentication error (use AsyncMock)
            mock_kc_manager.openid.a_decode_token = AsyncMock(
                side_effect=KeycloakAuthenticationError("Invalid credentials")
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            assert exc_info.value.reason == "invalid_credentials"
            assert "Invalid credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_token_decode_error_raises_authentication_error(self):
        """Test that token decoding errors raise AuthenticationError."""
        from unittest.mock import AsyncMock

        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer malformed_token"

        with patch("app.auth.KeycloakManager") as mock_kc_manager_class:
            mock_kc_manager = MagicMock()
            mock_kc_manager_class.return_value = mock_kc_manager

            # Simulate ValueError during token decode (use AsyncMock)
            mock_kc_manager.openid.a_decode_token = AsyncMock(
                side_effect=ValueError("Malformed token")
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            assert exc_info.value.reason == "token_decode_error"
            assert "Malformed token" in exc_info.value.detail

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

        with patch("app.auth.KeycloakManager") as mock_kc_manager_class:
            mock_kc_manager = MagicMock()
            mock_kc_manager_class.return_value = mock_kc_manager

            # Use AsyncMock for async method
            mock_kc_manager.openid.a_decode_token = AsyncMock(
                side_effect=JWTExpired("Token expired")
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            assert exc_info.value.reason == "token_expired"

    @pytest.mark.asyncio
    async def test_successful_authentication_no_error(self):
        """Test that successful authentication doesn't raise errors."""
        auth_backend = AuthBackend()

        request = MagicMock()
        request.scope = {"type": "http"}
        request.url.path = "/api/test"
        request.headers.get.return_value = "Bearer valid_token"

        with patch("app.auth.KeycloakManager") as mock_kc_manager_class:
            mock_kc_manager = MagicMock()
            mock_kc_manager_class.return_value = mock_kc_manager

            # Simulate successful token decode (async method)
            from unittest.mock import AsyncMock

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

        with patch("app.auth.KeycloakManager") as mock_kc_manager_class:
            mock_kc_manager = MagicMock()
            mock_kc_manager_class.return_value = mock_kc_manager

            error_message = "Detailed error: signature verification failed"
            # Use AsyncMock for async method
            mock_kc_manager.openid.a_decode_token = AsyncMock(
                side_effect=ValueError(error_message)
            )

            with pytest.raises(AuthenticationError) as exc_info:
                await auth_backend.authenticate(request)

            # Error should contain the detailed message
            assert error_message in exc_info.value.detail
            assert exc_info.value.reason == "token_decode_error"

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
        with patch("app.auth.KeycloakManager") as mock_kc_manager_class:
            mock_kc_manager = MagicMock()
            mock_kc_manager_class.return_value = mock_kc_manager
            # Use AsyncMock for async method
            mock_kc_manager.openid.a_decode_token = AsyncMock(
                side_effect=JWTExpired("expired")
            )

            try:
                await auth_backend.authenticate(request)
            except AuthenticationError as e:
                errors_caught.append(e.reason)

        # Test invalid credentials
        with patch("app.auth.KeycloakManager") as mock_kc_manager_class:
            mock_kc_manager = MagicMock()
            mock_kc_manager_class.return_value = mock_kc_manager
            # Use AsyncMock for async method
            mock_kc_manager.openid.a_decode_token = AsyncMock(
                side_effect=KeycloakAuthenticationError("invalid")
            )

            try:
                await auth_backend.authenticate(request)
            except AuthenticationError as e:
                errors_caught.append(e.reason)

        # Test decode error
        with patch("app.auth.KeycloakManager") as mock_kc_manager_class:
            mock_kc_manager = MagicMock()
            mock_kc_manager_class.return_value = mock_kc_manager
            # Use AsyncMock for async method
            mock_kc_manager.openid.a_decode_token = AsyncMock(
                side_effect=ValueError("decode error")
            )

            try:
                await auth_backend.authenticate(request)
            except AuthenticationError as e:
                errors_caught.append(e.reason)

        # All three error types should be distinguishable
        assert "token_expired" in errors_caught
        assert "invalid_credentials" in errors_caught
        assert "token_decode_error" in errors_caught
        assert len(set(errors_caught)) == 3  # All unique
