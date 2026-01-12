import os
import re
from enum import Enum
from typing import Any, Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """
    Application environment types.

    Determines configuration defaults and behavior for different deployment
    environments. Each environment has specific defaults for security,
    performance, and debugging settings.
    """

    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):  # type: ignore[misc]
    model_config = SettingsConfigDict(case_sensitive=True)

    # Environment configuration
    ENV: Environment = Environment.DEV

    # Keycloak settings
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_BASE_URL: str = "http://hw-keycloak:8080/"

    # Keycloak admin credentials
    KEYCLOAK_ADMIN_USERNAME: str
    KEYCLOAK_ADMIN_PASSWORD: str

    # Redis settings
    REDIS_IP: str = "localhost"
    REDIS_PORT: int = 6379

    USER_SESSION_REDIS_KEY_PREFIX: str = "session:"
    MAIN_REDIS_DB: int = 1
    AUTH_REDIS_DB: int = 10

    # Redis connection pool settings
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_CONNECT_TIMEOUT: int = 5
    REDIS_HEALTH_CHECK_INTERVAL: int = 30
    REDIS_RETRY_ON_TIMEOUT: bool = True

    # Database settings (credentials MUST be provided via environment)
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_HOST: str = "hw-db"
    DB_PORT: int = 5432
    DB_NAME: str = "hw-db"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True

    @property
    def DATABASE_URL(self) -> str:
        """Construct the database URL from individual components."""
        password = self.DB_PASSWORD.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{password}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    EXCLUDED_PATHS: re.Pattern[str] = re.compile(
        r"^(/docs|/openapi.json|/health|/metrics)$"
    )

    # Security settings
    ALLOWED_HOSTS: list[str] = [
        "*"
    ]  # ["example.com", "*.example.com"] in production
    MAX_REQUEST_BODY_SIZE: int = 1024 * 1024  # 1MB default
    # Trusted proxies for X-Forwarded-For header validation
    # Common private network ranges for Docker/Kubernetes environments
    TRUSTED_PROXIES: list[str] = [
        "10.0.0.0/8",  # Docker default network
        "172.16.0.0/12",  # Docker custom networks
        "192.168.0.0/16",  # Private networks
    ]

    # Database initialization settings
    DB_INIT_RETRY_INTERVAL: int = 2
    DB_INIT_MAX_RETRIES: int = 5

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20

    # Rate limiting settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_BURST: int = 10
    # Fail mode: "open" = allow requests when Redis unavailable, "closed" = deny requests
    RATE_LIMIT_FAIL_MODE: Literal["open", "closed"] = "open"

    # WebSocket rate limiting settings
    WS_MAX_CONNECTIONS_PER_USER: int = 5
    WS_MESSAGE_RATE_LIMIT: int = 100  # messages per minute

    # Logging settings
    LOG_FILE_PATH: str = "logs/logging_errors.log"
    # Paths to exclude from access logs (e.g., /metrics, /health)
    LOG_EXCLUDED_PATHS: list[str] = ["/metrics", "/health"]
    LOG_LEVEL: str = "INFO"
    # Console log format: 'json' for Grafana Alloy collection, 'human' for development
    LOG_CONSOLE_FORMAT: str = "human"

    # Loki integration settings (via Grafana Alloy)
    # Alloy scrapes Docker logs and sends to Loki
    # Alloy replaced deprecated Promtail (Feb 2025)
    # No direct LokiHandler needed - simplified architecture

    # Audit logging settings
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    AUDIT_QUEUE_MAX_SIZE: int = 10000
    AUDIT_BATCH_SIZE: int = 100
    AUDIT_BATCH_TIMEOUT: float = 1.0

    # Profiling settings (Scalene integration)
    PROFILING_ENABLED: bool = True
    PROFILING_OUTPUT_DIR: str = "profiling_reports"
    PROFILING_INTERVAL_SECONDS: int = 30  # Profiling snapshot interval

    # Circuit breaker settings (resilience pattern for external services)
    CIRCUIT_BREAKER_ENABLED: bool = True
    # Keycloak circuit breaker
    KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX: int = 5  # Open after 5 failures
    KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT: int = 60  # Stay open for 60 seconds
    # Redis circuit breaker
    REDIS_CIRCUIT_BREAKER_FAIL_MAX: int = 3  # Open after 3 failures
    REDIS_CIRCUIT_BREAKER_TIMEOUT: int = 30  # Stay open for 30 seconds

    def __init__(self, **kwargs: Any) -> None:
        """
        Initialize settings with environment-specific defaults.

        Environment-specific defaults are applied based on the ENV setting:
        - DEV: Permissive settings for local development
        - STAGING: Production-like settings with some debugging enabled
        - PRODUCTION: Strict security and performance settings

        Args:
            **kwargs: Keyword arguments passed to BaseSettings.
        """
        super().__init__(**kwargs)
        self._apply_environment_defaults()

    def _apply_environment_defaults(self) -> None:
        """Apply environment-specific configuration defaults."""
        if self.ENV == Environment.PRODUCTION:
            # Production environment: strict security and performance
            # Override only if not explicitly set via environment variables

            # Rate limiting: Fail closed in production (deny when Redis down)
            if os.getenv("RATE_LIMIT_FAIL_MODE") is None:
                self.RATE_LIMIT_FAIL_MODE = "closed"

            # Logging: JSON format for log aggregation
            if os.getenv("LOG_CONSOLE_FORMAT") is None:
                self.LOG_CONSOLE_FORMAT = "json"

            # Logging: Reduce log level for production
            if os.getenv("LOG_LEVEL") is None:
                self.LOG_LEVEL = "WARNING"

            # Profiling: Disable in production by default
            if os.getenv("PROFILING_ENABLED") is None:
                self.PROFILING_ENABLED = False

        elif self.ENV == Environment.STAGING:
            # Staging environment: production-like with some debugging

            # Rate limiting: Fail open (allow when Redis down)
            if os.getenv("RATE_LIMIT_FAIL_MODE") is None:
                self.RATE_LIMIT_FAIL_MODE = "open"

            # Logging: JSON format for log aggregation
            if os.getenv("LOG_CONSOLE_FORMAT") is None:
                self.LOG_CONSOLE_FORMAT = "json"

            # Logging: INFO level for staging
            if os.getenv("LOG_LEVEL") is None:
                self.LOG_LEVEL = "INFO"

            # Profiling: Enable for performance testing
            if os.getenv("PROFILING_ENABLED") is None:
                self.PROFILING_ENABLED = True

        else:  # Environment.DEV
            # Development environment: permissive settings for debugging

            # Rate limiting: Fail open (allow when Redis down)
            if os.getenv("RATE_LIMIT_FAIL_MODE") is None:
                self.RATE_LIMIT_FAIL_MODE = "open"

            # Logging: Human-readable format for development
            if os.getenv("LOG_CONSOLE_FORMAT") is None:
                self.LOG_CONSOLE_FORMAT = "human"

            # Logging: DEBUG level for development
            if os.getenv("LOG_LEVEL") is None:
                self.LOG_LEVEL = "DEBUG"

            # Profiling: Enable for local performance testing
            if os.getenv("PROFILING_ENABLED") is None:
                self.PROFILING_ENABLED = True

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
