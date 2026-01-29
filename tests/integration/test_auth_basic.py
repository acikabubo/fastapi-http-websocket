"""Tests for basic authentication functions."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from keycloak.exceptions import KeycloakAuthenticationError

from app.auth import basic_auth_keycloak_user
from app.schemas.user import UserModel
from tests.mocks.auth_mocks import create_mock_keycloak_manager


class TestBasicAuthKeycloakUser:
    """Tests for basic_auth_keycloak_user function."""

    @pytest.mark.asyncio
    async def test_basic_auth_success(self, mock_user_data):
        """Test successful basic authentication."""
        credentials = HTTPBasicCredentials(
            username="testuser", password="password"
        )

        # Mock Keycloak manager with async methods
        mock_kc_manager = create_mock_keycloak_manager()
        mock_kc_manager.openid.a_decode_token.return_value = mock_user_data

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            user = await basic_auth_keycloak_user(credentials)

        assert isinstance(user, UserModel)
        assert user.username == mock_user_data["preferred_username"]
        mock_kc_manager.login_async.assert_called_once_with(
            "testuser", "password"
        )

    @pytest.mark.asyncio
    async def test_basic_auth_invalid_credentials(self):
        """Test basic authentication with invalid credentials."""
        credentials = HTTPBasicCredentials(
            username="testuser", password="wrong"
        )

        # Mock Keycloak manager to raise authentication error
        mock_kc_manager = create_mock_keycloak_manager()
        mock_error = KeycloakAuthenticationError("Invalid credentials")
        mock_error.response_code = 401
        mock_kc_manager.login_async.side_effect = mock_error

        with patch("app.auth.keycloak_manager", mock_kc_manager):
            with pytest.raises(HTTPException) as exc_info:
                await basic_auth_keycloak_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in exc_info.value.detail
