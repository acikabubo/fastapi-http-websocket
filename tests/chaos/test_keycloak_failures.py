"""
Chaos tests for Keycloak failure scenarios.

Tests application resilience when Keycloak is unavailable or fails.

Run with: pytest tests/chaos/test_keycloak_failures.py -v -m chaos
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from keycloak.exceptions import (
    KeycloakAuthenticationError,
    KeycloakConnectionError,
    KeycloakGetError,
)

from app.managers.keycloak_manager import KeycloakManager

# Mark all tests in this module as chaos tests
pytestmark = pytest.mark.chaos


class TestKeycloakConnectionFailures:
    """Tests for Keycloak connection failure scenarios."""

    @pytest.mark.asyncio
    async def test_keycloak_server_unavailable(self):
        """Test authentication when Keycloak server is unavailable."""
        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.a_token = AsyncMock(
                side_effect=KeycloakConnectionError("Connection refused")
            )
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # Login should raise connection error
            with pytest.raises(KeycloakConnectionError):
                await manager.login_async("testuser", "password")

    @pytest.mark.asyncio
    async def test_keycloak_timeout(self):
        """Test authentication when Keycloak request times out."""
        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.a_token = AsyncMock(
                side_effect=KeycloakConnectionError("Request timeout")
            )
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # Should raise timeout error
            with pytest.raises(KeycloakConnectionError):
                await manager.login_async("testuser", "password")

    def test_invalid_token_decode(self):
        """Test token decoding when Keycloak validation fails."""
        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.decode_token = Mock(
                side_effect=KeycloakGetError("Invalid token signature")
            )
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # Token decode should raise error
            with pytest.raises(KeycloakGetError):
                manager.openid.decode_token("invalid_token")


class TestKeycloakAuthenticationErrors:
    """Tests for Keycloak authentication error scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_credentials(self):
        """Test login with invalid credentials."""
        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.a_token = AsyncMock(
                side_effect=KeycloakAuthenticationError(
                    "Invalid user credentials"
                )
            )
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # Should raise authentication error
            with pytest.raises(KeycloakAuthenticationError):
                await manager.login_async("baduser", "badpass")

    @pytest.mark.asyncio
    async def test_user_account_disabled(self):
        """Test login when user account is disabled in Keycloak."""
        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.a_token = AsyncMock(
                side_effect=KeycloakAuthenticationError("Account is disabled")
            )
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # Should raise authentication error
            with pytest.raises(KeycloakAuthenticationError):
                await manager.login_async("disabled_user", "password")

    def test_expired_token_introspection(self):
        """Test token introspection with expired token."""
        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.introspect = Mock(return_value={"active": False})
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # Introspection should indicate token is not active
            result = manager.openid.introspect("expired_token")
            assert result["active"] is False


class TestKeycloakIntermittentFailures:
    """Tests for intermittent Keycloak failures and recovery."""

    @pytest.mark.asyncio
    async def test_keycloak_flapping_availability(self):
        """Test authentication when Keycloak availability flaps (up/down/up)."""
        call_count = [0]

        async def mock_token(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First call: Keycloak available
                return {
                    "access_token": "token1",
                    "refresh_token": "refresh1",
                    "expires_in": 300,
                }
            elif call_count[0] == 2:
                # Second call: Keycloak unavailable
                raise KeycloakConnectionError("Connection lost")
            else:
                # Third call: Keycloak recovered
                return {
                    "access_token": "token2",
                    "refresh_token": "refresh2",
                    "expires_in": 300,
                }

        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.a_token = AsyncMock(side_effect=mock_token)
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # First login: success
            result1 = await manager.login_async("user", "pass")
            assert result1["access_token"] == "token1"

            # Second login: failure
            with pytest.raises(KeycloakConnectionError):
                await manager.login_async("user", "pass")

            # Third login: recovered
            result3 = await manager.login_async("user", "pass")
            assert result3["access_token"] == "token2"

    def test_token_refresh_after_keycloak_restart(self):
        """Test token refresh after Keycloak has restarted."""
        # Simulate Keycloak restart invalidating existing tokens
        call_count = [0]

        def mock_refresh(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First refresh: old session invalid after restart
                raise KeycloakGetError("Session not found")
            else:
                # User re-authenticated with new token
                return {"access_token": "new_token", "expires_in": 300}

        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.refresh_token = Mock(side_effect=mock_refresh)
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # First refresh fails (Keycloak restarted)
            with pytest.raises(KeycloakGetError):
                manager.openid.refresh_token("old_refresh_token")

            # Second attempt with new login succeeds
            result = manager.openid.refresh_token("new_refresh_token")
            assert result["access_token"] == "new_token"


class TestKeycloakNetworkPartitions:
    """Tests for Keycloak network partition scenarios."""

    @pytest.mark.asyncio
    async def test_slow_keycloak_response(self):
        """Test authentication when Keycloak responses are slow."""
        import asyncio
        import time

        async def slow_token(*args, **kwargs):
            await asyncio.sleep(1.0)  # 1 second delay
            return {
                "access_token": "slow_token",
                "refresh_token": "refresh",
                "expires_in": 300,
            }

        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.a_token = AsyncMock(side_effect=slow_token)
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            start = time.time()
            result = await manager.login_async("user", "pass")
            duration = time.time() - start

            # Login should complete but take longer
            assert result["access_token"] == "slow_token"
            assert duration >= 1.0, (
                f"Login should take at least 1s, took {duration:.3f}s"
            )

    @pytest.mark.asyncio
    async def test_partial_keycloak_service_degradation(self):
        """Test when some Keycloak services work but others fail."""
        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()

            # Login works
            mock_openid.a_token = AsyncMock(
                return_value={
                    "access_token": "token",
                    "refresh_token": "refresh",
                    "expires_in": 300,
                }
            )

            # But userinfo endpoint is down
            mock_openid.userinfo = Mock(
                side_effect=KeycloakConnectionError("Userinfo endpoint down")
            )

            mock_kc.return_value = mock_openid
            manager = KeycloakManager()

            # Login should succeed
            result = await manager.login_async("user", "pass")
            assert result["access_token"] == "token"

            # But userinfo should fail
            with pytest.raises(KeycloakConnectionError):
                manager.openid.userinfo("token")


class TestKeycloakConfigurationErrors:
    """Tests for Keycloak configuration error scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_client_credentials(self):
        """Test when Keycloak client credentials are invalid."""
        with patch("app.managers.keycloak_manager.KeycloakOpenID") as mock_kc:
            mock_openid = Mock()
            mock_openid.a_token = AsyncMock(
                side_effect=KeycloakAuthenticationError(
                    "Invalid client credentials"
                )
            )
            mock_kc.return_value = mock_openid

            manager = KeycloakManager()

            # Should raise authentication error
            with pytest.raises(KeycloakAuthenticationError):
                await manager.login_async("user", "pass")

    def test_invalid_realm_configuration(self):
        """Test when Keycloak realm does not exist."""
        with patch(
            "app.managers.keycloak_manager.KeycloakOpenID",
            side_effect=KeycloakGetError("Realm not found"),
        ):
            # Manager initialization should fail with invalid realm
            with pytest.raises(KeycloakGetError):
                KeycloakManager()
