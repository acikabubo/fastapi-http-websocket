from typing import Any, Callable

from keycloak import KeycloakOpenID
from pybreaker import (
    CircuitBreaker,
    CircuitBreakerListener,
    CircuitBreakerState,
)

from app.logging import logger
from app.settings import app_settings


class KeycloakCircuitBreakerListener(CircuitBreakerListener):  # type: ignore[misc]
    """
    Listener for Keycloak circuit breaker events.

    Tracks state changes and failures, updating Prometheus metrics.
    """

    def before_call(
        self,
        _cb: CircuitBreaker,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Called before circuit breaker calls the function."""
        pass  # No action needed before call

    def success(self, _cb: CircuitBreaker) -> None:
        """Called when circuit breaker call succeeds."""
        pass  # No action needed on success

    def failure(self, _cb: CircuitBreaker, exc: BaseException) -> None:
        """Called when circuit breaker call fails."""
        logger.error(f"Keycloak circuit breaker failure: {exc}")

        from app.utils.metrics import circuit_breaker_failures_total

        circuit_breaker_failures_total.labels(service="keycloak").inc()

    def state_change(
        self,
        _cb: CircuitBreaker,
        old_state: CircuitBreakerState | None,
        new_state: CircuitBreakerState,
    ) -> None:
        """Called when circuit breaker state changes."""
        old_state_name = old_state.name if old_state else "unknown"
        new_state_name = new_state.name

        logger.warning(
            f"Keycloak circuit breaker state changed: "
            f"{old_state_name} → {new_state_name}"
        )

        # Lazy import to avoid circular dependency
        from app.utils.metrics import (
            circuit_breaker_state,
            circuit_breaker_state_changes_total,
        )

        # Map states to numeric values for Gauge metric
        state_mapping = {"closed": 0, "open": 1, "half_open": 2}

        circuit_breaker_state.labels(service="keycloak").set(
            state_mapping.get(new_state_name, 0)
        )
        circuit_breaker_state_changes_total.labels(
            service="keycloak",
            from_state=old_state_name,
            to_state=new_state_name,
        ).inc()


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
            self.circuit_breaker = CircuitBreaker(
                fail_max=app_settings.KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX,
                reset_timeout=app_settings.KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT,
                name="keycloak",
                listeners=[KeycloakCircuitBreakerListener()],
            )
            logger.info(
                f"Keycloak circuit breaker initialized "
                f"(fail_max={app_settings.KEYCLOAK_CIRCUIT_BREAKER_FAIL_MAX}, "
                f"timeout={app_settings.KEYCLOAK_CIRCUIT_BREAKER_TIMEOUT}s)"
            )

            # Initialize metrics with default values (circuit breaker starts in closed state)
            from app.utils.metrics import circuit_breaker_state

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
