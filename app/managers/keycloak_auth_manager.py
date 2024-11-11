from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from keycloak import KeycloakAdmin, KeycloakOpenID

from app.logging import logger
from app.schemas.user import UserModel
from app.settings import (
    KEYCLOAK_ADMIN_PASSWORD,
    KEYCLOAK_ADMIN_USERNAME,
    KEYCLOAK_BASE_URL,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_REALM,
)


class KeycloakAuthManager:
    __instance = None

    def __init__(self):
        """
        Initialize KeycloakAuthManager instance.

        This method initializes two Keycloak clients: `admin` and `openid`.
        The `admin` client is used for administrative tasks, while the `openid` client is used for OpenID Connect operations.

        Parameters:
        None

        Returns:
        None
        """
        self.admin = KeycloakAdmin(
            server_url=KEYCLOAK_BASE_URL,
            username=KEYCLOAK_ADMIN_USERNAME,
            password=KEYCLOAK_ADMIN_PASSWORD,
            realm_name=KEYCLOAK_REALM,
            user_realm_name="master",
        )

        self.openid = KeycloakOpenID(
            server_url=f"{KEYCLOAK_BASE_URL}/",
            client_id=KEYCLOAK_CLIENT_ID,
            realm_name=KEYCLOAK_REALM,
            # client_secret_key=KEYCLOAK_CLIENT_SECRET
        )

        # Cache public key to avoid frequent requests to Keycloak
        self.public_key = None

    def get_public_key(self):
        """Cache and return the public key"""
        if not self.public_key:
            try:
                self.public_key = self.openid.public_key()
                return self.public_key
            except Exception as e:
                logger.error(f"Failed to fetch public key: {e}")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service unavailable",
                )
        return self.public_key

    def verify_token(self, token: str) -> dict:
        """Verify the JWT token"""
        try:
            public_key = self.get_public_key()
            return self.openid.decode_token(
                token,
                key=public_key,
                options={
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_exp": True,
                },
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            )

    def login(self, username: str, password: str):
        """
        Authenticate a user and obtain a token for subsequent API calls.

        Parameters:
        username (str): The username of the user to authenticate.
        password (str): The password of the user to authenticate.

        Returns:
        str: The access token obtained after successful authentication.
        """
        return self.openid.token(username=username, password=password)

    def __new__(cls):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls)
        return cls.__instance

    def get_user_from_token(self, token: str) -> UserModel:
        """Extract user information from token"""
        user_data = self.openid.decode_token(token["access_token"])

        return UserModel(**user_data)


# FIXME: Check and clean the code below


# Create singleton instance
@lru_cache()
def get_auth_handler():
    return KeycloakAuthManager()


# OAuth2 scheme for FastAPI
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_BASE_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
)


# Dependency for protected routes
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_handler: KeycloakAuthManager = Depends(get_auth_handler),
) -> UserModel:
    return await auth_handler.get_user_from_token(token)


# Admin-only dependency
async def get_admin_user(
    current_user: UserModel = Depends(get_current_user),
) -> UserModel:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
