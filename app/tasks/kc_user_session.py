from asyncio import CancelledError, TimeoutError, sleep

from app.connection_registry import ws_clients
from app.constants import REDIS_MESSAGE_TIMEOUT_SECONDS, TASK_SLEEP_INTERVAL_SECONDS
from app.logging import logger
from app.settings import app_settings
from app.storage.redis import get_auth_redis_connection


async def kc_user_session_task():
    """
    Runs a task that monitors the expiration of user sessions stored in Redis.

    This task subscribes to the Redis `__keyevent@*__:expired` channel to listen for expired keys.
    When an expired key is detected that matches the `app_settings.USER_SESSION_REDIS_KEY_PREFIX`,
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
                ignore_subscribe_messages=True,
                timeout=REDIS_MESSAGE_TIMEOUT_SECONDS,
            )

            if not event:
                await sleep(TASK_SLEEP_INTERVAL_SECONDS)
                continue

            evt_key = event["data"]

            if not evt_key.startswith(
                app_settings.USER_SESSION_REDIS_KEY_PREFIX
            ):
                await sleep(TASK_SLEEP_INTERVAL_SECONDS)
                continue

            # Close websocket connection and delete user
            # relation with websocket connection
            if ws_conn := ws_clients.get(evt_key):
                await ws_conn.close()
                del ws_clients[evt_key]

            logger.info(f'Session for user "{evt_key}" has been expired')

            await sleep(TASK_SLEEP_INTERVAL_SECONDS)

        except CancelledError:
            logger.info("Task for keycloak user session cancelled!")
            break

        except TimeoutError:
            await sleep(TASK_SLEEP_INTERVAL_SECONDS)

        except Exception as ex:
            logger.error(
                f"Keycloak user session task error occurred with: {ex}"
            )
            rch = None
            await sleep(TASK_SLEEP_INTERVAL_SECONDS)
