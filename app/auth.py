from starlette.authentication import (
    AuthCredentials,
    AuthenticationBackend,
    BaseUser,
)

from app.logging import logger
from app.schemas.user import UserModel


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

        # FIXME: This is mocked user
        user_data = {
            "firstname": "Aleksandar",
            "lastname": "Krsteski",
            "username": "acika",
            "email": "krsteski_aleksandar@hotmail.com",
        }
        user: UserModel = UserModel(**user_data)
        roles = user.roles

        return AuthCredentials(roles), AuthUser(user)
        # return AuthCredentials(roles), AuthUser(None)
