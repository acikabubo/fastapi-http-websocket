"""
Pytest configuration and fixtures for testing.

This module provides shared fixtures for authentication, database,
and other common testing utilities.
"""

import os
from unittest.mock import AsyncMock, MagicMock, Mock, patch

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

# Import app modules after setting environment variables
from keycloak import KeycloakAdmin
from starlette.responses import Response
from testcontainers.keycloak import KeycloakContainer

from {{cookiecutter.module_name}}.managers.keycloak_manager import KeycloakManager
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.schemas.response import ResponseModel
from {{cookiecutter.module_name}}.schemas.user import UserModel

# Load WebSocket handlers to register them with the router
from {{cookiecutter.module_name}}.api.ws.handlers import load_handlers

load_handlers()  # type: ignore[no-untyped-call]


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
        "{{cookiecutter.module_name}}.managers.keycloak_manager.KeycloakManager"
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
    return AsyncMock()


@pytest.fixture
def mock_redis():
    """
    Provides a mock Redis connection for testing.

    Returns:
        AsyncMock: Mocked Redis connection with common methods
    """
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

    async def call_next_impl(request):
        return Response(status_code=200)

    return AsyncMock(side_effect=call_next_impl)


# Fixture Factories


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
    return ResponseModel(
        pkg_id=pkg_id, req_id=req_id, status_code=status_code, data=data or {}
    )


# Integration Testing Fixtures (Testcontainers)


@pytest.fixture(scope="session")
def keycloak_container():
    """
    Provides a real Keycloak container for integration testing.

    This fixture starts a Keycloak container using testcontainers and
    configures it with a test realm, client, and users. The container
    is session-scoped to avoid overhead of starting/stopping for each test.

    Yields:
        dict: Keycloak connection details with keys:
            - base_url: Keycloak base URL
            - realm: Realm name
            - client_id: Client ID
            - admin_username: Admin username
            - admin_password: Admin password
            - test_username: Test user username
            - test_password: Test user password
            - admin_user_username: Admin user username
            - admin_user_password: Admin user password

    Example:
        @pytest.mark.integration
        async def test_real_auth(keycloak_container):
            # Use real Keycloak for authentication
            base_url = keycloak_container["base_url"]
            ...
    """
    # Start Keycloak container with test realm
    # Using official Docker Hub image (faster and more reliable than quay.io)
    container = KeycloakContainer("keycloak/keycloak:26.0.0")
    container.start()

    try:
        # Get connection details
        base_url = container.get_url()
        admin_username = container.username
        admin_password = container.password

        # Configure test realm

        admin_client = KeycloakAdmin(
            server_url=base_url,
            username=admin_username,
            password=admin_password,
            realm_name="master",
            user_realm_name="master",
            verify=True,
        )

        # Create test realm
        test_realm = "test-realm"
        admin_client.create_realm(
            payload={
                "realm": test_realm,
                "enabled": True,
                "sslRequired": "none",
                "registrationAllowed": False,
                "loginWithEmailAllowed": True,
                "duplicateEmailsAllowed": False,
                "resetPasswordAllowed": True,
                "editUsernameAllowed": False,
                "bruteForceProtected": True,
            },
            skip_exists=True,
        )

        # Switch to test realm
        admin_client.connection.realm_name = test_realm

        # Create test client
        test_client_id = "test-client"
        client_id = admin_client.create_client(
            payload={
                "clientId": test_client_id,
                "enabled": True,
                "publicClient": True,
                "directAccessGrantsEnabled": True,
                "standardFlowEnabled": True,
                "implicitFlowEnabled": False,
                "serviceAccountsEnabled": False,
                "redirectUris": ["*"],
                "webOrigins": ["*"],
            },
            skip_exists=True,
        )

        # Create client roles (not realm roles)
        # UserModel extracts roles from resource_access[client_id]["roles"]
        test_roles = [
            "get-authors",
            "create-author",
            "update-author",
            "delete-author",
            "admin",
        ]
        for role_name in test_roles:
            admin_client.create_client_role(
                client_role_id=client_id,
                payload={
                    "name": role_name,
                    "description": f"Test role: {role_name}",
                },
                skip_exists=True,
            )

        # Create test user with limited permissions
        test_username = "testuser"
        test_password = "testpass123"
        test_user_id = admin_client.create_user(
            payload={
                "username": test_username,
                "email": "testuser@example.com",
                "firstName": "Test",
                "lastName": "User",
                "enabled": True,
                "emailVerified": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": test_password,
                        "temporary": False,
                    }
                ],
            },
            exist_ok=True,
        )

        # Assign client roles to test user
        test_user_roles = ["get-authors"]
        for role_name in test_user_roles:
            role = admin_client.get_client_role(
                client_id=client_id, role_name=role_name
            )
            admin_client.assign_client_role(
                client_id=client_id, user_id=test_user_id, roles=[role]
            )

        # Create admin user with full permissions
        admin_user_username = "adminuser"
        admin_user_password = "adminpass123"
        admin_user_id = admin_client.create_user(
            payload={
                "username": admin_user_username,
                "email": "admin@example.com",
                "firstName": "Admin",
                "lastName": "User",
                "enabled": True,
                "emailVerified": True,
                "credentials": [
                    {
                        "type": "password",
                        "value": admin_user_password,
                        "temporary": False,
                    }
                ],
            },
            exist_ok=True,
        )

        # Assign all client roles to admin user
        for role_name in test_roles:
            role = admin_client.get_client_role(
                client_id=client_id, role_name=role_name
            )
            admin_client.assign_client_role(
                client_id=client_id, user_id=admin_user_id, roles=[role]
            )

        # Return connection details
        yield {
            "base_url": base_url,
            "realm": test_realm,
            "client_id": test_client_id,
            "admin_username": admin_username,
            "admin_password": admin_password,
            "test_username": test_username,
            "test_password": test_password,
            "admin_user_username": admin_user_username,
            "admin_user_password": admin_user_password,
        }

    finally:
        # Stop container
        container.stop()


@pytest.fixture(scope="function")
def integration_keycloak_manager(keycloak_container):
    """
    Provides a real KeycloakManager connected to the test container.

    This fixture creates a KeycloakManager instance configured to use
    the real Keycloak testcontainer. Use this for integration tests
    that need to validate real authentication flows.

    Args:
        keycloak_container: Session-scoped Keycloak container fixture

    Yields:
        KeycloakManager: Real KeycloakManager instance

    Example:
        @pytest.mark.integration
        async def test_login(integration_keycloak_manager, keycloak_container):
            token = await integration_keycloak_manager.login_async(
                keycloak_container["test_username"],
                keycloak_container["test_password"]
            )
            assert "access_token" in token
    """
    # Patch app_settings to use testcontainer Keycloak
    with patch("{{cookiecutter.module_name}}.managers.keycloak_manager.app_settings") as mock_settings:
        mock_settings.KEYCLOAK_BASE_URL = keycloak_container["base_url"]
        mock_settings.KEYCLOAK_REALM = keycloak_container["realm"]
        mock_settings.KEYCLOAK_CLIENT_ID = keycloak_container["client_id"]
        mock_settings.KEYCLOAK_ADMIN_USERNAME = keycloak_container[
            "admin_username"
        ]
        mock_settings.KEYCLOAK_ADMIN_PASSWORD = keycloak_container[
            "admin_password"
        ]

        # Create real KeycloakManager with testcontainer settings
        manager = KeycloakManager()
        yield manager
