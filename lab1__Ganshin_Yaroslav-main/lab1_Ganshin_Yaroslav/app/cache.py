import os
import json
from typing import Any, List, Optional
from dotenv import load_dotenv
import redis.asyncio as redis
import logging
load_dotenv()
_redis: Optional[redis.Redis] = None
logger = logging.getLogger("cache")

async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis = redis.from_url(url, decode_responses=True)
    return _redis

async def get_json(key: str) -> Any:
    r = await get_redis()
    val = await r.get(key)
    if val is None:
        logger.info(f"cache.miss key={key}")
        return None
    try:
        logger.info(f"cache.hit key={key}")
        return json.loads(val)
    except Exception:
        logger.warning(f"cache.decode_error key={key}")
        return None

async def set_json(key: str, value: Any, ttl_seconds: int | None = None) -> None:
    r = await get_redis()
    data = json.dumps(value, ensure_ascii=False)
    if ttl_seconds:
        await r.set(key, data, ex=ttl_seconds)
        logger.info(f"cache.set key={key} ttl={ttl_seconds}")
    else:
        await r.set(key, data)
        logger.info(f"cache.set key={key} ttl=None")

async def delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)
    logger.info(f"cache.del key={key}")

async def mget_json(keys: List[str]) -> List[Any]:
    r = await get_redis()
    vals = await r.mget(keys)
    out: List[Any] = []
    for v in vals:
        if v is None:
            out.append(None)
        else:
            try:
                out.append(json.loads(v))
            except Exception:
                out.append(None)
    return out

async def sadd(key: str, member: str) -> None:
    r = await get_redis()
    await r.sadd(key, member)
    logger.info(f"cache.sadd key={key} member={member}")

async def srem(key: str, member: str) -> None:
    r = await get_redis()
    await r.srem(key, member)
    logger.info(f"cache.srem key={key} member={member}")

async def smembers(key: str) -> List[str]:
    r = await get_redis()
    members = await r.smembers(key)
    logger.info(f"cache.smembers key={key} count={len(members)}")
    return list(members)

async def delete_by_prefix(prefix: str) -> None:
    r = await get_redis()
    cursor: int = 0
    pattern = f"{prefix}*"
    while True:
        cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
        if keys:
            await r.delete(*keys)
            logger.info(f"cache.del_many prefix={prefix} count={len(keys)}")
        if cursor == 0:
            break
