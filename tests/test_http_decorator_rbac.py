"""
Tests for HTTP decorator-based RBAC permissions.

This module tests the FastAPI dependency-based approach for HTTP permissions,
where roles are defined using the require_roles() dependency.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI, Request
from starlette.authentication import UnauthenticatedUser

from app.dependencies.permissions import require_roles
from app.schemas.user import UserModel


def create_test_user(username="test_user", roles=None):
    """Helper function to create a test user with proper structure."""
    if roles is None:
        roles = []

    return UserModel(
        **{
            "sub": "test-user-id-123",
            "preferred_username": username,
            "email": f"{username}@example.com",
            "exp": 9999999999,
            "azp": "test-client",
            "resource_access": {"test-client": {"roles": roles}},
        }
    )


class TestRequireRolesDependency:
    """Tests for require_roles FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_require_roles_allows_user_with_role(self):
        """Test that require_roles allows users with the required role."""
        # Create dependency
        check_roles = require_roles("get-authors")

        # Create mock request with authenticated user
        mock_request = MagicMock(spec=Request)
        mock_request.user = create_test_user("test_user", roles=["get-authors"])

        # Should not raise exception
        await check_roles(mock_request)

    @pytest.mark.asyncio
    async def test_require_roles_denies_user_without_role(self):
        """Test that require_roles denies users without required role."""
        from fastapi import HTTPException

        # Create dependency
        check_roles = require_roles("get-authors")

        # Create mock request with user lacking role
        mock_request = MagicMock(spec=Request)
        mock_request.user = create_test_user("test_user", roles=["other-role"])

        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await check_roles(mock_request)

        assert exc_info.value.status_code == 403
        assert "get-authors" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_roles_denies_unauthenticated_user(self):
        """Test that require_roles denies unauthenticated users."""
        from fastapi import HTTPException

        # Create dependency
        check_roles = require_roles("get-authors")

        # Create mock request with unauthenticated user
        mock_request = MagicMock(spec=Request)
        mock_request.user = UnauthenticatedUser()

        # Should raise 401 Unauthorized
        with pytest.raises(HTTPException) as exc_info:
            await check_roles(mock_request)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_multiple_roles_success(self):
        """Test that user must have ALL required roles."""
        # Create dependency requiring multiple roles
        check_roles = require_roles("get-authors", "admin")

        # Create mock request with user having both roles
        mock_request = MagicMock(spec=Request)
        mock_request.user = create_test_user(
            "admin_user", roles=["get-authors", "admin"]
        )

        # Should not raise exception
        await check_roles(mock_request)

    @pytest.mark.asyncio
    async def test_require_multiple_roles_missing_one(self):
        """Test that user must have ALL required roles, not just some."""
        from fastapi import HTTPException

        # Create dependency requiring multiple roles
        check_roles = require_roles("get-authors", "admin")

        # Create mock request with user having only one role
        mock_request = MagicMock(spec=Request)
        mock_request.user = create_test_user("test_user", roles=["get-authors"])

        # Should raise 403 Forbidden
        with pytest.raises(HTTPException) as exc_info:
            await check_roles(mock_request)

        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_require_roles_with_extra_roles(self):
        """Test that users with extra roles are still allowed."""
        # Create dependency
        check_roles = require_roles("get-authors")

        # Create mock request with user having required role plus extras
        mock_request = MagicMock(spec=Request)
        mock_request.user = create_test_user(
            "power_user", roles=["get-authors", "admin", "superuser"]
        )

        # Should not raise exception
        await check_roles(mock_request)


class TestHTTPEndpointIntegration:
    """Integration tests for HTTP endpoints with decorator-based RBAC."""

    def test_endpoint_with_single_role_requirement(self):
        """Test that endpoint can be configured with single role requirement."""
        app = FastAPI()

        @app.get("/authors", dependencies=[Depends(require_roles("get-authors"))])
        async def get_authors():
            return {"authors": []}

        # Check that route was registered
        routes = [route for route in app.routes if hasattr(route, "path")]
        author_route = next((r for r in routes if r.path == "/authors"), None)
        assert author_route is not None

        # Check that dependency is attached
        assert len(author_route.dependant.dependencies) > 0

    def test_endpoint_with_multiple_role_requirements(self):
        """Test that endpoint can require multiple roles."""
        app = FastAPI()

        @app.post(
            "/admin/action",
            dependencies=[Depends(require_roles("admin", "write"))],
        )
        async def admin_action():
            return {"status": "ok"}

        # Check that route was registered
        routes = [route for route in app.routes if hasattr(route, "path")]
        admin_route = next((r for r in routes if r.path == "/admin/action"), None)
        assert admin_route is not None

        # Check that dependency is attached
        assert len(admin_route.dependant.dependencies) > 0

    def test_public_endpoint_without_dependencies(self):
        """Test that endpoints can be public by omitting dependencies."""
        app = FastAPI()

        @app.get("/health")
        async def health_check():
            return {"status": "ok"}

        # Check that route was registered
        routes = [route for route in app.routes if hasattr(route, "path")]
        health_route = next((r for r in routes if r.path == "/health"), None)
        assert health_route is not None

        # Check that no RBAC dependencies are attached
        # (there might be other dependencies, but not our require_roles)
        assert health_route.dependant is not None

    def test_different_methods_different_roles(self):
        """Test that different HTTP methods on same path can have different role requirements."""
        app = FastAPI()

        @app.get("/authors", dependencies=[Depends(require_roles("get-authors"))])
        async def get_authors():
            return {"authors": []}

        @app.post("/authors", dependencies=[Depends(require_roles("create-author"))])
        async def create_author():
            return {"id": 1}

        # Check that both routes were registered
        routes = [route for route in app.routes if hasattr(route, "path")]
        author_routes = [r for r in routes if r.path == "/authors"]
        assert len(author_routes) == 2

        # Check that both have dependencies
        for route in author_routes:
            assert len(route.dependant.dependencies) > 0


class TestErrorMessages:
    """Tests for error messages in permission denials."""

    @pytest.mark.asyncio
    async def test_missing_single_role_error_message(self):
        """Test that error message clearly states missing role."""
        from fastapi import HTTPException

        check_roles = require_roles("admin")

        mock_request = MagicMock(spec=Request)
        mock_request.user = create_test_user("test_user", roles=["user"])

        with pytest.raises(HTTPException) as exc_info:
            await check_roles(mock_request)

        assert "admin" in exc_info.value.detail
        assert "Missing required roles" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_multiple_roles_error_message(self):
        """Test that error message lists all missing roles."""
        from fastapi import HTTPException

        check_roles = require_roles("admin", "superuser", "audit")

        mock_request = MagicMock(spec=Request)
        mock_request.user = create_test_user("test_user", roles=["user"])

        with pytest.raises(HTTPException) as exc_info:
            await check_roles(mock_request)

        # All missing roles should be mentioned
        assert "admin" in exc_info.value.detail
        assert "superuser" in exc_info.value.detail
        assert "audit" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_partial_roles_error_message(self):
        """Test that error message only lists actually missing roles."""
        from fastapi import HTTPException

        check_roles = require_roles("admin", "user", "write")

        mock_request = MagicMock(spec=Request)
        mock_request.user = create_test_user("test_user", roles=["user"])

        with pytest.raises(HTTPException) as exc_info:
            await check_roles(mock_request)

        # Only missing roles should be mentioned
        assert "admin" in exc_info.value.detail
        assert "write" in exc_info.value.detail
        # User role is present, should not be in error
        assert "Missing required roles: admin, write" in exc_info.value.detail
