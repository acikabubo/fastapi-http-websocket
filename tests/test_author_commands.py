"""
Tests for Author commands.

These tests verify that commands correctly encapsulate business logic
and can be tested independently of HTTP/WebSocket handlers.
"""

import pytest
from unittest.mock import AsyncMock

from app.commands.author_commands import (
    CreateAuthorCommand,
    CreateAuthorInput,
    DeleteAuthorCommand,
    GetAuthorsCommand,
    GetAuthorsInput,
    UpdateAuthorCommand,
    UpdateAuthorInput,
)
from app.models.author import Author


class TestGetAuthorsCommand:
    """Tests for GetAuthorsCommand."""

    @pytest.mark.asyncio
    async def test_get_all_authors(self):
        """Test getting all authors without filters."""
        # Mock repository
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [
            Author(id=1, name="Author 1"),
            Author(id=2, name="Author 2"),
        ]

        command = GetAuthorsCommand(mock_repo)
        input_data = GetAuthorsInput()

        result = await command.execute(input_data)

        assert len(result) == 2
        assert result[0].name == "Author 1"
        assert result[1].name == "Author 2"
        mock_repo.get_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_authors_with_id_filter(self):
        """Test getting authors filtered by ID."""
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [Author(id=1, name="Author 1")]

        command = GetAuthorsCommand(mock_repo)
        input_data = GetAuthorsInput(id=1)

        result = await command.execute(input_data)

        assert len(result) == 1
        assert result[0].id == 1
        mock_repo.get_all.assert_called_once_with(id=1)

    @pytest.mark.asyncio
    async def test_get_authors_with_name_filter(self):
        """Test getting authors filtered by name."""
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = [Author(id=1, name="John Doe")]

        command = GetAuthorsCommand(mock_repo)
        input_data = GetAuthorsInput(name="John Doe")

        result = await command.execute(input_data)

        assert len(result) == 1
        assert result[0].name == "John Doe"
        mock_repo.get_all.assert_called_once_with(name="John Doe")

    @pytest.mark.asyncio
    async def test_get_authors_with_search_term(self):
        """Test searching authors by name pattern."""
        mock_repo = AsyncMock()
        mock_repo.search_by_name.return_value = [
            Author(id=1, name="John Doe"),
            Author(id=2, name="John Smith"),
        ]

        command = GetAuthorsCommand(mock_repo)
        input_data = GetAuthorsInput(search_term="John")

        result = await command.execute(input_data)

        assert len(result) == 2
        mock_repo.search_by_name.assert_called_once_with("John")
        # Should not call get_all when search_term is provided
        mock_repo.get_all.assert_not_called()


class TestCreateAuthorCommand:
    """Tests for CreateAuthorCommand."""

    @pytest.mark.asyncio
    async def test_create_author_success(self):
        """Test successfully creating an author."""
        mock_repo = AsyncMock()
        mock_repo.get_by_name.return_value = None  # No existing author
        mock_repo.create.return_value = Author(id=1, name="New Author")

        command = CreateAuthorCommand(mock_repo)
        input_data = CreateAuthorInput(name="New Author")

        result = await command.execute(input_data)

        assert result.id == 1
        assert result.name == "New Author"
        mock_repo.get_by_name.assert_called_once_with("New Author")
        mock_repo.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_author_duplicate_name(self):
        """Test creating author with duplicate name raises error."""
        mock_repo = AsyncMock()
        # Existing author with same name
        mock_repo.get_by_name.return_value = Author(id=1, name="Existing")

        command = CreateAuthorCommand(mock_repo)
        input_data = CreateAuthorInput(name="Existing")

        with pytest.raises(ValueError, match="already exists"):
            await command.execute(input_data)

        mock_repo.get_by_name.assert_called_once_with("Existing")
        # Should not attempt to create
        mock_repo.create.assert_not_called()


class TestUpdateAuthorCommand:
    """Tests for UpdateAuthorCommand."""

    @pytest.mark.asyncio
    async def test_update_author_success(self):
        """Test successfully updating an author."""
        mock_repo = AsyncMock()
        existing_author = Author(id=1, name="Old Name")
        mock_repo.get_by_id.return_value = existing_author
        mock_repo.get_by_name.return_value = None  # No conflict
        mock_repo.update.return_value = Author(id=1, name="New Name")

        command = UpdateAuthorCommand(mock_repo)
        input_data = UpdateAuthorInput(id=1, name="New Name")

        result = await command.execute(input_data)

        assert result.id == 1
        assert result.name == "New Name"
        mock_repo.get_by_id.assert_called_once_with(1)
        mock_repo.get_by_name.assert_called_once_with("New Name")
        mock_repo.update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_author_not_found(self):
        """Test updating non-existent author raises error."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None  # Author doesn't exist

        command = UpdateAuthorCommand(mock_repo)
        input_data = UpdateAuthorInput(id=999, name="New Name")

        with pytest.raises(ValueError, match="not found"):
            await command.execute(input_data)

        mock_repo.get_by_id.assert_called_once_with(999)
        mock_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_author_name_conflict(self):
        """Test updating author with conflicting name raises error."""
        mock_repo = AsyncMock()
        # Author being updated
        mock_repo.get_by_id.return_value = Author(id=1, name="Old Name")
        # Another author with the new name
        mock_repo.get_by_name.return_value = Author(id=2, name="Conflict")

        command = UpdateAuthorCommand(mock_repo)
        input_data = UpdateAuthorInput(id=1, name="Conflict")

        with pytest.raises(ValueError, match="already exists"):
            await command.execute(input_data)

        mock_repo.update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_author_same_name_same_author(self):
        """Test updating author with its own name succeeds."""
        mock_repo = AsyncMock()
        existing_author = Author(id=1, name="Same Name")
        mock_repo.get_by_id.return_value = existing_author
        # Same author returned by get_by_name
        mock_repo.get_by_name.return_value = existing_author
        mock_repo.update.return_value = existing_author

        command = UpdateAuthorCommand(mock_repo)
        input_data = UpdateAuthorInput(id=1, name="Same Name")

        result = await command.execute(input_data)

        assert result.id == 1
        mock_repo.update.assert_called_once()


class TestDeleteAuthorCommand:
    """Tests for DeleteAuthorCommand."""

    @pytest.mark.asyncio
    async def test_delete_author_success(self):
        """Test successfully deleting an author."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = Author(id=1, name="To Delete")

        command = DeleteAuthorCommand(mock_repo)

        await command.execute(1)

        mock_repo.get_by_id.assert_called_once_with(1)
        mock_repo.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_author_not_found(self):
        """Test deleting non-existent author raises error."""
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None

        command = DeleteAuthorCommand(mock_repo)

        with pytest.raises(ValueError, match="not found"):
            await command.execute(999)

        mock_repo.get_by_id.assert_called_once_with(999)
        mock_repo.delete.assert_not_called()
