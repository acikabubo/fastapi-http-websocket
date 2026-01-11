"""Tests for package routing functionality."""

from {{cookiecutter.module_name}}.api.ws.constants import PkgID
from {{cookiecutter.module_name}}.routing import PackageRouter, collect_subrouters
from {{cookiecutter.module_name}}.schemas.request import RequestModel
from {{cookiecutter.module_name}}.schemas.response import ResponseModel


class TestPackageRouter:
    """Test PackageRouter handler registration and dispatch."""

    def test_register_handler_without_schema(self):
        """Test registering handler without JSON schema."""
        router = PackageRouter()

        @router.register(PkgID.UNREGISTERED_HANDLER)
        async def test_handler(request: RequestModel) -> ResponseModel:
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        assert PkgID.UNREGISTERED_HANDLER in router.handlers_registry
        assert (
            router.handlers_registry[PkgID.UNREGISTERED_HANDLER]
            == test_handler
        )

    def test_register_handler_with_roles(self):
        """Test registering handler with RBAC roles."""
        router = PackageRouter()

        @router.register(PkgID.UNREGISTERED_HANDLER, roles=["admin", "user"])
        async def test_handler(request: RequestModel) -> ResponseModel:
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        assert PkgID.UNREGISTERED_HANDLER in router.permissions_registry
        assert router.permissions_registry[PkgID.UNREGISTERED_HANDLER] == [
            "admin",
            "user",
        ]

    def test_get_permissions_returns_empty_list_for_public(self):
        """Test that get_permissions returns empty list for public endpoints."""
        router = PackageRouter()

        @router.register(PkgID.UNREGISTERED_HANDLER)  # No roles = public
        async def test_handler(request: RequestModel) -> ResponseModel:
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        permissions = router.get_permissions(PkgID.UNREGISTERED_HANDLER)

        assert permissions == []

    def test_get_permissions_returns_roles_list(self):
        """Test that get_permissions returns configured roles."""
        router = PackageRouter()

        @router.register(
            PkgID.UNREGISTERED_HANDLER, roles=["admin", "moderator"]
        )
        async def test_handler(request: RequestModel) -> ResponseModel:
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        permissions = router.get_permissions(PkgID.UNREGISTERED_HANDLER)

        assert permissions == ["admin", "moderator"]

    def test_has_handler_returns_true_when_registered(self):
        """Test _has_handler returns True for registered handler."""
        router = PackageRouter()

        @router.register(PkgID.UNREGISTERED_HANDLER)
        async def test_handler(request: RequestModel) -> ResponseModel:
            return ResponseModel.success(
                request.pkg_id, request.req_id, data={}
            )

        assert router._has_handler(PkgID.UNREGISTERED_HANDLER) is True

    def test_has_handler_returns_false_when_not_registered(self):
        """Test _has_handler returns False for unregistered handler."""
        router = PackageRouter()

        # Use a different value that's guaranteed not to be registered
        assert router._has_handler(9999) is False


class TestCollectSubrouters:
    """Test HTTP and WebSocket router collection."""

    def test_collect_subrouters_returns_api_router(self):
        """Test that collect_subrouters returns an APIRouter instance."""
        from fastapi import APIRouter

        router = collect_subrouters()

        assert isinstance(router, APIRouter)

    def test_collect_subrouters_includes_http_routes(self):
        """Test that HTTP routes are included."""
        router = collect_subrouters()

        # Should have routes from HTTP routers
        route_paths = [route.path for route in router.routes]

        # Check for known HTTP routes (health, metrics, etc.)
        assert any("/health" in path for path in route_paths)

    def test_collect_subrouters_includes_websocket_routes(self):
        """Test that WebSocket routes are included."""
        router = collect_subrouters()

        # Should have WebSocket routes
        route_paths = [route.path for route in router.routes]

        # Check for known WebSocket route
        assert any("/web" in path for path in route_paths)
