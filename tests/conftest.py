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
    return {
        "Authorization": f"Bearer {mock_keycloak_token['access_token']}"
    }


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
        "resource_access": {
            "test-client": {
                "roles": []
            }
        },
    }
