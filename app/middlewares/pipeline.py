"""
Explicit middleware pipeline with dependency validation and visualization.

This module provides a MiddlewarePipeline class that handles middleware
registration in a clear, logical order while managing FastAPI/Starlette's
reverse execution order internally.

The pipeline validates middleware dependencies at startup and provides
visualization of the execution order for debugging and documentation.
"""

from typing import Any

from fastapi import FastAPI
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.logging import logger
from app.middlewares.audit_middleware import AuditMiddleware
from app.middlewares.correlation_id import CorrelationIDMiddleware
from app.middlewares.logging_context import LoggingContextMiddleware
from app.middlewares.prometheus import PrometheusMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.request_size_limit import RequestSizeLimitMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware


class MiddlewarePipeline:
    """
    Manages middleware registration with explicit ordering and dependency validation.

    The middleware list represents the LOGICAL execution order (request → response).
    FastAPI/Starlette middleware executes in reverse order of registration, but this
    class handles that reversal internally so you can think in terms of execution flow.

    Example:
        ```python
        pipeline = MiddlewarePipeline(allowed_hosts=["example.com"])
        pipeline.validate_dependencies()
        pipeline.apply_to_app(app)
        logger.info(f"Middleware order: {pipeline.visualize()}")
        ```
    """

    def __init__(
        self,
        allowed_hosts: list[str] | None = None,
        auth_backend: Any | None = None,
    ):
        """
        Initialize middleware pipeline with configuration.

        Args:
            allowed_hosts: List of allowed host headers for TrustedHostMiddleware.
            auth_backend: Authentication backend for AuthenticationMiddleware.
        """
        # Middleware in LOGICAL execution order (request flow)
        # Each middleware is a tuple: (MiddlewareClass, kwargs_dict)
        self.middleware: list[tuple[type, dict[str, Any]]] = [
            # 1. TrustedHost - Validates host headers first (security layer)
            (TrustedHostMiddleware, {"allowed_hosts": allowed_hosts or ["*"]}),
            # 2. CorrelationID - Generate correlation ID early for request tracking
            (CorrelationIDMiddleware, {}),
            # 3. LoggingContext - Set up logging context with correlation ID
            (LoggingContextMiddleware, {}),
            # 4. Authentication - Identify user (required by RateLimit and Audit)
            (
                AuthenticationMiddleware,
                {"backend": auth_backend} if auth_backend else {},
            ),
            # 5. RateLimit - Check rate limits after authentication (needs user context)
            (RateLimitMiddleware, {}),
            # 6. RequestSizeLimit - Validate request size
            (RequestSizeLimitMiddleware, {}),
            # 7. Audit - Log authenticated requests (needs user context)
            (AuditMiddleware, {}),
            # 8. SecurityHeaders - Add security headers to response
            (SecurityHeadersMiddleware, {}),
            # 9. Prometheus - Collect metrics (should be last to measure everything)
            (PrometheusMiddleware, {}),
        ]

        # Dependency map: {MiddlewareClass: [list of required middleware classes]}
        # A middleware can only execute if its dependencies executed before it
        self.dependencies: dict[type, list[type]] = {
            # RateLimitMiddleware needs user context from AuthenticationMiddleware
            RateLimitMiddleware: [AuthenticationMiddleware],
            # AuditMiddleware needs user context from AuthenticationMiddleware
            AuditMiddleware: [AuthenticationMiddleware],
            # LoggingContextMiddleware needs correlation ID from CorrelationIDMiddleware
            LoggingContextMiddleware: [CorrelationIDMiddleware],
        }

    def apply_to_app(self, app: FastAPI) -> None:
        """
        Register middleware to FastAPI app in correct order.

        FastAPI/Starlette registers middleware in REVERSE order of execution,
        so we reverse our logical order before registration.

        Args:
            app: FastAPI application instance to register middleware on.
        """
        # Register in reverse order (FastAPI quirk)
        for middleware_class, kwargs in reversed(self.middleware):
            # Skip if backend is None (AuthenticationMiddleware without backend)
            if middleware_class == AuthenticationMiddleware and not kwargs.get(
                "backend"
            ):
                continue

            app.add_middleware(middleware_class, **kwargs)

        logger.info(f"Middleware pipeline applied: {self.visualize()}")

    def visualize(self) -> str:
        """
        Return string representation of middleware execution order.

        Returns:
            String showing middleware execution flow with arrows.

        Example:
            "TrustedHostMiddleware → CorrelationIDMiddleware → ... → PrometheusMiddleware"
        """
        return " → ".join(mw[0].__name__ for mw in self.middleware)

    def validate_dependencies(self) -> None:
        """
        Validate that middleware dependencies are satisfied.

        Checks that for each middleware with dependencies, all required
        middleware appear BEFORE it in the execution order.

        Raises:
            ValueError: If a middleware dependency is not satisfied.

        Example:
            ```python
            pipeline = MiddlewarePipeline()
            pipeline.validate_dependencies()  # Raises if dependencies invalid
            ```
        """
        # Build index of middleware positions
        middleware_positions = {
            mw_class: idx for idx, (mw_class, _) in enumerate(self.middleware)
        }

        # Check each middleware with dependencies
        for middleware_class, required_middleware in self.dependencies.items():
            # Get position of the middleware being checked
            if middleware_class not in middleware_positions:
                raise ValueError(
                    f"Middleware {middleware_class.__name__} has dependencies "
                    f"but is not in the pipeline"
                )

            middleware_position = middleware_positions[middleware_class]

            # Check that all required middleware appear BEFORE this one
            for required_class in required_middleware:
                if required_class not in middleware_positions:
                    raise ValueError(
                        f"Dependency {required_class.__name__} required by "
                        f"{middleware_class.__name__} is not in the pipeline"
                    )

                required_position = middleware_positions[required_class]

                if required_position >= middleware_position:
                    raise ValueError(
                        f"Middleware dependency violation: "
                        f"{middleware_class.__name__} requires "
                        f"{required_class.__name__} to execute before it, "
                        f"but {required_class.__name__} is at position "
                        f"{required_position} and {middleware_class.__name__} "
                        f"is at position {middleware_position}"
                    )

        logger.info("Middleware dependencies validated successfully")

    def get_middleware_list(self) -> list[tuple[type, dict[str, Any]]]:
        """
        Get the list of middleware in logical execution order.

        Returns:
            List of tuples containing (MiddlewareClass, kwargs_dict).
        """
        return self.middleware.copy()

    def get_middleware_count(self) -> int:
        """
        Get the number of middleware in the pipeline.

        Returns:
            Integer count of middleware.
        """
        return len(self.middleware)
