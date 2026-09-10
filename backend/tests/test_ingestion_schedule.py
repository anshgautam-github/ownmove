"""Scheduler correctness for `app.ingestion` -- specifically that
`DevpostHackathonAgent`'s daily job (registered at import time, see
`app/ingestion/agents/sources/devpost.py`'s bottom-of-module
`job_registry.set("devpost", ScheduleConfig.cron("0 6 * * *"))`) actually
becomes "due" at 06:00 UTC and nowhere else, that `DevfolioAgent`'s own
every-3-days job (`job_registry.set("devfolio", ScheduleConfig.every(3 * 24 * 60 * 60))`,
see `app/ingestion/agents/sources/devfolio.py`) becomes due exactly 3 days
after its last run (an `interval` schedule, not `cron` -- see that
module's own scheduling comment for why: production actually enforces
this cadence via an external scheduler calling `/ingestion/run/devfolio`
directly, not via this registration's `due_sources()`/`run-due` path, since
`JobRegistry`'s `_last_run_at` is in-memory and doesn't survive a process
restart on ephemeral hosting -- this file still covers the registration
itself, so `GET /ingestion/due` keeps reporting it accurately), and that
`should_run()`/`JobRegistry` handle invalid or missing schedule
configuration by refusing to construct rather than silently misbehaving at
runtime.

`app.ingestion.jobs.schedule.should_run()`'s own generic interval/cron
logic already has baseline coverage in `tests/test_ingestion_pipeline.py`
(`test_interval_schedule_due_logic` / `test_cron_schedule_due_logic`); this
file is specifically about (a) each hackathon source's OWN registered
schedule and (b) timezone correctness, since "the intended schedule is a
specific UTC time daily, do not assume local timezone" was an explicit
requirement.
"""

from datetime import UTC, datetime, timedelta

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
    at_six = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    assert "devpost" in job_registry.due_sources(now=at_six)


def test_devpost_due_sources_excludes_devpost_off_the_matching_minute():
    for hour, minute in [(5, 59), (6, 1), (0, 0), (18, 0), (23, 59)]:
        moment = datetime(2026, 9, 10, hour, minute, tzinfo=UTC)
        assert "devpost" not in job_registry.due_sources(now=moment), (hour, minute)


# ---------------------------------------------------------------------------
# Devfolio's own registration -- `interval`, every 3 days, deliberately
# NOT on the same clock-time-based mechanism Devpost uses; see
# devfolio.py's own scheduling comment for why (both the "every 3 days"
# choice itself and the operational caveat about what actually enforces it
# in production today).
# ---------------------------------------------------------------------------

_THREE_DAYS_SECONDS = 3 * 24 * 60 * 60


def test_devfolio_is_registered_with_an_every_3_days_interval_schedule():
    schedule = job_registry.get("devfolio")

    assert schedule is not None
    assert schedule.kind == "interval"
    assert schedule.interval_seconds == _THREE_DAYS_SECONDS
    assert schedule.enabled is True


def test_devfolio_due_sources_includes_devfolio_when_never_run():
    # Interval schedules (unlike cron) are due immediately the first time
    # they're checked -- there's no "matching minute" to wait for. Real
    # behavior difference from the old daily-cron registration, worth
    # pinning down explicitly rather than assuming it carried over.
    any_moment = datetime(2026, 9, 10, 3, 17, tzinfo=UTC)
    assert "devfolio" in job_registry.due_sources(now=any_moment)


def test_devfolio_due_sources_excludes_devfolio_before_3_days_have_passed():
    last_run = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    job_registry.record_run("devfolio", at=last_run)
    deltas = (timedelta(seconds=1), timedelta(days=1), timedelta(days=2, hours=23, minutes=59))
    try:
        for delta in deltas:
            moment = last_run + delta
            assert "devfolio" not in job_registry.due_sources(now=moment), delta
    finally:
        job_registry._last_run_at.pop("devfolio", None)  # noqa: SLF001 -- test cleanup only


def test_devfolio_due_sources_includes_devfolio_once_3_days_have_passed():
    last_run = datetime(2026, 9, 10, 12, 0, tzinfo=UTC)
    job_registry.record_run("devfolio", at=last_run)
    try:
        exactly_3_days_later = last_run + timedelta(days=3)
        assert "devfolio" in job_registry.due_sources(now=exactly_3_days_later)
    finally:
        job_registry._last_run_at.pop("devfolio", None)  # noqa: SLF001 -- test cleanup only


def test_devpost_and_devfolio_schedules_are_independent():
    # Devpost's cron schedule and Devfolio's interval schedule are governed
    # by entirely different mechanisms now (clock-time-of-day vs. time-
    # since-last-run) -- confirms checking one's due-ness at a moment that
    # matches (or doesn't match) the OTHER's schedule shape has no
    # crosstalk between the two sources' entries in the registry.
    at_six_devfolio_never_run = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    assert set(job_registry.due_sources(now=at_six_devfolio_never_run)) == {"devpost", "devfolio"}

    last_run = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    job_registry.record_run("devfolio", at=last_run)
    try:
        one_day_later_at_devpost_matching_minute = datetime(2026, 9, 11, 6, 0, tzinfo=UTC)
        assert job_registry.due_sources(now=one_day_later_at_devpost_matching_minute) == ["devpost"]
    finally:
        job_registry._last_run_at.pop("devfolio", None)  # noqa: SLF001 -- test cleanup only


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
    ist_local_06_00_as_utc = datetime(2026, 9, 10, 0, 30, tzinfo=UTC)
    assert should_run(schedule, last_run_at=None, now=ist_local_06_00_as_utc) is False

    # The genuine 06:00 UTC moment that same "day" (UTC) IS due.
    actual_06_00_utc = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    assert should_run(schedule, last_run_at=None, now=actual_06_00_utc) is True


def test_cron_06_00_utc_fires_again_the_next_day_after_a_run():
    schedule = ScheduleConfig.cron("0 6 * * *")
    day_one = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    day_two = day_one + timedelta(days=1)

    # Already ran within this same matching minute.
    assert should_run(schedule, last_run_at=day_one, now=day_one) is False
    # A full day later, due again.
    assert should_run(schedule, last_run_at=day_one, now=day_two) is True


def test_cron_06_00_utc_not_due_again_later_the_same_day():
    schedule = ScheduleConfig.cron("0 6 * * *")
    ran_at = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    later_same_day = datetime(2026, 9, 10, 14, 0, tzinfo=UTC)

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

    at_six = datetime(2026, 9, 10, 6, 0, tzinfo=UTC)
    assert registry.due_sources(now=at_six) == []


def test_job_registry_remove_clears_both_schedule_and_last_run():
    registry = JobRegistry()
    registry.set("some-source", ScheduleConfig.every(60))
    registry.record_run("some-source", at=datetime(2026, 9, 10, 6, 0, tzinfo=UTC))

    registry.remove("some-source")

    assert registry.get("some-source") is None
    assert registry.last_run_at("some-source") is None
