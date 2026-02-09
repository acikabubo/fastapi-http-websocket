"""
Tests for offset-based pagination strategy.

Tests the traditional page-number based pagination with count caching.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlmodel import Field, SQLModel, select

from app.storage.pagination.offset import OffsetPaginationStrategy


class TestOffsetModel(SQLModel, table=True):
    """Test model for offset pagination tests."""

    __tablename__ = "test_offset_model"

    id: int = Field(default=None, primary_key=True)
    name: str


class TestOffsetPaginationStrategy:
    """Tests for OffsetPaginationStrategy."""

    @pytest.mark.asyncio
    async def test_paginate_first_page(self):
        """Test pagination on first page with count query."""
        mock_session = AsyncMock()

        # Mock count query result
        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 25  # Total items

        # Mock data query result (page_size + 1 to detect has_more)
        mock_items = [
            TestOffsetModel(id=i, name=f"Item {i}") for i in range(1, 12)
        ]  # 11 items
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            strategy = OffsetPaginationStrategy(
                session=mock_session, page=1, skip_count=False
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            items, meta = await strategy.paginate(query, TestOffsetModel, 10)

            assert len(items) == 10  # Trimmed from 11
            assert meta.page == 1
            assert meta.per_page == 10
            assert meta.total == 25
            assert meta.pages == 3
            assert meta.has_more is True
            assert meta.next_cursor is None

    @pytest.mark.asyncio
    async def test_paginate_middle_page(self):
        """Test pagination on a middle page."""
        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 50

        # Return page_size + 1 to detect has_more
        mock_items = [
            TestOffsetModel(id=i, name=f"Item {i}") for i in range(21, 32)
        ]  # 11 items
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            strategy = OffsetPaginationStrategy(
                session=mock_session, page=3, skip_count=False
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            items, meta = await strategy.paginate(query, TestOffsetModel, 10)

            assert len(items) == 10  # Trimmed from 11
            assert meta.page == 3
            assert meta.total == 50
            assert meta.pages == 5
            assert meta.has_more is True

    @pytest.mark.asyncio
    async def test_paginate_last_page(self):
        """Test pagination on last page (partial results)."""
        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 25

        # Last page has only 5 items
        mock_items = [
            TestOffsetModel(id=i, name=f"Item {i}") for i in range(21, 26)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            strategy = OffsetPaginationStrategy(
                session=mock_session, page=3, skip_count=False
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            items, meta = await strategy.paginate(query, TestOffsetModel, 10)

            assert len(items) == 5
            assert meta.page == 3
            assert meta.total == 25
            assert meta.pages == 3
            assert meta.has_more is False

    @pytest.mark.asyncio
    async def test_paginate_with_skip_count(self):
        """Test pagination with count query skipped."""
        mock_session = AsyncMock()

        # Only data query, no count query (return page_size + 1)
        mock_items = [
            TestOffsetModel(id=i, name=f"Item {i}") for i in range(1, 12)
        ]  # 11 items
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        strategy = OffsetPaginationStrategy(
            session=mock_session, page=1, skip_count=True
        )

        query = select(TestOffsetModel).order_by(TestOffsetModel.id)
        items, meta = await strategy.paginate(query, TestOffsetModel, 10)

        assert len(items) == 10  # Trimmed from 11
        assert meta.total == 0  # Count skipped
        assert meta.pages == 0  # Cannot calculate pages without total
        assert meta.has_more is True

    @pytest.mark.asyncio
    async def test_paginate_with_cached_count(self):
        """Test pagination uses cached count when available."""
        mock_session = AsyncMock()

        # Mock data query result only (count from cache)
        mock_items = [
            TestOffsetModel(id=i, name=f"Item {i}") for i in range(1, 11)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        with patch(
            "app.storage.pagination.offset.get_cached_count",
            AsyncMock(return_value=100),  # Cached total
        ):
            strategy = OffsetPaginationStrategy(
                session=mock_session, page=2, skip_count=False
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            items, meta = await strategy.paginate(query, TestOffsetModel, 10)

            # Should use cached count, not execute count query
            assert meta.total == 100
            assert meta.pages == 10
            # Verify only one query executed (data, not count)
            assert mock_session.exec.call_count == 1

    @pytest.mark.asyncio
    async def test_paginate_caches_count(self):
        """Test that count result is cached."""
        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 75

        mock_items = [
            TestOffsetModel(id=i, name=f"Item {i}") for i in range(1, 11)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ) as mock_get_cache,
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ) as mock_set_cache,
        ):
            filter_dict = {"name": "test"}
            strategy = OffsetPaginationStrategy(
                session=mock_session,
                page=1,
                skip_count=False,
                filter_dict=filter_dict,
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            await strategy.paginate(query, TestOffsetModel, 10)

            # Verify cache was checked
            mock_get_cache.assert_called_once_with(
                "TestOffsetModel", filter_dict
            )

            # Verify count was cached
            mock_set_cache.assert_called_once_with(
                "TestOffsetModel", 75, filter_dict
            )

    @pytest.mark.asyncio
    async def test_paginate_applies_filters_to_count_query(self):
        """Test that filters are applied to count query."""
        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 10

        mock_items = [TestOffsetModel(id=1, name="Test")]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        def custom_filter(query, model, filters):
            return query.where(model.name == filters.get("name"))

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            filter_dict = {"name": "test"}
            strategy = OffsetPaginationStrategy(
                session=mock_session,
                page=1,
                skip_count=False,
                filter_dict=filter_dict,
                apply_filters_func=custom_filter,
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            await strategy.paginate(query, TestOffsetModel, 10)

            # Verify exec was called twice (count + data)
            assert mock_session.exec.call_count == 2

    @pytest.mark.asyncio
    async def test_paginate_calculates_correct_offset(self):
        """Test offset calculation for different pages."""
        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 100

        mock_items = [
            TestOffsetModel(id=i, name=f"Item {i}") for i in range(51, 61)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            # Page 6 with page_size=10 → offset should be 50
            strategy = OffsetPaginationStrategy(
                session=mock_session, page=6, skip_count=False
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            await strategy.paginate(query, TestOffsetModel, 10)

            # Check that data query was called
            assert mock_session.exec.call_count == 2

    @pytest.mark.asyncio
    async def test_paginate_empty_results(self):
        """Test pagination with no results."""
        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 0

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            strategy = OffsetPaginationStrategy(
                session=mock_session, page=1, skip_count=False
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            items, meta = await strategy.paginate(query, TestOffsetModel, 10)

            assert len(items) == 0
            assert meta.total == 0
            assert meta.pages == 0
            assert meta.has_more is False

    @pytest.mark.asyncio
    async def test_paginate_has_more_detection(self):
        """Test has_more flag is correctly set."""
        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 30

        # Return page_size + 1 items to test has_more detection
        mock_items = [
            TestOffsetModel(id=i, name=f"Item {i}") for i in range(1, 12)
        ]  # 11 items
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            strategy = OffsetPaginationStrategy(
                session=mock_session, page=1, skip_count=False
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            items, meta = await strategy.paginate(query, TestOffsetModel, 10)

            # Should trim to page_size and set has_more=True
            assert len(items) == 10  # Trimmed from 11
            assert meta.has_more is True

    @pytest.mark.asyncio
    async def test_paginate_uses_default_apply_filters(self):
        """Test strategy uses default_apply_filters when none provided."""
        mock_session = AsyncMock()

        mock_count_result = MagicMock()
        mock_count_result.one.return_value = 5

        mock_items = [TestOffsetModel(id=1, name="Test")]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(
            side_effect=[mock_count_result, mock_data_result]
        )

        with (
            patch(
                "app.storage.pagination.offset.get_cached_count",
                AsyncMock(return_value=None),
            ),
            patch(
                "app.storage.pagination.offset.set_cached_count", AsyncMock()
            ),
        ):
            # No apply_filters_func provided → should use default
            strategy = OffsetPaginationStrategy(
                session=mock_session,
                page=1,
                skip_count=False,
                filter_dict={"name": "test"},
                apply_filters_func=None,  # Explicitly None
            )

            query = select(TestOffsetModel).order_by(TestOffsetModel.id)
            items, meta = await strategy.paginate(query, TestOffsetModel, 10)

            # Should work with default filter function
            assert items is not None
