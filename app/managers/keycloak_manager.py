from typing import Any

from keycloak import KeycloakOpenID
from pybreaker import CircuitBreaker

from app.listeners.metrics import CircuitBreakerMetricsListener
from app.logging import logger
from app.settings import app_settings
from app.utils.metrics import circuit_breaker_state


class KeycloakManager:
    """
    Manager for Keycloak authentication operations.

    Provides OpenID Connect authentication and token management for the
    application using native async methods from python-keycloak library.

    Note: This class is instantiated as a module-level singleton (keycloak_manager) below.
    Import and use keycloak_manager instead of creating new instances.
    """

    def __init__(self) -> None:
        """
        Initialize KeycloakManager instance.

        This method initializes the KeycloakOpenID client for OpenID
        Connect operations and sets up the circuit breaker for resilience.
        """
        self.openid = KeycloakOpenID(
            server_url=f"{app_settings.KEYCLOAK_BASE_URL}/",
            client_id=app_settings.KEYCLOAK_CLIENT_ID,
            realm_name=app_settings.KEYCLOAK_REALM,
        )

        # Initialize circuit breaker for Keycloak operations
        if app_settings.CIRCUIT_BREAKER_ENABLED:
            self.circuit_breaker: CircuitBreaker | None = CircuitBreaker(
                fail_max=app_settings.KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX,
                reset_timeout=app_settings.KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT,
                name="keycloak",
                listeners=[
                    CircuitBreakerMetricsListener(service_name="keycloak")
                ],
            )
            logger.info(
                f"Keycloak circuit breaker initialized "
                f"(fail_max={app_settings.KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX}, "
                f"timeout={app_settings.KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT}s)"
            )

            # Initialize metrics with default values (circuit breaker starts in closed state)
            circuit_breaker_state.labels(service="keycloak").set(
                0
            )  # 0 = closed
        else:
            self.circuit_breaker = None
            logger.info("Keycloak circuit breaker disabled")

    async def login_async(
        self, username: str, password: str
    ) -> dict[str, Any]:
        """
        Authenticate a user asynchronously and obtain tokens.

        Uses native async method from python-keycloak library to prevent
        blocking the async event loop. Protected by circuit breaker pattern
        to prevent cascading failures when Keycloak is unavailable.

        Args:
            username: The username of the user to authenticate.
            password: The password of the user to authenticate.

        Returns:
            Token dictionary containing access_token, refresh_token,
            expires_in, etc.

        Raises:
            KeycloakAuthenticationError: If authentication fails.
            CircuitBreakerError: If circuit breaker is open (fail-fast).

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

        # Define the actual login operation
        async def _do_login() -> dict[str, Any]:
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

        try:
            # Call the login operation through circuit breaker
            if self.circuit_breaker:
                result = await self.circuit_breaker.call(_do_login)
            else:
                result = await _do_login()

            return result

        finally:
            # Track operation duration
            duration = time.time() - start_time
            keycloak_operation_duration_seconds.labels(
                operation="login"
            ).observe(duration)


# Module-level singleton instance
keycloak_manager = KeycloakManager()
