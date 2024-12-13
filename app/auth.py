from typing import Annotated, Any, List
from urllib.parse import parse_qsl

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    OAuth2PasswordBearer,
)
from fastapi.security.utils import get_authorization_scheme_param
from keycloak.exceptions import KeycloakAuthenticationError
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
)

from app.logging import logger
from app.managers.keycloak_manager import KeycloakManager
from app.schemas.user import UserModel
from app.settings import KEYCLOAK_CLIENT_ID


class AuthUser(BaseUser):
    def __init__(self, user) -> None:
        self.obj = user

    @property
    def is_authenticated(self) -> bool:
        return True


class AuthBackend(AuthenticationBackend):
    async def authenticate(self, request):  # pragma: no cover
        logger.debug(f"Request type -> {request.scope['type']}")

        if request.scope["type"] == "websocket":
            qs = dict(parse_qsl(request.scope["query_string"].decode("utf8")))
            auth_access_token = qs.get("Authorization", "")
        else:  # type -> http
            auth_access_token = request.headers.get("authorization", "")

        _, access_token = get_authorization_scheme_param(auth_access_token)

        try:
            kc_manager = KeycloakManager()

            # FIXME: Simulate keycloak user login
            # token = kc_manager.login("acika", "12345")
            # access_token = token["access_token"]
            # print()
            # print(access_token)
            # print()

            user_data = kc_manager.openid.decode_token(access_token)

            # Make logged in user object
            user: UserModel = UserModel(**user_data)
            roles = user.roles
            return AuthCredentials(roles), AuthUser(user)
        except KeycloakAuthenticationError as ex:
            raise HTTPException(
                status_code=ex.response_code,
                detail="Invalid credentials",
                headers={"WWW-Authenticate": "Basic"},
            )


class JWTBearer(HTTPBearer):
    def __init__(self, required_roles: List[str]):
        super(JWTBearer, self).__init__(auto_error=True)
        self.required_roles = required_roles

    async def __call__(self, request: Request):
        credentials: HTTPAuthorizationCredentials = await super(
            JWTBearer, self
        ).__call__(request)

        payload = self.verify_jwt(credentials.credentials)

        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

        request.scope["user"].obj = UserModel(**payload)

        return payload

    def verify_jwt(self, jwtoken: str):
        try:
            kc_manager = KeycloakManager()
            payload = kc_manager.openid.decode_token(jwtoken)

            user_roles = (
                payload.get("realm_access", {})
                # .get(KEYCLOAK_CLIENT_ID, {})
                .get("roles", [])
            )

            # FIXME: Temporary disable role check
            if self.required_roles in user_roles:
                return payload

            # return payload  # FIXME: this role need to be removed

            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have any of expected roles",
            )
        except Exception as ex:
            logger.error(ex)


def validate_token(token: str):
    """
    Validate Keycloak token
    """
    try:
        kc_manager = KeycloakManager()

        # Validate token configuration
        return kc_manager.openid.decode_token(token)
    except Exception as ex:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: str = Depends(OAuth2PasswordBearer(tokenUrl="/token")),
) -> dict[str, Any]:
    """
    Dependency to get the current authenticated user
    """
    # Validate the token
    user_data = validate_token(token)

    # Extract user information
    user: UserModel = UserModel(**user_data)

    return user


# USED FOR DEVELOP
def logged_kc_user(
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
