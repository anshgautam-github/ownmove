"""`ScheduleConfig` — how often an agent *should* run, independent of
whether anything currently reads that value to actually run it.

Two kinds, matching the two ways this tends to get expressed:

- `interval`: "every N seconds" — evaluated fully by `should_run()` below,
  no extra dependency needed.
- `cron`: a standard 5-field cron expression ("0 */6 * * *") — evaluated by
  the minimal matcher in this file. Deliberately dependency-free (no
  `croniter`) since the only thing needed right now is "does this expression
  match this minute", not calendar-accurate "next N run times" math; if that
  ever becomes a real requirement, swap `_cron_matches` for `croniter`
  without changing `ScheduleConfig`'s shape.
"""

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.utils.time import utc_now

ScheduleKind = Literal["interval", "cron"]

_CRON_FIELD_RE = re.compile(r"^(\*|\d+)(-(\d+))?(/(\d+))?$")


class ScheduleConfig(BaseModel):
    kind: ScheduleKind = "interval"
    enabled: bool = True

    # ---- kind="interval" ---------------------------------------------------
    interval_seconds: int | None = Field(default=None, gt=0)

    # ---- kind="cron" --------------------------------------------------------
    # Standard 5-field: minute hour day-of-month month day-of-week.
    cron_expression: str | None = None

    @model_validator(mode="after")
    def _check_required_field(self) -> "ScheduleConfig":
        if self.kind == "interval" and self.interval_seconds is None:
            raise ValueError("kind='interval' requires interval_seconds.")
        if self.kind == "cron":
            if not self.cron_expression:
                raise ValueError("kind='cron' requires cron_expression.")
            _validate_cron_expression(self.cron_expression)
        return self

    @classmethod
    def every(cls, seconds: int) -> "ScheduleConfig":
        return cls(kind="interval", interval_seconds=seconds)

    @classmethod
    def cron(cls, expression: str) -> "ScheduleConfig":
        return cls(kind="cron", cron_expression=expression)


def _parse_cron_field(raw: str, min_val: int, max_val: int) -> set[int]:
    values: set[int] = set()
    for part in raw.split(","):
        match = _CRON_FIELD_RE.match(part.strip())
        if not match:
            raise ValueError(f"Invalid cron field segment: {part!r}")
        base, _, range_end, _, step_str = match.groups()

        start = min_val if base == "*" else int(base)
        end = max_val if base == "*" else (int(range_end) if range_end else start)
        step = int(step_str) if step_str else 1

        if not (min_val <= start <= max_val) or not (min_val <= end <= max_val):
            raise ValueError(f"Cron field segment out of range [{min_val}, {max_val}]: {part!r}")

        values.update(range(start, end + 1, step))
    return values


def _validate_cron_expression(expression: str) -> None:
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError(f"Cron expression must have 5 fields (minute hour day month weekday), got: {expression!r}")
    bounds = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 7)]
    for field, (lo, hi) in zip(fields, bounds, strict=True):
        _parse_cron_field(field, lo, hi)


def _cron_matches(expression: str, moment: datetime) -> bool:
    minute, hour, day, month, weekday = expression.split()
    weekday_values = _parse_cron_field(weekday, 0, 7)
    # cron treats both 0 and 7 as Sunday; Python's weekday() is Monday=0.
    if 7 in weekday_values:
        weekday_values.add(0)
    python_weekday_to_cron = (moment.weekday() + 1) % 7  # Mon=0..Sun=6 -> Sun=0..Sat=6

    return (
        moment.minute in _parse_cron_field(minute, 0, 59)
        and moment.hour in _parse_cron_field(hour, 0, 23)
        and moment.day in _parse_cron_field(day, 1, 31)
        and moment.month in _parse_cron_field(month, 1, 12)
        and python_weekday_to_cron in weekday_values
    )


def should_run(schedule: ScheduleConfig, *, last_run_at: datetime | None, now: datetime | None = None) -> bool:
    """Whether an agent on this schedule is due to run right now.

    For `interval` schedules this is exact ("has at least
    `interval_seconds` passed since `last_run_at`"). For `cron` schedules
    this checks whether `now` falls within the expression's matching
    minute — the caller is expected to poll roughly once a minute (the
    resolution cron itself operates at), same as it would with any other
    cron-driven scheduler.
    """
    if not schedule.enabled:
        return False

    now = now or utc_now()

    if last_run_at is None:
        if schedule.kind == "interval":
            # Never run before: an interval schedule is due immediately —
            # there's no "matching minute" for it to wait for.
            return True
        # A cron schedule that has never run is NOT due at every moment
        # just because it hasn't run yet — it's still only due at its own
        # matching minute, same as it would be for any later check. Falling
        # through to _cron_matches below (instead of returning True here)
        # is what makes a never-run agent scheduled for "daily at 10:00"
        # wait for 10:00 rather than firing the instant it's first polled.
        assert schedule.cron_expression is not None
        return _cron_matches(schedule.cron_expression, now)

    if schedule.kind == "interval":
        assert schedule.interval_seconds is not None
        return (now - last_run_at).total_seconds() >= schedule.interval_seconds

    assert schedule.cron_expression is not None
    if last_run_at.replace(second=0, microsecond=0) == now.replace(second=0, microsecond=0):
        return False  # already ran within this same matching minute
    return _cron_matches(schedule.cron_expression, now)
