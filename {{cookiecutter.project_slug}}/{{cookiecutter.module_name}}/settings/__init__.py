"""Settings module with nested configuration groups."""

import os
import re
from enum import Enum
from typing import Any, Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from {{cookiecutter.module_name}}.settings.models import (
    CircuitBreakerSettings,
    DatabaseSettings,
    KeycloakSettings,
    LoggingSettings,
    ProfilingSettings,
    RedisSettings,
    SecuritySettings,
    ServiceCircuitBreakerSettings,
    WebSocketSettings,
)


class Environment(str, Enum):
    """Application environment types."""

    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):  # type: ignore[misc]
    """
    Main settings class.

    Provides both flat access (original) and nested access (new).
    Flat env vars like DB_USER are automatically grouped into nested models.
    """

    model_config = SettingsConfigDict(case_sensitive=True)

    # Environment configuration
    ENV: Environment = Environment.DEV

    # Database settings (flat - will be grouped into nested model)
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_HOST: str = "{{cookiecutter.project_slug}}-db"
    DB_PORT: int = 5432
    DB_NAME: str = "{{cookiecutter.project_slug}}-db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True
    DB_INIT_RETRY_INTERVAL: int = 2
    DB_INIT_MAX_RETRIES: int = 5

    # Redis settings (flat - will be grouped into nested model)
    REDIS_IP: str = "localhost"
    REDIS_PORT: int = 6379
    USER_SESSION_REDIS_KEY_PREFIX: str = "session:"
    MAIN_REDIS_DB: int = 1
    AUTH_REDIS_DB: int = 10
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_CONNECT_TIMEOUT: int = 5
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    REDIS_RETRY_ON_TIMEOUT: bool = True

    # Keycloak settings (flat - will be grouped into nested model)
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_BASE_URL: str = "http://hw-keycloak:8080/"
    KEYCLOAK_ADMIN_USERNAME: str
    KEYCLOAK_ADMIN_PASSWORD: str

    # Security settings (flat - will be grouped into nested model)
    ALLOWED_HOSTS: list[str] = ["*"]
    MAX_REQUEST_BODY_SIZE: int = 1024 * 1024
    TRUSTED_PROXIES: list[str] = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]

    # Rate limiting settings (flat - will be grouped into nested model)
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_BURST: int = 10
    RATE_LIMIT_FAIL_MODE: Literal["open", "closed"] = "open"

    # WebSocket settings (flat - will be grouped into nested model)
    WS_MAX_CONNECTIONS_PER_USER: int = 5
    WS_MESSAGE_RATE_LIMIT: int = 100
    ALLOWED_WS_ORIGINS: list[str] = ["*"]

    # Logging settings (flat - will be grouped into nested model)
    LOG_FILE_PATH: str = "logs/logging_errors.log"
    LOG_EXCLUDED_PATHS: list[str] = ["/metrics", "/health"]
    LOG_LEVEL: str = "INFO"
    LOG_CONSOLE_FORMAT: str = "human"

    # Audit settings (flat - will be grouped into nested model)
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    AUDIT_QUEUE_MAX_SIZE: int = 10000
    AUDIT_BATCH_SIZE: int = 100
    AUDIT_BATCH_TIMEOUT: float = 1.0
    AUDIT_QUEUE_TIMEOUT: float = 1.0

    # Profiling settings (flat - will be grouped into nested model)
    PROFILING_ENABLED: bool = True
    PROFILING_OUTPUT_DIR: str = "profiling_reports"
    PROFILING_INTERVAL_SECONDS: int = 30

    # Circuit breaker settings (flat - will be grouped into nested model)
    CIRCUIT_BREAKER_ENABLED: bool = True
    KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX: int = 5
    KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT: int = 60
    REDIS_CIRCUIT_BREAKER_FAIL_MAX: int = 3
    REDIS_CIRCUIT_BREAKER_TIMEOUT: int = 30

    # Other settings
    EXCLUDED_PATHS: re.Pattern[str] = re.compile(
        r"^(/docs|/openapi.json|/health|/metrics)$"
    )
    DEFAULT_PAGE_SIZE: int = 20

    def __init__(self, **kwargs: Any) -> None:
        """Initialize settings with environment-specific defaults."""
        super().__init__(**kwargs)
        self._apply_environment_defaults()

    def _apply_environment_defaults(self) -> None:
        """Apply environment-specific configuration defaults."""
        if self.ENV == Environment.PRODUCTION:
            if os.getenv("RATE_LIMIT_FAIL_MODE") is None:
                self.RATE_LIMIT_FAIL_MODE = "closed"
            if os.getenv("LOG_CONSOLE_FORMAT") is None:
                self.LOG_CONSOLE_FORMAT = "json"
            if os.getenv("LOG_LEVEL") is None:
                self.LOG_LEVEL = "WARNING"
            if os.getenv("PROFILING_ENABLED") is None:
                self.PROFILING_ENABLED = False

        elif self.ENV == Environment.STAGING:
            if os.getenv("RATE_LIMIT_FAIL_MODE") is None:
                self.RATE_LIMIT_FAIL_MODE = "open"
            if os.getenv("LOG_CONSOLE_FORMAT") is None:
                self.LOG_CONSOLE_FORMAT = "json"
            if os.getenv("LOG_LEVEL") is None:
                self.LOG_LEVEL = "INFO"
            if os.getenv("PROFILING_ENABLED") is None:
                self.PROFILING_ENABLED = True

        else:  # Environment.DEV
            if os.getenv("RATE_LIMIT_FAIL_MODE") is None:
                self.RATE_LIMIT_FAIL_MODE = "open"
            if os.getenv("LOG_CONSOLE_FORMAT") is None:
                self.LOG_CONSOLE_FORMAT = "human"
            if os.getenv("LOG_LEVEL") is None:
                self.LOG_LEVEL = "DEBUG"
            if os.getenv("PROFILING_ENABLED") is None:
                self.PROFILING_ENABLED = True

    # Nested model properties (new access pattern)
    @property
    def database(self) -> DatabaseSettings:
        """Get database settings as nested model."""
        return DatabaseSettings(
            USER=self.DB_USER,
            PASSWORD=self.DB_PASSWORD,
            HOST=self.DB_HOST,
            PORT=self.DB_PORT,
            NAME=self.DB_NAME,
            POOL_SIZE=self.DB_POOL_SIZE,
            MAX_OVERFLOW=self.DB_MAX_OVERFLOW,
            POOL_RECYCLE=self.DB_POOL_RECYCLE,
            POOL_PRE_PING=self.DB_POOL_PRE_PING,
            INIT_RETRY_INTERVAL=self.DB_INIT_RETRY_INTERVAL,
            INIT_MAX_RETRIES=self.DB_INIT_MAX_RETRIES,
        )

    @property
    def redis(self) -> RedisSettings:
        """Get Redis settings as nested model."""
        return RedisSettings(
            IP=self.REDIS_IP,
            PORT=self.REDIS_PORT,
            MAX_CONNECTIONS=self.REDIS_MAX_CONNECTIONS,
            SOCKET_TIMEOUT=self.REDIS_SOCKET_TIMEOUT,
            CONNECT_TIMEOUT=self.REDIS_CONNECT_TIMEOUT,
            HEALTH_CHECK_INTERVAL=self.REDIS_HEALTH_CHECK_INTERVAL,
            RETRY_ON_TIMEOUT=self.REDIS_RETRY_ON_TIMEOUT,
            MAIN_DB=self.MAIN_REDIS_DB,
            AUTH_DB=self.AUTH_REDIS_DB,
            USER_SESSION_KEY_PREFIX=self.USER_SESSION_REDIS_KEY_PREFIX,
        )

    @property
    def keycloak(self) -> KeycloakSettings:
        """Get Keycloak settings as nested model."""
        return KeycloakSettings(
            REALM=self.KEYCLOAK_REALM,
            CLIENT_ID=self.KEYCLOAK_CLIENT_ID,
            BASE_URL=self.KEYCLOAK_BASE_URL,
            ADMIN_USERNAME=self.KEYCLOAK_ADMIN_USERNAME,
            ADMIN_PASSWORD=self.KEYCLOAK_ADMIN_PASSWORD,
        )

    @property
    def security(self) -> SecuritySettings:
        """Get security settings as nested model."""
        from {{cookiecutter.module_name}}.settings.models import RateLimitSettings

        return SecuritySettings(
            ALLOWED_HOSTS=self.ALLOWED_HOSTS,
            MAX_REQUEST_BODY_SIZE=self.MAX_REQUEST_BODY_SIZE,
            TRUSTED_PROXIES=self.TRUSTED_PROXIES,
            rate_limit=RateLimitSettings(
                ENABLED=self.RATE_LIMIT_ENABLED,
                PER_MINUTE=self.RATE_LIMIT_PER_MINUTE,
                BURST=self.RATE_LIMIT_BURST,
                FAIL_MODE=self.RATE_LIMIT_FAIL_MODE,
            ),
        )

    @property
    def websocket(self) -> WebSocketSettings:
        """Get WebSocket settings as nested model."""
        return WebSocketSettings(
            MAX_CONNECTIONS_PER_USER=self.WS_MAX_CONNECTIONS_PER_USER,
            MESSAGE_RATE_LIMIT=self.WS_MESSAGE_RATE_LIMIT,
            ALLOWED_ORIGINS=self.ALLOWED_WS_ORIGINS,
        )

    @property
    def logging(self) -> LoggingSettings:
        """Get logging settings as nested model."""
        from {{cookiecutter.module_name}}.settings.models import AuditSettings

        return LoggingSettings(
            FILE_PATH=self.LOG_FILE_PATH,
            EXCLUDED_PATHS=self.LOG_EXCLUDED_PATHS,
            LEVEL=self.LOG_LEVEL,
            CONSOLE_FORMAT=self.LOG_CONSOLE_FORMAT,
            audit=AuditSettings(
                ENABLED=self.AUDIT_LOG_ENABLED,
                RETENTION_DAYS=self.AUDIT_LOG_RETENTION_DAYS,
                QUEUE_MAX_SIZE=self.AUDIT_QUEUE_MAX_SIZE,
                BATCH_SIZE=self.AUDIT_BATCH_SIZE,
                BATCH_TIMEOUT=self.AUDIT_BATCH_TIMEOUT,
                QUEUE_TIMEOUT=self.AUDIT_QUEUE_TIMEOUT,
            ),
        )

    @property
    def circuit_breaker(self) -> CircuitBreakerSettings:
        """Get circuit breaker settings as nested model."""
        return CircuitBreakerSettings(
            ENABLED=self.CIRCUIT_BREAKER_ENABLED,
            keycloak=ServiceCircuitBreakerSettings(
                FAIL_MAX=self.KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX,
                TIMEOUT=self.KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT,
            ),
            redis=ServiceCircuitBreakerSettings(
                FAIL_MAX=self.REDIS_CIRCUIT_BREAKER_FAIL_MAX,
                TIMEOUT=self.REDIS_CIRCUIT_BREAKER_TIMEOUT,
            ),
        )

    @property
    def profiling(self) -> ProfilingSettings:
        """Get profiling settings as nested model."""
        return ProfilingSettings(
            ENABLED=self.PROFILING_ENABLED,
            OUTPUT_DIR=self.PROFILING_OUTPUT_DIR,
            INTERVAL_SECONDS=self.PROFILING_INTERVAL_SECONDS,
        )

    # Backward compatibility property
    @property
    def DATABASE_URL(self) -> str:
        """Construct the database URL."""
        return self.database.url

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENV == Environment.PRODUCTION

    @property
    def is_staging(self) -> bool:
        """Check if running in staging environment."""
        return self.ENV == Environment.STAGING

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENV == Environment.DEV


app_settings = Settings()

__all__ = [
    "Settings",
    "app_settings",
    "Environment",
    # Nested models
    "DatabaseSettings",
    "RedisSettings",
    "KeycloakSettings",
    "SecuritySettings",
    "WebSocketSettings",
    "LoggingSettings",
    "CircuitBreakerSettings",
    "ProfilingSettings",
]
