from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.connection_manager import connection_manager
from app.db import get_session
from app.handlers.registry import get_handler
from app.logging import logger
from app.schemas import RequestModel, ResponseModel

router = APIRouter()


@router.websocket("/web")
async def web_websocket_endpoint(
    websocket: WebSocket, session: AsyncSession = Depends(get_session)
):
    await connection_manager.connect(websocket)
    try:
        while True:
            try:
                logger.debug("Waiting for client request...")

                data = await websocket.receive_json()
                request = RequestModel(**data)

                handler = get_handler(request.pkg_id, session)
                response = await handler.handle_request(request)

                await websocket.send_json(response.dict())

            except ValidationError as ex:
                print()
                print(print(repr(ex.errors()[0]["type"])))
                print()

            except Exception:
                import traceback

                traceback.print_exc()
                break
                # await websocket.send_json(
                #     ResponseModel(
                #         pkg_id=None,
                #         req_id=None,
                #         status_code=-2,
                #         data={"msg": str(e)},
                #     ).dict()
                # )
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        print("Client disconnected")
