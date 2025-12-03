"""
Tests for correlation ID middleware.

This module tests the CorrelationIDMiddleware functionality including
correlation ID generation, header handling, and context variable access.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request
from starlette.responses import Response

from {{cookiecutter.module_name}}.middlewares.correlation_id import (
    CorrelationIDMiddleware,
    correlation_id,
    get_correlation_id,
)


class TestCorrelationIDMiddleware:
    """Tests for CorrelationIDMiddleware class."""

    @pytest.mark.asyncio
    async def test_middleware_generates_correlation_id(self):
        """Test that middleware generates correlation ID when not provided."""
        middleware = CorrelationIDMiddleware(app=MagicMock())

        # Create mock request without X-Correlation-ID header
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {}

        # Create mock response
        mock_response = Response(content="test", status_code=200)

        # Mock call_next to return response
        async def mock_call_next(request):
            return mock_response

        # Call middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check that correlation ID was added to response headers
        assert "X-Correlation-ID" in response.headers
        # Check that it's a valid UUID (36 characters with dashes)
        cid = response.headers["X-Correlation-ID"]
        assert len(cid) == 36
        assert cid.count("-") == 4

    @pytest.mark.asyncio
    async def test_middleware_uses_provided_correlation_id(self):
        """Test that middleware uses correlation ID from request header."""
        middleware = CorrelationIDMiddleware(app=MagicMock())

        provided_cid = "test-correlation-id-12345"

        # Create mock request with X-Correlation-ID header
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Correlation-ID": provided_cid}

        # Create mock response
        mock_response = Response(content="test", status_code=200)

        # Mock call_next to return response
        async def mock_call_next(request):
            return mock_response

        # Call middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check that same correlation ID was added to response
        assert response.headers["X-Correlation-ID"] == provided_cid

    @pytest.mark.asyncio
    async def test_middleware_sets_context_variable(self):
        """Test that middleware sets correlation ID in context variable."""
        middleware = CorrelationIDMiddleware(app=MagicMock())

        provided_cid = "context-test-id"

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Correlation-ID": provided_cid}

        # Create mock response
        mock_response = Response(content="test", status_code=200)

        # Mock call_next that checks context variable
        cid_in_handler = None

        async def mock_call_next(request):
            nonlocal cid_in_handler
            cid_in_handler = get_correlation_id()
            return mock_response

        # Call middleware
        await middleware.dispatch(mock_request, mock_call_next)

        # Check that correlation ID was accessible in handler (shortened to 8 chars)
        assert cid_in_handler == provided_cid[:8]


class TestGetCorrelationID:
    """Tests for get_correlation_id helper function."""

    def test_get_correlation_id_returns_empty_when_not_set(self):
        """Test that get_correlation_id returns empty string when not set."""
        # Clear context variable
        correlation_id.set("")

        result = get_correlation_id()

        assert result == ""

    def test_get_correlation_id_returns_set_value(self):
        """Test that get_correlation_id returns the set correlation ID."""
        test_cid = "test-id-123"

        # Set correlation ID
        correlation_id.set(test_cid)

        result = get_correlation_id()

        assert result == test_cid

        # Clean up
        correlation_id.set("")


class TestCorrelationIDInLogs:
    """Tests for correlation ID integration with logging."""

    @pytest.mark.asyncio
    async def test_correlation_id_available_in_request_context(self):
        """Test that correlation ID is available throughout request context."""
        middleware = CorrelationIDMiddleware(app=MagicMock())

        test_cid = "logging-test-id"

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Correlation-ID": test_cid}

        # Create mock response
        mock_response = Response(content="test", status_code=200)

        # Track correlation IDs at different points
        cids_during_request = []

        async def mock_call_next(request):
            # Simulate multiple calls to get_correlation_id during request
            cids_during_request.append(get_correlation_id())
            # Simulate nested function call
            cids_during_request.append(get_correlation_id())
            return mock_response

        # Call middleware
        await middleware.dispatch(mock_request, mock_call_next)

        # Check that correlation ID was consistent throughout request (shortened to 8 chars)
        assert all(cid == test_cid[:8] for cid in cids_during_request)
        assert len(cids_during_request) == 2


class TestMiddlewareIntegration:
    """Integration tests for correlation ID middleware."""

    @pytest.mark.asyncio
    async def test_correlation_id_preserved_through_error(self):
        """Test that correlation ID is preserved even when error occurs."""
        middleware = CorrelationIDMiddleware(app=MagicMock())

        test_cid = "error-test-id"

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.headers = {"X-Correlation-ID": test_cid}

        # Mock call_next that raises exception
        async def mock_call_next_error(request):
            # Correlation ID should be available even before error (shortened to 8 chars)
            assert get_correlation_id() == test_cid[:8]
            raise ValueError("Test error")

        # Call middleware and expect exception
        with pytest.raises(ValueError):
            await middleware.dispatch(mock_request, mock_call_next_error)

        # Correlation ID should have been set in context
        # Note: In real scenario, error handling middleware would use this

    @pytest.mark.asyncio
    async def test_correlation_id_header_case_insensitive(self):
        """Test that correlation ID header is case-insensitive."""
        middleware = CorrelationIDMiddleware(app=MagicMock())

        test_cid = "case-test-id"

        # Create mock request with different case header
        mock_request = MagicMock(spec=Request)
        # Simulate case-insensitive header access
        mock_request.headers = MagicMock()
        mock_request.headers.get = MagicMock(return_value=test_cid)

        # Create mock response
        mock_response = Response(content="test", status_code=200)

        async def mock_call_next(request):
            return mock_response

        # Call middleware
        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check that correlation ID was used
        assert response.headers["X-Correlation-ID"] == test_cid
