"""
Tests for cursor-based pagination strategy.

Tests the stable, high-performance cursor pagination using item IDs.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlmodel import Field, SQLModel, select

from app.storage.db import encode_cursor
from app.storage.pagination.cursor import CursorPaginationStrategy


class TestCursorModel(SQLModel, table=True):
    """Test model for cursor pagination tests."""

    __tablename__ = "test_cursor_model"

    id: int = Field(default=None, primary_key=True)
    name: str


class TestCursorPaginationStrategy:
    """Tests for CursorPaginationStrategy."""

    @pytest.mark.asyncio
    async def test_paginate_first_page(self):
        """Test cursor pagination on first page (no cursor)."""
        mock_session = AsyncMock()

        # Return page_size items (no more results)
        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(1, 11)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        strategy = CursorPaginationStrategy(session=mock_session, cursor=None)

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        assert len(items) == 10
        assert meta.page == 1  # Always 1 for cursor pagination
        assert meta.per_page == 10
        assert meta.total == 0  # Count skipped for cursor pagination
        assert meta.pages == 0  # Not applicable
        assert meta.has_more is False
        assert meta.next_cursor is None

    @pytest.mark.asyncio
    async def test_paginate_first_page_with_more_results(self):
        """Test first page when more results exist."""
        mock_session = AsyncMock()

        # Return page_size + 1 items to indicate more results
        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(1, 12)
        ]  # 11 items
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        strategy = CursorPaginationStrategy(session=mock_session, cursor=None)

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        assert len(items) == 10  # Trimmed from 11
        assert meta.has_more is True
        assert meta.next_cursor is not None
        assert meta.next_cursor == encode_cursor(10)  # Cursor from last item

    @pytest.mark.asyncio
    async def test_paginate_with_cursor(self):
        """Test pagination with cursor (subsequent page)."""
        mock_session = AsyncMock()

        # Items after cursor (id > 10)
        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(11, 21)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        cursor = encode_cursor(10)  # Last item from previous page
        strategy = CursorPaginationStrategy(
            session=mock_session, cursor=cursor
        )

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        assert len(items) == 10
        assert items[0].id == 11  # First item after cursor
        assert meta.has_more is False
        assert meta.next_cursor is None

    @pytest.mark.asyncio
    async def test_paginate_cursor_with_more_results(self):
        """Test cursor pagination with more results available."""
        mock_session = AsyncMock()

        # Return page_size + 1 items after cursor
        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(21, 32)
        ]  # 11 items
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        cursor = encode_cursor(20)
        strategy = CursorPaginationStrategy(
            session=mock_session, cursor=cursor
        )

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        assert len(items) == 10  # Trimmed from 11
        assert items[0].id == 21
        assert items[-1].id == 30
        assert meta.has_more is True
        assert meta.next_cursor == encode_cursor(30)

    @pytest.mark.asyncio
    async def test_paginate_cursor_empty_results(self):
        """Test cursor pagination with no results after cursor."""
        mock_session = AsyncMock()

        mock_data_result = MagicMock()
        mock_data_result.all.return_value = []

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        cursor = encode_cursor(100)  # Beyond all items
        strategy = CursorPaginationStrategy(
            session=mock_session, cursor=cursor
        )

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        assert len(items) == 0
        assert meta.has_more is False
        assert meta.next_cursor is None

    @pytest.mark.asyncio
    async def test_paginate_cursor_decoding(self):
        """Test that cursor is properly decoded to last_id."""
        mock_session = AsyncMock()

        mock_items = [TestCursorModel(id=26, name="Item 26")]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        cursor = encode_cursor(25)  # Base64 encoded "25"
        strategy = CursorPaginationStrategy(
            session=mock_session, cursor=cursor
        )

        assert strategy.last_id == 25  # Decoded from cursor

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        # Should query items where id > 25
        assert items[0].id == 26

    def test_invalid_cursor_raises_error(self):
        """Test that invalid cursor raises ValueError."""
        mock_session = AsyncMock()

        with pytest.raises(ValueError, match="Invalid cursor format"):
            CursorPaginationStrategy(
                session=mock_session, cursor="invalid_base64!!!"
            )

    @pytest.mark.asyncio
    async def test_paginate_always_returns_count_zero(self):
        """Test that cursor pagination always returns total=0."""
        mock_session = AsyncMock()

        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(1, 6)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        strategy = CursorPaginationStrategy(session=mock_session, cursor=None)

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        # Count is always skipped for performance
        assert meta.total == 0
        assert meta.pages == 0

    @pytest.mark.asyncio
    async def test_paginate_applies_where_clause_with_cursor(self):
        """Test that WHERE id > last_id is applied when cursor provided."""
        mock_session = AsyncMock()

        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(51, 61)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        cursor = encode_cursor(50)
        strategy = CursorPaginationStrategy(
            session=mock_session, cursor=cursor
        )

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        # Verify query was executed
        mock_session.exec.assert_called_once()
        # Items should start from id > 50
        assert all(item.id > 50 for item in items)

    @pytest.mark.asyncio
    async def test_paginate_partial_last_page(self):
        """Test cursor pagination with partial results on last page."""
        mock_session = AsyncMock()

        # Only 3 items remaining
        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(98, 101)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        cursor = encode_cursor(97)
        strategy = CursorPaginationStrategy(
            session=mock_session, cursor=cursor
        )

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        assert len(items) == 3  # Less than page_size
        assert meta.has_more is False
        assert meta.next_cursor is None

    @pytest.mark.asyncio
    async def test_paginate_next_cursor_uses_last_item_id(self):
        """Test that next_cursor is generated from last item's ID."""
        mock_session = AsyncMock()

        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(11, 22)
        ]  # 11 items
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        strategy = CursorPaginationStrategy(session=mock_session, cursor=None)

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        # Last item in trimmed results is id=20
        assert items[-1].id == 20
        # Next cursor should encode this ID
        assert meta.next_cursor == encode_cursor(20)

    @pytest.mark.asyncio
    async def test_paginate_no_cursor_on_exact_page_size(self):
        """Test no next_cursor when exactly page_size items returned."""
        mock_session = AsyncMock()

        # Exactly page_size items (no +1)
        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(1, 11)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        strategy = CursorPaginationStrategy(session=mock_session, cursor=None)

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        assert len(items) == 10
        assert meta.has_more is False
        assert meta.next_cursor is None  # No more results

    @pytest.mark.asyncio
    async def test_paginate_metadata_structure(self):
        """Test metadata structure matches expected format."""
        mock_session = AsyncMock()

        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(1, 12)
        ]
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        strategy = CursorPaginationStrategy(session=mock_session, cursor=None)

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 10)

        # Verify all metadata fields exist
        assert hasattr(meta, "page")
        assert hasattr(meta, "per_page")
        assert hasattr(meta, "total")
        assert hasattr(meta, "pages")
        assert hasattr(meta, "has_more")
        assert hasattr(meta, "next_cursor")

        # Verify cursor-specific values
        assert meta.page == 1
        assert meta.per_page == 10
        assert meta.total == 0
        assert meta.pages == 0
        assert isinstance(meta.has_more, bool)
        assert meta.next_cursor is None or isinstance(meta.next_cursor, str)

    @pytest.mark.asyncio
    async def test_paginate_limit_includes_extra_item(self):
        """Test that query limit is page_size + 1 for has_more detection."""
        mock_session = AsyncMock()

        # Return exactly page_size + 1 items
        mock_items = [
            TestCursorModel(id=i, name=f"Item {i}") for i in range(1, 22)
        ]  # 21 items
        mock_data_result = MagicMock()
        mock_data_result.all.return_value = mock_items

        mock_session.exec = AsyncMock(return_value=mock_data_result)

        strategy = CursorPaginationStrategy(session=mock_session, cursor=None)

        query = select(TestCursorModel).order_by(TestCursorModel.id)
        items, meta = await strategy.paginate(query, TestCursorModel, 20)

        # Should trim to page_size
        assert len(items) == 20  # Trimmed from 21
        assert meta.has_more is True
        assert meta.next_cursor is not None
