"""public.opportunities and public.saved_opportunities."""

from datetime import date, datetime

from app.models.base import DBModel


class OpportunityRow(DBModel):
    id: str
    category: str
    title: str
    organization: str | None = None
    logo_url: str | None = None
    description: str | None = None
    location: str | None = None
    is_remote: bool = False
    apply_url: str | None = None
    tags: list[str] = []
    # Where the row came from (manual entry vs. a named scraper/partner feed)
    # and its stable ID there — the real de-dupe key for ingestion.
    source: str = "manual"
    source_id: str | None = None
    # Graduation years this listing is open to; matched against
    # profiles.graduation_year. Empty means "no year restriction stated".
    eligible_years: list[int] = []
    # Free text ("6 weeks", "48 hours", "Summer 2026") — categories don't
    # share a duration unit, so this is intentionally not a numeric column.
    duration: str | None = None
    application_deadline: date | None = None
    posted_at: datetime | None = None
    is_active: bool = True
    created_at: datetime | None = None


class SavedOpportunityRow(DBModel):
    id: str | None = None
    user_id: str
    opportunity_id: str
    created_at: datetime | None = None
