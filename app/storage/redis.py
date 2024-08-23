import logging
from asyncio import (
    CancelledError,
    TimeoutError,
    create_task,
    iscoroutinefunction,
    sleep,
)
from json import dumps, loads

from redis.asyncio import ConnectionPool, Redis, from_url

from app.schemas.user import UserModel
from app.settings import REDIS_IP, USER_SESSION_REDIS_KEY_PREFIX


class RedisPool(object):
    __instance = None
    _pool = ConnectionPool.from_url(
        f"redis://{REDIS_IP}:6379",
        db=1,
        encoding="utf-8",
        decode_responses=True,
    )

    async def __new__(cls):
        if cls.__instance is None:
            cls.__instance = await Redis.from_pool(cls._pool)

        return cls.__instance


async def get_redis_connection():
    try:
        return await RedisPool()
    except Exception as ex:
        logger.error(f"Error occurred while getting redis connection: {ex}")


class AuthRedisPool(object):  # -
    __instance = None  # -
    _pool = ConnectionPool.from_url(  # -
        f"redis://{REDIS_IP}:6379",  # -
        db=10,  # -
        encoding="utf-8",  # -
        decode_responses=True,  # -
    )  # -

    async def __new__(cls):
        """
        A metaclass method that creates a new instance of the Redis class using a connection pool.

        This method checks if an instance of the class has already been created. If not, it creates a new
        instance by calling the `Redis.from_pool` method with the predefined connection pool. The
        created instance is then stored as a class attribute for future use.

        Parameters:
        cls (class): The class that this method is being called on. In this case, it is the RedisPool class.

        Returns:
        cls.__instance (Redis): An instance of the Redis class created using the connection pool.
        """
        if cls.__instance is None:
            cls.__instance = await Redis.from_pool(cls._pool)

        return cls.__instance


# FIXME: Try to attach this function to redis instance, to use in websocket like <ws-instance>.r.add_kc_user_session
async def add_kc_user_session(r: Redis, user: UserModel):
    """
    Asynchronously adds a user session to the Redis database.

    This function takes a Redis instance and a UserModel object as parameters. It constructs
    a user session key using the USER_SESSION_REDIS_KEY_PREFIX and the user's username.
    Then, it sets the value of the user session key to 1 in the Redis database using the
    `set` method. After that, it sets an expiration time for the user session key using the
    `pexpire` method, which is the sum of the user's expired seconds and 10 seconds.

    Parameters:
    - r (Redis): An instance of the Redis class representing the Redis database connection.
    - user (UserModel): An instance of the UserModel class representing the user for whom the
                    session needs to be added.

    Returns:
    None
    """
    user_session_key = USER_SESSION_REDIS_KEY_PREFIX + user.username
    await r.set(user_session_key, 1)
    await r.pexpire(user_session_key, (user.expired_seconds + 10) * 1000)


async def get_auth_redis_connection():
    """
    Asynchronously gets a connection to the authentication Redis database.

    This function attempts to create a connection to the Redis database using the
    AuthRedisPool class. If the connection is successful, it returns the Redis
    instance. If an error occurs during the connection attempt, it logs the error
    message and returns None.

    Parameters:
    None

    Returns:
    redis_instance: An instance of the Redis class if the connection is successful,
                    or None if an error occurs.
    """
    try:
        return await AuthRedisPool()
    except Exception as ex:
        logger.error(
            f"Error occurred while getting auth redis connection: {ex}"
        )


class REventHandler:
    @staticmethod
    def get_logger():
        return logging.getLogger(REventHandler.__name__)

    def __init__(self, redis, channel):
        self.channel = channel
        self.redis = redis
        self.rch = None
        self.callbacks = []

    def add_callback(self, callback):
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    async def handle(self, ch_name, data):
        for callback, kw in self.callbacks:
            # stop execution at first error occurence in the list of callbacks
            try:
                await callback(ch_name, loads(data), **kw)
            except Exception as ex:
                REventHandler.get_logger().error(
                    f"Callback {callback} failed with {str(ex)}"
                )
                break

    async def loop(self):
        REventHandler.get_logger().info(
            f"Started REventHandler for {self.channel}"
        )
        while True:
            try:
                if self.rch is None:
                    self.rch = self.redis.pubsub()
                    await self.rch.subscribe(self.channel)

                msg = await self.rch.get_message(
                    ignore_subscribe_messages=True, timeout=1
                )

                if msg is None:
                    continue

                await self.handle(msg["channel"], msg["data"])
            except CancelledError:
                REventHandler.get_logger().info(
                    f"REventHandler on {self.channel} cancelled!"
                )
                break

            except ConnectionError:
                REventHandler.get_logger().error(
                    f"REventHandler {self.channel} lost connection to redis"
                )
                self.rch = None
                await sleep(0.5)

            except TimeoutError:
                await sleep(0.1)

            except Exception as ex:
                REventHandler.get_logger().error(
                    f"Callback error on {self.channel}: {str(ex)}"
                )
                await sleep(0.5)


class RedisHandler(object):
    event_handlers = {}
    tasks = []

    async def subscribe(self, channel, callback, **kwargs):
        if not iscoroutinefunction(callback):
            raise ValueError("Callback argument must be a coroutine")

        if channel not in self.event_handlers:
            r = await get_redis_connection()
            handler = REventHandler(r, channel)

            self.event_handlers[channel] = handler
            self.tasks.append(create_task(handler.loop()))

        self.event_handlers[channel].add_callback((callback, kwargs))


class RRedis(object):
    __instance = None

    async def __new__(cls):
        if cls.__instance is None:
            cls.__instance = RedisHandler()

        return cls.__instance
