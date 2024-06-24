from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

from app.connection_manager import connection_manager
from app.handlers.base_handler.py import BaseHandler
from app.models import Author, Genre, ResponseModel


class SubmoduleAHandler(BaseHandler):
    def __init__(self, session: AsyncSession):
        """
        Initializes the SubmoduleAHandler class with an AsyncSession instance.

        Args:
            session (AsyncSession): The SQLAlchemy AsyncSession instance to be used for database operations.
        """
        self.session = session

    async def handle_request(
        self, pkg_id: int, data: Dict[str, Any]
    ) -> ResponseModel:
        """
        Handles a request to the Submodule A of the application.

        Args:
            pkg_id (int): The package ID associated with the request.
            data (Dict[str, Any]): The data payload for the request.

        Returns:
            ResponseModel: The response model containing the result of the request handling.

        Raises:
            Exception: Any exception that occurs during the request handling.
        """
        try:
            match pkg_id:
                case 1:
                    return await self.function_a(data)
                case 2:
                    return await self.function_b(data)
                case _:
                    return ResponseModel(
                        pkg_id=pkg_id,
                        req_id=None,
                        status_code=-1,
                        data={"msg": "Invalid pkg_id for Submodule A"},
                    )
        except Exception as e:
            return ResponseModel(
                pkg_id=pkg_id,
                req_id=None,
                status_code=-2,
                data={"msg": str(e)},
            )

    async def function_a(self, data: Dict[str, Any]) -> ResponseModel:
        """
        Handles a request to create a new author in the application.

        Args:
            data (Dict[str, Any]): The data payload for the request, which should contain the necessary information to create a new author.

        Returns:
            ResponseModel: The response model containing the result of the author creation, including a success message and the created author data.

        Raises:
            Exception: Any exception that occurs during the author creation process.
        """
        author_data = Author(**data)
        async with self.session.begin():
            self.session.add(author_data)
        response = ResponseModel.ok_msg(
            pkg_id=1,
            req_id=data.get("req_id"),
            data={"message": "Author created"},
        )
        await connection_manager.broadcast(
            {"message": "Broadcast message from Submodule A"}
        )
        return response

    async def function_b(self, data: Dict[str, Any]) -> ResponseModel:
        """
        Handles a request to create a new genre in the application.

        Args:
            data (Dict[str, Any]): The data payload for the request, which should contain the necessary information to create a new genre.

        Returns:
            ResponseModel: The response model containing the result of the genre creation, including a success message and the created genre data.

        Raises:
            Exception: Any exception that occurs during the genre creation process.
        """
        genre_data = Genre(**data)
        async with self.session.begin():
            self.session.add(genre_data)
        response = ResponseModel.ok_msg(
            pkg_id=2,
            req_id=data.get("req_id"),
            data={"message": "Genre created"},
        )
        return response
