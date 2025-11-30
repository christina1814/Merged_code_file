"""
PostgreSQL connector for Sensei 2.0.

Provides:
- Connection pooling
- Basic CRUD helpers
- Retries with exponential backoff
- Trace-aware logging

Intended usage:
    from sensei_common.connectors.postgres_client import PostgresClient

    pg = PostgresClient(dsn="postgresql://user:pass@host:5432/db")

    row = await pg.fetch_one("SELECT * FROM sources WHERE id = :id", {"id": some_id})
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional

import asyncpg

from common.sensei_common.logging.logger import get_logger


class PostgresClient:
    """
    Simple asynchronous PostgreSQL client with pooling and retries.
    """

    def __init__(
        self,
        dsn: str,
        min_size: int = 1,
        max_size: int = 10,
        max_retries: int = 3,
        component: str = "common",
    ) -> None:
        """
        Initialize the Postgres client.

        Parameters
        ----------
        dsn : str
            PostgreSQL DSN string.
        min_size : int
            Minimum pool size.
        max_size : int
            Maximum pool size.
        max_retries : int
            Maximum number of retries per query.
        component : str
            Component label ("vendor", "authoring", "common").
        """
        self._dsn = dsn
        self._min_size = min_size
        self._max_size = max_size
        self._max_retries = max_retries
        self._pool: Optional[asyncpg.Pool] = None
        self._component = component

    async def connect(self) -> None:
        """
        Initialize the connection pool.
        """
        self._pool = await asyncpg.create_pool(
            dsn=self._dsn, min_size=self._min_size, max_size=self._max_size
        )

    async def close(self) -> None:
        """
        Close the connection pool.
        """
        if self._pool is not None:
            await self._pool.close()

    async def _run_with_retry(
        self, query_fn, trace_id: Optional[str] = None, **kwargs: Any
    ) -> Any:
        """
        Run a query function with retry and logging.

        Parameters
        ----------
        query_fn : Callable
            Callable that executes the query using a connection.
        trace_id : Optional[str]
            Correlation ID.
        kwargs : Any
            Additional logging parameters.

        Returns
        -------
        Any
            Result from the query_fn.
        """
        logger = get_logger(
            component=self._component, stage="db", feature="postgres", trace_id=trace_id
        )

        delay = 0.1
        for attempt in range(1, self._max_retries + 1):
            try:
                async with self._pool.acquire() as conn:
                    return await query_fn(conn)
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Postgres query failed on attempt %d: %s", attempt, exc
                )
                if attempt == self._max_retries:
                    logger.error(
                        "Postgres query failed permanently after %d attempts",
                        attempt,
                        ka_code="KA-DB-0003",
                    )
                    raise
                await asyncio.sleep(delay)
                delay *= 2

    async def fetch_one(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch a single row.

        Parameters
        ----------
        query : str
            SQL query.
        params : Optional[Dict[str, Any]]
            Named parameters for the query.
        trace_id : Optional[str]
            Correlation ID.

        Returns
        -------
        Optional[Dict[str, Any]]
            A single row as a dict or None.
        """

        async def _inner(conn: asyncpg.Connection) -> Optional[Dict[str, Any]]:
            row = await conn.fetchrow(query, *([] if params is None else params.values()))
            return dict(row) if row is not None else None

        return await self._run_with_retry(_inner, trace_id=trace_id)

    async def fetch_all(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch multiple rows.

        Parameters
        ----------
        query : str
            SQL query.
        params : Optional[Dict[str, Any]]
            Named parameters for the query.
        trace_id : Optional[str]
            Correlation ID.

        Returns
        -------
        List[Dict[str, Any]]
            A list of rows as dicts.
        """

        async def _inner(conn: asyncpg.Connection) -> List[Dict[str, Any]]:
            rows = await conn.fetch(query, *([] if params is None else params.values()))
            return [dict(r) for r in rows]

        return await self._run_with_retry(_inner, trace_id=trace_id)

    async def execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None,
    ) -> str:
        """
        Execute a write query (INSERT/UPDATE/DELETE).

        Parameters
        ----------
        query : str
            SQL statement.
        params : Optional[Dict[str, Any]]
            Named parameters for the query.
        trace_id : Optional[str]
            Correlation ID.

        Returns
        -------
        str
            Status string from asyncpg.
        """

        async def _inner(conn: asyncpg.Connection) -> str:
            return await conn.execute(
                query, *([] if params is None else params.values())
            )

        return await self._run_with_retry(_inner, trace_id=trace_id)
