"""
Mock factory functions for authentication testing.

Provides mocks for Keycloak, AuthBackend, and related auth components.
"""

from unittest.mock import AsyncMock, Mock


def create_mock_auth_backend():
    """
    Creates a mock AuthBackend for testing authentication middleware.

    Returns:
        AsyncMock: Mocked AuthBackend instance
    """
    from app.auth import AuthBackend

    backend_mock = AsyncMock(spec=AuthBackend)
    backend_mock.authenticate = AsyncMock(return_value=None)
    return backend_mock


def create_mock_keycloak_manager():
    """
    Creates a mock KeycloakManager with common methods.

    Returns:
        Mock: Mocked KeycloakManager instance
    """
    manager_mock = Mock()
    manager_mock.login = Mock(
        return_value={
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "expires_in": 300,
            "token_type": "Bearer",
        }
    )
    manager_mock.openid = Mock()
    manager_mock.openid.decode_token = Mock(
        return_value={
            "sub": "user-id-123",
            "preferred_username": "testuser",
            "email": "test@example.com",
            "realm_access": {"roles": ["admin", "user"]},
        }
    )
    manager_mock.admin = Mock()
    return manager_mock


def create_mock_user_model(
    user_id: str = "test-user-id",
    username: str = "testuser",
    roles: list[str] | None = None,
):
    """
    Creates a mock UserModel instance.

    Args:
        user_id: User ID (sub claim)
        username: Username (preferred_username claim)
        roles: List of user roles

    Returns:
        UserModel: Mocked UserModel instance
    """
    from app.schemas.user import UserModel

    return UserModel(
        sub=user_id,
        preferred_username=username,
        email=f"{username}@example.com",
        exp=9999999999,
        azp="test-client",
        realm_access={"roles": roles or ["user"]},
        resource_access={"test-client": {"roles": roles or ["user"]}},
    )


def create_mock_rbac_manager():
    """
    Creates a mock RBACManager for testing permission checks.

    Returns:
        Mock: Mocked RBACManager instance
    """
    from app.managers.rbac_manager import RBACManager

    manager_mock = Mock(spec=RBACManager)
    manager_mock.check_ws_permission = Mock(return_value=True)
    manager_mock.has_required_roles = Mock(return_value=True)
    return manager_mock
