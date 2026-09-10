"""Background job queue abstraction.

AI work (embedding backfills, recommendation recomputation, roadmap
generation) is too slow for a request/response cycle. Routes enqueue; workers
execute. Kept behind an interface so the concrete broker (Redis/RQ, Celery,
Supabase queues) can be chosen later without touching callers.
"""

from typing import Any, Protocol

from app.core.config import settings
from app.core.exceptions import NotImplementedYetError


class JobQueue(Protocol):
    async def enqueue(self, task: str, /, **payload: Any) -> str: ...


class InMemoryQueue:
    """Development stand-in. Executes nothing; records intent only."""

    def __init__(self) -> None:
        self.jobs: list[tuple[str, dict]] = []

    async def enqueue(self, task: str, /, **payload: Any) -> str:
        self.jobs.append((task, payload))
        return f"local-{len(self.jobs)}"


def get_queue() -> JobQueue:
    if not settings.ENABLE_BACKGROUND_WORKERS:
        return InMemoryQueue()
    raise NotImplementedYetError("No production job queue is configured yet.")
