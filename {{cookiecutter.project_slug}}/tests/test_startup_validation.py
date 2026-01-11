"""Tests for startup validation functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import OperationalError

from {{cookiecutter.module_name}}.startup_validation import (
    StartupValidationError,
    run_all_validations,
    validate_database_connection,
    validate_redis_connection,
    validate_settings,
)


class TestValidateSettings:
    """Tests for validate_settings function."""

    @pytest.mark.asyncio
    async def test_validate_settings_success(self):
        """Test successful settings validation with all required vars."""
        with patch("{{cookiecutter.module_name}}.startup_validation.app_settings") as mock_settings:
            # Mock all required settings
            mock_settings.KEYCLOAK_REALM = "test-realm"
            mock_settings.KEYCLOAK_CLIENT_ID = "test-client"
            mock_settings.KEYCLOAK_BASE_URL = "http://localhost:8080"
            mock_settings.KEYCLOAK_ADMIN_USERNAME = "admin"
            mock_settings.KEYCLOAK_ADMIN_PASSWORD = "password"
            mock_settings.DB_USER = "testuser"
            mock_settings.DB_PASSWORD.get_secret_value.return_value = (
                "testpass"
            )

            # Should not raise any exception
            await validate_settings()

    @pytest.mark.asyncio
    async def test_validate_settings_missing_keycloak_realm(self):
        """Test validation fails when KEYCLOAK_REALM is missing."""
        with patch("{{cookiecutter.module_name}}.startup_validation.app_settings") as mock_settings:
            mock_settings.KEYCLOAK_REALM = ""
            mock_settings.KEYCLOAK_CLIENT_ID = "test-client"
            mock_settings.KEYCLOAK_BASE_URL = "http://localhost:8080"
            mock_settings.KEYCLOAK_ADMIN_USERNAME = "admin"
            mock_settings.KEYCLOAK_ADMIN_PASSWORD = "password"
            mock_settings.DB_USER = "testuser"
            mock_settings.DB_PASSWORD.get_secret_value.return_value = (
                "testpass"
            )

            with pytest.raises(StartupValidationError) as exc_info:
                await validate_settings()

            assert "KEYCLOAK_REALM" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_settings_missing_db_user(self):
        """Test validation fails when DB_USER is missing."""
        with patch("{{cookiecutter.module_name}}.startup_validation.app_settings") as mock_settings:
            mock_settings.KEYCLOAK_REALM = "test-realm"
            mock_settings.KEYCLOAK_CLIENT_ID = "test-client"
            mock_settings.KEYCLOAK_BASE_URL = "http://localhost:8080"
            mock_settings.KEYCLOAK_ADMIN_USERNAME = "admin"
            mock_settings.KEYCLOAK_ADMIN_PASSWORD = "password"
            mock_settings.DB_USER = ""
            mock_settings.DB_PASSWORD.get_secret_value.return_value = (
                "testpass"
            )

            with pytest.raises(StartupValidationError) as exc_info:
                await validate_settings()

            assert "DB_USER" in str(exc_info.value)


class TestValidateDatabaseConnection:
    """Tests for validate_database_connection function."""

    @pytest.mark.asyncio
    async def test_validate_database_connection_success(self):
        """Test successful database connection validation."""
        # Mock database engine and connection
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (1,)

        # Create async context manager mock for connection
        class AsyncContextManagerMock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def execute(self, query):
                return mock_result

        mock_conn = AsyncContextManagerMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("{{cookiecutter.module_name}}.startup_validation.engine", mock_engine):
            with patch("{{cookiecutter.module_name}}.startup_validation.app_settings") as settings:
                settings.DB_HOST = "localhost"
                settings.DB_PORT = 5432
                settings.DB_NAME = "testdb"

                # Should not raise any exception
                await validate_database_connection()

    @pytest.mark.asyncio
    async def test_validate_database_connection_operational_error(self):
        """Test validation fails when database connection fails."""

        # Create async context manager that raises OperationalError
        class AsyncContextManagerMock:
            async def __aenter__(self):
                raise OperationalError("Connection refused", None, None)

            async def __aexit__(self, *args):
                pass

        mock_conn = AsyncContextManagerMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("{{cookiecutter.module_name}}.startup_validation.engine", mock_engine):
            with pytest.raises(StartupValidationError) as exc_info:
                await validate_database_connection()

            assert "Database connection failed" in str(exc_info.value)
            assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_database_connection_unexpected_result(self):
        """Test validation fails when health check returns wrong value."""
        # Mock result with unexpected value
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (999,)

        # Create async context manager mock for connection
        class AsyncContextManagerMock:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def execute(self, query):
                return mock_result

        mock_conn = AsyncContextManagerMock()
        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("{{cookiecutter.module_name}}.startup_validation.engine", mock_engine):
            with pytest.raises(StartupValidationError) as exc_info:
                await validate_database_connection()

            assert "unexpected result" in str(exc_info.value).lower()


class TestValidateRedisConnection:
    """Tests for validate_redis_connection function."""

    @pytest.mark.asyncio
    async def test_validate_redis_connection_success(self):
        """Test successful Redis connection validation."""
        # Mock Redis instance
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        with patch(
            "{{cookiecutter.module_name}}.startup_validation.Redis", return_value=mock_redis
        ) as mock_redis_class:
            with patch("{{cookiecutter.module_name}}.startup_validation.app_settings") as settings:
                settings.REDIS_IP = "localhost"
                settings.REDIS_PORT = 6379
                settings.MAIN_REDIS_DB = 1

                # Should not raise any exception
                await validate_redis_connection()

                # Verify Redis was created with correct parameters
                mock_redis_class.assert_called_once_with(
                    host="localhost",
                    port=6379,
                    db=1,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    decode_responses=True,
                )

                # Verify connection was closed
                mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_redis_connection_connection_error(self):
        """Test validation fails when Redis connection fails."""
        # Mock Redis to raise ConnectionError
        with patch(
            "{{cookiecutter.module_name}}.startup_validation.Redis",
            side_effect=RedisConnectionError("Connection refused"),
        ):
            with pytest.raises(StartupValidationError) as exc_info:
                await validate_redis_connection()

            assert "Redis connection failed" in str(exc_info.value)
            assert "Connection refused" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_redis_connection_ping_fails(self):
        """Test validation fails when PING command fails."""
        # Mock Redis with failed PING
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=False)
        mock_redis.aclose = AsyncMock()

        with patch("{{cookiecutter.module_name}}.startup_validation.Redis", return_value=mock_redis):
            with pytest.raises(StartupValidationError) as exc_info:
                await validate_redis_connection()

            assert "PING command returned unexpected result" in str(
                exc_info.value
            )

            # Verify connection was still closed
            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_validate_redis_connection_cleanup_on_error(self):
        """Test Redis connection is closed even when validation fails."""
        # Mock Redis that fails PING but should still be closed
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(
            side_effect=RedisConnectionError("Connection lost")
        )
        mock_redis.aclose = AsyncMock()

        with patch("{{cookiecutter.module_name}}.startup_validation.Redis", return_value=mock_redis):
            with pytest.raises(StartupValidationError):
                await validate_redis_connection()

            # Verify connection was closed despite error
            mock_redis.aclose.assert_called_once()


class TestRunAllValidations:
    """Tests for run_all_validations orchestration function."""

    @pytest.mark.asyncio
    async def test_run_all_validations_success(self):
        """Test all validations run successfully."""
        with patch(
            "{{cookiecutter.module_name}}.startup_validation.validate_settings"
        ) as mock_settings:
            with patch(
                "{{cookiecutter.module_name}}.startup_validation.validate_database_connection"
            ) as mock_db:
                with patch(
                    "{{cookiecutter.module_name}}.startup_validation.validate_redis_connection"
                ) as mock_redis:
                    mock_settings.return_value = AsyncMock()
                    mock_db.return_value = AsyncMock()
                    mock_redis.return_value = AsyncMock()

                    # Should not raise any exception
                    await run_all_validations()

                    # Verify all validators were called
                    mock_settings.assert_called_once()
                    mock_db.assert_called_once()
                    mock_redis.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_all_validations_settings_fail(self):
        """Test validation stops if settings validation fails."""
        with patch(
            "{{cookiecutter.module_name}}.startup_validation.validate_settings",
            side_effect=StartupValidationError("Settings invalid"),
        ):
            with patch(
                "{{cookiecutter.module_name}}.startup_validation.validate_database_connection"
            ) as mock_db:
                with patch(
                    "{{cookiecutter.module_name}}.startup_validation.validate_redis_connection"
                ) as mock_redis:
                    with pytest.raises(StartupValidationError) as exc_info:
                        await run_all_validations()

                    assert "Settings invalid" in str(exc_info.value)

                    # Database and Redis validation should not be called
                    mock_db.assert_not_called()
                    mock_redis.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_all_validations_database_fail(self):
        """Test validation continues through settings but fails on DB."""
        with patch(
            "{{cookiecutter.module_name}}.startup_validation.validate_settings"
        ) as mock_settings:
            with patch(
                "{{cookiecutter.module_name}}.startup_validation.validate_database_connection",
                side_effect=StartupValidationError("DB connection failed"),
            ):
                with patch(
                    "{{cookiecutter.module_name}}.startup_validation.validate_redis_connection"
                ) as mock_redis:
                    mock_settings.return_value = AsyncMock()

                    with pytest.raises(StartupValidationError) as exc_info:
                        await run_all_validations()

                    assert "DB connection failed" in str(exc_info.value)

                    # Settings should be called
                    mock_settings.assert_called_once()

                    # Redis validation should not be called
                    mock_redis.assert_not_called()
