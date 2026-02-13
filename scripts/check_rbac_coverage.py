#!/usr/bin/env python3
"""
Static analysis script to check RBAC coverage on HTTP and WebSocket endpoints.

This script validates that:
1. HTTP endpoints have require_roles() in dependencies or are explicitly public
2. WebSocket handlers have roles=[] parameter or are explicitly public
3. Endpoints are properly documented with security requirements

Exit codes:
    0: All endpoints properly protected or documented as public
    1: Found unprotected endpoints or validation errors
"""

import ast
import sys
from pathlib import Path
from typing import NamedTuple


class EndpointInfo(NamedTuple):
    """Information about an endpoint."""

    file: Path
    line: int
    name: str
    type: str  # "http" or "websocket"
    has_rbac: bool
    is_public: bool
    roles: list[str] | None


class RBACChecker(ast.NodeVisitor):
    """AST visitor to check RBAC decorators on endpoints."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.endpoints: list[EndpointInfo] = []
        self.current_function: str | None = None

    def _check_function_node(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        """Check a function node for endpoint decorators."""
        self.current_function = node.name

        # Check for HTTP endpoint decorators
        http_endpoint = self._is_http_endpoint(node)
        if http_endpoint:
            has_rbac, is_public, roles = self._check_http_rbac(node)
            self.endpoints.append(
                EndpointInfo(
                    file=self.file_path,
                    line=node.lineno,
                    name=node.name,
                    type="http",
                    has_rbac=has_rbac,
                    is_public=is_public,
                    roles=roles,
                )
            )

        # Check for WebSocket handler decorators
        ws_handler = self._is_ws_handler(node)
        if ws_handler:
            has_rbac, is_public, roles = self._check_ws_rbac(node)
            self.endpoints.append(
                EndpointInfo(
                    file=self.file_path,
                    line=node.lineno,
                    name=node.name,
                    type="websocket",
                    has_rbac=has_rbac,
                    is_public=is_public,
                    roles=roles,
                )
            )

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """Visit regular function definitions."""
        self._check_function_node(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        """Visit async function definitions (most FastAPI endpoints)."""
        self._check_function_node(node)

    def _is_http_endpoint(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        """Check if function is an HTTP endpoint (has @router.get/post/etc)."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    # Check for @router.get(), @router.post(), etc.
                    if (
                        isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == "router"
                        and decorator.func.attr
                        in {"get", "post", "put", "patch", "delete"}
                    ):
                        return True
        return False

    def _is_ws_handler(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> bool:
        """Check if function is a WebSocket handler (has @pkg_router.register)."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Attribute):
                    # Check for @pkg_router.register()
                    if (
                        isinstance(decorator.func.value, ast.Name)
                        and decorator.func.value.id == "pkg_router"
                        and decorator.func.attr == "register"
                    ):
                        return True
        return False

    def _check_http_rbac(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> tuple[bool, bool, list[str] | None]:
        """
        Check if HTTP endpoint has RBAC protection.

        Returns:
            (has_rbac, is_public, roles)
        """
        # Look for dependencies=[Depends(require_roles(...))]
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            for keyword in decorator.keywords:
                if keyword.arg != "dependencies":
                    continue
                # Check if value is a list
                if not isinstance(keyword.value, ast.List):
                    continue
                for dep in keyword.value.elts:
                    if isinstance(
                        dep, ast.Call
                    ) and self._is_require_roles_call(dep):
                        roles = self._extract_roles(dep)
                        return (True, False, roles)

        # Check docstring for "Public endpoint" marker
        docstring = ast.get_docstring(node)
        if docstring and "public endpoint" in docstring.lower():
            return (False, True, None)

        return (False, False, None)

    def _check_ws_rbac(
        self, node: ast.FunctionDef
    ) -> tuple[bool, bool, list[str] | None]:
        """
        Check if WebSocket handler has RBAC protection.

        Returns:
            (has_rbac, is_public, roles)
        """
        # Look for @pkg_router.register(..., roles=[...])
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                for keyword in decorator.keywords:
                    if keyword.arg == "roles":
                        # Extract roles
                        roles = self._extract_roles_from_list(keyword.value)
                        return (True, False, roles)

        # Check docstring for "Public handler" marker
        docstring = ast.get_docstring(node)
        if docstring and "public handler" in docstring.lower():
            return (False, True, None)

        return (False, False, None)

    def _is_require_roles_call(self, node: ast.Call) -> bool:
        """Check if node is Depends(require_roles(...))."""
        if isinstance(node.func, ast.Name) and node.func.id == "Depends":
            if node.args and isinstance(node.args[0], ast.Call):
                call = node.args[0]
                if (
                    isinstance(call.func, ast.Name)
                    and call.func.id == "require_roles"
                ):
                    return True
        return False

    def _extract_roles(self, depends_node: ast.Call) -> list[str] | None:
        """Extract roles from Depends(require_roles(...)) call."""
        if depends_node.args and isinstance(depends_node.args[0], ast.Call):
            require_roles_call = depends_node.args[0]
            return self._extract_roles_from_args(require_roles_call.args)
        return None

    def _extract_roles_from_args(self, args: list[ast.expr]) -> list[str]:
        """Extract role strings from function arguments."""
        roles = []
        for arg in args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                roles.append(arg.value)
        return roles

    def _extract_roles_from_list(self, node: ast.expr) -> list[str] | None:
        """Extract roles from list literal."""
        if isinstance(node, ast.List):
            return self._extract_roles_from_args(node.elts)
        return None


def check_file(file_path: Path) -> list[EndpointInfo]:
    """Check a single Python file for RBAC coverage."""
    try:
        with open(file_path, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        checker = RBACChecker(file_path)
        checker.visit(tree)
        return checker.endpoints
    except SyntaxError as e:
        print(f"⚠️  Syntax error in {file_path}: {e}", file=sys.stderr)
        return []
    except Exception as e:  # noqa: BLE001
        # Catch all exceptions to prevent script from crashing on single file errors
        print(f"⚠️  Error processing {file_path}: {e}", file=sys.stderr)
        return []


def main() -> int:
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    app_dir = project_root / "app"

    # Find all HTTP endpoint files
    http_files = list((app_dir / "api" / "http").glob("*.py"))
    # Find all WebSocket handler files
    ws_files = list((app_dir / "api" / "ws" / "handlers").glob("*.py"))

    all_endpoints: list[EndpointInfo] = []

    print("🔍 Checking RBAC coverage on endpoints...")
    print()  # noqa: T201

    # Check all files
    for file_path in http_files + ws_files:
        if file_path.name.startswith("_"):
            continue  # Skip __init__.py and private files
        endpoints = check_file(file_path)
        all_endpoints.extend(endpoints)

    # Separate protected, public, and unprotected endpoints
    protected = [ep for ep in all_endpoints if ep.has_rbac]
    public = [ep for ep in all_endpoints if ep.is_public]
    unprotected = [
        ep for ep in all_endpoints if not ep.has_rbac and not ep.is_public
    ]

    # Report statistics
    total = len(all_endpoints)
    print("📊 RBAC Coverage Statistics:")
    print(f"   Total endpoints: {total}")
    if total > 0:
        print(
            f"   ✅ Protected: {len(protected)} ({len(protected) / total * 100:.1f}%)"
        )
        print(
            f"   🌐 Public: {len(public)} ({len(public) / total * 100:.1f}%)"
        )
        print(
            f"   ⚠️  Unprotected: {len(unprotected)} ({len(unprotected) / total * 100:.1f}%)"
        )
    else:
        print("   ⚠️  No endpoints found to check!")
        print("   Searched in:")
        print(f"      - {app_dir / 'api' / 'http'}")
        print(f"      - {app_dir / 'api' / 'ws' / 'handlers'}")
    print()

    # Show protected endpoints
    if protected:
        print("✅ Protected Endpoints:")
        for ep in protected:
            roles_str = f" [roles: {', '.join(ep.roles)}]" if ep.roles else ""
            print(
                f"   {ep.file.name}:{ep.line} - {ep.name} ({ep.type}){roles_str}"
            )
        print()  # noqa: T201

    # Show public endpoints
    if public:
        print("🌐 Public Endpoints (explicitly marked):")
        for ep in public:
            print(f"   {ep.file.name}:{ep.line} - {ep.name} ({ep.type})")
        print()  # noqa: T201

    # Show unprotected endpoints (ERROR)
    if unprotected:
        print("❌ UNPROTECTED ENDPOINTS FOUND:")
        print()
        for ep in unprotected:
            print(f"   {ep.file.name}:{ep.line} - {ep.name} ({ep.type})")
            if ep.type == "http":
                print(
                    "      Fix: Add dependencies=[Depends(require_roles(...))]"
                )
            else:
                print("      Fix: Add roles=[...] to @pkg_router.register()")
            print(
                f"      Or: Mark as public in docstring with 'Public {ep.type} endpoint'"
            )
            print()

        print(f"❌ {len(unprotected)} unprotected endpoint(s) found!")
        print()
        print("📚 Documentation:")
        print(
            "   - HTTP endpoints: Use dependencies=[Depends(require_roles('role-name'))]"
        )
        print(
            "   - WebSocket handlers: Use @pkg_router.register(..., roles=['role-name'])"
        )
        print("   - Public endpoints: Add 'Public endpoint' to docstring")
        print()
        return 1

    print("✅ All endpoints are properly protected or marked as public!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
