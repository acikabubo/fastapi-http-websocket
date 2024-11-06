from decouple import config
from starlette.datastructures import Secret

ACTIONS_FILE_PATH = config(
    "ACTIONS_FILE_PATH", cast=str, default="actions.json"
)

# Keycloak settings
KEYCLOAK_REALM = config("KEYCLOAK_REALM", cast=str)
KEYCLOAK_CLIENT_ID = config("KEYCLOAK_CLIENT_ID", cast=str)
KEYCLOAK_BASE_URL = config(
    "KEYCLOAK_BASE_URL", cast=str, default="http://hw-keycloak:8080/"
)
KEYCLOAK_ADMIN_USERNAME = config("KEYCLOAK_ADMIN_USERNAME", cast=str)
KEYCLOAK_ADMIN_PASSWORD = config("KEYCLOAK_ADMIN_PASSWORD", cast=str)

# Redis settings
REDIS_IP = config("REDIS_IP", cast=str, default="localhost")

USER_SESSION_REDIS_KEY_PREFIX = config(
    "USER_SESSION_REDIS_KEY_PREFIX", cast=str, default="session:"
)

MAIN_REDIS_DB = config("MAIN_REDIS_DB", cast=int, default=1)
AUTH_REDIS_DB = config("AUTH_REDIS_DB", cast=int, default=10)
