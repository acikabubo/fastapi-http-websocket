import asyncio
import logging
from functools import partial
from json import loads

from redis.asyncio import ConnectionPool, Redis

from app.schemas.user import UserModel
from app.settings import REDIS_IP, USER_SESSION_REDIS_KEY_PREFIX

logger = logging.getLogger(__name__)


class RedisPool:
    __instances = {}

    @classmethod
    async def get_instance(cls, db=1):
        if db not in cls.__instances:
            cls.__instances[db] = await cls._create_instance(db)
        return cls.__instances[db]

    @classmethod
    async def _create_instance(cls, db):
        pool = ConnectionPool.from_url(
            f"redis://{REDIS_IP}:6379",
            db=db,
            encoding="utf-8",
            decode_responses=True,
        )
        redis_instance = await Redis.from_pool(pool)

        # TODO: Try not to use partial
        redis_instance.add_kc_user_session = partial(
            cls.add_kc_user_session, redis_instance
        )
        return redis_instance

    @staticmethod
    async def add_kc_user_session(r: Redis, user: UserModel):
        user_session_key = USER_SESSION_REDIS_KEY_PREFIX + user.username
        await r.set(user_session_key, 1)
        await r.pexpire(user_session_key, (user.expired_seconds + 10) * 1000)


async def get_redis_connection(db=1):
    try:
        return await RedisPool.get_instance(db)
    except Exception as ex:
        logger.error(f"Error getting Redis connection: {ex}")


async def get_auth_redis_connection():
    return await get_redis_connection(db=10)


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
            try:
                await callback(ch_name, loads(data), **kw)
            except Exception as ex:
                self.get_logger().error(f"Callback {callback} failed: {ex}")
                break

    async def loop(self):
        self.get_logger().info(f"Started REventHandler for {self.channel}")
        while True:
            try:
                if self.rch is None:
                    self.rch = self.redis.pubsub()
                    await self.rch.subscribe(self.channel)

                msg = await self.rch.get_message(
                    ignore_subscribe_messages=True, timeout=1
                )
                if msg:
                    await self.handle(msg["channel"], msg["data"])
            except asyncio.CancelledError:
                self.get_logger().info(
                    f"REventHandler on {self.channel} cancelled!"
                )
                break
            except Exception as ex:
                self.get_logger().error(
                    f"Error in REventHandler {self.channel}: {ex}"
                )
                await asyncio.sleep(0.5)


class RedisHandler:
    event_handlers = {}
    tasks = []

    async def subscribe(self, channel, callback, **kwargs):
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callback must be a coroutine")

        if channel not in self.event_handlers:
            redis = await get_redis_connection()
            handler = REventHandler(redis, channel)
            self.event_handlers[channel] = handler
            self.tasks.append(asyncio.create_task(handler.loop()))

        self.event_handlers[channel].add_callback((callback, kwargs))


class RRedis:
    __instance = None

    @classmethod
    async def get_instance(cls):
        if cls.__instance is None:
            cls.__instance = RedisHandler()
        return cls.__instance
