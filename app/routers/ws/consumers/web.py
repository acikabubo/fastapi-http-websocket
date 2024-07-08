from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.connection_manager import connection_manager
from app.contants import RSPCode
from app.db import get_session
from app.logging import logger
from app.routers.ws.handlers.registry import get_handler
from app.routers.ws.handlers.validation import is_request_data_valid
from app.schemas import RequestModel, ResponseModel
from jsonschema import ValidationError

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

                if response := is_request_data_valid(request) is not None:
                    await websocket.send_json(response.dict())
                    continue

                response = await handler(request, session)

                await websocket.send_json(response.dict())
            except ValueError as ex:
                logger.debug(f"No handler for PkgID {request.pkg_id}")
                await websocket.send_json(
                    ResponseModel.err_msg(request.pkg_id, msg=str(ex)).dict())
                # TODO: Need to close websocket connection?
            except ValidationError as ex:
                logger.error(f"Invalid data for PkgID {request.pkg_id}: \n{ex}")
                await websocket.send_json(
                    ResponseModel.err_msg(request.pkg_id, status_code=RSPCode.INVALID_DATA).dict())
                # TODO: Need to close websocket connection?
            except Exception as ex:
                await websocket.send_json(
                    ResponseModel.err_msg(request.pkg_id, msg=f"Error occurred while handle request for PkgID {request.pkg_id}: {ex}").dict()
                )
                # TODO: Need to close websocket connection?
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        print("Client disconnected")
