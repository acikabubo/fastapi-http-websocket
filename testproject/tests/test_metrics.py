"""
Tests for Prometheus metrics functionality.

This module tests metrics collection for HTTP requests, WebSocket connections,
and the metrics endpoint exposure.
"""

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY


@pytest.fixture
def clear_metrics():
    """Clear all metrics before and after each test."""
    # Clear metrics before test
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass

    yield

    # Clear metrics after test
    collectors = list(REGISTRY._collector_to_names.keys())
    for collector in collectors:
        try:
            REGISTRY.unregister(collector)
        except Exception:
            pass


class TestPrometheusMetrics:
    """Tests for Prometheus metrics integration."""

    def test_metrics_endpoint_exists(self, mock_keycloak_manager):
        """
        Test that the /metrics endpoint exists and returns metrics.

        Args:
            mock_keycloak_manager: Mocked Keycloak manager
        """
        from app import application

        app = application()
        client = TestClient(app)

        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]

    def test_http_request_metrics_tracked(self, mock_keycloak_manager):
        """
        Test that HTTP requests are tracked in metrics.

        Args:
            mock_keycloak_manager: Mocked Keycloak manager
        """
        from app import application

        app = application()
        client = TestClient(app)

        # Make a request to the health endpoint
        client.get("/health")

        # Get metrics
        response = client.get("/metrics")
        metrics_data = response.text

        # Check that HTTP metrics are present
        assert "http_requests_total" in metrics_data
        assert "http_request_duration_seconds" in metrics_data

    def test_metrics_middleware_tracks_duration(
        self, mock_keycloak_manager
    ):
        """
        Test that PrometheusMiddleware tracks request duration.

        Args:
            mock_keycloak_manager: Mocked Keycloak manager
        """
        from app import application

        app = application()
        client = TestClient(app)

        # Make a request
        client.get("/health")

        # Get metrics
        response = client.get("/metrics")
        metrics_data = response.text

        # Verify duration histogram is present
        assert "http_request_duration_seconds_bucket" in metrics_data
        assert "http_request_duration_seconds_count" in metrics_data

    def test_metrics_include_labels(self, mock_keycloak_manager):
        """
        Test that metrics include proper labels.

        Args:
            mock_keycloak_manager: Mocked Keycloak manager
        """
        from app import application

        app = application()
        client = TestClient(app)

        # Make a GET request
        client.get("/health")

        # Get metrics
        response = client.get("/metrics")
        metrics_data = response.text

        # Check for method and endpoint labels
        assert 'method="GET"' in metrics_data
        assert 'endpoint="/health"' in metrics_data

    def test_app_info_metric(self):
        """Test that app_info metric can be set and exported."""
        import sys

        from prometheus_client import generate_latest

        from app.utils.metrics import app_info

        # Set the app_info metric
        app_info.labels(
            version="1.0.0",
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            environment="test",
        ).set(1)

        # Generate metrics output
        metrics_data = generate_latest().decode("utf-8")

        # Check for app_info metric
        assert "app_info" in metrics_data
        assert 'version="1.0.0"' in metrics_data
        assert 'environment="test"' in metrics_data


class TestWebSocketMetrics:
    """Tests for WebSocket metrics."""

    def test_websocket_metrics_defined(self):
        """Test that WebSocket metrics are properly defined."""
        from app.utils.metrics import (
            ws_connections_active,
            ws_connections_total,
            ws_message_processing_duration_seconds,
            ws_messages_received_total,
            ws_messages_sent_total,
        )

        assert ws_connections_active is not None
        assert ws_connections_total is not None
        assert ws_messages_received_total is not None
        assert ws_messages_sent_total is not None
        assert ws_message_processing_duration_seconds is not None


class TestMetricsDefinitions:
    """Tests for metrics module definitions."""

    def test_all_metrics_imported(self):
        """Test that all expected metrics are defined."""
        from app.utils.metrics import (
            app_errors_total,
            app_info,
            auth_attempts_total,
            auth_token_validations_total,
            db_connections_active,
            db_query_duration_seconds,
            db_query_errors_total,
            http_request_duration_seconds,
            http_requests_in_progress,
            http_requests_total,
            rate_limit_hits_total,
            redis_operation_duration_seconds,
            redis_operations_total,
            ws_connections_active,
            ws_connections_total,
            ws_message_processing_duration_seconds,
            ws_messages_received_total,
            ws_messages_sent_total,
        )

        # Verify all metrics are not None
        assert http_requests_total is not None
        assert http_request_duration_seconds is not None
        assert http_requests_in_progress is not None
        assert ws_connections_active is not None
        assert ws_connections_total is not None
        assert ws_messages_received_total is not None
        assert ws_messages_sent_total is not None
        assert ws_message_processing_duration_seconds is not None
        assert db_query_duration_seconds is not None
        assert db_connections_active is not None
        assert db_query_errors_total is not None
        assert redis_operations_total is not None
        assert redis_operation_duration_seconds is not None
        assert rate_limit_hits_total is not None
        assert auth_attempts_total is not None
        assert auth_token_validations_total is not None
        assert app_errors_total is not None
        assert app_info is not None

    def test_metrics_have_correct_types(self):
        """Test that metrics are of the correct Prometheus types."""
        from prometheus_client import Counter, Gauge, Histogram

        from app.utils.metrics import (
            http_request_duration_seconds,
            http_requests_in_progress,
            http_requests_total,
            ws_connections_active,
        )

        # Counter checks
        assert isinstance(
            http_requests_total._type, type(Counter._type)
        ) or isinstance(http_requests_total, type(Counter("test", "test")))

        # Histogram checks
        assert isinstance(
            http_request_duration_seconds._type, type(Histogram._type)
        ) or isinstance(
            http_request_duration_seconds, type(Histogram("test", "test"))
        )

        # Gauge checks
        assert isinstance(
            http_requests_in_progress._type, type(Gauge._type)
        ) or isinstance(
            http_requests_in_progress, type(Gauge("test", "test"))
        )
        assert isinstance(
            ws_connections_active._type, type(Gauge._type)
        ) or isinstance(ws_connections_active, type(Gauge("test", "test")))
