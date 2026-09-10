"""The pipeline's final output shape - what `normalize()` produces and
`validate()` checks.

Field-for-field, this mirrors `app.schemas.opportunity.Opportunity` /
`app.models.opportunity.OpportunityRow` plus the `source`/`source_id`
de-dupe pair already present on `OpportunityRow` (see
`supabase/schema/005_opportunities_v2.sql` and
`supabase/schema/025_opportunities_ingestion_source_id_rename.sql`). That
overlap is intentional: a future persistence step should be able to
construct an `OpportunityRow` insert from a `NormalizedOpportunity` with a
straight attribute copy, no translation logic.

**Naming note:** this field was originally called `external_id` (matching
`005_opportunities_v2.sql`'s comment), but the live `public.opportunities`
table actually has a column named `source_id` - at some point after 005 was
written, the column was renamed directly on the live table without a
migration ever being committed for it (the same "changed on the live table,
brought into source control after the fact" situation `010_opportunities_v3.sql`
documents for `eligible_years`/`duration`). Every reference here was renamed
to `source_id` to match reality - see `025_opportunities_ingestion_source_id_rename.sql`.
"""

from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.opportunity import OpportunityCategory
from app.utils.text import normalise_tags


class NormalizedOpportunity(BaseModel):
    category: OpportunityCategory
    title: str
    organization: str | None = None
    logo_url: str | None = None
    description: str | None = None
    location: str | None = None
    is_remote: bool = False
    apply_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    eligible_years: list[int] = Field(default_factory=list)
    duration: str | None = None
    application_deadline: date | None = None
    posted_at: datetime | None = None

    # ---- ingestion identity, not part of the public wire schema ----------
    # Which agent produced this row, and that agent's stable id for it (e.g.
    # a slug, a listing id) - together the real de-dupe key, mirroring
    # `OpportunityRow.source` / `OpportunityRow.source_id`.
    source: str
    source_id: str

    # Traceability back to the page(s) this was extracted from - useful for
    # debugging a bad normalization without re-running discovery.
    source_url: str | None = None

    @field_validator("tags", mode="after")
    @classmethod
    def _normalise_tags(cls, value: list[str]) -> list[str]:
        return normalise_tags(value)

    @field_validator("title", "source", "source_id", mode="after")
    @classmethod
    def _strip_required(cls, value: str) -> str:
        return value.strip()
