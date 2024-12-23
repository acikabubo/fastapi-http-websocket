from typing import Any

from keycloak import KeycloakAdmin, KeycloakOpenID

from app.settings import (
    KEYCLOAK_ADMIN_PASSWORD,
    KEYCLOAK_ADMIN_USERNAME,
    KEYCLOAK_BASE_URL,
    KEYCLOAK_CLIENT_ID,
    KEYCLOAK_REALM,
)


class KeycloakManager:
    __instance = None

    def __init__(self):
        """
        Initialize KeycloakManager instance.

        This method initializes two Keycloak clients: `admin` and `openid`.
        The `admin` client is used for administrative tasks, while the `openid` client is used for OpenID Connect operations.

        Parameters:
        None

        Returns:
        None
        """
        # FIXME: Unnecessary admin client, probably should be removed
        # self.admin = KeycloakAdmin(
        #     server_url=KEYCLOAK_BASE_URL,
        #     username=KEYCLOAK_ADMIN_USERNAME,
        #     password=KEYCLOAK_ADMIN_PASSWORD,
        #     realm_name=KEYCLOAK_REALM,
        #     user_realm_name="master",
        # )

        self.openid = KeycloakOpenID(
            server_url=f"{KEYCLOAK_BASE_URL}/",
            client_id=KEYCLOAK_CLIENT_ID,
            realm_name=KEYCLOAK_REALM,
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
