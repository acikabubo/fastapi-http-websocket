from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi_keycloak_rbac.backend import AuthBackend as AuthBackend  # noqa: F401
from keycloak.exceptions import KeycloakAuthenticationError

from app.managers.keycloak_manager import keycloak_manager
from app.schemas.user import UserModel


# USED FOR DEVELOP
async def basic_auth_keycloak_user(
    credentials: Annotated[HTTPBasicCredentials, Depends(HTTPBasic())],
) -> UserModel:
    """
    Authenticate user using Keycloak basic auth credentials (async).

    Args:
        credentials: HTTP Basic authentication credentials containing
            username and password.

    Returns:
        UserModel: Authenticated user model with roles and claims.

    Raises:
        HTTPException: 401 Unauthorized if authentication fails.
    """
    try:
        token = await keycloak_manager.login_async(
            credentials.username, credentials.password
        )
        user_data = await keycloak_manager.openid.a_decode_token(
            token["access_token"]
        )
        return UserModel(**user_data)
    except KeycloakAuthenticationError as ex:
        raise HTTPException(
            status_code=ex.response_code,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
