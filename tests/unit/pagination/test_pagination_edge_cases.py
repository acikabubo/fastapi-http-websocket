"""
Comprehensive edge case tests for pagination functionality.

This module tests critical edge cases in pagination including invalid page numbers,
per_page limits, empty result sets, and concurrent pagination operations.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.constants import MAX_PAGE_SIZE
from app.models.author import Author
from app.settings import app_settings
from app.storage.db import get_paginated_results

# Get default page size from settings
DEFAULT_PAGE_SIZE = app_settings.DEFAULT_PAGE_SIZE


class TestInvalidPageNumbers:
    """Test handling of invalid page number parameters."""

    @pytest.mark.asyncio
    async def test_page_zero(self):
        """
        Test that page=0 is rejected.

        Page numbers should start from 1, not 0.
        """
        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 10

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []

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
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            with pytest.raises(
                ValidationError, match="greater than or equal to 1"
            ):
                await get_paginated_results(Author, page=0, per_page=10)

    @pytest.mark.asyncio
    async def test_negative_page_number(self):
        """Test that negative page numbers are rejected."""
        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 10

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(return_value=mock_count_result)

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with (
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            with pytest.raises(
                ValidationError, match="greater than or equal to 1"
            ):
                await get_paginated_results(Author, page=-1, per_page=10)

    @pytest.mark.asyncio
    async def test_negative_per_page(self):
        """Test that negative per_page values are rejected."""
        with pytest.raises(ValueError, match="per_page must be >= 1"):
            await get_paginated_results(Author, page=1, per_page=-10)

    @pytest.mark.asyncio
    async def test_zero_per_page(self):
        """Test that per_page=0 is rejected."""
        with pytest.raises(ValueError, match="per_page must be >= 1"):
            await get_paginated_results(Author, page=1, per_page=0)

    @pytest.mark.asyncio
    async def test_very_large_page_number(self):
        """
        Test behavior with very large page numbers.

        Should return empty results, not error.
        """
        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 10  # Only 10 total items

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []  # No items on page 1000

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
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            results, meta = await get_paginated_results(
                Author, page=1000, per_page=10
            )

            # Should return empty results
            assert results == []
            assert meta.page == 1000


class TestPerPageLimits:
    """Test per_page size limit enforcement."""

    @pytest.mark.asyncio
    async def test_per_page_exceeds_max(self):
        """
        Test that per_page values exceeding MAX_PAGE_SIZE are clamped.

        Should automatically limit to MAX_PAGE_SIZE.
        """
        mock_authors = [Author(id=i, name=f"Author {i}") for i in range(100)]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 1000

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
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            results, meta = await get_paginated_results(
                Author,
                page=1,
                per_page=10000,  # Way over max
            )

            # Should be clamped to MAX_PAGE_SIZE
            assert meta.per_page == MAX_PAGE_SIZE
            assert len(results) <= MAX_PAGE_SIZE

    @pytest.mark.asyncio
    async def test_per_page_exactly_at_max(self):
        """Test per_page exactly at MAX_PAGE_SIZE limit."""
        mock_authors = [
            Author(id=i, name=f"Author {i}") for i in range(MAX_PAGE_SIZE)
        ]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 1000

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
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            results, meta = await get_paginated_results(
                Author, page=1, per_page=MAX_PAGE_SIZE
            )

            # Should be allowed
            assert meta.per_page == MAX_PAGE_SIZE
            assert len(results) == MAX_PAGE_SIZE

    @pytest.mark.asyncio
    async def test_per_page_default_value(self):
        """Test that default per_page is applied when not specified."""
        mock_authors = [Author(id=i, name=f"Author {i}") for i in range(20)]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 100

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
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            # Don't specify per_page
            results, meta = await get_paginated_results(Author, page=1)

            # Should use default
            assert meta.per_page == DEFAULT_PAGE_SIZE


class TestEmptyResultSets:
    """Test handling of empty result sets."""

    @pytest.mark.asyncio
    async def test_empty_table(self):
        """Test pagination on empty table (0 total items)."""
        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 0  # No items

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []

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
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            results, meta = await get_paginated_results(
                Author, page=1, per_page=10
            )

            assert results == []
            assert meta.total == 0
            assert meta.pages == 0
            assert meta.has_more is False

    @pytest.mark.asyncio
    async def test_filters_return_empty(self):
        """Test pagination when filters return no results."""
        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 0  # Filters match nothing

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []

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
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            results, meta = await get_paginated_results(
                Author, page=1, per_page=10, filters={"name": "nonexistent"}
            )

            assert results == []
            assert meta.total == 0

    @pytest.mark.asyncio
    async def test_last_page_partial_results(self):
        """
        Test last page with fewer items than per_page.

        Example: 25 total items, per_page=10, page=3 should return 5 items.
        """
        mock_authors = [Author(id=i, name=f"Author {i}") for i in range(5)]

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 25  # 25 total items

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = (
            mock_authors  # 5 items on last page
        )

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
            patch("app.storage.db.async_session", mock_session_maker),
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            results, meta = await get_paginated_results(
                Author, page=3, per_page=10
            )

            assert len(results) == 5
            assert meta.page == 3
            assert meta.total == 25
            assert meta.pages == 3
            assert meta.has_more is False


class TestCursorPagination:
    """Test cursor-based pagination edge cases."""

    @pytest.mark.asyncio
    async def test_empty_cursor_first_page(self):
        """Test cursor pagination with empty cursor (first page)."""
        mock_authors = [Author(id=i, name=f"Author {i}") for i in range(21)]

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

        with patch("app.storage.db.async_session", mock_session_maker):
            results, meta = await get_paginated_results(
                Author, per_page=20, cursor=""
            )

            # Should return first 20 items
            assert len(results) == 20
            assert meta.has_more is True
            assert meta.next_cursor is not None

    @pytest.mark.asyncio
    async def test_invalid_cursor_format(self):
        """Test handling of malformed cursor values."""
        mock_authors = [Author(id=i, name=f"Author {i}") for i in range(20)]

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

        with patch("app.storage.db.async_session", mock_session_maker):
            # Invalid base64 cursor
            with pytest.raises(ValueError):
                await get_paginated_results(
                    Author, per_page=20, cursor="not-valid-base64!!!"
                )

    @pytest.mark.asyncio
    async def test_cursor_no_more_results(self):
        """Test cursor pagination when no more results exist."""
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []  # No more results

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = AsyncMock(return_value=mock_data_result)

        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(
            return_value=mock_session_inst
        )
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)

        mock_session_maker = MagicMock(return_value=mock_context_manager)

        with patch("app.storage.db.async_session", mock_session_maker):
            # Valid cursor but no more results
            import base64

            cursor = base64.b64encode(b"999").decode()
            results, meta = await get_paginated_results(
                Author, per_page=20, cursor=cursor
            )

            assert results == []
            assert meta.has_more is False
            assert meta.next_cursor is None


class TestConcurrentPaginationQueries:
    """Test concurrent pagination operations."""

    @pytest.mark.asyncio
    async def test_concurrent_page_requests(self):
        """
        Test that pagination function can handle rapid sequential requests.

        NOTE: True concurrent testing requires actual database and connection pool.
        This test verifies basic sequential access pattern works correctly.
        """
        from tests.conftest import create_author_fixture

        mock_authors_page1 = [
            create_author_fixture(id=i, name=f"Author {i}")
            for i in range(1, 11)
        ]
        mock_authors_page2 = [
            create_author_fixture(id=i, name=f"Author {i}")
            for i in range(11, 21)
        ]

        call_count = [0]

        async def mock_exec(stmt):
            """Mock session.exec for count and data queries."""
            result = MagicMock()

            # Determine if this is a count query or data query
            stmt_str = str(stmt)
            if "COUNT" in stmt_str:
                result.one.return_value = 20
            else:
                # Data query - alternate between page 1 and page 2
                call_count[0] += 1
                result.all.return_value = (
                    mock_authors_page1
                    if call_count[0] % 2 == 1
                    else mock_authors_page2
                )
            return result

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = mock_exec

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
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=20),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            # Sequential requests (simpler than true concurrency)
            results1, meta1 = await get_paginated_results(
                Author, page=1, per_page=10
            )
            results2, meta2 = await get_paginated_results(
                Author, page=2, per_page=10
            )

            # Both requests should succeed
            assert len(results1) == 10
            assert len(results2) == 10
            assert meta1.page == 1
            assert meta2.page == 2

    @pytest.mark.asyncio
    async def test_data_changes_between_pages(self):
        """
        Test that pagination handles changing data gracefully.

        NOTE: This is a known limitation of offset-based pagination - data changes
        between page requests can cause duplicates or gaps. Cursor-based pagination
        handles this better. This test verifies the function doesn't crash.
        """
        from tests.conftest import create_author_fixture

        # Mock data that changes between calls
        mock_authors_page1 = [
            create_author_fixture(id=i, name=f"Author {i}")
            for i in range(1, 21)
        ]
        mock_authors_page2 = [
            create_author_fixture(id=i, name=f"Author {i}")
            for i in range(11, 31)
        ]

        call_count = [0]

        async def mock_exec(stmt):
            """Mock session.exec for count and data queries."""
            result = MagicMock()

            # Determine if this is a count query or data query
            stmt_str = str(stmt)
            if "COUNT" in stmt_str:
                result.one.return_value = 30
            else:
                # Data query - return different results for page 1 and page 2
                call_count[0] += 1
                result.all.return_value = (
                    mock_authors_page1
                    if call_count[0] == 1
                    else mock_authors_page2
                )
            return result

        mock_session_inst = AsyncMock()
        mock_session_inst.exec = mock_exec

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
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=30),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            # Page 1
            results1, meta1 = await get_paginated_results(
                Author, page=1, per_page=20
            )

            # Page 2 (data may have shifted due to concurrent inserts)
            results2, meta2 = await get_paginated_results(
                Author, page=2, per_page=20
            )

            # Both requests should succeed despite data changes
            # (offset pagination may have duplicates/gaps, but doesn't crash)
            assert len(results1) == 20
            assert len(results2) == 20
            assert meta1.page == 1
            assert meta2.page == 2
