import os
import re

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from {{cookiecutter.module_name}}.constants import (
{% if cookiecutter.enable_audit_logging == "yes" %}    AUDIT_BATCH_SIZE,
    AUDIT_BATCH_TIMEOUT_SECONDS,
    AUDIT_QUEUE_MAX_SIZE,
{% endif %}    DB_MAX_RETRIES,
    DB_RETRY_DELAY_SECONDS,
    DEFAULT_PAGE_SIZE,
    DEFAULT_RATE_LIMIT_BURST,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    DEFAULT_WS_MAX_CONNECTIONS_PER_USER,
    DEFAULT_WS_MESSAGE_RATE_LIMIT,
    REDIS_CONNECT_TIMEOUT_SECONDS,
    REDIS_DEFAULT_PORT,
    REDIS_HEALTH_CHECK_INTERVAL_SECONDS,
    REDIS_MAX_CONNECTIONS,
    REDIS_SOCKET_TIMEOUT_SECONDS,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True)

    # Keycloak settings
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_BASE_URL: str = (
        "http://{{cookiecutter.project_slug}}-keycloak:8080/"
    )

    # Keycloak admin credentials
    KEYCLOAK_ADMIN_USERNAME: str
    KEYCLOAK_ADMIN_PASSWORD: str

    # Redis settings
    REDIS_IP: str = "localhost"
    REDIS_PORT: int = REDIS_DEFAULT_PORT

    USER_SESSION_REDIS_KEY_PREFIX: str = "session:"
    MAIN_REDIS_DB: int = 1
    AUTH_REDIS_DB: int = 10

    # Redis connection pool settings
    REDIS_MAX_CONNECTIONS: int = REDIS_MAX_CONNECTIONS
    REDIS_SOCKET_TIMEOUT: int = REDIS_SOCKET_TIMEOUT_SECONDS
    REDIS_CONNECT_TIMEOUT: int = REDIS_CONNECT_TIMEOUT_SECONDS
    REDIS_HEALTH_CHECK_INTERVAL: int = REDIS_HEALTH_CHECK_INTERVAL_SECONDS
    REDIS_RETRY_ON_TIMEOUT: bool = True

    # Database settings (credentials MUST be provided via environment)
    DB_USER: str
    DB_PASSWORD: SecretStr
    DB_HOST: str = "{{cookiecutter.project_slug}}-db"
    DB_PORT: int = 5432
    DB_NAME: str = "{{cookiecutter.project_slug}}-db"
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

    EXCLUDED_PATHS: re.Pattern = re.compile(
        r"^(/docs|/openapi.json|/health|/metrics)$"
    )

    # Debug mode settings (for local development/testing)
    # Users should create a Keycloak account and put credentials here for testing
    DEBUG_AUTH: bool = False
    DEBUG_AUTH_USERNAME: str = ""  # Set your Keycloak username for local dev
    DEBUG_AUTH_PASSWORD: str = ""  # Set your Keycloak password for local dev

    @field_validator("DEBUG_AUTH")
    @classmethod
    def validate_debug_auth(cls, v: bool) -> bool:
        """Prevent DEBUG_AUTH from being enabled in production."""
        if v and os.getenv("ENVIRONMENT") == "production":
            raise ValueError("DEBUG_AUTH cannot be enabled in production environment")
        return v

    # Database initialization settings
    DB_INIT_RETRY_INTERVAL: int = DB_RETRY_DELAY_SECONDS
    DB_INIT_MAX_RETRIES: int = DB_MAX_RETRIES

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = DEFAULT_PAGE_SIZE

    # Rate limiting settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = DEFAULT_RATE_LIMIT_PER_MINUTE
    RATE_LIMIT_BURST: int = DEFAULT_RATE_LIMIT_BURST

    # WebSocket rate limiting settings
    WS_MAX_CONNECTIONS_PER_USER: int = DEFAULT_WS_MAX_CONNECTIONS_PER_USER
    WS_MESSAGE_RATE_LIMIT: int = DEFAULT_WS_MESSAGE_RATE_LIMIT  # messages per minute

    # Logging settings
    LOG_FILE_PATH: str = "logs/logging_errors.log"
    # Paths to exclude from access logs (e.g., /metrics, /health)
    LOG_EXCLUDED_PATHS: list[str] = ["/metrics", "/health"]
{% if cookiecutter.enable_audit_logging == "yes" %}
    # Audit logging settings
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    AUDIT_QUEUE_MAX_SIZE: int = AUDIT_QUEUE_MAX_SIZE
    AUDIT_BATCH_SIZE: int = AUDIT_BATCH_SIZE
    AUDIT_BATCH_TIMEOUT: float = AUDIT_BATCH_TIMEOUT_SECONDS
{% endif %}

app_settings = Settings()
