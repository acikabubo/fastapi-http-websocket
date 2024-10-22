from typing import Type

from icecream import ic
from starlette import status
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket

from app.api.ws.connection_manager import connection_manager
from app.logging import logger
from app.schemas.response import ResponseModel


class PackagedWebSocket(WebSocket):
    async def send_response(self, response: ResponseModel) -> None:
        await self.send_json(response.dict())


class PackageWebSocketEndpoint(WebSocketEndpoint):
    encoding = "json"
    websocket_class: Type[WebSocket] = PackagedWebSocket

    async def dispatch(self) -> None:
        websocket = self.websocket_class(
            self.scope, receive=self.receive, send=self.send
        )
        await self.on_connect(websocket)

        close_code = status.WS_1000_NORMAL_CLOSURE

        try:
            while True:
                message = await websocket.receive()
                if message["type"] == "websocket.receive":
                    data = await self.decode(websocket, message)
                    await self.on_receive(websocket, data)
                elif message["type"] == "websocket.disconnect":
                    close_code = int(
                        message.get("code") or status.WS_1000_NORMAL_CLOSURE
                    )
                    break
        except Exception as exc:
            close_code = status.WS_1011_INTERNAL_ERROR
            raise exc
        finally:
            await self.on_disconnect(websocket, close_code)

    async def on_connect(self, websocket):
        await super().on_connect(websocket)

        user = self.scope["user"].obj
        if user is None:
            logger.debug(
                "Client is not logged in, websocket connection will be closed!"
            )
            await websocket.close()
            return

        self.user = user

        connection_manager.connect(websocket)
        logger.debug("Client connected to the websocket connection")

    async def on_disconnect(self, websocket, close_code):
        await super().on_disconnect(websocket, close_code)
        connection_manager.disconnect(websocket)
        logger.debug(
            f"Client disconnected from websocket connection with code {close_code}"
        )
