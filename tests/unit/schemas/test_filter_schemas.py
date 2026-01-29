"""
Tests for type-safe filter schemas.

This module tests the Pydantic filter schemas used for pagination queries,
ensuring type safety and preventing runtime errors from invalid filter keys.
"""

import pytest
from pydantic import ValidationError

from app.models.author import Author
from app.schemas.filters import AuthorFilters, UserActionFilters
from app.storage.db import get_paginated_results
from tests.conftest import create_author_fixture


class TestBaseFilter:
    """Test BaseFilter class functionality."""

    def test_to_dict_excludes_none_values(self):
        """
        Test that to_dict() excludes None values.

        Only non-None filter values should be returned.
        """
        filters = AuthorFilters(name="John", id=None)
        result = filters.to_dict()

        assert result == {"name": "John"}
        assert "id" not in result

    def test_to_dict_all_none_values(self):
        """Test to_dict() with all None values returns empty dict."""
        filters = AuthorFilters(id=None, name=None)
        result = filters.to_dict()

        assert result == {}

    def test_to_dict_no_none_values(self):
        """Test to_dict() with no None values returns all fields."""
        filters = AuthorFilters(id=42, name="John")
        result = filters.to_dict()

        assert result == {"id": 42, "name": "John"}

    def test_extra_fields_forbidden(self):
        """
        Test that extra fields are rejected.

        BaseFilter has extra="forbid" config, should raise ValidationError.
        """
        with pytest.raises(
            ValidationError, match="Extra inputs are not permitted"
        ):
            AuthorFilters(id=1, name="John", invalid_field="value")  # type: ignore[call-arg]


class TestAuthorFilters:
    """Test AuthorFilters schema."""

    def test_valid_id_filter(self):
        """Test creating filter with valid id field."""
        filters = AuthorFilters(id=42)

        assert filters.id == 42
        assert filters.name is None

    def test_valid_name_filter(self):
        """Test creating filter with valid name field."""
        filters = AuthorFilters(name="John Doe")

        assert filters.name == "John Doe"
        assert filters.id is None

    def test_multiple_filters(self):
        """Test creating filter with multiple fields."""
        filters = AuthorFilters(id=42, name="John Doe")

        assert filters.id == 42
        assert filters.name == "John Doe"

    def test_empty_filters(self):
        """Test creating filter with no fields."""
        filters = AuthorFilters()

        assert filters.id is None
        assert filters.name is None
        assert filters.to_dict() == {}

    def test_invalid_id_type(self):
        """Test that invalid id type raises ValidationError."""
        with pytest.raises(
            ValidationError, match="Input should be a valid integer"
        ):
            AuthorFilters(id="not_an_int")  # type: ignore[arg-type]

    def test_invalid_name_type(self):
        """Test that invalid name type raises ValidationError."""
        with pytest.raises(
            ValidationError, match="Input should be a valid string"
        ):
            AuthorFilters(name=123)  # type: ignore[arg-type]


class TestUserActionFilters:
    """Test UserActionFilters schema."""

    def test_valid_basic_filters(self):
        """Test creating filter with basic string fields."""
        filters = UserActionFilters(
            username="john.doe", action_type="GET", outcome="success"
        )

        assert filters.username == "john.doe"
        assert filters.action_type == "GET"
        assert filters.outcome == "success"

    def test_valid_datetime_filters(self):
        """Test creating filter with datetime range."""
        from datetime import UTC, datetime

        start = datetime(2025, 1, 1, tzinfo=UTC)
        end = datetime(2025, 1, 31, tzinfo=UTC)

        filters = UserActionFilters(
            timestamp_after=start, timestamp_before=end
        )

        assert filters.timestamp_after == start
        assert filters.timestamp_before == end

    def test_to_dict_with_datetime(self):
        """Test that to_dict() handles datetime objects correctly."""
        from datetime import UTC, datetime

        start = datetime(2025, 1, 1, tzinfo=UTC)
        filters = UserActionFilters(timestamp_after=start)
        result = filters.to_dict()

        assert "timestamp_after" in result
        assert result["timestamp_after"] == start

    def test_invalid_user_id_type(self):
        """Test that invalid user_id type raises ValidationError."""
        with pytest.raises(
            ValidationError, match="Input should be a valid string"
        ):
            UserActionFilters(user_id=123)  # type: ignore[arg-type]


class TestPaginationWithPydanticFilters:
    """Test get_paginated_results with Pydantic filter schemas."""

    @pytest.mark.asyncio
    async def test_pagination_with_pydantic_filter(self):
        """
        Test pagination with Pydantic filter schema.

        Verifies that Pydantic filters are converted to dict and applied correctly.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock data
        mock_authors = [
            create_author_fixture(id=1, name="John Doe"),
            create_author_fixture(id=2, name="Jane Doe"),
        ]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 2

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_authors

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "app.storage.db.async_session",
                MagicMock(return_value=mock_context_manager),
            ),
            patch(
                "app.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("app.storage.db.set_cached_count", AsyncMock()),
        ):
            # Create Pydantic filter
            filters = AuthorFilters(name="Doe")

            # Get paginated results
            results, meta = await get_paginated_results(
                Author, page=1, per_page=10, filters=filters
            )

            # Verify results
            assert len(results) == 2
            assert meta.total == 2
            assert meta.page == 1

    @pytest.mark.asyncio
    async def test_pagination_with_legacy_dict_filter(self):
        """
        Test pagination with legacy dict filter (backward compatibility).

        Ensures that existing code using dict filters still works.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock data
        mock_authors = [create_author_fixture(id=1, name="John Doe")]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_authors

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "app.storage.db.async_session",
                MagicMock(return_value=mock_context_manager),
            ),
            patch(
                "app.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("app.storage.db.set_cached_count", AsyncMock()),
        ):
            # Use legacy dict filter
            filters = {"name": "John"}

            # Get paginated results
            results, meta = await get_paginated_results(
                Author, page=1, per_page=10, filters=filters
            )

            # Verify results
            assert len(results) == 1
            assert meta.total == 1

    @pytest.mark.asyncio
    async def test_pagination_with_empty_pydantic_filter(self):
        """
        Test pagination with empty Pydantic filter.

        Empty filters should return all results (no filters applied).
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        # Mock data
        mock_authors = [
            create_author_fixture(id=i, name=f"Author {i}")
            for i in range(1, 6)
        ]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 5

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_authors

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "app.storage.db.async_session",
                MagicMock(return_value=mock_context_manager),
            ),
            patch(
                "app.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("app.storage.db.set_cached_count", AsyncMock()),
        ):
            # Empty Pydantic filter
            filters = AuthorFilters()

            # Get paginated results
            results, meta = await get_paginated_results(
                Author, page=1, per_page=10, filters=filters
            )

            # Verify all results returned (no filters applied)
            assert len(results) == 5
            assert meta.total == 5

    @pytest.mark.asyncio
    async def test_pagination_filter_validation_prevents_invalid_keys(self):
        """
        Test that Pydantic filter prevents invalid keys at parse time.

        Invalid filter keys should raise ValidationError before query execution.
        """
        # Attempt to create filter with invalid key
        with pytest.raises(
            ValidationError, match="Extra inputs are not permitted"
        ):
            AuthorFilters(invalid_key="value")  # type: ignore[call-arg]


class TestCustomPydanticFilterWithoutToDict:
    """Test Pydantic filters that don't implement to_dict() method."""

    @pytest.mark.asyncio
    async def test_pagination_with_pydantic_model_without_to_dict(self):
        """
        Test fallback for Pydantic models without to_dict() method.

        Should use model_dump() and filter None values automatically.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from pydantic import BaseModel as PydanticBaseModel

        # Custom filter without to_dict() method
        class CustomFilter(PydanticBaseModel):
            name: str | None = None
            id: int | None = None

        # Mock data
        mock_authors = [create_author_fixture(id=1, name="John")]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_authors

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        with (
            patch(
                "app.storage.db.async_session",
                MagicMock(return_value=mock_context_manager),
            ),
            patch(
                "app.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("app.storage.db.set_cached_count", AsyncMock()),
        ):
            # Custom Pydantic filter
            filters = CustomFilter(name="John", id=None)

            # Get paginated results
            results, meta = await get_paginated_results(
                Author, page=1, per_page=10, filters=filters
            )

            # Verify results
            assert len(results) == 1
            assert meta.total == 1
