"""
Tests for file I/O utilities.

This module tests the read_json_file function for reading and validating JSON files.
"""

import json
import pytest
from unittest.mock import patch
from jsonschema import ValidationError


class TestReadJsonFile:
    """Tests for read_json_file function."""

    def test_read_valid_json_file(self, tmp_path):
        """Test reading a valid JSON file without schema validation."""
        from app.utils.file_io import read_json_file

        # Create a test JSON file
        test_file = tmp_path / "test.json"
        test_data = {"name": "test", "value": 123}
        test_file.write_text(json.dumps(test_data))

        result = read_json_file(str(test_file), schema=None)

        assert result == test_data

    def test_read_valid_json_with_schema_validation(self, tmp_path):
        """Test reading and validating JSON file against schema."""
        from app.utils.file_io import read_json_file

        test_file = tmp_path / "test.json"
        test_data = {"name": "test", "value": 123}
        test_file.write_text(json.dumps(test_data))

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
            },
            "required": ["name", "value"],
        }

        result = read_json_file(str(test_file), schema=schema)

        assert result == test_data

    def test_read_json_with_invalid_schema_raises_validation_error(
        self, tmp_path
    ):
        """Test reading JSON file that doesn't match schema raises ValidationError."""
        from app.utils.file_io import read_json_file

        test_file = tmp_path / "test.json"
        test_data = {"name": "test", "value": "not_a_number"}
        test_file.write_text(json.dumps(test_data))

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
            },
            "required": ["name", "value"],
        }

        with pytest.raises(ValidationError):
            read_json_file(str(test_file), schema=schema)

    def test_read_nonexistent_file_returns_empty_dict(self):
        """Test reading non-existent file returns empty dictionary."""
        from app.utils.file_io import read_json_file

        result = read_json_file("/nonexistent/path/file.json", schema=None)

        assert result == {}

    def test_read_invalid_json_returns_empty_dict(self, tmp_path):
        """Test reading invalid JSON returns empty dictionary."""
        from app.utils.file_io import read_json_file

        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json }")

        result = read_json_file(str(test_file), schema=None)

        assert result == {}

    def test_read_file_with_os_error_returns_empty_dict(self):
        """Test that OSError during file reading returns empty dictionary."""
        from app.utils.file_io import read_json_file

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            result = read_json_file("test.json", schema=None)

            assert result == {}

    def test_read_file_with_io_error_returns_empty_dict(self):
        """Test that IOError during file reading returns empty dictionary."""
        from app.utils.file_io import read_json_file

        with patch("builtins.open", side_effect=IOError("I/O error")):
            result = read_json_file("test.json", schema=None)

            assert result == {}

    def test_read_empty_json_file(self, tmp_path):
        """Test reading an empty JSON object."""
        from app.utils.file_io import read_json_file

        test_file = tmp_path / "empty.json"
        test_file.write_text("{}")

        result = read_json_file(str(test_file), schema=None)

        assert result == {}

    def test_read_complex_nested_json(self, tmp_path):
        """Test reading complex nested JSON structure."""
        from app.utils.file_io import read_json_file

        test_file = tmp_path / "complex.json"
        test_data = {
            "users": [
                {"id": 1, "name": "Alice", "roles": ["admin", "user"]},
                {"id": 2, "name": "Bob", "roles": ["user"]},
            ],
            "settings": {"theme": "dark", "notifications": True},
        }
        test_file.write_text(json.dumps(test_data))

        result = read_json_file(str(test_file), schema=None)

        assert result == test_data

    def test_validation_error_is_logged(self, tmp_path):
        """Test that ValidationError is logged when schema validation fails."""
        from app.utils.file_io import read_json_file

        test_file = tmp_path / "test.json"
        test_data = {"name": "test"}  # Missing required field 'value'
        test_file.write_text(json.dumps(test_data))

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "value": {"type": "number"},
            },
            "required": ["name", "value"],
        }

        with patch("app.utils.file_io.logger") as mock_logger:
            with pytest.raises(ValidationError):
                read_json_file(str(test_file), schema=schema)

            # Verify logger.error was called
            mock_logger.error.assert_called_once()
            assert "Invalid data" in str(mock_logger.error.call_args)

    def test_json_decode_error_is_logged(self, tmp_path):
        """Test that JSONDecodeError is logged when JSON is malformed."""
        from app.utils.file_io import read_json_file

        test_file = tmp_path / "invalid.json"
        test_file.write_text("not json at all")

        with patch("app.utils.file_io.logger") as mock_logger:
            result = read_json_file(str(test_file), schema=None)

            assert result == {}
            mock_logger.error.assert_called_once()
            assert "Invalid JSON" in str(mock_logger.error.call_args)

    def test_os_error_is_logged(self):
        """Test that OSError is logged when file cannot be read."""
        from app.utils.file_io import read_json_file

        with patch("builtins.open", side_effect=OSError("Permission denied")):
            with patch("app.utils.file_io.logger") as mock_logger:
                result = read_json_file("test.json", schema=None)

                assert result == {}
                mock_logger.error.assert_called_once()
                assert "Failed to open or read" in str(
                    mock_logger.error.call_args
                )
