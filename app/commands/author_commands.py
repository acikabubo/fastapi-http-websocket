"""
Commands for Author business operations.

Commands encapsulate business logic and can be reused across
HTTP and WebSocket handlers.

Example:
    ```python
    from app.commands.author_commands import GetAuthorsCommand, GetAuthorsInput
    from app.repositories.author_repository import AuthorRepository


    # In HTTP handler
    @router.get("/authors")
    async def get_authors(repo: AuthorRepoDep) -> list[Author]:
        command = GetAuthorsCommand(repo)
        input_data = GetAuthorsInput(name=None)
        return await command.execute(input_data)


    # In WebSocket handler
    @pkg_router.register(PkgID.GET_AUTHORS)
    async def get_authors_ws(request: RequestModel) -> ResponseModel:
        async with async_session() as session:
            repo = AuthorRepository(session)
            command = GetAuthorsCommand(repo)
            input_data = GetAuthorsInput(**request.data)
            authors = await command.execute(input_data)
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data=[a.model_dump() for a in authors],
            )
    ```
"""

from typing import Any

from pydantic import BaseModel, Field

from app.commands.base import BaseCommand
from app.exceptions import ConflictError, NotFoundError
from app.models.author import Author
from app.protocols import Repository
from app.repositories.author_repository import AuthorRepository


# ============================================================================
# Input/Output Models
# ============================================================================


class GetAuthorsInput(BaseModel):  # type: ignore[misc]
    """Input model for getting authors."""

    id: int | None = Field(default=None, description="Filter by author ID")
    name: str | None = Field(default=None, description="Filter by author name")
    search_term: str | None = Field(
        default=None,
        description="Search term for name (case-insensitive partial match)",
    )


class CreateAuthorInput(BaseModel):  # type: ignore[misc]
    """Input model for creating an author."""

    name: str = Field(..., min_length=1, description="Author name")


class UpdateAuthorInput(BaseModel):  # type: ignore[misc]
    """Input model for updating an author."""

    id: int = Field(..., description="Author ID to update")
    name: str = Field(..., min_length=1, description="New author name")


# ============================================================================
# Commands
# ============================================================================


class GetAuthorsCommand(BaseCommand[GetAuthorsInput, list[Author]]):
    """
    Command to get authors with optional filtering.

    Supports filtering by ID, exact name match, or search term.
    If search_term is provided, it takes precedence over name filter.

    Note: Uses concrete AuthorRepository type instead of Repository[Author]
    protocol because it requires the search_by_name() extension method.
    """

    def __init__(self, repository: AuthorRepository):
        """
        Initialize command with repository.

        Args:
            repository: Author repository for data access.
        """
        self.repository = repository

    async def execute(self, input_data: GetAuthorsInput) -> list[Author]:
        """
        Execute command to get authors.

        Args:
            input_data: Filters to apply.

        Returns:
            List of authors matching filters.

        Example:
            ```python
            # Get all authors
            result = await command.execute(GetAuthorsInput())

            # Get by ID
            result = await command.execute(GetAuthorsInput(id=1))

            # Search by name pattern
            result = await command.execute(GetAuthorsInput(search_term="John"))
            ```
        """
        # If search term provided, use search functionality
        if input_data.search_term:
            return await self.repository.search_by_name(input_data.search_term)

        # Otherwise, use exact filters
        filters: dict[str, Any] = {}
        if input_data.id is not None:
            filters["id"] = input_data.id
        if input_data.name is not None:
            filters["name"] = input_data.name

        return await self.repository.get_all(**filters)


class CreateAuthorCommand(BaseCommand[CreateAuthorInput, Author]):
    """
    Command to create a new author.

    Validates that author name doesn't already exist before creating.

    Note: Uses concrete AuthorRepository type because it requires the
    get_by_name() extension method.
    """

    def __init__(self, repository: AuthorRepository):
        """
        Initialize command with repository.

        Args:
            repository: Author repository for data access.
        """
        self.repository = repository

    async def execute(self, input_data: CreateAuthorInput) -> Author:
        """
        Execute command to create author.

        Args:
            input_data: Author data to create.

        Returns:
            Created author with generated ID.

        Raises:
            ConflictError: If author with same name already exists.

        Example:
            ```python
            input_data = CreateAuthorInput(name="John Doe")
            author = await command.execute(input_data)
            print(f"Created author with ID: {author.id}")
            ```
        """
        # Business logic: Check if author with same name exists
        existing = await self.repository.get_by_name(input_data.name)
        if existing:
            raise ConflictError(
                f"Author with name '{input_data.name}' already exists"
            )

        # Create author
        author = Author(name=input_data.name)
        return await self.repository.create(author)


class UpdateAuthorCommand(BaseCommand[UpdateAuthorInput, Author]):
    """
    Command to update an existing author.

    Validates that the author exists and new name doesn't conflict.
    """

    def __init__(self, repository: AuthorRepository):
        """
        Initialize command with repository.

        Args:
            repository: Author repository for data access.
        """
        self.repository = repository

    async def execute(self, input_data: UpdateAuthorInput) -> Author:
        """
        Execute command to update author.

        Args:
            input_data: Author ID and new data.

        Returns:
            Updated author.

        Raises:
            NotFoundError: If author not found.
            ConflictError: If name conflicts with another author.

        Example:
            ```python
            input_data = UpdateAuthorInput(id=1, name="Jane Doe")
            author = await command.execute(input_data)
            ```
        """
        # Check if author exists
        author = await self.repository.get_by_id(input_data.id)
        if not author:
            raise NotFoundError(f"Author with ID {input_data.id} not found")

        # Check if new name conflicts with another author
        existing = await self.repository.get_by_name(input_data.name)
        if existing and existing.id != input_data.id:
            raise ConflictError(
                f"Author with name '{input_data.name}' already exists"
            )

        # Update author
        author.name = input_data.name
        return await self.repository.update(author)


class DeleteAuthorCommand(BaseCommand[int, None]):
    """
    Command to delete an author.

    Validates that the author exists before deleting.

    Uses Repository[Author] protocol for flexible dependency injection,
    as it only requires standard get_by_id() and delete() methods.
    """

    def __init__(self, repository: Repository[Author]):
        """
        Initialize command with repository.

        Args:
            repository: Author repository for data access (any implementation
                of Repository[Author] protocol).
        """
        self.repository = repository

    async def execute(self, author_id: int) -> None:
        """
        Execute command to delete author.

        Args:
            author_id: ID of author to delete.

        Raises:
            NotFoundError: If author not found.

        Example:
            ```python
            await command.execute(1)  # Delete author with ID 1
            ```
        """
        author = await self.repository.get_by_id(author_id)
        if not author:
            raise NotFoundError(f"Author with ID {author_id} not found")

        await self.repository.delete(author)
