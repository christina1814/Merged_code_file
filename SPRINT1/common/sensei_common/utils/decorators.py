"""
Common decorators for logging spans and retrying operations.
"""

from __future__ import annotations

import asyncio
import functools
import random
from typing import Any, Awaitable, Callable, TypeVar, Union

from sensei_common.logging.logger import get_logger  # adapt to your logger module
from sensei_common.utils.timing import start_timer
from sensei_common.utils.exceptions import SenseiError

F = TypeVar("F", bound=Callable[..., Any])


def log_span(component: str, stage: str, feature: str) -> Callable[[F], F]:
    """
    Decorator that logs start/end and duration for a function.

    Usage:
        @log_span("authoring", "api", "submit_draft")
        async def submit(...):
            ...
    """

    def decorator(func: F) -> F:
        logger = get_logger(component=component, stage=stage, feature=feature)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            timer = start_timer()
            logger.info("span_start", extra={"component": component, "stage": stage, "feature": feature})
            try:
                result = await func(*args, **kwargs)
                logger.info(
                    "span_end",
                    extra={
                        "component": component,
                        "stage": stage,
                        "feature": feature,
                        "duration_ms": timer.elapsed_ms,
                    },
                )
                return result
            except SenseiError as e:
                logger.error(
                    "span_error",
                    extra={
                        "component": component,
                        "stage": stage,
                        "feature": feature,
                        "duration_ms": timer.elapsed_ms,
                        "ka_code": e.code,
                        "http_status": e.http_status,
                    },
                )
                raise
            except Exception as e:  # noqa: BLE001
                logger.exception(
                    "span_exception",
                    extra={
                        "component": component,
                        "stage": stage,
                        "feature": feature,
                        "duration_ms": timer.elapsed_ms,
                    },
                )
                raise

        return async_wrapper  # type: ignore[misc]

    return decorator


def retry_with_backoff(
    retries: int = 3,
    base_delay_ms: int = 200,
    max_delay_ms: int = 2000,
) -> Callable[[F], F]:
    """
    Decorator for async functions to retry on retriable SenseiError.

    Intended for:
    - transient DB errors
    - Kafka 5xx
    - HTTP 5xx from providers
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            attempt = 0
            while True:
                try:
                    return await func(*args, **kwargs)
                except SenseiError as e:
                    attempt += 1
                    if not e.retriable or attempt > retries:
                        raise
                    delay = min(
                        max_delay_ms,
                        base_delay_ms * (2 ** (attempt - 1)),
                    )
                    # jitter
                    delay = delay * (0.8 + random.random() * 0.4)
                    await asyncio.sleep(delay / 1000.0)

        return async_wrapper  # type: ignore[misc]

    return decorator
