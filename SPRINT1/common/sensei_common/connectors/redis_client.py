"""
Redis connector for Sensei 2.0.

Used for:
- Embedding cache
- Autosave drafts
- Short-term conversation memory
"""

from __future__ import annotations

from typing import Any, Optional

from redis.asyncio import Redis

from common.sensei_common.logging.logger import get_logger


class RedisClient:
    """
    Simple asynchronous Redis client for key/value and hash operations.
    """

    def __init__(
        self,
        url: str,
        component: str = "common",
    ) -> None:
        """
        Initialize the Redis client.

        Parameters
        ----------
        url : str
            Redis connection URL (e.g. redis://host:6379/0).
        component : str
            Component label ("vendor", "authoring", "common").
        """
        self._redis = Redis.from_url(url, decode_responses=True)
        self._component = component

    async def get(self, key: str, trace_id: Optional[str] = None) -> Optional[str]:
        """
        Get a string value for the given key.
        """
        logger = get_logger(self._component, "cache", "redis", trace_id)
        try:
            return await self._redis.get(key)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis GET failed: %s", exc, ka_code="KA-CACHE-0001")
            raise

    async def set(
        self,
        key: str,
        value: str,
        ttl: int,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Set a string value with TTL.

        Parameters
        ----------
        ttl : int
            Time to live in seconds.
        """
        logger = get_logger(self._component, "cache", "redis", trace_id)
        try:
            await self._redis.set(key, value, ex=ttl)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis SET failed: %s", exc, ka_code="KA-CACHE-0002")
            raise

    async def hset(
        self,
        key: str,
        field: str,
        value: str,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Set a hash field for a key.
        """
        logger = get_logger(self._component, "cache", "redis", trace_id)
        try:
            await self._redis.hset(key, field, value)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis HSET failed: %s", exc, ka_code="KA-CACHE-0003")
            raise

    async def hget(
        self,
        key: str,
        field: str,
        trace_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get a hash field value for a key.
        """
        logger = get_logger(self._component, "cache", "redis", trace_id)
        try:
            return await self._redis.hget(key, field)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis HGET failed: %s", exc, ka_code="KA-CACHE-0004")
            raise

    async def delete(self, key: str, trace_id: Optional[str] = None) -> None:
        """
        Delete a key.
        """
        logger = get_logger(self._component, "cache", "redis", trace_id)
        try:
            await self._redis.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.error("Redis DEL failed: %s", exc, ka_code="KA-CACHE-0005")
            raise
