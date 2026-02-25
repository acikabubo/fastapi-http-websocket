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

from app.middlewares.pipeline import PrometheusMiddleware


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
        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "GET"

        call_next = AsyncMock(return_value=Response(status_code=200))

        with (
            patch(
                "app.middlewares.pipeline.MetricsCollector.record_http_request_start"
            ) as mock_start,
            patch(
                "app.middlewares.pipeline.MetricsCollector.record_http_request_end"
            ) as mock_end,
        ):
            middleware = PrometheusMiddleware(app)
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 200

            # Check that start and end were called
            mock_start.assert_called_once_with("GET", "/api/authors")
            mock_end.assert_called_once()
            # Verify the end call has correct method, path, and status code
            call_args = mock_end.call_args[0]
            assert call_args[0] == "GET"
            assert call_args[1] == "/api/authors"
            assert call_args[2] == 200
            # Verify duration is >= 0
            duration = call_args[3]
            assert duration >= 0

    @pytest.mark.asyncio
    async def test_middleware_tracks_error_response(self, app):
        """Test that middleware tracks metrics for error responses."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/authors"
        request.method = "POST"

        call_next = AsyncMock(return_value=Response(status_code=500))

        with (
            patch(
                "app.middlewares.pipeline.MetricsCollector.record_http_request_start"
            ) as mock_start,
            patch(
                "app.middlewares.pipeline.MetricsCollector.record_http_request_end"
            ) as mock_end,
        ):
            middleware = PrometheusMiddleware(app)
            response = await middleware.dispatch(request, call_next)

            assert response.status_code == 500

            # Check that start and end were called with 500 status
            mock_start.assert_called_once_with("POST", "/api/authors")
            mock_end.assert_called_once()
            call_args = mock_end.call_args[0]
            assert call_args[0] == "POST"
            assert call_args[1] == "/api/authors"
            assert call_args[2] == 500

    @pytest.mark.asyncio
    async def test_middleware_tracks_exception(self, app):
        """Test that middleware tracks metrics when exception is raised."""
        request = MagicMock(spec=Request)
        request.url.path = "/api/crash"
        request.method = "DELETE"

        test_exception = ValueError("Test error")
        call_next = AsyncMock(side_effect=test_exception)

        with (
            patch(
                "app.middlewares.pipeline.MetricsCollector.record_http_request_start"
            ) as mock_start,
            patch(
                "app.middlewares.pipeline.MetricsCollector.record_http_request_end"
            ) as mock_end,
        ):
            middleware = PrometheusMiddleware(app)

            # Should re-raise the exception
            with pytest.raises(ValueError, match="Test error"):
                await middleware.dispatch(request, call_next)

            # Check that start was called
            mock_start.assert_called_once_with("DELETE", "/api/crash")

            # Check that exception was tracked as 500 error
            mock_end.assert_called_once()
            call_args = mock_end.call_args[0]
            assert call_args[0] == "DELETE"
            assert call_args[1] == "/api/crash"
            assert call_args[2] == 500

    @pytest.mark.asyncio
    async def test_middleware_different_http_methods(self, app):
        """Test that middleware tracks different HTTP methods correctly."""
        methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]

        for method in methods:
            request = MagicMock(spec=Request)
            request.url.path = "/api/test"
            request.method = method

            call_next = AsyncMock(return_value=Response(status_code=200))

            with (
                patch(
                    "app.middlewares.pipeline.MetricsCollector.record_http_request_start"
                ) as mock_start,
                patch(
                    "app.middlewares.pipeline.MetricsCollector.record_http_request_end"
                ) as mock_end,
            ):
                middleware = PrometheusMiddleware(app)
                response = await middleware.dispatch(request, call_next)

                assert response.status_code == 200

                # Verify method was tracked correctly
                mock_start.assert_called_with(method, "/api/test")
                mock_end.assert_called_once()
                call_args = mock_end.call_args[0]
                assert call_args[0] == method
                assert call_args[1] == "/api/test"
                assert call_args[2] == 200

    @pytest.mark.asyncio
    async def test_middleware_different_endpoints(self, app):
        """Test that middleware tracks different endpoints correctly."""
        endpoints = ["/api/authors", "/api/books", "/health", "/metrics"]

        for endpoint in endpoints:
            request = MagicMock(spec=Request)
            request.url.path = endpoint
            request.method = "GET"

            call_next = AsyncMock(return_value=Response(status_code=200))

            with (
                patch(
                    "app.middlewares.pipeline.MetricsCollector.record_http_request_start"
                ) as mock_start,
                patch(
                    "app.middlewares.pipeline.MetricsCollector.record_http_request_end"
                ) as mock_end,
            ):
                middleware = PrometheusMiddleware(app)
                response = await middleware.dispatch(request, call_next)

                assert response.status_code == 200

                # Verify endpoint was tracked correctly
                mock_start.assert_called_with("GET", endpoint)
                mock_end.assert_called_once()
                call_args = mock_end.call_args[0]
                assert call_args[0] == "GET"
                assert call_args[1] == endpoint
                assert call_args[2] == 200
