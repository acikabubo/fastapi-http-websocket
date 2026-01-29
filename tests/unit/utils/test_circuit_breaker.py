"""
Tests for circuit breaker implementation.

Tests circuit breaker functionality for external service integrations
(Keycloak and Redis) including state transitions, failure handling,
and metrics tracking.
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.managers.keycloak_manager import KeycloakManager
from app.storage.redis import get_redis_connection, redis_circuit_breaker


class TestKeycloakCircuitBreaker:
    """Tests for Keycloak circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_login_success_with_circuit_breaker_disabled(
        self,
    ) -> None:
        """Test successful login with circuit breaker disabled."""
        with patch("app.settings.app_settings.CIRCUIT_BREAKER_ENABLED", False):
            manager = KeycloakManager()

            # Mock the Keycloak token call
            manager.openid.a_token = AsyncMock(
                return_value={"access_token": "test_token"}
            )

            # Call login_async
            result = await manager.login_async("user", "password")

            assert result == {"access_token": "test_token"}
            manager.openid.a_token.assert_called_once_with(
                username="user", password="password"
            )

    @pytest.mark.asyncio
    async def test_circuit_breaker_initialized(self) -> None:
        """Test circuit breaker is properly initialized."""
        with patch("app.settings.app_settings.CIRCUIT_BREAKER_ENABLED", True):
            manager = KeycloakManager()

            assert manager.circuit_breaker is not None
            assert manager.circuit_breaker.name == "keycloak"


class TestRedisCircuitBreaker:
    """Tests for Redis circuit breaker functionality."""

    @pytest.mark.asyncio
    async def test_get_connection_circuit_breaker_opens_after_failures(
        self,
    ) -> None:
        """Test circuit breaker opens after consecutive Redis failures."""
        # Reset circuit breaker state for this test
        if redis_circuit_breaker:
            redis_circuit_breaker._state.counter = 0
            redis_circuit_breaker._state._opened = None

        with patch("app.storage.redis.RedisPool.get_instance") as mock_get:
            # Mock consecutive failures
            mock_get.side_effect = ConnectionError("Redis unavailable")

            # First FAIL_MAX calls should return None (graceful degradation)
            for _ in range(
                redis_circuit_breaker.fail_max if redis_circuit_breaker else 3
            ):
                result = await get_redis_connection(db=1)
                assert result is None

            # Circuit breaker should now be open
            # Next call should fail fast and return None
            result = await get_redis_connection(db=1)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_connection_circuit_breaker_disabled(self) -> None:
        """Test Redis connection with circuit breaker disabled."""
        with (
            patch("app.settings.app_settings.CIRCUIT_BREAKER_ENABLED", False),
            patch("app.storage.redis.redis_circuit_breaker", None),
            patch("app.storage.redis.RedisPool.get_instance") as mock_get,
        ):
            mock_redis = AsyncMock()
            mock_get.return_value = mock_redis

            result = await get_redis_connection(db=1)

            assert result == mock_redis
            mock_get.assert_called_once_with(1)

    def test_redis_circuit_breaker_initialized(self) -> None:
        """Test Redis circuit breaker is properly initialized."""
        assert redis_circuit_breaker is not None
        assert redis_circuit_breaker.name == "redis"


class TestCircuitBreakerConfiguration:
    """Tests for circuit breaker configuration."""

    def test_keycloak_circuit_breaker_config(self) -> None:
        """Test Keycloak circuit breaker uses correct configuration."""
        with (
            patch("app.settings.app_settings.CIRCUIT_BREAKER_ENABLED", True),
            patch(
                "app.settings.app_settings.KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX",
                10,
            ),
            patch(
                "app.settings.app_settings.KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT",
                120,
            ),
        ):
            manager = KeycloakManager()

            assert manager.circuit_breaker is not None
            assert manager.circuit_breaker.name == "keycloak"
            assert manager.circuit_breaker.fail_max == 10
            assert manager.circuit_breaker.reset_timeout == 120

    def test_redis_circuit_breaker_config(self) -> None:
        """Test Redis circuit breaker uses correct configuration."""
        if redis_circuit_breaker:
            assert redis_circuit_breaker.name == "redis"
            # Note: Config values depend on current settings
            assert redis_circuit_breaker.fail_max > 0
            assert redis_circuit_breaker.reset_timeout > 0

    def test_circuit_breaker_disabled(self) -> None:
        """Test circuit breaker is None when disabled."""
        with patch("app.settings.app_settings.CIRCUIT_BREAKER_ENABLED", False):
            manager = KeycloakManager()

            assert manager.circuit_breaker is None
