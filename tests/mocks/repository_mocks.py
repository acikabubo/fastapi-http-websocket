"""
Mock factory functions for repository testing.

Provides pre-configured repository mocks with common method stubs.
"""

from unittest.mock import AsyncMock

from app.repositories.author_repository import AuthorRepository
from app.repositories.base_repository import BaseRepository


def create_mock_author_repository():
    """
    Creates a mock AuthorRepository with common methods.

    Returns:
        AsyncMock: Mocked AuthorRepository instance
    """
    repo_mock = AsyncMock(spec=AuthorRepository)
    repo_mock.get_by_id = AsyncMock(return_value=None)
    repo_mock.get_all = AsyncMock(return_value=[])
    repo_mock.create = AsyncMock()
    repo_mock.update = AsyncMock()
    repo_mock.delete = AsyncMock()
    repo_mock.exists = AsyncMock(return_value=False)
    return repo_mock


def create_mock_base_repository():
    """
    Creates a generic mock BaseRepository with common CRUD methods.

    Returns:
        AsyncMock: Mocked BaseRepository instance
    """
    repo_mock = AsyncMock(spec=BaseRepository)
    repo_mock.get_by_id = AsyncMock(return_value=None)
    repo_mock.get_all = AsyncMock(return_value=[])
    repo_mock.create = AsyncMock()
    repo_mock.update = AsyncMock()
    repo_mock.delete = AsyncMock()
    repo_mock.exists = AsyncMock(return_value=False)
    repo_mock.count = AsyncMock(return_value=0)
    return repo_mock
