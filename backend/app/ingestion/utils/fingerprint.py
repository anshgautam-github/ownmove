"""Deterministic, content-based fingerprint for cross-source duplicate
detection.

`(source, external_id)` (`supabase/schema/005_opportunities_v2.sql`) is the
strongest identity signal when present — "this exact listing, as tracked by
this specific source." It says nothing about two DIFFERENT sources listing
the SAME real-world opportunity (e.g. a company's own careers page and a
separate aggregator both listing the same program). `generate_fingerprint()`
hashes the opportunity's actual content instead of its origin, so
`OpportunityService.find_duplicate()` can catch that case too — see
`supabase/schema/019_opportunities_ingestion.sql`'s `fingerprint` column.
"""

import hashlib
from urllib.parse import urlparse

from app.ingestion.models.opportunity import NormalizedOpportunity


def _normalize_text(value: str | None) -> str:
    """Lowercase, trim, and collapse internal whitespace, so "Google  Inc."
    and "google inc." (or trailing/leading spaces from a scraped page)
    hash identically."""
    return " ".join((value or "").strip().lower().split())


def _normalize_url(value: str | None) -> str:
    """Strips query string, fragment, and a trailing slash, and lowercases
    scheme/host — so a tracking parameter (`?utm_source=...`) or a stray
    trailing slash doesn't make the same page hash differently."""
    if not value:
        return ""
    parsed = urlparse(value.strip().lower())
    path = parsed.path.rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def generate_fingerprint(opportunity: NormalizedOpportunity) -> str:
    """SHA-256 over normalized (title, organization, apply_url).

    Deterministic: the same real-world opportunity always produces the same
    fingerprint regardless of which agent extracted it, when, or in what
    field order — normalization happens before hashing specifically so
    cosmetic differences (case, whitespace, URL tracking params) don't
    produce a different value for what is, in substance, the same listing.
    """
    parts = [
        _normalize_text(opportunity.title),
        _normalize_text(opportunity.organization),
        _normalize_url(opportunity.apply_url),
    ]
    digest_input = "|".join(parts).encode("utf-8")
    return hashlib.sha256(digest_input).hexdigest()
