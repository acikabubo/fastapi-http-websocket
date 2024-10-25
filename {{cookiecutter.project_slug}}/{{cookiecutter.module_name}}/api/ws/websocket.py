from typing import Type

from starlette import status
from starlette.endpoints import WebSocketEndpoint
from starlette.websockets import WebSocket

from app import ws_clients
from {{cookiecutter.module_name}}.api.ws.connection_manager import connection_manager
from {{cookiecutter.module_name}}.logging import logger
from {{cookiecutter.module_name}}.schemas.response import ResponseModel
from {{cookiecutter.module_name}}.settings import USER_SESSION_REDIS_KEY_PREFIX
{% if cookiecutter.use_redis == "y" and cookiecutter.use_keycloak == "y" %}
from {{cookiecutter.module_name}}.storage.redis import add_kc_user_session, get_auth_redis_connection
{% endif %}


class PackagedWebSocket(WebSocket):
    async def send_response(self, response: ResponseModel) -> None:
        await self.send_json(response.dict())


class PackageAuthWebSocketEndpoint(WebSocketEndpoint):
    encoding = "json"
    websocket_class: Type[WebSocket] = PackagedWebSocket

    async def dispatch(self) -> None:
        """
        This function is responsible for managing the WebSocket connection lifecycle.

        Parameters:
        - self: The instance of the class that this method belongs to.

        Returns:
        - None: This function does not return any value.

        The function performs the following steps:
        1. Creates a WebSocket instance using the provided scope, receive, and send parameters.
        2. Calls the on_connect method with the WebSocket instance.
        3. Initializes the close_code variable with the value of WS_1000_NORMAL_CLOSURE.
        4. Enters a try-except-finally block to handle the WebSocket communication.
        5. Inside the try block, it continuously receives messages from the WebSocket.
        - If the message type is "websocket.receive", it decodes the message and calls the on_receive method.
        - If the message type is "websocket.disconnect", it sets the close_code and breaks the loop.
        6. In the except block, it sets the close_code to WS_1011_INTERNAL_ERROR and re-raises the exception.
        7. In the finally block, it calls the on_disconnect method with the WebSocket and close_code.
        """
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

        {% if cookiecutter.use_redis == "y" and cookiecutter.use_keycloak == "y" %}
        # Attach auth redis instance on websocket connection instance
        self.r = await get_auth_redis_connection()
        {% endif %}

        user = self.scope["user"].obj
        if user is None:
            logger.debug(
                "Client is not logged in, websocket connection will be closed!"
            )
            await websocket.close()
            return

        self.user = user

        {% if cookiecutter.use_redis == "y" and cookiecutter.use_keycloak == "y" %}
        # Set user username in redis with TTL from expired seconds from keycloak
        await add_kc_user_session(self.r, user)
        {% endif %}

        # Map username with websocket instance
        ws_clients[USER_SESSION_REDIS_KEY_PREFIX + user.username] = websocket

        connection_manager.connect(websocket)
        logger.debug("Client connected to the websocket connection")

    async def on_disconnect(self, websocket, close_code):
        await super().on_disconnect(websocket, close_code)
        connection_manager.disconnect(websocket)
        logger.debug(
            f"Client of user {self.user.username} disconnected from websocket connection with code {close_code}"
        )