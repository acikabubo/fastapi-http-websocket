import json
from typing import Annotated, Any, Callable

from fastapi import Depends
from fastapi.encoders import jsonable_encoder
from sqlmodel import SQLModel, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.connection_manager import connection_manager
from app.contants import PkgID
from app.db import get_session
from app.handlers.base_handler import BaseHandler
from app.handlers.registry import register_handler
from app.logging import logger
from app.models import Author
from app.schemas import RequestModel, ResponseModel


@register_handler(PkgID.GET_AUTHORS, PkgID.THIRD)
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
        logger.debug(
            f"Attach db session to the handler {__class__.__name__} object"
        )

        self.handlers: dict[PkgID, Callable] = {
            PkgID.GET_AUTHORS: self.get_authors_handler,
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
                case PkgID.GET_AUTHORS:
                    resp_data = await self.get_authors_handler(request.data)
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

            return ResponseModel[Author](
                pkg_id=request.pkg_id, req_id=request.req_id, data=resp_data
            )
        except Exception as e:
            return ResponseModel(
                pkg_id=request.pkg_id,
                req_id=request.req_id,
                status_code=-2,
                data={"msg": str(e)},
            )

    async def get_authors_handler(
        self, data: dict[str, Any] | None = {}
    ) -> list[dict[str, Any]]:
        try:
            # author = Author(**data)
            # self.session.add(author)
            # await self.session.commit()
            # await self.session.refresh(author)

            result = await self.session.exec(select(Author))
            authors = result.all()
            return authors

        except Exception as ex:
            print()
            print(ex)
            print()

        # await connection_manager.broadcast(
        #     {
        #         "message": f"Broadcast message from Submodule A PkgID: {PkgID.GET_AUTHORS}"
        #     }
        # )

    async def function_b(self, data: dict[str, Any]) -> ResponseModel:
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
