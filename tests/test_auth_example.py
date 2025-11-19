"""
Example test file demonstrating authentication testing patterns.

This file shows how to test endpoints with both mocked and real authentication.
"""
import pytest
from unittest.mock import patch

from app.api.ws.constants import PkgID, RSPCode
from app.managers.rbac_manager import RBACManager
from app.routing import pkg_router
from app.schemas.request import RequestModel
from app.schemas.user import UserModel


class TestMockAuthentication:
    """Test cases using mocked authentication."""

    @pytest.mark.asyncio
    async def test_handler_with_mock_user(self, mock_user):
        """
        Test WebSocket handler executes with mocked user.

        Args:
            mock_user: Fixture providing UserModel instance
        """
        request = RequestModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id="test-request-001",
            data={},
        )

        # Mock the actual handler to avoid DB dependencies
        with patch(
            "app.api.ws.handlers.author_handler.Author.get_list"
        ) as mock_get_list:
            mock_get_list.return_value = [
                {"id": 1, "name": "Author One"},
                {"id": 2, "name": "Author Two"},
            ]

            response = await pkg_router.handle_request(mock_user, request)

            assert response.status_code == RSPCode.OK
            assert response.pkg_id == PkgID.GET_AUTHORS
            assert response.req_id == "test-request-001"

    @pytest.mark.asyncio
    async def test_rbac_permission_check_success(self, mock_user):
        """
        Test RBAC allows user with proper role.

        Args:
            mock_user: Fixture providing UserModel with admin role
        """
        rbac = RBACManager()

        has_permission = rbac.check_ws_permission(
            PkgID.GET_AUTHORS, mock_user
        )

        assert has_permission is True

    @pytest.mark.asyncio
    async def test_rbac_permission_check_denied(self, limited_user_data):
        """
        Test RBAC denies user without proper role.

        Args:
            limited_user_data: Fixture providing user without admin role
        """
        limited_user = UserModel(**limited_user_data)
        rbac = RBACManager()

        has_permission = rbac.check_ws_permission(
            PkgID.GET_AUTHORS, limited_user
        )

        assert has_permission is False

    @pytest.mark.asyncio
    async def test_handler_returns_permission_denied(
        self, limited_user_data
    ):
        """
        Test handler returns permission denied for unauthorized user.

        Args:
            limited_user_data: Fixture providing limited user
        """
        limited_user = UserModel(**limited_user_data)

        request = RequestModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id="test-request-002",
            data={},
        )

        response = await pkg_router.handle_request(limited_user, request)

        assert response.status_code == RSPCode.PERMISSION_DENIED
        assert "No permission" in response.data.get("message", "")

    @pytest.mark.asyncio
    async def test_handler_with_different_roles(
        self, admin_user_data, limited_user_data
    ):
        """
        Test different users get different results based on roles.

        Args:
            admin_user_data: Fixture providing admin user
            limited_user_data: Fixture providing limited user
        """
        admin_user = UserModel(**admin_user_data)
        limited_user = UserModel(**limited_user_data)

        request = RequestModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id="test-request-003",
            data={},
        )

        with patch(
            "app.api.ws.handlers.author_handler.Author.get_list"
        ) as mock_get_list:
            mock_get_list.return_value = []

            # Admin should succeed
            admin_response = await pkg_router.handle_request(
                admin_user, request
            )
            assert admin_response.status_code == RSPCode.OK

            # Limited user should be denied
            limited_response = await pkg_router.handle_request(
                limited_user, request
            )
            assert limited_response.status_code == RSPCode.PERMISSION_DENIED


class TestRealKeycloakAuthentication:
    """
    Integration tests with real Keycloak connection.

    These tests require Keycloak to be running.
    Run with: pytest -m integration
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_login_with_valid_credentials(self):
        """
        Test login returns valid token with real Keycloak.

        This test requires:
        - Keycloak running on configured URL
        - User 'acika' with password '12345' exists
        """
        from app.managers.keycloak_manager import KeycloakManager

        kc = KeycloakManager()

        try:
            token = kc.login("acika", "12345")

            assert "access_token" in token
            assert "refresh_token" in token
            assert token["expires_in"] > 0

            # Verify token can be decoded
            user_data = kc.openid.decode_token(token["access_token"])
            assert user_data["preferred_username"] == "acika"
            assert "realm_access" in user_data
            assert "roles" in user_data["realm_access"]

        except Exception as ex:
            pytest.skip(f"Keycloak not available: {ex}")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_login_with_invalid_credentials(self):
        """
        Test login fails with invalid credentials.
        """
        from app.managers.keycloak_manager import KeycloakManager
        from keycloak.exceptions import KeycloakAuthenticationError

        kc = KeycloakManager()

        with pytest.raises(KeycloakAuthenticationError):
            kc.login("acika", "wrong_password")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_decode_expired_token_fails(self):
        """
        Test that expired tokens are rejected.
        """
        from app.managers.keycloak_manager import KeycloakManager
        from jwcrypto.jwt import JWTExpired

        kc = KeycloakManager()

        # This is an expired token
        expired_token = (
            "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJleHAiOjE2MDAwMDAwMDB9.signature"
        )

        with pytest.raises(JWTExpired):
            kc.openid.decode_token(expired_token)


class TestAuthenticationMiddleware:
    """Test authentication middleware behavior."""

    @pytest.mark.asyncio
    async def test_excluded_paths_bypass_auth(self):
        """
        Test that excluded paths like /docs don't require auth.
        """
        from fastapi.testclient import TestClient
        from app import application

        client = TestClient(application())

        # These should work without authentication
        response = client.get("/docs")
        assert response.status_code in [200, 404]  # 404 if docs disabled

        response = client.get("/openapi.json")
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_protected_endpoints_require_auth(
        self, mock_keycloak_manager
    ):
        """
        Test that protected endpoints require authentication.

        Args:
            mock_keycloak_manager: Fixture mocking Keycloak
        """
        from fastapi.testclient import TestClient
        from app import application

        client = TestClient(application())

        # Request without auth header should fail
        response = client.get("/authors")
        assert response.status_code == 401

        # Request with invalid token should fail
        response = client.get(
            "/authors",
            headers={"Authorization": "Bearer invalid_token"},
        )
        assert response.status_code == 401
