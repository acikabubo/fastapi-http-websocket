"""Nested settings models (BaseModel, not BaseSettings)."""

from typing import Literal

from pydantic import BaseModel, SecretStr


class DatabaseSettings(BaseModel):  # type: ignore[misc]
    """Database configuration."""

    USER: str
    PASSWORD: SecretStr
    HOST: str = "{{cookiecutter.project_slug}}-db"
    PORT: int = 5432
    NAME: str = "{{cookiecutter.project_slug}}-db"
    POOL_SIZE: int = 20
    MAX_OVERFLOW: int = 10
    POOL_RECYCLE: int = 3600
    POOL_PRE_PING: bool = True
    INIT_RETRY_INTERVAL: int = 2
    INIT_MAX_RETRIES: int = 5

    @property
    def url(self) -> str:
        """Construct database URL."""
        password = self.PASSWORD.get_secret_value()
        return (
            f"postgresql+asyncpg://{self.USER}:{password}"
            f"@{self.HOST}:{self.PORT}/{self.NAME}"
        )


class RedisSettings(BaseModel):  # type: ignore[misc]
    """Redis configuration."""

    IP: str = "localhost"
    PORT: int = 6379
    MAX_CONNECTIONS: int = 50
    SOCKET_TIMEOUT: int = 5
    CONNECT_TIMEOUT: int = 5
    HEALTH_CHECK_INTERVAL: int = 30
    RETRY_ON_TIMEOUT: bool = True
    MAIN_DB: int = 1
    AUTH_DB: int = 10
    USER_SESSION_KEY_PREFIX: str = "session:"


class KeycloakSettings(BaseModel):  # type: ignore[misc]
    """Keycloak configuration."""

    REALM: str
    CLIENT_ID: str
    BASE_URL: str = "http://hw-keycloak:8080/"
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str


class RateLimitSettings(BaseModel):  # type: ignore[misc]
    """Rate limiting configuration."""

    ENABLED: bool = True
    PER_MINUTE: int = 10
    BURST: int = 10
    FAIL_MODE: Literal["open", "closed"] = "open"


class SecuritySettings(BaseModel):  # type: ignore[misc]
    """Security configuration."""

    ALLOWED_HOSTS: list[str] = ["*"]
    MAX_REQUEST_BODY_SIZE: int = 1024 * 1024
    TRUSTED_PROXIES: list[str] = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
    ]
    rate_limit: RateLimitSettings = RateLimitSettings()


class WebSocketSettings(BaseModel):  # type: ignore[misc]
    """WebSocket configuration."""

    MAX_CONNECTIONS_PER_USER: int = 5
    MESSAGE_RATE_LIMIT: int = 100
    ALLOWED_ORIGINS: list[str] = ["*"]


class AuditSettings(BaseModel):  # type: ignore[misc]
    """Audit logging configuration."""

    ENABLED: bool = True
    RETENTION_DAYS: int = 365
    QUEUE_MAX_SIZE: int = 10000
    BATCH_SIZE: int = 100
    BATCH_TIMEOUT: float = 1.0
    QUEUE_TIMEOUT: float = 1.0


class LoggingSettings(BaseModel):  # type: ignore[misc]
    """Logging configuration."""

    FILE_PATH: str = "logs/logging_errors.log"
    EXCLUDED_PATHS: list[str] = ["/metrics", "/health"]
    LEVEL: str = "INFO"
    CONSOLE_FORMAT: str = "human"
    audit: AuditSettings = AuditSettings()


class ServiceCircuitBreakerSettings(BaseModel):  # type: ignore[misc]
    """Circuit breaker for a service."""

    FAIL_MAX: int
    TIMEOUT: int


class CircuitBreakerSettings(BaseModel):  # type: ignore[misc]
    """Circuit breaker configuration."""

    ENABLED: bool = True
    keycloak: ServiceCircuitBreakerSettings = ServiceCircuitBreakerSettings(
        FAIL_MAX=5, TIMEOUT=60
    )
    redis: ServiceCircuitBreakerSettings = ServiceCircuitBreakerSettings(
        FAIL_MAX=3, TIMEOUT=30
    )


class ProfilingSettings(BaseModel):  # type: ignore[misc]
    """Profiling configuration."""

    ENABLED: bool = True
    OUTPUT_DIR: str = "profiling_reports"
    INTERVAL_SECONDS: int = 30
