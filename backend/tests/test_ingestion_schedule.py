"""Scheduler correctness for `app.ingestion` -- specifically that
`DevpostHackathonAgent`'s daily job (registered at import time, see
`app/ingestion/agents/sources/devpost.py`'s bottom-of-module
`job_registry.set("devpost", ScheduleConfig.cron("0 6 * * *"))`) actually
becomes "due" at 06:00 UTC and nowhere else, that `DevfolioAgent`'s own
daily job (`job_registry.set("devfolio", ScheduleConfig.cron("0 12 * * *"))`,
see `app/ingestion/agents/sources/devfolio.py`) becomes due at 12:00 UTC and
nowhere else, and that `should_run()`/`JobRegistry` handle invalid or
missing schedule configuration by refusing to construct rather than
silently misbehaving at runtime.

`app.ingestion.jobs.schedule.should_run()`'s own generic interval/cron
logic already has baseline coverage in `tests/test_ingestion_pipeline.py`
(`test_interval_schedule_due_logic` / `test_cron_schedule_due_logic`); this
file is specifically about (a) each hackathon source's OWN registered
schedule and (b) timezone correctness, since "the intended schedule is a
specific UTC time daily, do not assume local timezone" was an explicit
requirement.
"""

from datetime import datetime, timedelta, timezone

import pytest

# Importing the agents.sources package registers DevpostHackathonAgent and
# DevfolioAgent (and schedules both) as a side effect -- see that package's
# __init__.py.
import app.ingestion.agents.sources  # noqa: F401
from app.ingestion.jobs.registry import JobRegistry, job_registry
from app.ingestion.jobs.schedule import ScheduleConfig, should_run

# ---------------------------------------------------------------------------
# Devpost's own registration
# ---------------------------------------------------------------------------


def test_devpost_is_registered_with_a_daily_06_00_utc_cron_schedule():
    schedule = job_registry.get("devpost")

    assert schedule is not None
    assert schedule.kind == "cron"
    assert schedule.cron_expression == "0 6 * * *"
    assert schedule.enabled is True


def test_devpost_due_sources_includes_devpost_at_06_00_utc():
    at_six = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)
    assert "devpost" in job_registry.due_sources(now=at_six)


def test_devpost_due_sources_excludes_devpost_off_the_matching_minute():
    for hour, minute in [(5, 59), (6, 1), (0, 0), (18, 0), (23, 59)]:
        moment = datetime(2026, 9, 10, hour, minute, tzinfo=timezone.utc)
        assert "devpost" not in job_registry.due_sources(now=moment), (hour, minute)


# ---------------------------------------------------------------------------
# Devfolio's own registration -- offset from Devpost's (12:00 UTC vs 06:00
# UTC) purely so the two hackathon sources' daily runs don't land in the
# same minute; see devfolio.py's own scheduling comment.
# ---------------------------------------------------------------------------


def test_devfolio_is_registered_with_a_daily_12_00_utc_cron_schedule():
    schedule = job_registry.get("devfolio")

    assert schedule is not None
    assert schedule.kind == "cron"
    assert schedule.cron_expression == "0 12 * * *"
    assert schedule.enabled is True


def test_devfolio_due_sources_includes_devfolio_at_12_00_utc():
    at_noon = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)
    assert "devfolio" in job_registry.due_sources(now=at_noon)


def test_devfolio_due_sources_excludes_devfolio_off_the_matching_minute():
    for hour, minute in [(11, 59), (12, 1), (0, 0), (6, 0), (23, 59)]:
        moment = datetime(2026, 9, 10, hour, minute, tzinfo=timezone.utc)
        assert "devfolio" not in job_registry.due_sources(now=moment), (hour, minute)


def test_devpost_and_devfolio_do_not_collide_on_the_same_run_minute():
    # Both hackathon sources are registered simultaneously (see
    # app/ingestion/agents/sources/__init__.py) -- confirms their schedules
    # don't accidentally share a matching minute, which would make
    # /ingestion/run-due trigger both at once every day.
    at_six = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)
    at_noon = datetime(2026, 9, 10, 12, 0, tzinfo=timezone.utc)

    assert job_registry.due_sources(now=at_six) == ["devpost"]
    assert job_registry.due_sources(now=at_noon) == ["devfolio"]


# ---------------------------------------------------------------------------
# Timezone correctness: "06:00" must mean 06:00 UTC, never a local wall
# clock time that happens to read "06:00" in some other offset.
# ---------------------------------------------------------------------------


def test_cron_06_00_utc_is_not_due_at_a_different_utc_hour_that_reads_06_00_locally():
    schedule = ScheduleConfig.cron("0 6 * * *")

    # 06:00 IST (UTC+5:30) is 00:30 UTC -- must NOT be treated as due, since
    # `should_run()`/`_cron_matches()` only ever look at the UTC wall-clock
    # fields of the `now` passed in (see `app.utils.time.utc_now()` -- every
    # real caller passes a UTC-aware datetime, never a local one).
    ist_local_06_00_as_utc = datetime(2026, 9, 10, 0, 30, tzinfo=timezone.utc)
    assert should_run(schedule, last_run_at=None, now=ist_local_06_00_as_utc) is False

    # The genuine 06:00 UTC moment that same "day" (UTC) IS due.
    actual_06_00_utc = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)
    assert should_run(schedule, last_run_at=None, now=actual_06_00_utc) is True


def test_cron_06_00_utc_fires_again_the_next_day_after_a_run():
    schedule = ScheduleConfig.cron("0 6 * * *")
    day_one = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)
    day_two = day_one + timedelta(days=1)

    # Already ran within this same matching minute.
    assert should_run(schedule, last_run_at=day_one, now=day_one) is False
    # A full day later, due again.
    assert should_run(schedule, last_run_at=day_one, now=day_two) is True


def test_cron_06_00_utc_not_due_again_later_the_same_day():
    schedule = ScheduleConfig.cron("0 6 * * *")
    ran_at = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)
    later_same_day = datetime(2026, 9, 10, 14, 0, tzinfo=timezone.utc)

    assert should_run(schedule, last_run_at=ran_at, now=later_same_day) is False


# ---------------------------------------------------------------------------
# Invalid / missing configuration
# ---------------------------------------------------------------------------


def test_schedule_config_cron_requires_an_expression():
    with pytest.raises(ValueError):
        ScheduleConfig(kind="cron")  # cron_expression missing


def test_schedule_config_interval_requires_interval_seconds():
    with pytest.raises(ValueError):
        ScheduleConfig(kind="interval")  # interval_seconds missing


@pytest.mark.parametrize(
    "expression",
    [
        "0 6 * *",  # only 4 fields
        "0 6 * * * *",  # 6 fields
        "60 6 * * *",  # minute out of range
        "0 24 * * *",  # hour out of range
        "0 6 32 * *",  # day-of-month out of range
        "0 6 * 13 *",  # month out of range
        "0 6 * * 8",  # weekday out of range
        "not-a-cron-expression * * * *",
    ],
)
def test_schedule_config_rejects_invalid_cron_expressions(expression):
    with pytest.raises(ValueError):
        ScheduleConfig.cron(expression)


def test_job_registry_get_returns_none_for_an_unregistered_source():
    registry = JobRegistry()
    assert registry.get("nonexistent-source") is None


def test_job_registry_due_sources_empty_when_nothing_registered():
    registry = JobRegistry()
    assert registry.due_sources() == []


def test_job_registry_due_sources_skips_a_disabled_schedule():
    registry = JobRegistry()
    disabled = ScheduleConfig(kind="cron", cron_expression="0 6 * * *", enabled=False)
    registry.set("some-source", disabled)

    at_six = datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc)
    assert registry.due_sources(now=at_six) == []


def test_job_registry_remove_clears_both_schedule_and_last_run():
    registry = JobRegistry()
    registry.set("some-source", ScheduleConfig.every(60))
    registry.record_run("some-source", at=datetime(2026, 9, 10, 6, 0, tzinfo=timezone.utc))

    registry.remove("some-source")

    assert registry.get("some-source") is None
    assert registry.last_run_at("some-source") is None
