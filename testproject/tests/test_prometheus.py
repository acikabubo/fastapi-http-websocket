"""
Tests for Prometheus metrics middleware.

This module tests the PrometheusMiddleware functionality including
metric tracking for HTTP requests.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import Response

from app.middlewares.prometheus import PrometheusMiddleware


@pytest.fixture
def app():
    """
    Provides a FastAPI app instance.

    Returns:
        FastAPI: Test app
    """
    return FastAPI()


class TestPrometheusMiddleware:
    """Tests for PrometheusMiddleware class."""

    @pytest.mark.asyncio
    async def test_middleware_tracks_successful_request(self, app):
        """Test that middleware tracks metrics for successful requests."""
        middleware = PrometheusMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "GET"

        call_next = AsyncMock(return_value=Response(status_code=200))

        with (
            patch(
                "app.middlewares.prometheus.http_requests_total"
            ) as mock_total,
            patch(
                "app.middlewares.prometheus.http_request_duration_seconds"
            ) as mock_duration,
            patch(
                "app.middlewares.prometheus.http_requests_in_progress"
            ) as mock_in_progress,
        ):
            # Setup label chain
            mock_total_labels = MagicMock()
            mock_total.labels.return_value = mock_total_labels

            mock_duration_labels = MagicMock()
            mock_duration.labels.return_value = mock_duration_labels

            mock_in_progress_labels = MagicMock()
            mock_in_progress.labels.return_value = mock_in_progress_labels

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            # Check that in_progress was incremented and decremented
            mock_in_progress.labels.assert_called_with(
                method="GET", endpoint="/api/authors"
            )
            assert mock_in_progress_labels.inc.call_count == 1
            assert mock_in_progress_labels.dec.call_count == 1

            # Check that duration was recorded
            mock_duration.labels.assert_called_with(
                method="GET", endpoint="/api/authors"
            )
            mock_duration_labels.observe.assert_called_once()
            duration = mock_duration_labels.observe.call_args[0][0]
            assert duration >= 0

            # Check that request was counted
            mock_total.labels.assert_called_with(
                method="GET", endpoint="/api/authors", status_code=200
            )
            mock_total_labels.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_tracks_error_response(self, app):
        """Test that middleware tracks metrics for error responses."""
        middleware = PrometheusMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "POST"

        call_next = AsyncMock(return_value=Response(status_code=500))

        with (
            patch(
                "app.middlewares.prometheus.http_requests_total"
            ) as mock_total,
            patch(
                "app.middlewares.prometheus.http_request_duration_seconds"
            ) as mock_duration,
            patch(
                "app.middlewares.prometheus.http_requests_in_progress"
            ) as mock_in_progress,
        ):
            mock_total_labels = MagicMock()
            mock_total.labels.return_value = mock_total_labels

            mock_duration_labels = MagicMock()
            mock_duration.labels.return_value = mock_duration_labels

            mock_in_progress_labels = MagicMock()
            mock_in_progress.labels.return_value = mock_in_progress_labels

            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 500

            # Check that 500 error was tracked
            mock_total.labels.assert_called_with(
                method="POST", endpoint="/api/authors", status_code=500
            )
            mock_total_labels.inc.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_tracks_exception(self, app):
        """Test that middleware tracks metrics when exception is raised."""
        middleware = PrometheusMiddleware(app)

        request = MagicMock(spec=Request)
        request.url.path = "/api/crash"
        request.method = "DELETE"

        test_exception = ValueError("Test error")
        call_next = AsyncMock(side_effect=test_exception)

        with (
            patch(
                "app.middlewares.prometheus.http_requests_total"
            ) as mock_total,
            patch(
                "app.middlewares.prometheus.http_request_duration_seconds"
            ) as mock_duration,
            patch(
                "app.middlewares.prometheus.http_requests_in_progress"
            ) as mock_in_progress,
        ):
            mock_total_labels = MagicMock()
            mock_total.labels.return_value = mock_total_labels

            mock_duration_labels = MagicMock()
            mock_duration.labels.return_value = mock_duration_labels

            mock_in_progress_labels = MagicMock()
            mock_in_progress.labels.return_value = mock_in_progress_labels

            # Should re-raise the exception
            with pytest.raises(ValueError, match="Test error"):
                await middleware.dispatch(request, call_next)

            # Check that duration was still recorded
            mock_duration.labels.assert_called_with(
                method="DELETE", endpoint="/api/crash"
            )
            mock_duration_labels.observe.assert_called_once()

            # Check that exception was tracked as 500 error
            mock_total.labels.assert_called_with(
                method="DELETE", endpoint="/api/crash", status_code=500
            )
            mock_total_labels.inc.assert_called_once()

            # Check that in_progress was decremented (in finally block)
            assert mock_in_progress_labels.dec.call_count == 1

    @pytest.mark.asyncio
    async def test_middleware_different_http_methods(self, app):
        """Test that middleware tracks different HTTP methods correctly."""
        middleware = PrometheusMiddleware(app)

        methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]

        for method in methods:
            request = MagicMock(spec=Request)
            request.url.path = "/api/test"
            request.method = method

            call_next = AsyncMock(return_value=Response(status_code=200))

            with (
                patch(
                    "app.middlewares.prometheus.http_requests_total"
                ) as mock_total,
                patch(
                    "app.middlewares.prometheus.http_request_duration_seconds"
                ) as mock_duration,
                patch(
                    "app.middlewares.prometheus.http_requests_in_progress"
                ) as mock_in_progress,
            ):
                mock_total_labels = MagicMock()
                mock_total.labels.return_value = mock_total_labels

                mock_duration_labels = MagicMock()
                mock_duration.labels.return_value = mock_duration_labels

                mock_in_progress_labels = MagicMock()
                mock_in_progress.labels.return_value = mock_in_progress_labels

                response = await middleware.dispatch(request, call_next)

                assert response.status_code == 200

                # Verify method was tracked correctly
                mock_in_progress.labels.assert_called_with(
                    method=method, endpoint="/api/test"
                )
                mock_duration.labels.assert_called_with(
                    method=method, endpoint="/api/test"
                )
                mock_total.labels.assert_called_with(
                    method=method, endpoint="/api/test", status_code=200
                )

    @pytest.mark.asyncio
    async def test_middleware_different_endpoints(self, app):
        """Test that middleware tracks different endpoints correctly."""
        middleware = PrometheusMiddleware(app)

        endpoints = ["/api/authors", "/api/books", "/health", "/metrics"]

        for endpoint in endpoints:
            request = MagicMock(spec=Request)
            request.url.path = endpoint
            request.method = "GET"

            call_next = AsyncMock(return_value=Response(status_code=200))

            with (
                patch(
                    "app.middlewares.prometheus.http_requests_total"
                ) as mock_total,
                patch(
                    "app.middlewares.prometheus.http_request_duration_seconds"
                ) as mock_duration,
                patch(
                    "app.middlewares.prometheus.http_requests_in_progress"
                ) as mock_in_progress,
            ):
                mock_total_labels = MagicMock()
                mock_total.labels.return_value = mock_total_labels

                mock_duration_labels = MagicMock()
                mock_duration.labels.return_value = mock_duration_labels

                mock_in_progress_labels = MagicMock()
                mock_in_progress.labels.return_value = mock_in_progress_labels

                response = await middleware.dispatch(request, call_next)

                assert response.status_code == 200

                # Verify endpoint was tracked correctly
                mock_in_progress.labels.assert_called_with(
                    method="GET", endpoint=endpoint
                )
                mock_duration.labels.assert_called_with(
                    method="GET", endpoint=endpoint
                )
                mock_total.labels.assert_called_with(
                    method="GET", endpoint=endpoint, status_code=200
                )
