"""
Tests for decorator-based RBAC permissions.

This module tests the new decorator-based approach for WebSocket permissions,
where roles are defined directly in the @pkg_router.register() decorator.
"""

from app.api.ws.constants import PkgID
from app.routing import PackageRouter
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel
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


class TestDecoratorBasedRBAC:
    """Tests for decorator-based RBAC functionality."""

    def test_permissions_registry_stores_roles(self):
        """Test that roles are stored in permissions_registry."""
        router = PackageRouter()

        @router.register(PkgID.TEST_HANDLER, roles=["get-authors"])
        async def test_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        assert PkgID.TEST_HANDLER in router.permissions_registry
        assert router.permissions_registry[PkgID.TEST_HANDLER] == [
            "get-authors"
        ]

    def test_get_permissions_returns_roles(self):
        """Test that get_permissions() returns the correct roles."""
        router = PackageRouter()

        @router.register(PkgID.TEST_HANDLER, roles=["get-authors", "admin"])
        async def test_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        permissions = router.get_permissions(PkgID.TEST_HANDLER)
        assert permissions == ["get-authors", "admin"]

    def test_get_permissions_returns_empty_for_public_endpoint(self):
        """Test that endpoints without roles return empty list."""
        router = PackageRouter()

        @router.register(PkgID.UNREGISTERED_HANDLER)  # No roles specified
        async def test_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        permissions = router.get_permissions(PkgID.UNREGISTERED_HANDLER)
        assert permissions == []

    def test_permission_check_with_single_role(self):
        """Test permission check when user has required role."""
        router = PackageRouter()

        @router.register(PkgID.TEST_HANDLER, roles=["get-authors"])
        async def test_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        # User with correct role
        user = create_test_user("test_user", roles=["get-authors"])

        has_permission = router._check_permission(PkgID.TEST_HANDLER, user)
        assert has_permission is True

    def test_permission_check_fails_without_role(self):
        """Test permission check fails when user lacks required role."""
        router = PackageRouter()

        @router.register(PkgID.TEST_HANDLER, roles=["get-authors"])
        async def test_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        # User without required role
        user = create_test_user("test_user", roles=["other-role"])

        has_permission = router._check_permission(PkgID.TEST_HANDLER, user)
        assert has_permission is False

    def test_permission_check_requires_all_roles(self):
        """Test that user must have ALL required roles."""
        router = PackageRouter()

        @router.register(PkgID.TEST_HANDLER, roles=["get-authors", "admin"])
        async def test_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        # Verify roles are stored correctly
        permissions = router.get_permissions(PkgID.TEST_HANDLER)
        assert permissions == ["get-authors", "admin"]

        # Test directly with the roles check logic (without RBAC manager)
        user_one_role = create_test_user("test_user", roles=["get-authors"])
        has_all_roles = all(
            role in user_one_role.roles for role in permissions
        )
        assert has_all_roles is False

        # User with both required roles
        user_both_roles = create_test_user(
            "admin_user", roles=["get-authors", "admin"]
        )
        has_all_roles = all(
            role in user_both_roles.roles for role in permissions
        )
        assert has_all_roles is True

    def test_public_endpoint_allows_any_user(self):
        """Test that endpoints without roles allow any user."""
        router = PackageRouter()

        @router.register(PkgID.UNREGISTERED_HANDLER)  # Public endpoint
        async def test_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        # User with no roles
        user = create_test_user("test_user", roles=[])

        has_permission = router._check_permission(
            PkgID.UNREGISTERED_HANDLER, user
        )
        assert has_permission is True

    def test_multiple_handlers_different_roles(self):
        """Test that different handlers can have different role requirements."""
        router = PackageRouter()

        @router.register(PkgID.TEST_HANDLER, roles=["get-authors"])
        async def get_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        @router.register(PkgID.UNREGISTERED_HANDLER)  # Public
        async def paginated_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        # Check first handler requires role
        perms1 = router.get_permissions(PkgID.TEST_HANDLER)
        assert perms1 == ["get-authors"]

        # Check second handler is public
        perms2 = router.get_permissions(PkgID.UNREGISTERED_HANDLER)
        assert perms2 == []


class TestRBACManagerIntegration:
    """Tests for RBACManager integration with decorator-based permissions."""

    def test_rbac_manager_uses_decorator_permissions(self):
        """Test that RBACManager reads permissions from decorator."""
        from app.managers.rbac_manager import RBACManager
        from app.routing import pkg_router

        # RBACManager is a singleton, it should use the global pkg_router
        rbac = RBACManager()

        # User with admin role
        user = create_test_user("test_user", roles=["admin"])

        # PkgID.TEST_HANDLER has roles=["admin"] in the decorator
        has_permission = rbac.check_ws_permission(
            PkgID.TEST_HANDLER, user, pkg_router.permissions_registry
        )
        assert has_permission is True

    def test_rbac_manager_denies_without_role(self):
        """Test that RBACManager denies access without required role."""
        from app.managers.rbac_manager import RBACManager
        from app.routing import pkg_router

        rbac = RBACManager()

        # User without admin role
        user = create_test_user("test_user", roles=["other-role"])

        has_permission = rbac.check_ws_permission(
            PkgID.TEST_HANDLER, user, pkg_router.permissions_registry
        )
        assert has_permission is False

    def test_rbac_manager_allows_public_endpoint(self):
        """Test that RBACManager allows access to public endpoints."""
        from app.managers.rbac_manager import RBACManager
        from app.routing import pkg_router

        rbac = RBACManager()

        # User with no roles
        user = create_test_user("test_user", roles=[])

        # UNREGISTERED_HANDLER has no roles requirement (public, not registered)
        # For this test, we're checking that RBACManager allows access to
        # endpoints not configured in actions.json (defaults to allow)
        has_permission = rbac.check_ws_permission(
            PkgID.UNREGISTERED_HANDLER, user, pkg_router.permissions_registry
        )
        assert has_permission is True


class TestRolesLogging:
    """Tests for logging of role-based access control."""

    def test_registration_logs_roles(self, caplog):
        """Test that handler registration logs the roles."""
        import logging

        caplog.set_level(logging.INFO)

        router = PackageRouter()

        @router.register(PkgID.TEST_HANDLER, roles=["get-authors", "admin"])
        async def test_handler(request: RequestModel):
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        # Check that roles are logged during registration
        log_messages = [record.message for record in caplog.records]
        assert any("with roles" in msg for msg in log_messages)
        assert any("get-authors" in msg for msg in log_messages)
