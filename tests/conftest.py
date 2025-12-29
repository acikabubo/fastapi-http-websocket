"""
Pytest configuration and fixtures for testing.

This module provides shared fixtures for authentication, database,
and other common testing utilities.
"""

import os
from unittest.mock import Mock, patch

import pytest

# Set required environment variables for testing before importing app modules
os.environ.setdefault("KEYCLOAK_REALM", "test-realm")
os.environ.setdefault("KEYCLOAK_CLIENT_ID", "test-client")
os.environ.setdefault("KEYCLOAK_BASE_URL", "http://localhost:8080/")
os.environ.setdefault("KEYCLOAK_ADMIN_USERNAME", "admin")
os.environ.setdefault("KEYCLOAK_ADMIN_PASSWORD", "admin")

# Database credentials (required after removing hardcoded defaults)
os.environ.setdefault("DB_USER", "test-user")
os.environ.setdefault("DB_PASSWORD", "test-password")


@pytest.fixture
def mock_keycloak_token():
    """
    Provides a mock Keycloak token response.

    Returns:
        dict: Mock token response with access_token, refresh_token, etc.
    """
    return {
        "access_token": "mock_access_token_12345",
        "expires_in": 300,
        "refresh_expires_in": 1800,
        "refresh_token": "mock_refresh_token_67890",
        "token_type": "Bearer",
        "not-before-policy": 0,
        "session_state": "mock-session-state",
        "scope": "openid email profile",
    }


@pytest.fixture
def mock_user_data():
    """
    Provides mock decoded user data from Keycloak token.

    Returns:
        dict: Mock user data with roles and claims
    """
    return {
        "sub": "f86caf01-69b4-4892-ba2d-ffa58fdd5dab",
        "preferred_username": "testuser",
        "given_name": "Test",
        "family_name": "User",
        "email": "testuser@example.com",
        "exp": 9999999999,
        "azp": "test-client",
        "realm_access": {
            "roles": [
                "offline_access",
                "admin",
                "get-authors",
                "uma_authorization",
            ]
        },
        "resource_access": {
            "test-client": {
                "roles": [
                    "admin",
                    "get-authors",
                ]
            }
        },
    }


@pytest.fixture
def mock_user(mock_user_data):
    """
    Provides a UserModel instance for testing.

    Args:
        mock_user_data: Fixture providing mock user data

    Returns:
        UserModel: Mock user instance
    """
    from app.schemas.user import UserModel

    return UserModel(**mock_user_data)


@pytest.fixture
def mock_keycloak_manager(mock_keycloak_token, mock_user_data):
    """
    Mocks KeycloakManager for testing without real Keycloak connection.

    Args:
        mock_keycloak_token: Fixture providing mock token
        mock_user_data: Fixture providing mock user data

    Yields:
        Mock: Mocked KeycloakManager instance
    """
    with patch(
        "app.managers.keycloak_manager.KeycloakManager"
    ) as mock_kc_manager:
        mock_instance = Mock()
        mock_instance.login.return_value = mock_keycloak_token
        mock_instance.openid.decode_token.return_value = mock_user_data

        mock_kc_manager.return_value = mock_instance

        yield mock_instance


@pytest.fixture
def auth_headers(mock_keycloak_token):
    """
    Provides HTTP headers with authentication token.

    Args:
        mock_keycloak_token: Fixture providing mock token

    Returns:
        dict: Headers dictionary with Authorization header
    """
    return {"Authorization": f"Bearer {mock_keycloak_token['access_token']}"}


@pytest.fixture
def admin_user_data():
    """
    Provides mock admin user data with elevated privileges.

    Returns:
        dict: Mock admin user data
    """
    return {
        "sub": "admin-user-id",
        "preferred_username": "admin",
        "given_name": "Admin",
        "family_name": "User",
        "email": "admin@example.com",
        "exp": 9999999999,
        "azp": "test-client",
        "realm_access": {
            "roles": [
                "offline_access",
                "admin",
                "get-authors",
                "uma_authorization",
                "default-roles-app",
            ]
        },
        "resource_access": {
            "test-client": {
                "roles": [
                    "admin",
                    "get-authors",
                ]
            }
        },
    }


@pytest.fixture
def limited_user_data():
    """
    Provides mock user data with limited privileges.

    Returns:
        dict: Mock limited user data
    """
    return {
        "sub": "limited-user-id",
        "preferred_username": "limiteduser",
        "given_name": "Limited",
        "family_name": "User",
        "email": "limited@example.com",
        "exp": 9999999999,
        "azp": "test-client",
        "realm_access": {"roles": ["offline_access"]},
        "resource_access": {"test-client": {"roles": []}},
    }


@pytest.fixture
def mock_db_session():
    """
    Provides a mock database session for testing.

    Returns:
        Mock: Mock AsyncSession instance
    """
    from unittest.mock import AsyncMock

    return AsyncMock()


@pytest.fixture
def mock_redis():
    """
    Provides a mock Redis connection for testing.

    Returns:
        AsyncMock: Mocked Redis connection with common methods
    """
    from unittest.mock import AsyncMock

    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.delete = AsyncMock(return_value=True)
    redis_mock.incr = AsyncMock(return_value=1)
    redis_mock.expire = AsyncMock(return_value=True)
    redis_mock.setex = AsyncMock(return_value=True)
    redis_mock.sismember = AsyncMock(return_value=False)
    redis_mock.sadd = AsyncMock(return_value=1)
    redis_mock.srem = AsyncMock(return_value=1)
    redis_mock.scard = AsyncMock(return_value=0)
    return redis_mock


@pytest.fixture
def mock_websocket():
    """
    Provides a mock WebSocket connection for testing.

    Returns:
        Mock: Mocked WebSocket instance
    """
    from unittest.mock import AsyncMock, MagicMock

    ws_mock = MagicMock()
    ws_mock.send_json = AsyncMock()
    ws_mock.send_text = AsyncMock()
    ws_mock.send_bytes = AsyncMock()
    ws_mock.receive_json = AsyncMock()
    ws_mock.receive_text = AsyncMock()
    ws_mock.accept = AsyncMock()
    ws_mock.close = AsyncMock()
    return ws_mock


@pytest.fixture
def mock_request():
    """
    Provides a mock HTTP request for testing.

    Returns:
        Mock: Mocked Request instance
    """
    from unittest.mock import MagicMock

    request_mock = MagicMock()
    request_mock.url.path = "/test"
    request_mock.method = "GET"
    request_mock.headers = {}
    request_mock.state = MagicMock()
    request_mock.state.user = None
    return request_mock


@pytest.fixture
def mock_call_next():
    """
    Provides a mock call_next function for middleware testing.

    Returns:
        AsyncMock: Mocked call_next function
    """
    from unittest.mock import AsyncMock
    from starlette.responses import Response

    async def call_next_impl(request):
        return Response(status_code=200)

    return AsyncMock(side_effect=call_next_impl)


# Fixture Factories
def create_author_fixture(
    id: int = 1, name: str = "Test Author", bio: str = "Test bio"
):
    """
    Factory function to create Author instances for testing.

    Args:
        id: Author ID
        name: Author name
        bio: Author biography

    Returns:
        Author: Author instance
    """
    from app.models.author import Author

    return Author(id=id, name=name, bio=bio)


def create_request_model_fixture(
    pkg_id: int = 1,
    req_id: str = "test-req-id",
    data: dict | None = None,
):
    """
    Factory function to create RequestModel instances for testing.

    Args:
        pkg_id: Package ID
        req_id: Request ID
        data: Request data

    Returns:
        RequestModel: Request model instance
    """
    from app.schemas.request import RequestModel

    return RequestModel(pkg_id=pkg_id, req_id=req_id, data=data or {})


def create_response_model_fixture(
    pkg_id: int = 1,
    req_id: str = "test-req-id",
    status_code: int = 0,
    data: dict | None = None,
):
    """
    Factory function to create ResponseModel instances for testing.

    Args:
        pkg_id: Package ID
        req_id: Request ID
        status_code: Response status code
        data: Response data

    Returns:
        ResponseModel: Response model instance
    """
    from app.schemas.response import ResponseModel

    return ResponseModel(
        pkg_id=pkg_id, req_id=req_id, status_code=status_code, data=data or {}
    )
