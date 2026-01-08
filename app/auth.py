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

from app.exceptions import AuthenticationError
from app.logging import logger
from app.managers.keycloak_manager import keycloak_manager
from app.schemas.user import UserModel
from app.settings import app_settings


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
            - Expired JWT tokens (message contains 'token_expired')
            - Invalid Keycloak credentials (message contains 'invalid_credentials')
            - Token decoding errors (message contains 'token_decode_error')
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.excluded_paths = app_settings.EXCLUDED_PATHS

    async def authenticate(
        self, request: Any
    ) -> tuple[AuthCredentials, UserModel] | None:
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
        import time

        from app.utils.metrics import (
            auth_backend_requests_total,
            keycloak_operation_duration_seconds,
            keycloak_token_validation_total,
        )
        from app.utils.token_cache import (
            cache_token_claims,
            get_cached_token_claims,
        )

        logger.debug(f"Request type -> {request.scope['type']}")

        request_type = (
            "websocket" if request.scope["type"] == "websocket" else "http"
        )
        start_time = time.time()

        if request.scope["type"] == "websocket":
            qs = dict(parse_qsl(request.scope["query_string"].decode("utf8")))
            auth_access_token = qs.get("Authorization", "")
        else:  # type -> http
            if self.excluded_paths.match(request.url.path):
                return None

            auth_access_token = request.headers.get("authorization", "")

        _, access_token = get_authorization_scheme_param(auth_access_token)

        try:
            # Debug mode: bypass token validation (ONLY for development)
            if app_settings.DEBUG_AUTH:
                logger.warning(
                    "DEBUG_AUTH is enabled - using debug credentials. "
                    "NEVER enable this in production!"
                )
                token = await keycloak_manager.login_async(
                    app_settings.DEBUG_AUTH_USERNAME,
                    app_settings.DEBUG_AUTH_PASSWORD,
                )
                access_token = token["access_token"]

            # Check cache first for decoded token claims
            user_data = await get_cached_token_claims(access_token)

            if user_data is None:
                # Cache miss - decode token from Keycloak
                user_data = await keycloak_manager.openid.a_decode_token(
                    access_token
                )

                # Cache the decoded claims for future requests
                await cache_token_claims(access_token, user_data)

            # Make logged in user object
            user: UserModel = UserModel(**user_data)

            # Track successful token validation
            keycloak_token_validation_total.labels(
                status="valid", reason="success"
            ).inc()

            # Track successful auth backend request
            auth_backend_requests_total.labels(
                type=request_type, outcome="success"
            ).inc()

            return AuthCredentials(user.roles), user

        except JWTExpired as ex:
            logger.error(f"JWT token expired: {ex}")

            # Track expired token
            keycloak_token_validation_total.labels(
                status="expired", reason="token_expired"
            ).inc()

            # Track failed auth backend request
            auth_backend_requests_total.labels(
                type=request_type, outcome="denied"
            ).inc()

            raise AuthenticationError(f"token_expired: {ex}")

        except KeycloakAuthenticationError as ex:
            logger.error(f"Invalid credentials: {ex}")

            # Track invalid token
            keycloak_token_validation_total.labels(
                status="invalid", reason="invalid_credentials"
            ).inc()

            # Track failed auth backend request
            auth_backend_requests_total.labels(
                type=request_type, outcome="denied"
            ).inc()

            raise AuthenticationError(f"invalid_credentials: {ex}")

        except ValueError as ex:
            logger.error(f"Error occurred while decode auth token: {ex}")

            # Track token decode error
            keycloak_token_validation_total.labels(
                status="error", reason="token_decode_error"
            ).inc()

            # Track error in auth backend request
            auth_backend_requests_total.labels(
                type=request_type, outcome="error"
            ).inc()

            raise AuthenticationError(f"token_decode_error: {ex}")

        finally:
            # Track operation duration
            duration = time.time() - start_time
            keycloak_operation_duration_seconds.labels(
                operation="validate_token"
            ).observe(duration)


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
        token = await keycloak_manager.login_async(
            credentials.username, credentials.password
        )
        user_data = await keycloak_manager.openid.a_decode_token(
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
