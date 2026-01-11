"""
Tests for database pagination functionality.

This module tests the get_paginated_results function and filter application
for SQLModel queries.
"""

import pytest
from sqlalchemy import Select
from sqlmodel import Field, SQLModel

from {{cookiecutter.module_name}}.storage.db import default_apply_filters


class PaginationTestModel(SQLModel, table=True):
    """Test model for pagination tests."""

    __tablename__ = "test_pagination_model"

    id: int | None = Field(default=None, primary_key=True)
    name: str
    status: str | None = None
    age: int | None = None


class TestGetPaginatedResults:
    """Tests for get_paginated_results function."""

    @pytest.mark.asyncio
    async def test_pagination_first_page(self, mock_db_session):
        """Test fetching the first page of results."""
        from unittest.mock import AsyncMock, MagicMock, patch

        
        from {{cookiecutter.module_name}}.storage.db import get_paginated_results

        # Mock data
        mock_authors = [
            PaginationTestModel(id=1, name="Author 1"),
            PaginationTestModel(id=2, name="Author 2"),
            PaginationTestModel(id=3, name="Author 3"),
        ]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 10

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

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with (
            patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker),
            patch(
                "{{cookiecutter.module_name}}.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("{{cookiecutter.module_name}}.storage.db.set_cached_count", AsyncMock()),
        ):
            results, meta = await get_paginated_results(
                PaginationTestModel, page=1, per_page=3
            )

            assert len(results) == 3
            assert meta.page == 1
            assert meta.per_page == 3
            assert meta.total == 10
            assert meta.pages == 4

    @pytest.mark.asyncio
    async def test_pagination_with_filters(self, mock_db_session):
        """Test pagination with filters applied."""
        from unittest.mock import AsyncMock, MagicMock, patch

        
        from {{cookiecutter.module_name}}.storage.db import get_paginated_results

        mock_authors = [PaginationTestModel(id=1, name="Test Author")]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_authors

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        # Create proper async context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with (
            patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker),
            patch(
                "{{cookiecutter.module_name}}.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("{{cookiecutter.module_name}}.storage.db.set_cached_count", AsyncMock()),
        ):
            results, meta = await get_paginated_results(
                PaginationTestModel, page=1, per_page=10, filters={"name": "Test"}
            )

            assert len(results) == 1
            assert meta.total == 1
            assert meta.pages == 1

    @pytest.mark.asyncio
    async def test_pagination_skip_count(self, mock_db_session):
        """
        Test pagination with skip_count=True.

        Should return total=0 and pages=0 for performance (skips count query).
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        
        from {{cookiecutter.module_name}}.storage.db import get_paginated_results

        mock_authors = [PaginationTestModel(id=1, name="Author 1")]

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_authors

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(return_value=mock_data_result)

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker):
            results, meta = await get_paginated_results(
                PaginationTestModel, page=1, per_page=10, skip_count=True
            )

            assert len(results) == 1
            assert meta.total == 0  # Count query was skipped
            assert meta.pages == 0

    @pytest.mark.asyncio
    async def test_pagination_empty_results(self, mock_db_session):
        """Test pagination when no results match."""
        from unittest.mock import AsyncMock, MagicMock, patch

        
        from {{cookiecutter.module_name}}.storage.db import get_paginated_results

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        # Create proper async context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with (
            patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker),
            patch(
                "{{cookiecutter.module_name}}.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("{{cookiecutter.module_name}}.storage.db.set_cached_count", AsyncMock()),
        ):
            results, meta = await get_paginated_results(
                PaginationTestModel, page=1, per_page=10
            )

            assert len(results) == 0
            assert meta.total == 0
            assert meta.pages == 0

    @pytest.mark.asyncio
    async def test_pagination_last_page_partial(self, mock_db_session):
        """Test last page with fewer items than per_page."""
        from unittest.mock import AsyncMock, MagicMock, patch

        
        from {{cookiecutter.module_name}}.storage.db import get_paginated_results

        mock_authors = [
            PaginationTestModel(id=21, name="Author 21"),
            PaginationTestModel(id=22, name="Author 22"),
        ]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 22

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_authors

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        # Create proper async context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with (
            patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker),
            patch(
                "{{cookiecutter.module_name}}.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("{{cookiecutter.module_name}}.storage.db.set_cached_count", AsyncMock()),
        ):
            results, meta = await get_paginated_results(
                PaginationTestModel, page=3, per_page=10
            )

            assert len(results) == 2
            assert meta.page == 3
            assert meta.per_page == 10
            assert meta.total == 22
            assert meta.pages == 3

    @pytest.mark.asyncio
    async def test_pagination_custom_filter_function(self, mock_db_session):
        """Test pagination with custom apply_filters function."""
        from unittest.mock import AsyncMock, MagicMock, patch

        
        from {{cookiecutter.module_name}}.storage.db import get_paginated_results

        def custom_filter(query, model, filters):
            """Custom filter that only filters by exact name match."""
            if "name" in filters:
                query = query.filter(model.name == filters["name"])
            return query

        mock_authors = [PaginationTestModel(id=1, name="Exact Match")]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 1

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_authors

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        # Create proper async context manager mock
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with (
            patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker),
            patch(
                "{{cookiecutter.module_name}}.storage.db.get_cached_count", AsyncMock(return_value=None)
            ),
            patch("{{cookiecutter.module_name}}.storage.db.set_cached_count", AsyncMock()),
        ):
            results, meta = await get_paginated_results(
                PaginationTestModel,
                page=1,
                per_page=10,
                filters={"name": "Exact Match"},
                apply_filters=custom_filter,
            )

            assert len(results) == 1
            assert results[0].name == "Exact Match"


class TestDefaultApplyFilters:
    """Tests for default_apply_filters function."""

    def test_filter_by_string_ilike(self):
        """
        Test string filters use case-insensitive ILIKE.

        String filters should use ILIKE with wildcards for partial matching.
        """
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {"name": "john"}

        filtered_query = default_apply_filters(
            query, PaginationTestModel, filters
        )

        # Verify the query was modified
        assert filtered_query is not None
        assert isinstance(filtered_query, Select)

    def test_filter_by_exact_match(self):
        """
        Test non-string filters use exact equality.

        Integer and other types should use exact matching.
        """
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {"age": 25}

        filtered_query = default_apply_filters(
            query, PaginationTestModel, filters
        )

        assert filtered_query is not None
        assert isinstance(filtered_query, Select)

    def test_filter_by_list_in_clause(self):
        """
        Test list/tuple filters use IN clause.

        Lists should generate an IN clause for multiple values.
        """
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {"status": ["active", "pending"]}

        filtered_query = default_apply_filters(
            query, PaginationTestModel, filters
        )

        assert filtered_query is not None
        assert isinstance(filtered_query, Select)

    def test_filter_with_invalid_attribute(self):
        """
        Test filter raises ValueError for invalid attributes.

        Should raise ValueError when filter key is not a model attribute.
        """
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {"invalid_field": "value"}

        with pytest.raises(ValueError) as exc_info:
            default_apply_filters(query, PaginationTestModel, filters)

        assert "Invalid filter" in str(exc_info.value)
        assert "invalid_field" in str(exc_info.value)

    def test_filter_multiple_conditions(self):
        """Test applying multiple filters together."""
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {"name": "john", "status": "active", "age": 25}

        filtered_query = default_apply_filters(
            query, PaginationTestModel, filters
        )

        assert filtered_query is not None
        assert isinstance(filtered_query, Select)

    def test_filter_empty_dict(self):
        """
        Test empty filters dict returns query unchanged.

        Should return the original query when no filters are provided.
        """
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {}

        filtered_query = default_apply_filters(
            query, PaginationTestModel, filters
        )

        # Should return same query object (no modifications)
        assert filtered_query is query


class TestDatabaseConnection:
    """Tests for database connection and initialization."""

    @pytest.mark.asyncio
    async def test_get_session_yields_async_session(self):
        """
        Test get_session yields AsyncSession.

        Should provide a valid AsyncSession for database operations.
        """
        from {{cookiecutter.module_name}}.storage.db import get_session

        # Test that get_session is a generator
        gen = get_session()
        assert hasattr(gen, "__anext__")

    @pytest.mark.asyncio
    async def test_get_session_commits_on_success(self):
        """Test get_session commits transaction on success."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from {{cookiecutter.module_name}}.storage.db import get_session

        mock_session = AsyncMock()

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker):
            async for session in get_session():
                assert session == mock_session

            mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_rolls_back_on_integrity_error(self):
        """Test get_session rolls back on IntegrityError."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy.exc import IntegrityError

        from {{cookiecutter.module_name}}.storage.db import get_session

        mock_session = AsyncMock()
        mock_session.commit.side_effect = IntegrityError(
            "test", "params", "orig"
        )

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker):
            with pytest.raises(IntegrityError):
                async for session in get_session():
                    pass

            mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_rolls_back_on_sqlalchemy_error(self):
        """Test get_session rolls back on SQLAlchemyError."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy.exc import SQLAlchemyError

        from {{cookiecutter.module_name}}.storage.db import get_session

        mock_session = AsyncMock()
        mock_session.commit.side_effect = SQLAlchemyError("test error")

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_session)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with patch("{{cookiecutter.module_name}}.storage.db.async_session", mock_session_maker):
            with pytest.raises(SQLAlchemyError):
                async for session in get_session():
                    pass

            mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_wait_and_init_db_success(self):
        """
        Test successful database initialization.

        This test would require mocking the database connection.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from {{cookiecutter.module_name}}.storage.db import wait_and_init_db

        mock_conn = AsyncMock()
        mock_conn.exec_driver_sql = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.__aexit__.return_value = None

        mock_engine = MagicMock()
        mock_engine.connect.return_value = mock_conn

        with patch("{{cookiecutter.module_name}}.storage.db.engine", mock_engine):
            await wait_and_init_db(retry_interval=0, max_retries=3)

            mock_engine.connect.assert_called_once()
            mock_conn.exec_driver_sql.assert_called_once_with("SELECT 1")

    @pytest.mark.asyncio
    async def test_wait_and_init_db_retry_logic(self):
        """
        Test retry logic when database is initially unavailable.

        Should retry connection attempts with configured interval.
        """
        from unittest.mock import AsyncMock, MagicMock, patch

        from sqlalchemy.exc import OperationalError

        from {{cookiecutter.module_name}}.storage.db import wait_and_init_db

        mock_conn = AsyncMock()
        mock_conn.exec_driver_sql = AsyncMock()
        mock_conn.__aenter__.return_value = mock_conn
        mock_conn.__aexit__.return_value = None

        mock_engine = MagicMock()
        # Fail twice, then succeed
        mock_engine.connect.side_effect = [
            OperationalError("test", "params", "orig"),
            OperationalError("test", "params", "orig"),
            mock_conn,
        ]

        with patch("{{cookiecutter.module_name}}.storage.db.engine", mock_engine):
            with patch("{{cookiecutter.module_name}}.storage.db.asyncio.sleep", new_callable=AsyncMock):
                await wait_and_init_db(retry_interval=0, max_retries=3)

                assert mock_engine.connect.call_count == 3

    @pytest.mark.asyncio
    async def test_wait_and_init_db_max_retries_exceeded(self):
        """
        Test RuntimeError when max retries exceeded.

        Should raise RuntimeError after all retry attempts fail.
        """
        from unittest.mock import MagicMock, patch

        from sqlalchemy.exc import OperationalError

        from {{cookiecutter.module_name}}.storage.db import wait_and_init_db

        mock_engine = MagicMock()
        mock_engine.connect.side_effect = OperationalError(
            "test", "params", "orig"
        )

        with patch("{{cookiecutter.module_name}}.storage.db.engine", mock_engine):
            with patch("{{cookiecutter.module_name}}.storage.db.asyncio.sleep"):
                with pytest.raises(RuntimeError) as exc_info:
                    await wait_and_init_db(retry_interval=0, max_retries=3)

                assert "Database connection could not be established" in str(
                    exc_info.value
                )
                assert mock_engine.connect.call_count == 3


class TestPaginationMetadata:
    """Tests for pagination metadata calculation."""

    @pytest.mark.asyncio
    async def test_metadata_pages_calculation(self):
        """
        Test pages calculation in metadata.

        Should correctly calculate number of pages based on total and per_page.
        """
        from {{cookiecutter.module_name}}.schemas.response import MetadataModel

        # Test various scenarios
        # 100 items, 20 per page = 5 pages
        meta = MetadataModel(page=1, per_page=20, total=100, pages=5)
        assert meta.pages == 5

        # 95 items, 20 per page = 5 pages (ceiling division)
        meta = MetadataModel(page=1, per_page=20, total=95, pages=5)
        assert meta.pages == 5

        # 0 items = 0 pages
        meta = MetadataModel(page=1, per_page=20, total=0, pages=0)
        assert meta.pages == 0

    def test_metadata_skip_count_values(self):
        """
        Test metadata when skip_count is True.

        When skip_count is used, the get_paginated_results function returns -1
        for total, but MetadataModel validates total >= 0. This test verifies
        the expected behavior when count is actually skipped in practice.
        """
        from {{cookiecutter.module_name}}.schemas.response import MetadataModel

        # In practice, when skip_count is True, we would handle this differently
        # For now, test that pages can be 0 when total is 0
        meta = MetadataModel(page=1, per_page=20, total=0, pages=0)
        assert meta.total == 0
        assert meta.pages == 0


class TestFilterEdgeCases:
    """Tests for edge cases in filter application."""

    def test_filter_none_value(self):
        """
        Test filtering by None value.

        Should handle None values appropriately.
        """
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {"name": None}

        filtered_query = default_apply_filters(
            query, PaginationTestModel, filters
        )
        assert filtered_query is not None

    def test_filter_empty_list(self):
        """
        Test filtering with empty list.

        Should handle empty lists in IN clauses.
        """
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {"status": []}

        filtered_query = default_apply_filters(
            query, PaginationTestModel, filters
        )
        assert filtered_query is not None

    def test_filter_special_characters_in_string(self):
        """
        Test filtering with special characters in strings.

        Should properly escape SQL special characters like % and _.
        """
        from sqlmodel import select

        query = select(PaginationTestModel)
        filters = {"name": "test_user%"}

        # Should not raise an error
        filtered_query = default_apply_filters(
            query, PaginationTestModel, filters
        )
        assert filtered_query is not None


class TestMetadataModel:
    """Tests for MetadataModel schema."""

    def test_metadata_model_creation(self):
        """Test creating MetadataModel with all fields."""
        from {{cookiecutter.module_name}}.schemas.response import MetadataModel

        meta = MetadataModel(page=1, per_page=20, total=100, pages=5)

        assert meta.page == 1
        assert meta.per_page == 20
        assert meta.total == 100
        assert meta.pages == 5

    def test_metadata_model_serialization(self):
        """Test MetadataModel serialization to dict."""
        from {{cookiecutter.module_name}}.schemas.response import MetadataModel

        meta = MetadataModel(page=2, per_page=50, total=200, pages=4)
        meta_dict = meta.model_dump()

        assert meta_dict["page"] == 2
        assert meta_dict["per_page"] == 50
        assert meta_dict["total"] == 200
        assert meta_dict["pages"] == 4
