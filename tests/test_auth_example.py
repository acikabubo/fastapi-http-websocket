"""
Example test file demonstrating authentication testing patterns.

This file shows how to test endpoints with both mocked and real authentication.
"""

import uuid
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
            req_id=str(uuid.uuid4()),
            data={},
        )

        # Mock the actual handler to avoid DB dependencies
        from unittest.mock import AsyncMock

        with patch(
            "app.repositories.author_repository.AuthorRepository.get_all",
            new_callable=AsyncMock,
        ) as mock_get_all:
            mock_get_all.return_value = []

            response = await pkg_router.handle_request(mock_user, request)

            assert response.status_code == RSPCode.OK
            assert response.pkg_id == PkgID.GET_AUTHORS
            assert response.req_id == request.req_id

    @pytest.mark.asyncio
    async def test_rbac_permission_check_success(self, mock_user):
        """
        Test RBAC allows user with proper role.

        Args:
            mock_user: Fixture providing UserModel with admin role
        """
        from app.routing import pkg_router

        rbac = RBACManager()

        has_permission = rbac.check_ws_permission(
            PkgID.GET_AUTHORS, mock_user, pkg_router.permissions_registry
        )

        assert has_permission is True

    @pytest.mark.asyncio
    async def test_rbac_permission_check_denied(self, limited_user_data):
        """
        Test RBAC denies user without proper role.

        Args:
            limited_user_data: Fixture providing user without admin role
        """
        from app.routing import pkg_router

        limited_user = UserModel(**limited_user_data)
        rbac = RBACManager()

        has_permission = rbac.check_ws_permission(
            PkgID.GET_AUTHORS, limited_user, pkg_router.permissions_registry
        )

        assert has_permission is False

    @pytest.mark.asyncio
    async def test_handler_returns_permission_denied(self, limited_user_data):
        """
        Test handler returns permission denied for unauthorized user.

        Args:
            limited_user_data: Fixture providing limited user
        """
        limited_user = UserModel(**limited_user_data)

        request = RequestModel(
            pkg_id=PkgID.GET_AUTHORS,
            req_id=str(uuid.uuid4()),
            data={},
        )

        response = await pkg_router.handle_request(limited_user, request)

        assert response.status_code == RSPCode.PERMISSION_DENIED
        assert "No permission" in response.data.get("msg", "")

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
            req_id=str(uuid.uuid4()),
            data={},
        )

        from unittest.mock import AsyncMock

        with patch(
            "app.repositories.author_repository.AuthorRepository.get_all",
            new_callable=AsyncMock,
        ) as mock_get_all:
            mock_get_all.return_value = []

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

    @pytest.mark.asyncio
    async def test_rbac_default_allow_unconfigured_pkg_id(
        self, limited_user_data
    ):
        """
        Test RBAC allows access to pkg_ids not configured in actions.json.

        This tests the "default allow" behavior where pkg_ids without
        explicit role requirements are accessible to all authenticated users.

        Args:
            limited_user_data: Fixture providing user with minimal roles
        """
        from app.routing import pkg_router

        limited_user = UserModel(**limited_user_data)
        rbac = RBACManager()

        # Use a pkg_id that is not in actions.json (assuming 999 is not configured)
        # Since limited_user has no special roles, this tests default allow
        has_permission = rbac.check_ws_permission(
            999, limited_user, pkg_router.permissions_registry
        )

        # Should allow access since pkg_id 999 is not in actions.json
        assert has_permission is True


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
    async def test_protected_endpoints_require_auth(self):
        """
        Test that protected endpoints require authentication via dependencies.

        With decorator-based RBAC, endpoints now use require_roles() dependencies
        which check for authentication. This test verifies the endpoints are
        properly configured with authentication dependencies.
        """
        from fastapi import FastAPI
        from app.api.http.author import router

        # Create a minimal test app with just the author router
        test_app = FastAPI()
        test_app.include_router(router)

        # Check that routes have dependencies configured
        routes = [route for route in test_app.routes if hasattr(route, "path")]

        # Find author routes
        author_get_route = next(
            (r for r in routes if r.path == "/authors" and "GET" in r.methods),
            None,
        )
        author_post_route = next(
            (
                r
                for r in routes
                if r.path == "/authors" and "POST" in r.methods
            ),
            None,
        )

        # Verify routes exist
        assert author_get_route is not None, "GET /authors route should exist"
        assert author_post_route is not None, (
            "POST /authors route should exist"
        )

        # Verify they have dependencies (from RBACDep)
        assert len(author_get_route.dependant.dependencies) > 0, (
            "GET /authors should have dependencies"
        )
        assert len(author_post_route.dependant.dependencies) > 0, (
            "POST /authors should have dependencies"
        )
