import secrets
from typing import Annotated, List

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
from keycloak.exceptions import KeycloakAuthenticationError
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
)

from app.logging import logger
from app.managers.keycloak_auth_manager import KeycloakAuthManager
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

        # if request.scope["type"] == "websocket":
        #     qs = dict(parse_qsl(request.scope["query_string"].decode("utf8")))
        #     auth_access_token = qs.get("Authorization", "")
        # else:  # type -> http
        #     auth_access_token = request.headers.get("authorization", "")

        # scheme, access_token = get_authorization_scheme_param(
        #     auth_access_token
        # )

        # FIXME: Simulate keycloak user login
        try:
            kc_auth_manager = KeycloakAuthManager()

            token = kc_auth_manager.login("acika", "12345")

            # Make logged in user object
            user: UserModel = kc_auth_manager.get_user_from_token(token)

            return AuthCredentials(user.roles), AuthUser(user)
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

        request.scope["user"] = UserModel(**payload)

        return payload

    def verify_jwt(self, jwtoken: str):
        try:
            kc_auth_manager = KeycloakAuthManager()
            payload = kc_auth_manager.openid.decode_token(jwtoken)

            user_roles = (
                payload.get("resource_access", {})
                .get(KEYCLOAK_CLIENT_ID, {})
                .get("roles", [])
            )

            # print()
            # print(f"    User roles: {user_roles}")
            # print(f"Required roles: {self.required_roles}")
            # print()
            # FIXME: Temporary disable role check
            # for role in self.required_roles:
            #     if role in user_roles:
            #         return payload
            return payload  # FIXME: this role need to be removed

            # raise HTTPException(
            #     status_code=status.HTTP_403_FORBIDDEN,
            #     detail="User does not have any of expected roles",
            # )
        except Exception as ex:
            logger.error(ex)


def logged_kc_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())],
) -> UserModel:
    try:
        kc_auth_manager = KeycloakAuthManager()
        token = kc_auth_manager.login(
            credentials.username, credentials.password
        )

        user: UserModel = kc_auth_manager.get_user_from_token(token)

        return user
    except KeycloakAuthenticationError as ex:
        raise HTTPException(
            status_code=ex.response_code,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


# Admin-only dependency
async def get_admin_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())],
) -> UserModel:
    try:
        kc_auth_manager = KeycloakAuthManager()
        token = kc_auth_manager.login(
            credentials.username, credentials.password
        )

        user: UserModel = kc_auth_manager.get_user_from_token(token)

        if not user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

        return user
    except KeycloakAuthenticationError as ex:
        raise HTTPException(
            status_code=ex.response_code,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
