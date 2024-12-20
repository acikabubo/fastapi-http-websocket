from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security.utils import get_authorization_scheme_param
from jwcrypto.jwt import JWTExpired

{% if cookiecutter.use_keycloak == "y" %}
from keycloak.exceptions import KeycloakAuthenticationError
{% endif %}
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend
)
{% if cookiecutter.use_keycloak == "y" %}
from {{cookiecutter.module_name}}.managers.keycloak_manager import KeycloakManager
{% endif %}
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.schemas.user import UserModel
from {{cookiecutter.module_name}}.settings import EXCLUDED_PATHS


class AuthBackend(AuthenticationBackend):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.excluded_paths = EXCLUDED_PATHS
    async def authenticate(self, request):  # pragma: no cover
        logger.debug(f"Request type -> {request.scope['type']}")

        if request.scope["type"] == "websocket":
            qs = dict(parse_qsl(request.scope["query_string"].decode("utf8")))
            auth_access_token = qs.get("Authorization", "")
        else:  # type -> http
            if self.excluded_paths.match(request.url.path):
                return

            auth_access_token = request.headers.get("authorization", "")

        _, access_token = get_authorization_scheme_param(auth_access_token)

        try:
            # FIXME: Simulate keycloak user login
            user = None
            roles = []

            {% if cookiecutter.use_keycloak == "y" %}
            kc_manager = KeycloakManager()

            token = kc_manager.login("acika", "12345")
            access_token = token["access_token"]

            user_data = kc_manager.openid.decode_token(access_token)

            # Make logged in user object
            user: UserModel = UserModel(**user_data)
            roles = user.roles
            {% endif %}

            return AuthCredentials(roles), user
        except JWTExpired as ex:
            logger.error(f"JWT token expired: {ex}")
            return

        except KeycloakAuthenticationError as ex:
            logger.error(f"Invalid credentials: {ex}")
            return

        except ValueError as ex:
            logger.error(f"Error occurred while decode auth token: {ex}")
            return


# USED FOR DEVELOP
def basic_auth_keycloak_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())],
) -> UserModel:
    try:
        kc_manager = KeycloakManager()
        token = kc_manager.login(credentials.username, credentials.password)
        user_data = kc_manager.openid.decode_token(token["access_token"])

        user: UserModel = UserModel(**user_data)

        return user
    except KeycloakAuthenticationError as ex:
        raise HTTPException(
            status_code=ex.response_code,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
