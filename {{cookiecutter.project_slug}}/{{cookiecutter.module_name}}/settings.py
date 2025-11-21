import re

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True)

    ACTIONS_FILE_PATH: str = "actions.json"

    # Debug mode settings
    DEBUG_AUTH: bool = False

    {% if cookiecutter.use_keycloak == "y" %}
    # Keycloak settings
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_BASE_URL: str = "http://hw-keycloak:8080/"

    # Keycloak admin credentials
    KEYCLOAK_ADMIN_USERNAME: str
    KEYCLOAK_ADMIN_PASSWORD: str

    DEBUG_AUTH_USERNAME: str = "acika"
    DEBUG_AUTH_PASSWORD: str = "12345"
    {% endif %}

    {% if cookiecutter.use_redis == "y" %}
    # Redis settings
    REDIS_IP: str = "localhost"
    REDIS_PORT: int = 6379

    USER_SESSION_REDIS_KEY_PREFIX: str = "session:"
    MAIN_REDIS_DB: int = 1
    AUTH_REDIS_DB: int = 10
    {% endif %}

    # Database settings
    DB_USER: str = "hw-user"
    DB_PASSWORD: str = "hw-pass"
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
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    EXCLUDED_PATHS: re.Pattern = re.compile(
        r"^(/docs|/openapi.json|/health)$"
    )



    # Database initialization settings
    DB_INIT_RETRY_INTERVAL: int = 2
    DB_INIT_MAX_RETRIES: int = 10

    # Pagination defaults
    DEFAULT_PAGE_SIZE: int = 20

    # Logging settings
    LOG_FILE_PATH: str = "logs/logging_errors.log"


app_settings = Settings()
