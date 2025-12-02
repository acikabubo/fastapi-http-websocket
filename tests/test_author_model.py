"""
Tests for Author model database operations.

This module tests the Author model's create and get_list methods with
database session handling and error scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.author import Author


@pytest.fixture
def mock_session():
    """
    Provides a mock AsyncSession for testing.

    Returns:
        AsyncMock: Mocked database session
    """
    session = AsyncMock(spec=AsyncSession)
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.rollback = AsyncMock()
    session.exec = AsyncMock()
    return session


class TestAuthorCreate:
    """Tests for Author.create method."""

    @pytest.mark.asyncio
    async def test_create_author_success(self, mock_session):
        """
        Test successful author creation.

        Args:
            mock_session: Mocked database session
        """
        author = Author(name="Test Author")

        result = await Author.create(mock_session, author)

        assert result == author
        mock_session.add.assert_called_once_with(author)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(author)
        mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_author_integrity_error(self, mock_session):
        """
        Test author creation with IntegrityError.

        Args:
            mock_session: Mocked database session
        """
        author = Author(name="Duplicate Author")
        mock_session.flush.side_effect = IntegrityError(
            "duplicate key", {}, None
        )

        with pytest.raises(IntegrityError):
            await Author.create(mock_session, author)

        mock_session.add.assert_called_once_with(author)
        mock_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_author_sqlalchemy_error(self, mock_session):
        """
        Test author creation with SQLAlchemyError.

        Args:
            mock_session: Mocked database session
        """
        author = Author(name="Error Author")
        mock_session.flush.side_effect = SQLAlchemyError("Database error")

        with pytest.raises(SQLAlchemyError):
            await Author.create(mock_session, author)

        mock_session.add.assert_called_once_with(author)
        mock_session.rollback.assert_called_once()


class TestAuthorGetList:
    """Tests for Author.get_list method."""

    @pytest.mark.asyncio
    async def test_get_list_no_filters(self, mock_session):
        """
        Test get_list with no filters.

        Args:
            mock_session: Mocked database session
        """
        expected_authors = [
            Author(id=1, name="Author 1"),
            Author(id=2, name="Author 2"),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = expected_authors

        async def mock_exec(*args):
            return mock_result

        mock_session.exec = mock_exec

        result = await Author.get_list(mock_session)

        assert result == expected_authors

    @pytest.mark.asyncio
    async def test_get_list_with_filters(self, mock_session):
        """
        Test get_list with filters.

        Args:
            mock_session: Mocked database session
        """
        expected_authors = [Author(id=1, name="Specific Author")]

        mock_result = MagicMock()
        mock_result.all.return_value = expected_authors

        async def mock_exec(*args):
            return mock_result

        mock_session.exec = mock_exec

        result = await Author.get_list(mock_session, name="Specific Author")

        assert result == expected_authors

    @pytest.mark.asyncio
    async def test_get_list_empty_result(self, mock_session):
        """
        Test get_list returning empty list.

        Args:
            mock_session: Mocked database session
        """
        mock_result = MagicMock()
        mock_result.all.return_value = []

        async def mock_exec(*args):
            return mock_result

        mock_session.exec = mock_exec

        result = await Author.get_list(mock_session)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_list_sqlalchemy_error(self, mock_session):
        """
        Test get_list with SQLAlchemyError.

        Args:
            mock_session: Mocked database session
        """

        async def mock_exec(*args):
            raise SQLAlchemyError("Database error")

        mock_session.exec = mock_exec

        with pytest.raises(SQLAlchemyError):
            await Author.get_list(mock_session)

    @pytest.mark.asyncio
    async def test_get_list_multiple_filters(self, mock_session):
        """
        Test get_list with multiple filter conditions.

        Args:
            mock_session: Mocked database session
        """
        expected_authors = [Author(id=5, name="Multi Filter Author")]

        mock_result = MagicMock()
        mock_result.all.return_value = expected_authors

        async def mock_exec(*args):
            return mock_result

        mock_session.exec = mock_exec

        result = await Author.get_list(
            mock_session, id=5, name="Multi Filter Author"
        )

        assert result == expected_authors
