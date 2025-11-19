import re

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=True)

    ACTIONS_FILE_PATH: str = "actions.json"

    # Keycloak settings
    KEYCLOAK_REALM: str
    KEYCLOAK_CLIENT_ID: str
    KEYCLOAK_BASE_URL: str = "http://hw-keycloak:8080/"

    # Keycloak admin credentials
    KEYCLOAK_ADMIN_USERNAME: str
    KEYCLOAK_ADMIN_PASSWORD: str

    # Redis settings
    REDIS_IP: str = "localhost"

    USER_SESSION_REDIS_KEY_PREFIX: str = "session:"
    MAIN_REDIS_DB: int = 1
    AUTH_REDIS_DB: int = 10

    EXCLUDED_PATHS: re.Pattern = re.compile(r"^(/docs|/openapi.json)$")

    # Debug mode settings
    DEBUG_AUTH: bool = False
    DEBUG_AUTH_USERNAME: str = "acika"
    DEBUG_AUTH_PASSWORD: str = "12345"


app_settings = Settings()
