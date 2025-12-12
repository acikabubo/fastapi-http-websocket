import os
import re

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    DB_INIT_RETRY_INTERVAL: int = 2
    DB_INIT_MAX_RETRIES: int = 5

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20

    # Rate limiting settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # WebSocket rate limiting settings
    WS_MAX_CONNECTIONS_PER_USER: int = 5
    WS_MESSAGE_RATE_LIMIT: int = 100  # messages per minute

    # Logging settings
    LOG_FILE_PATH: str = "logs/logging_errors.log"
    # Paths to exclude from access logs (e.g., /metrics, /health)
    LOG_EXCLUDED_PATHS: list[str] = ["/metrics", "/health"]
{% if cookiecutter.enable_audit_logging == "yes" %}
    # Audit logging settings
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 365
    AUDIT_QUEUE_MAX_SIZE: int = 10000
    AUDIT_BATCH_SIZE: int = 100
    AUDIT_BATCH_TIMEOUT: float = 1.0
{% endif %}

app_settings = Settings()
