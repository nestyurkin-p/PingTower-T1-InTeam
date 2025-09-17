from typing import List
from core import redis, config, SUBSCRIPTIONS_KEY


async def add(chat_id: int) -> None:
    await redis.sadd(SUBSCRIPTIONS_KEY, chat_id)


async def remove(chat_id: int) -> None:
    await redis.srem(SUBSCRIPTIONS_KEY, chat_id)


async def get_all() -> List[int]:
    raw = await redis.smembers(SUBSCRIPTIONS_KEY)
    # redis returns ints as bytes sometimes; unify to int
    res = []
    for x in raw:
        try:
            res.append(int(x))
        except Exception:
            try:
                res.append(int(x.decode()))
            except Exception:
                pass
    return res
