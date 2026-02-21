import time
from typing import Any

from fastapi_keycloak_rbac.config import KeycloakAuthSettings
from fastapi_keycloak_rbac.manager import (
    KeycloakManager as _BaseKeycloakManager,
)
from keycloak.exceptions import KeycloakAuthenticationError
from pybreaker import CircuitBreaker

from app.listeners.metrics import CircuitBreakerMetricsListener
from app.logging import logger
from app.settings import app_settings
from app.utils.metrics import (
    circuit_breaker_state,
    keycloak_auth_attempts_total,
    keycloak_operation_duration_seconds,
)


def _make_settings() -> KeycloakAuthSettings:
    """Build KeycloakAuthSettings from project app_settings."""
    return KeycloakAuthSettings(
        server_url=f"{app_settings.KEYCLOAK_BASE_URL}/",
        realm=app_settings.KEYCLOAK_REALM,
        client_id=app_settings.KEYCLOAK_CLIENT_ID,
    )


class _KeycloakManagerWithMetrics:
    """
    Wraps the package KeycloakManager adding circuit breaker and Prometheus metrics.

    Preserves the same interface (openid, login_async, decode_token) so all
    existing callers continue to work without changes.
    """

    def __init__(self) -> None:
        self._manager = _BaseKeycloakManager(settings=_make_settings())
        # Expose openid client directly (used by auth.py for basic auth)
        self.openid = self._manager.openid

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
            circuit_breaker_state.labels(service="keycloak").set(
                0
            )  # 0 = closed
        else:
            self.circuit_breaker = None
            logger.info("Keycloak circuit breaker disabled")

    async def login_async(
        self, username: str, password: str
    ) -> dict[str, Any]:
        """Login with circuit breaker protection and Prometheus metrics."""
        start_time = time.time()

        async def _do_login() -> dict[str, Any]:
            try:
                result = await self._manager.login_async(username, password)
                keycloak_auth_attempts_total.labels(
                    status="success", method="password"
                ).inc()
                return result
            except KeycloakAuthenticationError:
                keycloak_auth_attempts_total.labels(
                    status="failure", method="password"
                ).inc()
                raise
            except Exception:
                keycloak_auth_attempts_total.labels(
                    status="error", method="password"
                ).inc()
                raise

        try:
            if self.circuit_breaker:
                return await self.circuit_breaker.call(_do_login)
            return await _do_login()
        finally:
            keycloak_operation_duration_seconds.labels(
                operation="login"
            ).observe(time.time() - start_time)

    async def decode_token(self, token: str) -> dict[str, Any]:
        """Decode a Keycloak JWT token."""
        return await self._manager.decode_token(token)


# Public alias used by tests and other modules
KeycloakManager = _KeycloakManagerWithMetrics

# Module-level singleton instance
keycloak_manager = _KeycloakManagerWithMetrics()
