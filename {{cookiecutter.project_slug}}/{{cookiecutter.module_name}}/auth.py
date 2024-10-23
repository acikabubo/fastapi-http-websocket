import secrets
from typing import Annotated, List

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
)
{% if cookiecutter.use_keycloak == "y" %}
from keycloak.exceptions import KeycloakAuthenticationError
{% endif %}
from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
)
{% if cookiecutter.use_keycloak == "y" %}
from {{cookiecutter.module_name}}.keycloak_manager import KeycloakManager
{% endif %}
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.schemas.user import UserModel
from {{cookiecutter.module_name}}.settings import KEYCLOAK_CLIENT_ID


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
        user = None
        roles = []

        {% if cookiecutter.use_keycloak == "y" %}
        kc_manager = KeycloakManager()

        token = kc_manager.login("acika", "12345")
        user_data = kc_manager.openid.decode_token(token["access_token"])

        # Make logged in user object
        user: UserModel = UserModel(**user_data)
        roles = user.roles
        {% endif %}

        return AuthCredentials(roles), AuthUser(user)


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
            kc_manager = KeycloakManager()
            payload = kc_manager.openid.decode_token(jwtoken)

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
