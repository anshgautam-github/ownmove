"""The first two pipeline stages' output shapes: a URL worth extracting
(`discover()`), and the raw content fetched from it (`extract()`).

Both are intentionally "dumb" containers — no parsing, no business rules.
Interpreting `raw_content` into a real opportunity is `normalize()`'s job.
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.utils.time import utc_now

RawContentType = Literal["html", "json", "text"]


class DiscoveredListing(BaseModel):
    """One candidate URL surfaced by an agent's `discover()`, plus whatever
    cheap metadata was visible on the listing/index page without a second
    request (e.g. a title glimpsed in a card, a listing id from a query
    param) — `extract()` may use these as hints but must not assume they are
    complete or authoritative."""

    url: str
    source: str
    discovered_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RawExtraction(BaseModel):
    """Unprocessed content fetched from a `DiscoveredListing.url`.

    `raw_content` is kept as a plain string deliberately — agents are free to
    fetch HTML, JSON, or plain text, and `normalize()` (which knows the
    source's shape) is the only place that should parse it. The pipeline
    itself never inspects `raw_content`.
    """

    url: str
    source: str
    fetched_at: datetime = Field(default_factory=utc_now)
    content_type: RawContentType = "html"
    http_status: int | None = None
    raw_content: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
