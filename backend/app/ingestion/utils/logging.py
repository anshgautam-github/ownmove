"""Structured-ish logging for ingestion runs.

Reuses `app.core.logging.get_logger` — the same console (dev) / JSON (prod)
setup as the rest of the API — rather than introducing a second logging
config, and layers per-run/per-source/per-stage context on top via
`logging.LoggerAdapter`, so a single grepped `run_id` reconstructs one
agent's entire run across discover/extract/normalize/validate.
"""

import logging

from app.core.logging import get_logger


class IngestionLogAdapter(logging.LoggerAdapter):
    """Prepends `[key=value ...]` context to every message. Works with both
    of `app.core.logging`'s formatters unmodified: the JSON formatter still
    sees one `message` string (now containing the context), and console
    output gets the same context inline — no change to `core/logging.py`
    required."""

    def process(self, msg, kwargs):
        context = " ".join(f"{key}={value}" for key, value in self.extra.items() if value is not None)
        return (f"[{context}] {msg}" if context else msg), kwargs

    def bind(self, **extra) -> "IngestionLogAdapter":
        """A new adapter with additional context merged in, e.g.
        `logger.bind(stage="extract", url=listing.url)` inside a loop —
        without mutating the shared per-run logger other stages still hold
        a reference to."""
        merged = {**self.extra, **extra}
        return IngestionLogAdapter(self.logger, merged)


def get_agent_logger(source: str, run_id: str | None = None) -> IngestionLogAdapter:
    base = get_logger(f"app.ingestion.agents.{source}")
    return IngestionLogAdapter(base, {"source": source, "run_id": run_id})
