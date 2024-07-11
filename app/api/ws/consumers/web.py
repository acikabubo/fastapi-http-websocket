from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ws import (
    handlers,  # FIXME: Need this import for handler registration, try to find better way
)
from app.core.connection_manager import connection_manager
from app.core.db import get_session
from app.core.logging import logger
from app.routing import pkg_router
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel

router = APIRouter()


@router.websocket("/web")
async def web_websocket_endpoint(
    websocket: WebSocket, session: AsyncSession = Depends(get_session)
):
    """
    Handles the WebSocket connection for the web client.

    This function is responsible for managing the WebSocket connection with the web client. It connects the client to the connection manager, and then enters a loop to handle incoming requests from the client. For each request, it processes the request, generates a response, and sends the response back to the client.

    If the client disconnects or an error occurs during the request handling, the function will catch the exception, log the error, and send an error response to the client if possible.

    Finally, when the client disconnects, the function will remove the client from the connection manager.
    """
    await connection_manager.connect(websocket)
    try:
        while True:
            try:
                logger.debug("Waiting for client request...")

                data = await websocket.receive_json()
                request = RequestModel(**data)
                response = await pkg_router.handle_request(request, session)

                await websocket.send_json(response.dict())
                logger.debug(
                    f"Successfully sent response for PkgID {request.pkg_id}"
                )
            except WebSocketDisconnect as ex:
                logger.info(f"WebSocket disconnected with code {ex.code}")
                break
            except Exception as ex:
                logger.error(f"Error occurred while handling request: {ex}")
                try:
                    await websocket.send_json(
                        ResponseModel.err_msg(
                            request.pkg_id,
                            msg=f"Error occurred while handling request for PkgID {request.pkg_id}: {ex}",
                        ).dict()
                    )
                except WebSocketDisconnect:
                    logger.info(
                        "WebSocket disconnected while sending error message"
                    )
                    break
    finally:
        connection_manager.disconnect(websocket)
        logger.info("Client disconnected")
