"""Time helpers. Always UTC, always ISO-8601 on the wire."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def iso(value: datetime | None = None) -> str:
    return (value or utc_now()).isoformat()
