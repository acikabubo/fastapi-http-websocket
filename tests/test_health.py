"""Tests for the health check endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.http.health import router


@pytest.fixture
def app():
    """
    Create a minimal FastAPI app with only the health endpoint.

    Returns:
        FastAPI: FastAPI application instance.
    """
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app):
    """
    Create a test client for the FastAPI application.

    Args:
        app: FastAPI application fixture.

    Returns:
        TestClient: FastAPI test client instance.
    """
    return TestClient(app)


@pytest.mark.asyncio
async def test_health_endpoint_all_services_healthy(client):
    """
    Test health endpoint when all services are healthy.

    Args:
        client: FastAPI test client fixture.
    """
    # Mock successful database connection
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # Mock successful Redis connection
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    # Mock WebSocket health info
    mock_ws_health = {"status": "healthy", "active_connections": 5}

    with (
        patch("app.api.http.health.engine", mock_engine),
        patch(
            "app.api.http.health.get_redis_connection",
            return_value=mock_redis,
        ),
        patch(
            "app.api.http.health.get_websocket_health_info",
            return_value=mock_ws_health,
        ),
    ):
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"
    assert data["websocket"]["status"] == "healthy"
    assert data["websocket"]["active_connections"] == 5


@pytest.mark.asyncio
async def test_health_endpoint_database_unhealthy(client):
    """
    Test health endpoint when database is unhealthy.

    Args:
        client: FastAPI test client fixture.
    """
    # Mock failed database connection
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Database connection error")

    # Mock successful Redis connection
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True

    # Mock WebSocket health info
    mock_ws_health = {"status": "healthy", "active_connections": 3}

    with (
        patch("app.api.http.health.engine", mock_engine),
        patch(
            "app.api.http.health.get_redis_connection",
            return_value=mock_redis,
        ),
        patch(
            "app.api.http.health.get_websocket_health_info",
            return_value=mock_ws_health,
        ),
    ):
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "unhealthy"
    assert data["redis"] == "healthy"
    assert data["websocket"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_endpoint_redis_unhealthy(client):
    """
    Test health endpoint when Redis is unhealthy.

    Args:
        client: FastAPI test client fixture.
    """
    # Mock successful database connection
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    # Mock failed Redis connection
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = Exception("Redis connection error")

    # Mock WebSocket health info
    mock_ws_health = {"status": "healthy", "active_connections": 2}

    with (
        patch("app.api.http.health.engine", mock_engine),
        patch(
            "app.api.http.health.get_redis_connection",
            return_value=mock_redis,
        ),
        patch(
            "app.api.http.health.get_websocket_health_info",
            return_value=mock_ws_health,
        ),
    ):
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "healthy"
    assert data["redis"] == "unhealthy"
    assert data["websocket"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_endpoint_all_services_unhealthy(client):
    """
    Test health endpoint when all services are unhealthy.

    Args:
        client: FastAPI test client fixture.
    """
    # Mock failed database connection
    mock_engine = MagicMock()
    mock_engine.connect.side_effect = Exception("Database connection error")

    # Mock failed Redis connection
    mock_redis = AsyncMock()
    mock_redis.ping.side_effect = Exception("Redis connection error")

    # Mock WebSocket health info
    mock_ws_health = {"status": "healthy", "active_connections": 1}

    with (
        patch("app.api.http.health.engine", mock_engine),
        patch(
            "app.api.http.health.get_redis_connection",
            return_value=mock_redis,
        ),
        patch(
            "app.api.http.health.get_websocket_health_info",
            return_value=mock_ws_health,
        ),
    ):
        response = client.get("/health")

    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"] == "unhealthy"
    assert data["redis"] == "unhealthy"
    assert data["websocket"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_endpoint_no_authentication_required(client):
    """
    Test that health endpoint does not require authentication.

    Args:
        client: FastAPI test client fixture.
    """
    # Mock services to be healthy
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    mock_redis = AsyncMock()
    mock_redis.ping.return_value = True
    mock_ws_health = {"status": "healthy", "active_connections": 0}

    with (
        patch("app.api.http.health.engine", mock_engine),
        patch(
            "app.api.http.health.get_redis_connection",
            return_value=mock_redis,
        ),
        patch(
            "app.api.http.health.get_websocket_health_info",
            return_value=mock_ws_health,
        ),
    ):
        # Request without authentication headers
        response = client.get("/health")

    # Should succeed without authentication
    assert response.status_code == 200
