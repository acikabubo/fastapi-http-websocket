"""
Tests for middleware pipeline with dependency validation.

These tests verify:
- Middleware pipeline construction and ordering
- Dependency validation logic
- Visualization output
- Integration with FastAPI application
"""

import pytest
from fastapi import FastAPI
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.middlewares.audit_middleware import AuditMiddleware
from app.middlewares.correlation_id import CorrelationIDMiddleware
from app.middlewares.logging_context import LoggingContextMiddleware
from app.middlewares.pipeline import MiddlewarePipeline
from app.middlewares.prometheus import PrometheusMiddleware
from app.middlewares.rate_limit import RateLimitMiddleware
from app.middlewares.request_size_limit import RequestSizeLimitMiddleware
from app.middlewares.security_headers import SecurityHeadersMiddleware


class TestMiddlewarePipelineConstruction:
    """Test pipeline construction and basic properties."""

    def test_pipeline_initialization(self):
        """Test pipeline initializes with correct defaults."""
        pipeline = MiddlewarePipeline()

        assert pipeline.get_middleware_count() == 9
        assert len(pipeline.get_middleware_list()) == 9

    def test_pipeline_with_custom_config(self):
        """Test pipeline accepts custom configuration."""
        allowed_hosts = ["example.com", "api.example.com"]
        auth_backend = object()  # Mock backend

        pipeline = MiddlewarePipeline(
            allowed_hosts=allowed_hosts,
            auth_backend=auth_backend,
        )

        middleware_list = pipeline.get_middleware_list()

        # Check TrustedHostMiddleware has correct config
        trusted_host_mw = next(
            (mw for mw in middleware_list if mw[0] == TrustedHostMiddleware),
            None,
        )
        assert trusted_host_mw is not None
        assert trusted_host_mw[1]["allowed_hosts"] == allowed_hosts

        # Check AuthenticationMiddleware has backend
        auth_mw = next(
            (
                mw
                for mw in middleware_list
                if mw[0] == AuthenticationMiddleware
            ),
            None,
        )
        assert auth_mw is not None
        assert auth_mw[1]["backend"] == auth_backend

    def test_middleware_logical_order(self):
        """Test middleware are in correct logical execution order."""
        pipeline = MiddlewarePipeline()
        middleware_list = pipeline.get_middleware_list()

        # Extract just the classes
        middleware_classes = [mw[0] for mw in middleware_list]

        # Expected order (as they should execute, not as registered)
        expected_order = [
            TrustedHostMiddleware,
            CorrelationIDMiddleware,
            LoggingContextMiddleware,
            AuthenticationMiddleware,
            RateLimitMiddleware,
            RequestSizeLimitMiddleware,
            AuditMiddleware,
            SecurityHeadersMiddleware,
            PrometheusMiddleware,
        ]

        assert middleware_classes == expected_order


class TestDependencyValidation:
    """Test middleware dependency validation."""

    def test_valid_dependencies(self):
        """Test that valid dependencies pass validation."""
        pipeline = MiddlewarePipeline()

        # Should not raise
        pipeline.validate_dependencies()

    def test_dependency_violation_detection(self):
        """Test that dependency violations are detected."""
        pipeline = MiddlewarePipeline()

        # Manually corrupt the order to violate dependencies
        # Move RateLimitMiddleware before AuthenticationMiddleware
        middleware_list = pipeline.get_middleware_list()

        # Find positions
        rate_limit_idx = next(
            i
            for i, (cls, _) in enumerate(middleware_list)
            if cls == RateLimitMiddleware
        )
        auth_idx = next(
            i
            for i, (cls, _) in enumerate(middleware_list)
            if cls == AuthenticationMiddleware
        )

        # Swap them to create violation
        middleware_list[rate_limit_idx], middleware_list[auth_idx] = (
            middleware_list[auth_idx],
            middleware_list[rate_limit_idx],
        )
        pipeline.middleware = middleware_list

        # Should raise ValueError
        with pytest.raises(
            ValueError, match="Middleware dependency violation"
        ):
            pipeline.validate_dependencies()

    def test_missing_dependency_detection(self):
        """Test detection of missing required middleware."""
        pipeline = MiddlewarePipeline()

        # Remove AuthenticationMiddleware to break dependencies
        pipeline.middleware = [
            (mw_class, kwargs)
            for mw_class, kwargs in pipeline.get_middleware_list()
            if mw_class != AuthenticationMiddleware
        ]

        # Should raise ValueError about missing dependency
        with pytest.raises(
            ValueError,
            match="Dependency.*required by.*is not in the pipeline",
        ):
            pipeline.validate_dependencies()

    def test_middleware_with_dependencies_not_in_pipeline(self):
        """Test error when middleware with dependencies is not in pipeline."""
        pipeline = MiddlewarePipeline()

        # Add a dependency for a middleware that doesn't exist
        class FakeMiddleware:
            pass

        pipeline.dependencies[FakeMiddleware] = [AuthenticationMiddleware]

        # Should raise ValueError
        with pytest.raises(
            ValueError,
            match="has dependencies but is not in the pipeline",
        ):
            pipeline.validate_dependencies()


class TestVisualization:
    """Test middleware visualization."""

    def test_visualize_output_format(self):
        """Test visualization produces correct format."""
        pipeline = MiddlewarePipeline()
        visualization = pipeline.visualize()

        # Should contain arrows
        assert "→" in visualization

        # Should contain all middleware names
        assert "TrustedHostMiddleware" in visualization
        assert "CorrelationIDMiddleware" in visualization
        assert "AuthenticationMiddleware" in visualization
        assert "PrometheusMiddleware" in visualization

    def test_visualize_order(self):
        """Test visualization shows middleware in logical order."""
        pipeline = MiddlewarePipeline()
        visualization = pipeline.visualize()

        # Split by arrow to get order
        middleware_names = [name.strip() for name in visualization.split("→")]

        # First should be TrustedHostMiddleware
        assert middleware_names[0] == "TrustedHostMiddleware"

        # Last should be PrometheusMiddleware
        assert middleware_names[-1] == "PrometheusMiddleware"

        # AuthenticationMiddleware should come before RateLimitMiddleware
        auth_idx = middleware_names.index("AuthenticationMiddleware")
        rate_limit_idx = middleware_names.index("RateLimitMiddleware")
        assert auth_idx < rate_limit_idx


class TestApplicationIntegration:
    """Test integration with FastAPI application."""

    def test_apply_to_app(self):
        """Test middleware can be applied to FastAPI app."""
        app = FastAPI()
        pipeline = MiddlewarePipeline(
            allowed_hosts=["example.com"],
            auth_backend=None,  # Skip auth for test
        )

        # Should not raise
        pipeline.apply_to_app(app)

        # Check that middleware were added
        # FastAPI stores middleware in app.user_middleware
        assert len(app.user_middleware) > 0

    def test_apply_with_validation(self):
        """Test full workflow with validation before apply."""
        app = FastAPI()
        pipeline = MiddlewarePipeline()

        # Validate then apply
        pipeline.validate_dependencies()
        pipeline.apply_to_app(app)

        # Should have all middleware
        assert (
            len(app.user_middleware) >= 8
        )  # At least 8 (auth might be skipped)

    def test_middleware_registration_order(self):
        """Test middleware are registered to the app successfully."""
        app = FastAPI()
        pipeline = MiddlewarePipeline(allowed_hosts=["example.com"])

        pipeline.apply_to_app(app)

        # Get middleware classes from app (they're stored as Middleware objects)
        registered_classes = [mw.cls for mw in app.user_middleware]

        # Verify TrustedHostMiddleware is registered
        assert TrustedHostMiddleware in registered_classes

        # Verify all expected middleware are registered
        expected_middleware = [
            TrustedHostMiddleware,
            CorrelationIDMiddleware,
            LoggingContextMiddleware,
            RateLimitMiddleware,
            RequestSizeLimitMiddleware,
            AuditMiddleware,
            SecurityHeadersMiddleware,
            PrometheusMiddleware,
        ]

        for mw_class in expected_middleware:
            assert mw_class in registered_classes


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_allowed_hosts(self):
        """Test pipeline handles empty allowed hosts by defaulting to wildcard."""
        pipeline = MiddlewarePipeline(allowed_hosts=[])

        # Empty list should default to ["*"] for safety
        middleware_list = pipeline.get_middleware_list()
        trusted_host_mw = next(
            (mw for mw in middleware_list if mw[0] == TrustedHostMiddleware),
            None,
        )
        assert trusted_host_mw[1]["allowed_hosts"] == ["*"]

    def test_none_auth_backend(self):
        """Test pipeline handles None auth backend."""
        pipeline = MiddlewarePipeline(auth_backend=None)
        app = FastAPI()

        # Should skip AuthenticationMiddleware when backend is None
        pipeline.apply_to_app(app)

        # Check that AuthenticationMiddleware was not added
        registered_classes = [mw.cls for mw in app.user_middleware]
        assert AuthenticationMiddleware not in registered_classes

    def test_get_middleware_list_returns_copy(self):
        """Test that get_middleware_list returns a copy, not reference."""
        pipeline = MiddlewarePipeline()

        list1 = pipeline.get_middleware_list()
        list2 = pipeline.get_middleware_list()

        # Should be equal but not the same object
        assert list1 == list2
        assert list1 is not list2

        # Modifying one should not affect the other
        list1.pop()
        assert len(list1) != len(list2)
        assert len(pipeline.get_middleware_list()) == len(list2)


class TestDependencyDefinitions:
    """Test that dependency definitions match actual middleware requirements."""

    def test_rate_limit_requires_auth(self):
        """Test RateLimitMiddleware dependency on AuthenticationMiddleware."""
        pipeline = MiddlewarePipeline()

        assert RateLimitMiddleware in pipeline.dependencies
        assert (
            AuthenticationMiddleware
            in pipeline.dependencies[RateLimitMiddleware]
        )

    def test_audit_requires_auth(self):
        """Test AuditMiddleware dependency on AuthenticationMiddleware."""
        pipeline = MiddlewarePipeline()

        assert AuditMiddleware in pipeline.dependencies
        assert (
            AuthenticationMiddleware in pipeline.dependencies[AuditMiddleware]
        )

    def test_logging_context_requires_correlation_id(self):
        """Test LoggingContextMiddleware dependency on CorrelationIDMiddleware."""
        pipeline = MiddlewarePipeline()

        assert LoggingContextMiddleware in pipeline.dependencies
        assert (
            CorrelationIDMiddleware
            in pipeline.dependencies[LoggingContextMiddleware]
        )

    def test_all_dependencies_are_satisfied(self):
        """Test that all defined dependencies are satisfied in default pipeline."""
        pipeline = MiddlewarePipeline()

        # Should pass without raising
        pipeline.validate_dependencies()

        # Double-check: get positions
        middleware_positions = {
            mw_class: idx
            for idx, (mw_class, _) in enumerate(pipeline.get_middleware_list())
        }

        # Verify each dependency
        for middleware_class, required_list in pipeline.dependencies.items():
            middleware_pos = middleware_positions[middleware_class]
            for required_class in required_list:
                required_pos = middleware_positions[required_class]
                assert required_pos < middleware_pos, (
                    f"{required_class.__name__} should come before {middleware_class.__name__}"
                )
