from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.connection_manager import connection_manager
from app.db import get_session
from app.logging import logger
from app.routers.ws.handlers.registry import get_handler
from app.schemas import RequestModel

router = APIRouter()


@router.websocket("/web")
async def web_websocket_endpoint(
    websocket: WebSocket, session: AsyncSession = Depends(get_session)
):
    """
    Handles the WebSocket connection for the web client.

    This function is the main entry point for the WebSocket connection. It connects the client to the connection manager, and then enters a loop to handle incoming requests from the client.

    For each incoming request, it:
    - Deserializes the request data into a `RequestModel` object
    - Retrieves the appropriate handler for the request
    - Calls the handler with the request and the database session
    - Sends the response back to the client as JSON

    If a `ValidationError` occurs, it logs the error and continues waiting for the next request.

    If any other exception occurs, it logs the traceback and breaks out of the loop, disconnecting the client.

    If the client disconnects, it removes the client from the connection manager.
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            try:
                logger.debug("Waiting for client request...")

                data = await websocket.receive_json()
                request = RequestModel(**data)
                handler = get_handler(request.pkg_id)
                response = await handler(request, session)

                await websocket.send_json(response.dict())
            except ValidationError as ex:
                print()
                print(print(repr(ex.errors()[0]["type"])))
                print()

            except Exception:
                import traceback

                traceback.print_exc()
                break
                # TODO: websocket.send_json(...) -> websocket.send_response(ResponseModel)
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
