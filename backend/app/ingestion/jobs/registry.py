"""Maps a registered agent's `source` to its `ScheduleConfig`.

Deliberately separate from `AgentRegistry` (`app.ingestion.agents.registry`)
— an agent can exist and be runnable on demand
(`IngestionService.run_source()`) without having a schedule at all; adding
one is opt-in, one call to `job_registry.set(...)`.
"""

from datetime import datetime

from app.ingestion.jobs.schedule import ScheduleConfig, should_run


class JobRegistry:
    def __init__(self) -> None:
        self._schedules: dict[str, ScheduleConfig] = {}
        self._last_run_at: dict[str, datetime] = {}

    def set(self, source: str, schedule: ScheduleConfig) -> None:
        self._schedules[source] = schedule

    def get(self, source: str) -> ScheduleConfig | None:
        return self._schedules.get(source)

    def remove(self, source: str) -> None:
        self._schedules.pop(source, None)
        self._last_run_at.pop(source, None)

    def record_run(self, source: str, *, at: datetime) -> None:
        """Called after an `IngestionService` run completes, successful or
        not — scheduling cares about "did we attempt this recently", not
        "did it succeed"; a persistently failing source should still back
        off on its normal cadence rather than retry every polling tick."""
        self._last_run_at[source] = at

    def last_run_at(self, source: str) -> datetime | None:
        return self._last_run_at.get(source)

    def due_sources(self, *, now: datetime | None = None) -> list[str]:
        """Sources whose schedule says they should run right now. A future
        scheduler loop (APScheduler, a periodic Celery beat task, a cron
        entry polling once a minute) is the intended caller — nothing in
        this framework calls this on a timer itself yet."""
        return sorted(
            source
            for source, schedule in self._schedules.items()
            if should_run(schedule, last_run_at=self._last_run_at.get(source), now=now)
        )

    def all_sources(self) -> list[str]:
        return sorted(self._schedules)


# Process-wide registry, same pattern as `agent_registry` — a source's
# module registers a schedule for itself alongside registering its agent
# class, if it wants one.
job_registry = JobRegistry()
