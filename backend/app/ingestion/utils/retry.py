"""Retry support for any async ingestion call (discovery/extraction
requests are the expected use, but nothing here is HTTP-specific).

Exponential backoff with full jitter (sleep `random(0, backoff)` rather than
exactly `backoff`) so a batch of listings failing at the same moment doesn't
retry in lockstep and re-hammer the source all at once.
"""

import asyncio
import random
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import TypeVar

from app.ingestion.models.config import RetryConfig

T = TypeVar("T")


class RetryExhaustedError(Exception):
    """Raised once every attempt has failed. Wraps the last exception seen
    so the original traceback/type isn't lost, while giving callers one
    stable exception type to catch regardless of what `fn` itself raises."""

    def __init__(self, attempts: int, last_error: BaseException):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Gave up after {attempts} attempt(s): {last_error}")


def _compute_delay(attempt: int, config: RetryConfig) -> float:
    backoff = min(config.base_delay_seconds * (2 ** (attempt - 1)), config.max_delay_seconds)
    return random.uniform(0, backoff) if config.jitter else backoff


async def retry_async(
    fn: Callable[[], Awaitable[T]],
    *,
    config: RetryConfig | None = None,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Run `fn` (a zero-arg async callable — callers close over whatever
    arguments they need, e.g. `lambda: agent.extract(ctx, listing)`),
    retrying on any exception in `retry_on` with exponential backoff +
    jitter, up to `config.max_attempts` total attempts.

    `on_retry(attempt_number, exception)` is called before each sleep, so
    callers can log the attempt without this function needing to know
    anything about logging.

    Raises `RetryExhaustedError` if every attempt fails.
    """
    config = config or RetryConfig()
    last_error: BaseException | None = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            return await fn()
        except retry_on as exc:
            last_error = exc
            if attempt == config.max_attempts:
                break
            if on_retry:
                on_retry(attempt, exc)
            await asyncio.sleep(_compute_delay(attempt, config))

    raise RetryExhaustedError(config.max_attempts, last_error) from last_error


def with_retry(
    config: RetryConfig | None = None,
    *,
    retry_on: tuple[type[BaseException], ...] = (Exception,),
):
    """Decorator form of `retry_async`, for a method that should always
    retry the same way (e.g. `BaseOpportunityAgent.extract`'s default
    behavior) rather than wrapping individual call sites."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await retry_async(lambda: func(*args, **kwargs), config=config, retry_on=retry_on)

        return wrapper

    return decorator
