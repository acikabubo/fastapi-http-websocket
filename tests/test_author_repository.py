"""
Tests for AuthorRepository.

These tests verify that the repository correctly interacts with the
database session and provides the expected CRUD operations using mocks.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlmodel.ext.asyncio.session import AsyncSession

from app.models.author import Author
from app.repositories.author_repository import AuthorRepository


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
    session.get = AsyncMock()
    session.delete = AsyncMock()
    return session


class TestAuthorRepositoryCreate:
    """Tests for repository create operations."""

    @pytest.mark.asyncio
    async def test_create_author(self, mock_session):
        """Test creating an author."""
        repo = AuthorRepository(mock_session)
        author = Author(name="Test Author")

        created = await repo.create(author)

        assert created == author
        mock_session.add.assert_called_once_with(author)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(author)

    @pytest.mark.asyncio
    async def test_create_multiple_authors(self, mock_session):
        """Test creating multiple authors."""
        repo = AuthorRepository(mock_session)

        author1 = await repo.create(Author(name="Author 1"))
        author2 = await repo.create(Author(name="Author 2"))

        assert author1.name == "Author 1"
        assert author2.name == "Author 2"
        assert mock_session.add.call_count == 2
        assert mock_session.flush.call_count == 2


class TestAuthorRepositoryRead:
    """Tests for repository read operations."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, mock_session):
        """Test getting author by ID when exists."""
        repo = AuthorRepository(mock_session)
        expected_author = Author(id=1, name="Test Author")
        mock_session.get.return_value = expected_author

        found = await repo.get_by_id(1)

        assert found == expected_author
        mock_session.get.assert_called_once_with(Author, 1)

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, mock_session):
        """Test getting author by ID when doesn't exist."""
        repo = AuthorRepository(mock_session)
        mock_session.get.return_value = None

        found = await repo.get_by_id(99999)

        assert found is None
        mock_session.get.assert_called_once_with(Author, 99999)

    @pytest.mark.asyncio
    async def test_get_all_multiple(self, mock_session):
        """Test getting all authors."""
        repo = AuthorRepository(mock_session)
        expected_authors = [
            Author(id=1, name="Author 1"),
            Author(id=2, name="Author 2"),
        ]

        # Mock the exec result
        mock_result = MagicMock()
        mock_result.all.return_value = expected_authors
        mock_session.exec.return_value = mock_result

        authors = await repo.get_all()

        assert len(authors) == 2
        assert authors == expected_authors
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_with_filter(self, mock_session):
        """Test getting authors with filter."""
        repo = AuthorRepository(mock_session)
        expected_author = [Author(id=1, name="John Doe")]

        mock_result = MagicMock()
        mock_result.all.return_value = expected_author
        mock_session.exec.return_value = mock_result

        authors = await repo.get_all(name="John Doe")

        assert len(authors) == 1
        assert authors[0].name == "John Doe"
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, mock_session):
        """Test get_by_name when author exists."""
        repo = AuthorRepository(mock_session)
        expected_author = Author(id=1, name="John Doe")

        mock_result = MagicMock()
        mock_result.first.return_value = expected_author
        mock_session.exec.return_value = mock_result

        found = await repo.get_by_name("John Doe")

        assert found == expected_author
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, mock_session):
        """Test get_by_name when author doesn't exist."""
        repo = AuthorRepository(mock_session)

        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.exec.return_value = mock_result

        found = await repo.get_by_name("Nonexistent Author")

        assert found is None
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_search_by_name(self, mock_session):
        """Test searching authors by name pattern."""
        repo = AuthorRepository(mock_session)
        expected_authors = [
            Author(id=1, name="John Doe"),
            Author(id=2, name="John Smith"),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = expected_authors
        mock_session.exec.return_value = mock_result

        results = await repo.search_by_name("John")

        assert len(results) == 2
        names = [a.name for a in results]
        assert "John Doe" in names
        assert "John Smith" in names
        mock_session.exec.assert_called_once()


class TestAuthorRepositoryUpdate:
    """Tests for repository update operations."""

    @pytest.mark.asyncio
    async def test_update_author(self, mock_session):
        """Test updating an author."""
        repo = AuthorRepository(mock_session)
        author = Author(id=1, name="Updated Name")

        updated = await repo.update(author)

        assert updated == author
        mock_session.add.assert_called_once_with(author)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(author)


class TestAuthorRepositoryDelete:
    """Tests for repository delete operations."""

    @pytest.mark.asyncio
    async def test_delete_author(self, mock_session):
        """Test deleting an author."""
        repo = AuthorRepository(mock_session)
        author = Author(id=1, name="To Delete")

        await repo.delete(author)

        mock_session.delete.assert_called_once_with(author)
        mock_session.flush.assert_called_once()


class TestAuthorRepositoryExists:
    """Tests for repository exists check."""

    @pytest.mark.asyncio
    async def test_exists_true(self, mock_session):
        """Test exists returns True when author exists."""
        repo = AuthorRepository(mock_session)

        mock_result = MagicMock()
        mock_result.first.return_value = Author(id=1, name="Existing Author")
        mock_session.exec.return_value = mock_result

        exists = await repo.exists(name="Existing Author")

        assert exists is True
        mock_session.exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_exists_false(self, mock_session):
        """Test exists returns False when author doesn't exist."""
        repo = AuthorRepository(mock_session)

        mock_result = MagicMock()
        mock_result.first.return_value = None
        mock_session.exec.return_value = mock_result

        exists = await repo.exists(name="Nonexistent Author")

        assert exists is False
        mock_session.exec.assert_called_once()
