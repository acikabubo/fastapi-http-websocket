"""
Integration tests for Keycloak authentication using testcontainers.

These tests use a real Keycloak container to validate authentication flows,
token decoding, and RBAC role mappings. They are marked with @pytest.mark.integration
and can be run separately from fast unit tests.

Run with:
    pytest -m integration tests/integration/
    make test-integration
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_with_valid_credentials(
    integration_keycloak_manager, keycloak_container
):
    """
    Test successful login with valid user credentials.

    Validates that:
    - Login succeeds with correct credentials
    - Access token is returned
    - Token has expected structure
    """
    # Login with test user
    token_response = await integration_keycloak_manager.login_async(
        keycloak_container["test_username"],
        keycloak_container["test_password"],
    )

    # Verify token structure
    assert "access_token" in token_response
    assert "refresh_token" in token_response
    assert "expires_in" in token_response
    assert token_response["token_type"] == "Bearer"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_with_invalid_credentials(integration_keycloak_manager):
    """
    Test login failure with invalid credentials.

    Validates that:
    - Login fails with incorrect password
    - Appropriate exception is raised
    """
    from keycloak.exceptions import KeycloakAuthenticationError

    with pytest.raises(KeycloakAuthenticationError):
        await integration_keycloak_manager.login_async(
            "testuser", "wrongpassword"
        )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_decode_with_real_jwt(
    integration_keycloak_manager, keycloak_container
):
    """
    Test decoding real JWT token from Keycloak.

    Validates that:
    - Token can be decoded successfully
    - User claims are present
    - Roles are correctly mapped
    """
    # Login to get real token
    token_response = await integration_keycloak_manager.login_async(
        keycloak_container["test_username"],
        keycloak_container["test_password"],
    )

    # Decode token
    user_data = await integration_keycloak_manager.openid.a_decode_token(
        token_response["access_token"]
    )

    # Verify user data
    assert (
        user_data["preferred_username"] == keycloak_container["test_username"]
    )
    assert "sub" in user_data
    assert "exp" in user_data
    assert "realm_access" in user_data
    assert "roles" in user_data["realm_access"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rbac_roles_in_token(
    integration_keycloak_manager, keycloak_container
):
    """
    Test RBAC roles are correctly included in JWT token.

    Validates that:
    - Test user has "get-authors" role
    - Admin user has all roles
    - Roles can be used for permission checks
    """
    # Test user with limited permissions
    test_token = await integration_keycloak_manager.login_async(
        keycloak_container["test_username"],
        keycloak_container["test_password"],
    )
    test_user_data = await integration_keycloak_manager.openid.a_decode_token(
        test_token["access_token"]
    )

    # Verify test user roles (client roles, not realm roles)
    # UserModel extracts from resource_access[client_id]["roles"]
    client_id = keycloak_container["client_id"]
    test_roles = test_user_data["resource_access"][client_id]["roles"]
    assert "get-authors" in test_roles
    assert "admin" not in test_roles
    assert "delete-author" not in test_roles

    # Admin user with full permissions
    admin_token = await integration_keycloak_manager.login_async(
        keycloak_container["admin_user_username"],
        keycloak_container["admin_user_password"],
    )
    admin_user_data = await integration_keycloak_manager.openid.a_decode_token(
        admin_token["access_token"]
    )

    # Verify admin user roles (client roles)
    admin_roles = admin_user_data["resource_access"][client_id]["roles"]
    assert "get-authors" in admin_roles
    assert "create-author" in admin_roles
    assert "update-author" in admin_roles
    assert "delete-author" in admin_roles
    assert "admin" in admin_roles


@pytest.mark.integration
@pytest.mark.asyncio
async def test_token_expiration_claim(
    integration_keycloak_manager, keycloak_container
):
    """
    Test JWT token includes expiration claim.

    Validates that:
    - Token has 'exp' claim
    - Expiration is in the future
    - Expiration follows configured token lifetime
    """
    import time

    # Login to get real token
    token_response = await integration_keycloak_manager.login_async(
        keycloak_container["test_username"],
        keycloak_container["test_password"],
    )

    # Decode token
    user_data = await integration_keycloak_manager.openid.a_decode_token(
        token_response["access_token"]
    )

    # Verify expiration
    current_time = int(time.time())
    token_exp = user_data["exp"]

    assert token_exp > current_time, "Token expiration should be in the future"
    assert token_exp - current_time <= token_response["expires_in"] + 10, (
        "Token expiration should match expires_in claim (with 10s tolerance)"
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_token_flow(
    integration_keycloak_manager, keycloak_container
):
    """
    Test refresh token can be used to get new access token.

    Validates that:
    - Refresh token is returned on login
    - Refresh token can be used to get new access token
    - New token is different from original
    """
    # Login to get initial tokens
    initial_token = await integration_keycloak_manager.login_async(
        keycloak_container["test_username"],
        keycloak_container["test_password"],
    )

    # Use refresh token to get new access token
    refreshed_token = integration_keycloak_manager.openid.refresh_token(
        initial_token["refresh_token"]
    )

    # Verify new access token
    assert "access_token" in refreshed_token
    assert refreshed_token["access_token"] != initial_token["access_token"]

    # Verify new access token is valid
    user_data = await integration_keycloak_manager.openid.a_decode_token(
        refreshed_token["access_token"]
    )
    assert (
        user_data["preferred_username"] == keycloak_container["test_username"]
    )


@pytest.mark.integration
@pytest.mark.asyncio
async def test_user_model_creation_from_real_token(
    integration_keycloak_manager, keycloak_container
):
    """
    Test UserModel can be created from real decoded token.

    Validates that:
    - Token data matches UserModel schema
    - All required fields are present
    - UserModel instance is valid
    """
    from app.schemas.user import UserModel

    # Login and decode token
    token_response = await integration_keycloak_manager.login_async(
        keycloak_container["test_username"],
        keycloak_container["test_password"],
    )
    user_data = await integration_keycloak_manager.openid.a_decode_token(
        token_response["access_token"]
    )

    # Create UserModel from real token data
    user = UserModel(**user_data)

    # Verify user model (UserModel only has id, username, roles, expired_in)
    assert user.username == keycloak_container["test_username"]
    assert user.id == user_data["sub"]
    assert "get-authors" in user.roles
    assert user.expired_in == user_data["exp"]
