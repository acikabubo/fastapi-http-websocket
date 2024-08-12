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

REDIS_IP = config("REDIS_IP", cast=str, default="localhost")
