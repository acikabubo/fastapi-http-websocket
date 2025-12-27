"""
Base command for encapsulating business operations.

The Command pattern encapsulates business logic as objects, making it
reusable across HTTP and WebSocket handlers and easy to test in isolation.

Example:
    ```python
    from pydantic import BaseModel
    from app.commands.base import BaseCommand


    class CreateAuthorInput(BaseModel):
        name: str
        email: str


    class CreateAuthorCommand(BaseCommand[CreateAuthorInput, Author]):
        def __init__(self, repository: AuthorRepository):
            self.repository = repository

        async def execute(self, input_data: CreateAuthorInput) -> Author:
            # Check if email exists
            if await self.repository.exists(email=input_data.email):
                raise ValueError("Email already exists")

            # Create author
            author = Author(**input_data.model_dump())
            return await self.repository.create(author)


    # Usage in HTTP handler
    @router.post("/authors")
    async def create_author(
        data: CreateAuthorInput, repo: AuthorRepoDep
    ) -> Author:
        command = CreateAuthorCommand(repo)
        return await command.execute(data)


    # Usage in WebSocket handler
    @pkg_router.register(PkgID.CREATE_AUTHOR)
    async def create_author_ws(request: RequestModel) -> ResponseModel:
        async with async_session() as session:
            repo = AuthorRepository(session)
            command = CreateAuthorCommand(repo)
            input_data = CreateAuthorInput(**request.data)
            author = await command.execute(input_data)
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                data=author.model_dump(),
            )
    ```
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class BaseCommand(ABC, Generic[TInput, TOutput]):
    """
    Base command for business operations.

    Commands encapsulate business logic and can be reused across
    different handler types (HTTP, WebSocket). They depend on
    repositories for data access.

    Type Parameters:
        TInput: Input data type (usually a Pydantic model).
        TOutput: Output data type.

    Example:
        ```python
        class GetAuthorsCommand(BaseCommand[GetAuthorsInput, list[Author]]):
            def __init__(self, repository: AuthorRepository):
                self.repository = repository

            async def execute(
                self, input_data: GetAuthorsInput
            ) -> list[Author]:
                filters = {}
                if input_data.name:
                    filters["name"] = input_data.name
                return await self.repository.get_all(**filters)
        ```
    """

    @abstractmethod
    async def execute(self, input_data: TInput) -> TOutput:
        """
        Execute the command.

        This method must be implemented by subclasses to define
        the business logic of the command.

        Args:
            input_data: Input data for the command.

        Returns:
            Result of the command execution.

        Raises:
            ValueError: For business logic validation errors.
            HTTPException: For HTTP-specific errors (in HTTP handlers).
            Any other exceptions as appropriate.
        """
        pass
