"""Configurable per-agent schedules.

This package defines WHEN an agent should run (`ScheduleConfig`) and keeps
a registry of those schedules (`JobRegistry`) — it does not itself run
anything on a timer. No scheduler daemon (APScheduler, Celery beat, a cron
entry calling a management command) is wired up yet; that is a deliberately
separate, later piece of work once there is somewhere to persist ingestion
output. See `app/ingestion/README.md`.
"""

from app.ingestion.jobs.registry import JobRegistry, job_registry
from app.ingestion.jobs.schedule import ScheduleConfig, should_run

__all__ = ["ScheduleConfig", "should_run", "JobRegistry", "job_registry"]
