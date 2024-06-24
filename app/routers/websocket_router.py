from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.connection_manager import connection_manager
from app.handlers.submodule_a import SubmoduleAHandler
from app.models import RequestModel, ResponseModel

DATABASE_URL = "postgresql+asyncpg://postgres:postgres@db:5432/app_db"
engine = create_async_engine(DATABASE_URL, echo=True, future=True)
async_session = sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

router = APIRouter()


async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session


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
