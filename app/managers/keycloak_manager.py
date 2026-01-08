from typing import Any

from keycloak import KeycloakOpenID

from app.settings import app_settings
from app.utils.singleton import SingletonMeta


class KeycloakManager(metaclass=SingletonMeta):
    """
    Singleton manager for Keycloak authentication operations.

    Provides OpenID Connect authentication and token management for the
    application using native async methods from python-keycloak library.
    """

    def __init__(self) -> None:
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

    async def login_async(
        self, username: str, password: str
    ) -> dict[str, Any]:
        """
        Authenticate a user asynchronously and obtain tokens.

        Uses native async method from python-keycloak library to prevent
        blocking the async event loop.

        Args:
            username: The username of the user to authenticate.
            password: The password of the user to authenticate.

        Returns:
            Token dictionary containing access_token, refresh_token,
            expires_in, etc.

        Raises:
            KeycloakAuthenticationError: If authentication fails.

        Example:
            >>> kc_manager = KeycloakManager()
            >>> token = await kc_manager.login_async("user", "pass")
            >>> access_token = token["access_token"]
        """
        import time

        from keycloak.exceptions import KeycloakAuthenticationError

        from app.utils.metrics import (
            keycloak_auth_attempts_total,
            keycloak_operation_duration_seconds,
        )

        start_time = time.time()

        try:
            result = await self.openid.a_token(
                username=username, password=password
            )

            # Track successful login
            keycloak_auth_attempts_total.labels(
                status="success", method="password"
            ).inc()

            return result

        except KeycloakAuthenticationError:
            # Track failed login (invalid credentials)
            keycloak_auth_attempts_total.labels(
                status="failure", method="password"
            ).inc()
            raise

        except Exception:
            # Track error (Keycloak unavailable, network error, etc.)
            keycloak_auth_attempts_total.labels(
                status="error", method="password"
            ).inc()
            raise

        finally:
            # Track operation duration
            duration = time.time() - start_time
            keycloak_operation_duration_seconds.labels(
                operation="login"
            ).observe(duration)
