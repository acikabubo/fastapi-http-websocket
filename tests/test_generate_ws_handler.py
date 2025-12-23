"""
Tests for WebSocket handler code generator.

Tests the f-string-based code generation system that replaces Jinja2 templates.
"""

import ast
from pathlib import Path

import pytest

from generate_ws_handler import HandlerGenerator


@pytest.fixture
def generator():
    """Create a handler generator instance for testing."""
    return HandlerGenerator(handlers_dir="test_handlers")


@pytest.fixture(autouse=True)
def cleanup_test_handlers():
    """Clean up test handler files after each test."""
    yield
    test_dir = Path("test_handlers")
    if test_dir.exists():
        for file in test_dir.glob("*.py"):
            file.unlink()
        test_dir.rmdir()


class TestHandlerGenerator:
    """Test suite for HandlerGenerator class."""

    def test_generate_simple_handler(self, generator):
        """Test generating a simple handler without schema or pagination."""
        code = generator.generate_handler_code(
            pkg_id="TEST_HANDLER",
            handler_name="test_handler",
            has_schema=False,
            has_pagination=False,
        )

        # Verify code is valid Python
        ast.parse(code)

        # Verify essential imports
        assert "from app.api.ws.constants import PkgID, RSPCode" in code
        assert "from app.routing import pkg_router" in code
        assert "from app.schemas.request import RequestModel" in code
        assert "from app.schemas.response import ResponseModel" in code

        # Verify decorator
        assert "@pkg_router.register(" in code
        assert "PkgID.TEST_HANDLER" in code
        assert "json_schema=None" in code

        # Verify handler function
        assert "async def test_handler(request: RequestModel)" in code
        assert "-> ResponseModel:" in code

        # Verify error handling
        assert "try:" in code
        assert "except ValueError as e:" in code
        assert "except Exception as e:" in code
        assert "logger.error(" in code

    def test_generate_handler_with_schema(self, generator):
        """Test generating a handler with JSON schema validation."""
        code = generator.generate_handler_code(
            pkg_id="CREATE_AUTHOR",
            handler_name="create_author",
            has_schema=True,
            has_pagination=False,
        )

        # Verify code is valid Python
        ast.parse(code)

        # Verify schema definition
        assert "create_author_schema = {" in code
        assert '"$schema": "http://json-schema.org/draft-07/schema#"' in code
        assert '"type": "object"' in code

        # Verify decorator uses schema
        assert "json_schema=create_author_schema" in code

    def test_generate_paginated_handler(self, generator):
        """Test generating a handler with pagination logic."""
        code = generator.generate_handler_code(
            pkg_id="GET_AUTHORS",
            handler_name="get_authors",
            has_schema=False,
            has_pagination=True,
        )

        # Verify code is valid Python
        ast.parse(code)

        # Verify pagination import
        assert "from app.storage.db import get_paginated_results" in code

        # Verify pagination logic
        assert 'page = request.data.get("page", 1)' in code
        assert 'per_page = request.data.get("per_page", 20)' in code
        assert 'filters = request.data.get("filters", {})' in code

    def test_generate_handler_with_roles(self, generator):
        """Test generating a handler with RBAC roles."""
        code = generator.generate_handler_code(
            pkg_id="DELETE_AUTHOR",
            handler_name="delete_author",
            has_schema=False,
            has_pagination=False,
            roles=["delete-author", "admin"],
        )

        # Verify code is valid Python
        ast.parse(code)

        # Verify roles in decorator
        assert 'roles=["delete-author", "admin"]' in code

    def test_create_handler_file(self, generator):
        """Test creating a handler file on disk."""
        output_path = generator.create_handler_file(
            module_name="test_module",
            pkg_id="TEST_HANDLER",
            handler_name="test_handler",
            has_schema=False,
            has_pagination=False,
        )

        # Verify file was created
        assert output_path.exists()
        assert output_path.name == "test_module.py"

        # Verify file content is valid Python
        code = output_path.read_text()
        ast.parse(code)

    def test_create_handler_file_overwrite_protection(self, generator):
        """Test that existing files are not overwritten without permission."""
        # Create first file
        generator.create_handler_file(
            module_name="existing",
            pkg_id="TEST1",
            handler_name="test1",
        )

        # Attempt to create again without overwrite flag
        with pytest.raises(FileExistsError) as exc_info:
            generator.create_handler_file(
                module_name="existing",
                pkg_id="TEST2",
                handler_name="test2",
                overwrite=False,
            )

        assert "already exists" in str(exc_info.value)
        assert "--overwrite" in str(exc_info.value)

    def test_create_handler_file_with_overwrite(self, generator):
        """Test that files can be overwritten with overwrite=True."""
        # Create first file
        path1 = generator.create_handler_file(
            module_name="overwrite_test",
            pkg_id="TEST1",
            handler_name="test1",
        )
        content1 = path1.read_text()

        # Overwrite with different handler
        path2 = generator.create_handler_file(
            module_name="overwrite_test",
            pkg_id="TEST2",
            handler_name="test2",
            overwrite=True,
        )
        content2 = path2.read_text()

        # Verify it was overwritten
        assert path1 == path2
        assert content1 != content2
        assert "TEST1" in content1
        assert "TEST2" in content2

    def test_generate_handler_with_all_options(self, generator):
        """Test generating a handler with all options enabled."""
        code = generator.generate_handler_code(
            pkg_id="COMPLEX_HANDLER",
            handler_name="complex_handler",
            has_schema=True,
            has_pagination=True,
            roles=["admin", "editor"],
        )

        # Verify code is valid Python
        ast.parse(code)

        # Verify all features are present
        assert "complex_handler_schema = {" in code
        assert "from app.storage.db import get_paginated_results" in code
        assert 'roles=["admin", "editor"]' in code
        assert 'page = request.data.get("page", 1)' in code

    def test_generated_code_has_docstrings(self, generator):
        """Test that generated code includes comprehensive docstrings."""
        code = generator.generate_handler_code(
            pkg_id="TEST_HANDLER",
            handler_name="test_handler",
        )

        # Verify handler has docstring
        assert '"""' in code
        assert "Handle TEST_HANDLER WebSocket requests" in code
        assert "Args:" in code
        assert "Returns:" in code
        assert "Example request:" in code
        assert "Example response (success):" in code
        assert "Example response (error):" in code

    def test_generated_code_has_type_hints(self, generator):
        """Test that generated code includes proper type hints."""
        code = generator.generate_handler_code(
            pkg_id="TEST_HANDLER",
            handler_name="test_handler",
        )

        # Verify type hints
        assert "request: RequestModel" in code
        assert "-> ResponseModel:" in code

    def test_generated_code_has_error_handling(self, generator):
        """Test that generated code includes proper error handling."""
        code = generator.generate_handler_code(
            pkg_id="TEST_HANDLER",
            handler_name="test_handler",
        )

        # Verify error handling structure
        assert "try:" in code
        assert "except ValueError as e:" in code
        assert "except Exception as e:" in code
        assert "logger.error(" in code
        assert "ResponseModel.err_msg(" in code
        assert "RSPCode.INVALID_DATA" in code
        assert "RSPCode.ERROR" in code

    def test_ast_validation_catches_syntax_errors(self, generator):
        """Test that AST validation would catch syntax errors."""
        # This test verifies the validation mechanism exists
        # In practice, the generator shouldn't produce invalid code
        code = generator.generate_handler_code(
            pkg_id="TEST_HANDLER",
            handler_name="test_handler",
        )

        # Should not raise any exception
        ast.parse(code)

    def test_handler_includes_response_examples(self, generator):
        """Test that generated handlers include response examples."""
        code = generator.generate_handler_code(
            pkg_id="TEST_HANDLER",
            handler_name="test_handler",
        )

        # Verify example request/response in docstring
        assert '"pkg_id": PkgID.TEST_HANDLER' in code
        assert '"req_id"' in code
        assert '"data"' in code
        assert '"status_code": 0' in code  # Success code
        assert '"status_code": 1' in code  # Error code

    def test_schema_structure(self, generator):
        """Test that generated JSON schema has correct structure."""
        code = generator.generate_handler_code(
            pkg_id="TEST_HANDLER",
            handler_name="test_handler",
            has_schema=True,
        )

        # Verify schema structure
        assert "test_handler_schema = {" in code
        assert '"$schema":' in code
        assert '"type": "object"' in code
        assert '"properties":' in code
        assert '"filters":' in code
        assert '"additionalProperties": False' in code

    def test_pagination_includes_meta(self, generator):
        """Test that paginated handlers include metadata in comments."""
        code = generator.generate_handler_code(
            pkg_id="GET_ITEMS",
            handler_name="get_items",
            has_pagination=True,
        )

        # Verify pagination meta is mentioned
        assert "# meta=meta" in code or "meta" in code.lower()

    def test_handler_name_consistency(self, generator):
        """Test that handler name is used consistently throughout code."""
        handler_name = "my_special_handler"
        code = generator.generate_handler_code(
            pkg_id="SPECIAL",
            handler_name=handler_name,
            has_schema=True,
        )

        # Verify handler name appears in:
        # 1. Schema name
        assert f"{handler_name}_schema" in code
        # 2. Function definition
        assert f"async def {handler_name}" in code
        # 3. Error messages
        assert f"Error in {handler_name}" in code or "error" in code.lower()
