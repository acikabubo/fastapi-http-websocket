"""Tests for basic authentication functions."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPBasicCredentials
from keycloak.exceptions import KeycloakAuthenticationError

from app.auth import basic_auth_keycloak_user
from app.schemas.user import UserModel


class TestBasicAuthKeycloakUser:
    """Tests for basic_auth_keycloak_user function."""

    @pytest.mark.asyncio
    async def test_basic_auth_success(self, mock_user_data):
        """Test successful basic authentication."""
        credentials = HTTPBasicCredentials(username="testuser", password="password")

        # Mock Keycloak manager
        mock_kc_manager = MagicMock()
        mock_kc_manager.login.return_value = {"access_token": "test-token"}
        mock_kc_manager.openid.decode_token.return_value = mock_user_data

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            user = basic_auth_keycloak_user(credentials)

        assert isinstance(user, UserModel)
        assert user.username == mock_user_data["preferred_username"]
        mock_kc_manager.login.assert_called_once_with("testuser", "password")

    @pytest.mark.asyncio
    async def test_basic_auth_invalid_credentials(self):
        """Test basic authentication with invalid credentials."""
        credentials = HTTPBasicCredentials(username="testuser", password="wrong")

        # Mock Keycloak manager to raise authentication error
        mock_kc_manager = MagicMock()
        mock_error = KeycloakAuthenticationError("Invalid credentials")
        mock_error.response_code = 401
        mock_kc_manager.login.side_effect = mock_error

        with patch("app.auth.KeycloakManager", return_value=mock_kc_manager):
            with pytest.raises(HTTPException) as exc_info:
                basic_auth_keycloak_user(credentials)

        assert exc_info.value.status_code == 401
        assert "Invalid credentials" in exc_info.value.detail
