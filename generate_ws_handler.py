"""
WebSocket Handler Code Generator.

This module provides functionality to generate WebSocket handler code using
Python f-strings with AST validation and automatic formatting.

Replaces the old Jinja2 template system with a more maintainable and
type-safe approach.
"""

import ast
import sys
from pathlib import Path
from typing import Any

try:
    import black
    HAS_BLACK = True
except ImportError:
    HAS_BLACK = False


class HandlerGenerator:
    """
    Generates WebSocket handler code with AST validation and formatting.

    This generator creates properly formatted Python code for WebSocket
    handlers with comprehensive docstrings, error handling, and type hints.
    """

    def __init__(self, handlers_dir: str = "app/api/ws/handlers"):
        """
        Initialize the handler generator.

        Args:
            handlers_dir: Directory where handler files will be created.
        """
        self.handlers_dir = Path(handlers_dir)
        self.handlers_dir.mkdir(parents=True, exist_ok=True)

    def generate_handler_code(
        self,
        pkg_id: str,
        handler_name: str,
        has_schema: bool = False,
        has_pagination: bool = False,
        roles: list[str] | None = None,
    ) -> str:
        """
        Generate WebSocket handler code using f-strings.

        Args:
            pkg_id: The PkgID enum name (e.g., "GET_AUTHORS").
            handler_name: The handler function name (e.g., "get_authors").
            has_schema: Whether to include JSON schema validation.
            has_pagination: Whether to include pagination logic.
            roles: List of required RBAC roles (optional).

        Returns:
            Generated Python code as a string.

        Raises:
            SyntaxError: If generated code has syntax errors.
        """
        # Generate imports
        imports = self._generate_imports(has_pagination)

        # Generate schema (if needed)
        schema_code = (
            self._generate_schema(handler_name) if has_schema else ""
        )

        # Generate decorator
        decorator = self._generate_decorator(
            pkg_id, handler_name, has_schema, roles
        )

        # Generate handler function
        handler_code = self._generate_handler_function(
            handler_name, pkg_id, has_pagination
        )

        # Combine all parts
        code = f"{imports}\n\n{schema_code}{decorator}\n{handler_code}"

        # Validate AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            raise SyntaxError(
                f"Generated code has syntax errors: {e}"
            ) from e

        # Format with Black (if available)
        if HAS_BLACK:
            try:
                code = black.format_str(
                    code,
                    mode=black.Mode(line_length=79)
                )
            except Exception:
                # If formatting fails, continue with unformatted code
                pass

        return code

    def _generate_imports(self, has_pagination: bool) -> str:
        """Generate import statements."""
        base_imports = """from app.api.ws.constants import PkgID, RSPCode
from app.logging import logger
from app.routing import pkg_router
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel"""

        if has_pagination:
            pagination_import = (
                "\nfrom app.storage.db import get_paginated_results"
            )
            return base_imports + pagination_import

        return base_imports

    def _generate_schema(self, handler_name: str) -> str:
        """Generate JSON schema example."""
        return f'''# JSON Schema for request data validation
{handler_name}_schema = {{
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "properties": {{
        "filters": {{
            "type": "object",
            "properties": {{
                "id": {{"type": "integer"}},
                "name": {{"type": "string"}},
            }},
            "additionalProperties": False,
        }},
    }},
    "additionalProperties": False,
}}


'''

    def _generate_decorator(
        self,
        pkg_id: str,
        handler_name: str,
        has_schema: bool,
        roles: list[str] | None
    ) -> str:
        """Generate @pkg_router.register decorator."""
        schema_arg = (
            f"{handler_name}_schema"
            if has_schema else "None"
        )

        roles_arg = ""
        if roles:
            roles_str = ", ".join(f'"{role}"' for role in roles)
            roles_arg = f",\n    roles=[{roles_str}]"

        return f'''@pkg_router.register(
    PkgID.{pkg_id},
    json_schema={schema_arg}{roles_arg}
)'''

    def _generate_handler_function(
        self,
        handler_name: str,
        pkg_id: str,
        has_pagination: bool
    ) -> str:
        """Generate handler function with docstring and error handling."""
        # Generate docstring
        docstring = f'''    """
    Handle {pkg_id} WebSocket requests.

    Args:
        request: WebSocket request containing request data.

    Returns:
        ResponseModel with result or error message.

    Example request:
        {{
            "pkg_id": PkgID.{pkg_id},
            "req_id": "550e8400-e29b-41d4-a716-446655440000",
            "data": {{"filters": {{"name": "example"}}}}
        }}

    Example response (success):
        {{
            "pkg_id": PkgID.{pkg_id},
            "req_id": "550e8400-e29b-41d4-a716-446655440000",
            "status_code": 0,
            "data": [{{"id": 1, "name": "example"}}]
        }}

    Example response (error):
        {{
            "pkg_id": PkgID.{pkg_id},
            "req_id": "550e8400-e29b-41d4-a716-446655440000",
            "status_code": 1,
            "data": {{"msg": "Error message"}}
        }}
    """'''

        # Generate handler body
        if has_pagination:
            body = '''    try:
        # Extract pagination parameters
        page = request.data.get("page", 1)
        per_page = request.data.get("per_page", 20)
        filters = request.data.get("filters", {})

        # TODO: Replace YourModel with actual model
        # results, meta = await get_paginated_results(
        #     YourModel,
        #     page=page,
        #     per_page=per_page,
        #     filters=filters
        # )

        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data=[],  # TODO: Add [r.model_dump() for r in results]
            # meta=meta  # TODO: Uncomment to include pagination meta
        )
    except ValueError as e:
        logger.error(f"Validation error in {handler_name}: {e}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg=str(e),
            status_code=RSPCode.INVALID_DATA
        )
    except Exception as e:
        logger.error(
            f"Error in {handler_name}: {e}",
            exc_info=True
        )
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="An error occurred while processing the request",
            status_code=RSPCode.ERROR
        )'''
        else:
            body = '''    try:
        # TODO: Implement your handler logic here
        # Example: Get data from request
        # data = request.data.get("key")

        return ResponseModel.success(
            request.pkg_id,
            request.req_id,
            data={"status": "success"}  # TODO: Replace with actual data
        )
    except ValueError as e:
        logger.error(f"Validation error in {handler_name}: {e}")
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg=str(e),
            status_code=RSPCode.INVALID_DATA
        )
    except Exception as e:
        logger.error(
            f"Error in {handler_name}: {e}",
            exc_info=True
        )
        return ResponseModel.err_msg(
            request.pkg_id,
            request.req_id,
            msg="An error occurred while processing the request",
            status_code=RSPCode.ERROR
        )'''

        return f'''async def {handler_name}(request: RequestModel) -> ResponseModel:
{docstring}
{body}
'''

    def create_handler_file(
        self,
        module_name: str,
        pkg_id: str,
        handler_name: str,
        has_schema: bool = False,
        has_pagination: bool = False,
        roles: list[str] | None = None,
        overwrite: bool = False,
    ) -> Path:
        """
        Create a new handler file with generated code.

        Args:
            module_name: Name of the module file (without .py).
            pkg_id: The PkgID enum name.
            handler_name: The handler function name.
            has_schema: Whether to include JSON schema validation.
            has_pagination: Whether to include pagination logic.
            roles: List of required RBAC roles.
            overwrite: Whether to overwrite existing file.

        Returns:
            Path to the created file.

        Raises:
            FileExistsError: If file exists and overwrite=False.
            SyntaxError: If generated code has syntax errors.
        """
        output_path = self.handlers_dir / f"{module_name}.py"

        # Check if file exists
        if output_path.exists() and not overwrite:
            raise FileExistsError(
                f"File already exists: {output_path}\n"
                "Use --overwrite to replace it."
            )

        # Generate code
        code = self.generate_handler_code(
            pkg_id=pkg_id,
            handler_name=handler_name,
            has_schema=has_schema,
            has_pagination=has_pagination,
            roles=roles,
        )

        # Write to file
        output_path.write_text(code)

        return output_path


def main() -> int:
    """
    Command-line interface for generating handlers.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate WebSocket handler code"
    )
    parser.add_argument(
        "handler_name",
        help="Handler function name (e.g., get_authors)"
    )
    parser.add_argument(
        "pkg_id",
        help="PkgID enum name (e.g., GET_AUTHORS)"
    )
    parser.add_argument(
        "--module",
        default=None,
        help="Module name (default: same as handler_name)"
    )
    parser.add_argument(
        "--schema",
        action="store_true",
        help="Include JSON schema validation"
    )
    parser.add_argument(
        "--paginated",
        action="store_true",
        help="Include pagination logic"
    )
    parser.add_argument(
        "--roles",
        nargs="+",
        help="Required RBAC roles (space-separated)"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing file"
    )

    args = parser.parse_args()

    module_name = args.module or args.handler_name

    try:
        generator = HandlerGenerator()
        output_path = generator.create_handler_file(
            module_name=module_name,
            pkg_id=args.pkg_id,
            handler_name=args.handler_name,
            has_schema=args.schema,
            has_pagination=args.paginated,
            roles=args.roles,
            overwrite=args.overwrite,
        )
        print(f"✅ Handler created: {output_path}")
        return 0
    except FileExistsError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1
    except SyntaxError as e:
        print(f"❌ Syntax error in generated code: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
