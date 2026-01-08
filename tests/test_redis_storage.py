"""
Tests for Redis storage utilities.

This module tests Redis connection pooling, pub/sub event handling,
and Keycloak user session management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.user import UserModel
from app.storage.redis import (
    REventHandler,
    RedisHandler,
    RedisPool,
    RRedis,
    get_auth_redis_connection,
    get_redis_connection,
)
from tests.mocks.redis_mocks import create_mock_redis_connection


@pytest.fixture
def mock_redis():
    """
    Provides a mock Redis connection.

    Returns:
        AsyncMock: Mocked Redis instance
    """
    redis_mock = create_mock_redis_connection()
    redis_mock.pexpire = AsyncMock()
    redis_mock.pubsub = AsyncMock()
    return redis_mock


@pytest.fixture
def mock_user():
    """
    Provides a mock UserModel.

    Returns:
        UserModel: Mock user instance
    """
    from datetime import datetime

    # Create a future timestamp (current time + 300 seconds)
    future_exp = int(datetime.now().timestamp()) + 300

    return UserModel(
        sub="user-id-123",
        exp=future_exp,
        preferred_username="testuser",
        azp="test-client",
        resource_access={"test-client": {"roles": ["user"]}},
    )


class TestRedisPool:
    """Tests for RedisPool class."""

    @pytest.mark.asyncio
    async def test_get_instance_creates_new(self):
        """Test that get_instance creates new Redis instance."""
        mock_redis_instance = AsyncMock()

        with (
            patch("app.storage.redis.ConnectionPool.from_url") as mock_pool,
            patch(
                "app.storage.redis.Redis.from_pool",
                new=AsyncMock(return_value=mock_redis_instance),
            ),
        ):
            # Clear instances
            RedisPool._RedisPool__instances = {}

            result = await RedisPool.get_instance(db=1)

            assert result == mock_redis_instance
            mock_pool.assert_called_once()
            assert hasattr(result, "add_kc_user_session")

    @pytest.mark.asyncio
    async def test_get_instance_returns_existing(self):
        """Test that get_instance returns existing Redis instance."""
        mock_redis = AsyncMock()
        RedisPool._RedisPool__instances = {2: mock_redis}

        result = await RedisPool.get_instance(db=2)

        assert result == mock_redis

    @pytest.mark.asyncio
    async def test_add_kc_user_session(self, mock_redis, mock_user):
        """
        Test adding Keycloak user session to Redis.

        Args:
            mock_redis: Mocked Redis connection
            mock_user: Mock user model
        """
        with patch("app.storage.redis.app_settings") as mock_settings:
            mock_settings.USER_SESSION_REDIS_KEY_PREFIX = "session:"

            await RedisPool.add_kc_user_session(mock_redis, mock_user)

            mock_redis.set.assert_called_once_with("session:testuser", 1)
            mock_redis.pexpire.assert_called_once()
            # Verify expiration time is approximately (expired_seconds + 10) * 1000 ms
            call_args = mock_redis.pexpire.call_args
            assert call_args[0][0] == "session:testuser"
            # Allow for slight time difference (within 1 second)
            expected_expiry = (mock_user.expired_seconds + 10) * 1000
            actual_expiry = call_args[0][1]
            assert abs(actual_expiry - expected_expiry) < 1000


class TestGetRedisConnection:
    """Tests for get_redis_connection functions."""

    @pytest.mark.asyncio
    async def test_get_redis_connection_success(self):
        """Test successful Redis connection retrieval."""
        mock_redis = AsyncMock()

        with patch.object(RedisPool, "get_instance", return_value=mock_redis):
            result = await get_redis_connection(db=1)

            assert result == mock_redis

    @pytest.mark.asyncio
    async def test_get_redis_connection_error(self):
        """Test Redis connection error handling."""
        with patch.object(
            RedisPool,
            "get_instance",
            side_effect=Exception("Connection failed"),
        ):
            result = await get_redis_connection(db=1)

            # Should return None on error (graceful degradation)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_auth_redis_connection(self):
        """Test get_auth_redis_connection uses correct DB."""
        mock_redis = AsyncMock()

        with (
            patch("app.storage.redis.get_redis_connection") as mock_get_conn,
            patch("app.storage.redis.app_settings") as mock_settings,
        ):
            mock_settings.AUTH_REDIS_DB = 5
            mock_get_conn.return_value = mock_redis

            result = await get_auth_redis_connection()

            mock_get_conn.assert_called_once_with(db=5)
            assert result == mock_redis


class TestREventHandler:
    """Tests for REventHandler class."""

    def test_get_logger(self):
        """Test get_logger returns logger instance."""
        logger = REventHandler.get_logger()

        assert logger is not None
        assert logger.name == "REventHandler"

    def test_init(self, mock_redis):
        """
        Test REventHandler initialization.

        Args:
            mock_redis: Mocked Redis connection
        """
        handler = REventHandler(mock_redis, "test_channel")

        assert handler.channel == "test_channel"
        assert handler.redis == mock_redis
        assert handler.rch is None
        assert handler.callbacks == []

    def test_add_callback(self, mock_redis):
        """
        Test adding callback to event handler.

        Args:
            mock_redis: Mocked Redis connection
        """

        async def test_callback(ch, data):
            pass

        handler = REventHandler(mock_redis, "test_channel")
        handler.add_callback((test_callback, {}))

        assert len(handler.callbacks) == 1
        assert handler.callbacks[0][0] == test_callback

    def test_add_callback_duplicate(self, mock_redis):
        """
        Test adding duplicate callback.

        Args:
            mock_redis: Mocked Redis connection
        """

        async def test_callback(ch, data):
            pass

        callback_tuple = (test_callback, {})
        handler = REventHandler(mock_redis, "test_channel")
        handler.add_callback(callback_tuple)
        handler.add_callback(callback_tuple)

        # Should only add once
        assert len(handler.callbacks) == 1

    @pytest.mark.asyncio
    async def test_handle_success(self, mock_redis):
        """
        Test successful message handling.

        Args:
            mock_redis: Mocked Redis connection
        """
        callback = AsyncMock()
        handler = REventHandler(mock_redis, "test_channel")
        handler.add_callback((callback, {"key": "value"}))

        await handler.handle("test_channel", '{"data": "test"}')

        callback.assert_called_once_with(
            "test_channel", {"data": "test"}, key="value"
        )

    @pytest.mark.asyncio
    async def test_handle_callback_error(self, mock_redis):
        """
        Test message handling with callback error.

        Args:
            mock_redis: Mocked Redis connection
        """
        callback = AsyncMock(side_effect=Exception("Callback failed"))
        handler = REventHandler(mock_redis, "test_channel")
        handler.add_callback((callback, {}))

        # Should not raise exception
        await handler.handle("test_channel", '{"data": "test"}')

        callback.assert_called_once()


class TestRedisHandler:
    """Tests for RedisHandler class."""

    @pytest.mark.asyncio
    async def test_subscribe_new_channel(self):
        """Test subscribing to a new channel."""
        mock_redis = AsyncMock()

        async def test_callback(ch, data):
            pass

        with patch(
            "app.storage.redis.get_redis_connection", return_value=mock_redis
        ):
            handler = RedisHandler()
            handler.event_handlers = {}
            handler.tasks = []

            await handler.subscribe("new_channel", test_callback)

            assert "new_channel" in handler.event_handlers
            assert len(handler.tasks) == 1

    @pytest.mark.asyncio
    async def test_subscribe_existing_channel(self):
        """Test subscribing to an existing channel."""

        async def test_callback(ch, data):
            pass

        mock_event_handler = MagicMock(spec=REventHandler)
        mock_event_handler.add_callback = MagicMock()

        handler = RedisHandler()
        handler.event_handlers = {"existing_channel": mock_event_handler}
        handler.tasks = []

        await handler.subscribe("existing_channel", test_callback)

        mock_event_handler.add_callback.assert_called_once()
        # Should not create new task for existing channel
        assert len(handler.tasks) == 0

    @pytest.mark.asyncio
    async def test_subscribe_invalid_callback(self):
        """Test subscribing with non-coroutine callback raises error."""

        def sync_callback(ch, data):
            pass

        handler = RedisHandler()

        with pytest.raises(
            ValueError, match="Callback argument must be a coroutine"
        ):
            await handler.subscribe("test_channel", sync_callback)


class TestRRedis:
    """Tests for RRedis singleton."""

    def test_rredis_module_instance(self):
        """Test that r_redis is the module-level singleton instance."""
        from app.storage.redis import r_redis

        # Import again to verify it's the same instance
        from app.storage.redis import r_redis as r_redis2

        assert r_redis is r_redis2
        assert isinstance(r_redis, RRedis)
