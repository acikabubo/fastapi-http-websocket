from typing import Annotated, Any
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


class AuthenticationError(Exception):
    """
    Custom exception for authentication failures.

    This exception provides structured error information for authentication failures,
    allowing better error handling and debugging.

    Attributes:
        reason: A machine-readable error code (e.g., 'token_expired', 'invalid_credentials')
        detail: Human-readable error details
    """

    def __init__(self, reason: str, detail: str) -> None:
        """
        Initialize the AuthenticationError.

        Args:
            reason: A machine-readable error code indicating the failure type
            detail: Human-readable description of the error
        """
        self.reason = reason
        self.detail = detail
        super().__init__(f"{reason}: {detail}")


class AuthBackend(AuthenticationBackend):  # type: ignore[misc]
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

    Raises:
        AuthenticationError: When authentication fails due to:
            - Expired JWT tokens (reason='token_expired')
            - Invalid Keycloak credentials (reason='invalid_credentials')
            - Token decoding errors (reason='token_decode_error')
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.excluded_paths = app_settings.EXCLUDED_PATHS

    async def authenticate(self, request):  # type: ignore[no-untyped-def] # pragma: no cover
        """
        Authenticates a request by decoding the access token and retrieving the user data.

        This method is used to handle both HTTP and WebSocket requests, with different logic for each request type.
        It attempts to decode the access token using the KeycloakManager, and if successful, creates a UserModel object from the decoded user data.

        Args:
            request: The incoming request object (HTTP or WebSocket)

        Returns:
            Tuple of (AuthCredentials, UserModel) on success, None for excluded paths

        Raises:
            AuthenticationError: When authentication fails with specific reason codes
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

            # Debug mode: bypass token validation (ONLY for development)
            if app_settings.DEBUG_AUTH:
                logger.warning(
                    "DEBUG_AUTH is enabled - using debug credentials. "
                    "NEVER enable this in production!"
                )
                token = await kc_manager.login_async(
                    app_settings.DEBUG_AUTH_USERNAME,
                    app_settings.DEBUG_AUTH_PASSWORD,
                )
                access_token = token["access_token"]

            # Decode access token and get user data (async to prevent event loop blocking)
            user_data = await kc_manager.openid.a_decode_token(access_token)

            # Make logged in user object
            user: UserModel = UserModel(**user_data)

            return AuthCredentials(user.roles), user

        except JWTExpired as ex:
            logger.error(f"JWT token expired: {ex}")
            raise AuthenticationError("token_expired", str(ex))

        except KeycloakAuthenticationError as ex:
            logger.error(f"Invalid credentials: {ex}")
            raise AuthenticationError("invalid_credentials", str(ex))

        except ValueError as ex:
            logger.error(f"Error occurred while decode auth token: {ex}")
            raise AuthenticationError("token_decode_error", str(ex))


# USED FOR DEVELOP
async def basic_auth_keycloak_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())],
) -> UserModel:
    """
    Authenticate user using Keycloak basic auth credentials (async).

    This function authenticates a user by verifying their username and
    password against a Keycloak identity provider. If authentication is
    successful, it decodes the access token and creates a UserModel object.

    Uses native async methods from python-keycloak library to prevent
    blocking the event loop.

    Args:
        credentials: HTTP Basic authentication credentials containing
            username and password.

    Returns:
        UserModel: Authenticated user model with roles and claims.

    Raises:
        HTTPException: 401 Unauthorized if authentication fails.

    Example:
        >>> from fastapi.security import HTTPBasicCredentials
        >>> credentials = HTTPBasicCredentials(
        ...     username="user", password="pass"
        ... )
        >>> user = await basic_auth_keycloak_user(credentials)
    """
    try:
        kc_manager = KeycloakManager()
        token = await kc_manager.login_async(
            credentials.username, credentials.password
        )
        user_data = await kc_manager.openid.a_decode_token(
            token["access_token"]
        )

        user: UserModel = UserModel(**user_data)

        return user
    except KeycloakAuthenticationError as ex:
        raise HTTPException(
            status_code=ex.response_code,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
