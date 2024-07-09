from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.ws.handlers.registry import get_handler
from app.connection_manager import connection_manager
from app.db import get_session
from app.logging import logger
from app.schemas.request import RequestModel
from app.schemas.response import ResponseModel

router = APIRouter()


@router.websocket("/web")
async def web_websocket_endpoint(
    websocket: WebSocket, session: AsyncSession = Depends(get_session)
):
    """
    Handles the WebSocket connection for the web client.

    This function is the main entry point for the web client WebSocket connection. It manages the connection lifecycle, including connecting, receiving and processing client requests, and handling disconnections.

    The function performs the following steps:
    1. Connects the WebSocket to the connection manager.
    2. Enters a loop to continuously receive and process client requests.
    3. For each request:
       - Deserializes the request data into a `RequestModel` instance.
       - Retrieves the appropriate request handler based on the `pkg_id` in the request.
       - Calls the request handler with the request and the database session.
       - Sends the response back to the client.
    4. Handles any exceptions that occur during request processing.
    5. Disconnects the WebSocket from the connection manager when the client disconnects.

    Args:
        websocket (WebSocket): The WebSocket connection for the client.
        session (AsyncSession): The database session to use for the request.
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
                logger.debug(
                    f"Succesfully send response for PkgID {request.pkg_id}"
                )
            except ValueError as ex:
                logger.debug(f"No handler for PkgID {request.pkg_id}")
                await websocket.send_json(
                    ResponseModel.err_msg(request.pkg_id, msg=str(ex)).dict()
                )
                # TODO: Need to close websocket connection?
            except Exception as ex:
                await websocket.send_json(
                    ResponseModel.err_msg(
                        request.pkg_id,
                        msg=f"Error occurred while handle request for PkgID {request.pkg_id}: {ex}",
                    ).dict()
                )
                # TODO: Need to close websocket connection?
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        print("Client disconnected")
