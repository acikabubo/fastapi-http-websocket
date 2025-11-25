from keycloak import KeycloakOpenID

from app.settings import app_settings
from app.utils.singleton import SingletonMeta


class KeycloakManager(metaclass=SingletonMeta):
    """
    Singleton manager for Keycloak authentication operations.

    Provides OpenID Connect authentication and token management for the application.
    """

    def __init__(self):
        """
        Initialize KeycloakManager instance.

        This method initializes the KeycloakOpenID client for OpenID
        Connect operations.
        """
        self.openid = KeycloakOpenID(
            server_url=f"{app_settings.KEYCLOAK_BASE_URL}/",
            client_id=app_settings.KEYCLOAK_CLIENT_ID,
            realm_name=app_settings.KEYCLOAK_REALM,
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
