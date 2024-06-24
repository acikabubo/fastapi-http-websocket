from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.connection_manager import connection_manager
from app.db import get_session
from app.handlers.submodule_a import SubmoduleAHandler
from app.schemas import RequestModel, ResponseModel

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, session: AsyncSession = Depends(get_session)
):
    await connection_manager.connect(websocket)
    handler = SubmoduleAHandler(session)
    try:
        while True:
            try:
                data = await websocket.receive_json()
                request = RequestModel(**data)

                response = await handler.handle_request(
                    request.pkg_id, request.data
                )
                await websocket.send_json(response.dict())
            except Exception as e:
                await websocket.send_json(
                    ResponseModel(
                        pkg_id=None,
                        req_id=None,
                        status_code=-2,
                        data={"msg": str(e)},
                    ).dict()
                )
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        print("Client disconnected")
