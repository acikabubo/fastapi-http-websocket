from asyncio import CancelledError, TimeoutError, sleep

import app  # FIXME: Import like this to avoid circular import. Try another way to use ws_clients!
from app.logging import logger
from app.settings import USER_SESSION_REDIS_KEY_PREFIX
from app.storage.redis import get_auth_redis_connection


async def kc_user_session_task():
    """
    Runs a task that monitors the expiration of user sessions stored in Redis.

    This task subscribes to the Redis `__keyevent@*__:expired` channel to listen for expired keys.
    When an expired key is detected that matches the `USER_SESSION_REDIS_KEY_PREFIX`,
    the task closes the associated WebSocket connection (if it exists) and removes the user from the `ws_clients` dictionary.

    This ensures that when a user's session expires, their WebSocket connection is properly closed and cleaned up.
    """
    # Get auth redis instance
    r = await get_auth_redis_connection()

    rch = None

    while True:
        try:
            if not rch:
                rch = r.pubsub()
                await rch.psubscribe("__keyevent@*__:expired")

            event = await rch.get_message(
                ignore_subscribe_messages=True, timeout=1
            )

            if not event:
                await sleep(0.5)
                continue

            evt_key = event["data"]

            if not evt_key.startswith(USER_SESSION_REDIS_KEY_PREFIX):
                await sleep(1)
                continue

            # Close websocket connection and delete user
            # relation with websocket connection
            if ws_conn := app.ws_clients.get(evt_key):
                await ws_conn.close()
                del app.ws_clients[evt_key]

            logger.info(f'Session for user "{evt_key}" has been expired')

            await sleep(1)

        except CancelledError:
            logger.info("Task for keycloak user session cancelled!")
            break

        except TimeoutError:
            await sleep(0.1)

        except Exception as ex:
            logger.error(
                f"Keycloak user session task error occurred with: {ex}"
            )
            rch = None
            await sleep(0.5)
