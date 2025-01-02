from typing import Annotated
from urllib.parse import parse_qsl

from fastapi import Depends, HTTPException
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
)
from fastapi.security.utils import get_authorization_scheme_param
from jwcrypto.jwt import JWTExpired
from keycloak.exceptions import KeycloakAuthenticationError
from starlette.authentication import AuthCredentials, AuthenticationBackend

from app.logging import logger
from app.managers.keycloak_manager import KeycloakManager
from app.schemas.user import UserModel
from app.settings import app_settings


class AuthBackend(AuthenticationBackend):
    """
    Authentication backend for handling both HTTP and WebSocket requests using Keycloak tokens.

    This class extends AuthenticationBackend to provide token-based authentication against a Keycloak server.
    It processes both HTTP and WebSocket requests differently, extracting the access token from either
    headers or query parameters respectively.

    Attributes:
        excluded_paths: A list of URL paths that should bypass authentication

    The authentication process involves:
    1. Extracting the access token from the request
    2. Decoding and validating the token using KeycloakManager
    3. Creating a UserModel from the decoded token data
    4. Returning authentication credentials and user object if successful

    Authentication will fail silently (return None) in cases of:
    - Expired JWT tokens
    - Invalid Keycloak credentials
    - Token decoding errors
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.excluded_paths = app_settings.EXCLUDED_PATHS

    async def authenticate(self, request):  # pragma: no cover
        """
        Authenticates a request by decoding the access token and retrieving the user data.
        This method is used to handle both HTTP and WebSocket requests, with different logic for each request type.
        It attempts to decode the access token using the KeycloakManager, and if successful, creates a UserModel object from the decoded user data.
        If the access token is expired or invalid, it logs the error and returns without authentication.
        """
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
            kc_manager = KeycloakManager()

            # FIXME: Simulate keycloak user login
            token = kc_manager.login("acika", "12345")
            access_token = token["access_token"]
            print()
            print(access_token)
            print()

            # Decode access token and get user data
            user_data = kc_manager.openid.decode_token(access_token)

            # Make logged in user object
            user: UserModel = UserModel(**user_data)

            return AuthCredentials(user.roles), user

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
    """
    Authenticates a user using Keycloak basic authentication credentials and returns a UserModel object.

    This function is used to authenticate a user by verifying their username and password against a Keycloak identity provider.
    If the authentication is successful, it decodes the access token and creates a UserModel object from the user data.

    If the authentication fails, it raises a HTTPException with a 401 Unauthorized status code and a "Invalid credentials" detail.
    """
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
