from typing import Annotated, Any, Dict

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import SQLModel, select

from app.connection_manager import connection_manager
from app.contants import PkgID
from app.db import get_session
from app.handlers.base_handler import BaseHandler
from app.handlers.registry import register_handler
from app.logging import logger
from app.models import Author
from app.schemas import RequestModel, ResponseModel


@register_handler(PkgID.FIRST, PkgID.THIRD)
class SubmoduleAHandler(BaseHandler):
    """
    Handles a request to the Submodule A of the application.

    Args:
        request (RequestModel): The request model containing the necessary information to handle the request.

    Returns:
        ResponseModel: The response model containing the result of the request handling.

    Raises:
        Exception: Any exception that occurs during the request handling.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(session)

        self.handlers: dict[PkgID, Callable] = {
            PkgID.FIRST: self.function_a,
            PkgID.THIRD: self.function_b,
        }

    async def handle_request(
        self,
        request: RequestModel,
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
            # TODO: WHERE TO PUT DATA VALIDATION
            match request.pkg_id:
                case PkgID.FIRST:
                    resp_data = await self.function_a(request.data)
                case PkgID.THIRD:
                    resp_data = await self.function_b(request.data)
                case _:
                    logger.debug(
                        f"Missing handler method for PkgID {request.pkg_id} in {__class__.__name__}"
                    )
                    return ResponseModel(
                        pkg_id=request.pkg_id,
                        req_id=request.req_id,
                        status_code=-1,
                        data={
                            "msg": f"Missing handler for PkgID {request.pkg_id}"
                        },
                    )

            return ResponseModel(
                pkg_id=request.pkg_id, req_id=request.req_id, data=resp_data
            )
        except Exception as e:
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                status_code=-2,
                data={"msg": str(e)},
            )

    async def function_a(self, data: Dict[str, Any]) -> dict[str, Any]:
        """
        Handles a request to create a new author in the application.

        Args:
            data (Dict[str, Any]): The data payload for the request, which should contain the necessary information to create a new author.

        Returns:
            ResponseModel: The response model containing the result of the author creation, including a success message and the created author data.

        Raises:
            Exception: Any exception that occurs during the author creation process.
        """
        try:
            author = Author(**data)

            # self.session.add(author)
            # await self.session.commit()
            # await self.session.refresh(author)

            print()
            print(author)
            print()
        except Exception as ex:
            print()
            print(ex)
            print()

        await connection_manager.broadcast(
            {
                "message": f"Broadcast message from Submodule A PkgID: {PkgID.FIRST}"
            }
        )
        return {"message": "Author created"}

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
        # genre_data = Genre(**data)
        # async with self.session.begin():
        #     self.session.add(genre_data)

        await connection_manager.broadcast(
            {
                "message": f"Broadcast message from Submodule A PkgID: {PkgID.THIRD}"
            }
        )
        # response = ResponseModel.ok_msg(
        #     pkg_id=3,
        #     req_id=data.get("req_id"),
        #     data={"message": "Genre created"},
        # )
        # await connection_manager.broadcast(
        #     {"message": "Broadcast message from Submodule B"}
        # )
        # return response
