"""
Mock factory functions for Keycloak testing.

Provides mocks for KeycloakOpenID and KeycloakAdmin clients.
"""

from unittest.mock import Mock


def create_mock_keycloak_openid():
    """
    Creates a mock KeycloakOpenID client.

    Returns:
        Mock: Mocked KeycloakOpenID instance
    """
    openid_mock = Mock()

    # Token operations
    openid_mock.token = Mock(
        return_value={
            "access_token": "mock_access_token_12345",
            "expires_in": 300,
            "refresh_expires_in": 1800,
            "refresh_token": "mock_refresh_token_67890",
            "token_type": "Bearer",
            "session_state": "mock-session-state",
            "scope": "openid email profile",
        }
    )

    openid_mock.refresh_token = Mock(
        return_value={
            "access_token": "refreshed_access_token",
            "refresh_token": "refreshed_refresh_token",
            "expires_in": 300,
        }
    )

    # Token introspection and decoding
    openid_mock.introspect = Mock(return_value={"active": True})

    openid_mock.decode_token = Mock(
        return_value={
            "sub": "f86caf01-69b4-4892-ba2d-ffa58fdd5dab",
            "preferred_username": "testuser",
            "given_name": "Test",
            "family_name": "User",
            "email": "testuser@example.com",
            "exp": 9999999999,
            "azp": "test-client",
            "realm_access": {"roles": ["admin", "user", "get-authors"]},
            "resource_access": {
                "test-client": {"roles": ["admin", "get-authors"]}
            },
        }
    )

    # User info
    openid_mock.userinfo = Mock(
        return_value={
            "sub": "f86caf01-69b4-4892-ba2d-ffa58fdd5dab",
            "email": "testuser@example.com",
            "preferred_username": "testuser",
        }
    )

    # Logout
    openid_mock.logout = Mock(return_value=None)

    return openid_mock


def create_mock_keycloak_admin():
    """
    Creates a mock KeycloakAdmin client.

    Returns:
        Mock: Mocked KeycloakAdmin instance
    """
    admin_mock = Mock()

    # User management
    admin_mock.create_user = Mock(return_value="new-user-id")
    admin_mock.get_user = Mock(
        return_value={
            "id": "user-id-123",
            "username": "testuser",
            "email": "testuser@example.com",
            "enabled": True,
        }
    )
    admin_mock.get_users = Mock(return_value=[])
    admin_mock.update_user = Mock(return_value=None)
    admin_mock.delete_user = Mock(return_value=None)

    # Role management
    admin_mock.get_realm_roles = Mock(return_value=[])
    admin_mock.get_user_realm_roles = Mock(return_value=[])
    admin_mock.assign_realm_roles = Mock(return_value=None)
    admin_mock.delete_realm_roles_of_user = Mock(return_value=None)

    # Group management
    admin_mock.get_groups = Mock(return_value=[])
    admin_mock.get_user_groups = Mock(return_value=[])
    admin_mock.group_user_add = Mock(return_value=None)
    admin_mock.group_user_remove = Mock(return_value=None)

    # Session management
    admin_mock.get_sessions = Mock(return_value=[])
    admin_mock.user_logout = Mock(return_value=None)

    return admin_mock
