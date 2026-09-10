"""Row shapes for public.career_roadmaps and public.roadmap_activity.

Kept separate from schemas/roadmap.py on purpose (same rule profile_analysis
follows, see app/models/base.py's docstring): this describes what Postgres
actually stores. `career_roadmaps` has a `unique(user_id)` constraint — one
row per user, overwritten on regenerate — unlike `profile_analysis`, which
is append-only history. `roadmap_json` is one jsonb blob holding the entire
generated `RoadmapContent` shape (title/overview/starting_point/phases/
expected_skills/portfolio_outcomes/final_outcome/...) rather than one column
per section, since none of that structure needs to be queried or indexed
independently — it's read back whole and rendered whole.

`roadmap_json`'s internal shape was deepened considerably (starting_point,
per-phase builds_on/unlocks/personalization_reason, per-phase objectives
with resources, a single milestone per phase) without any change to the
column itself — it is still just `dict` here. No migration is required for
that change; only rows generated before it will have the old, shallower
shape, which `roadmap_service._to_response` handles defensively (see that
file) rather than assuming every stored row matches the current schema."""

from datetime import datetime

from app.models.base import DBModel


class CareerRoadmapRow(DBModel):
    id: str
    user_id: str
    target_role: str
    timeline_months: int
    weekly_commitment: int
    primary_goal: str
    roadmap_json: dict
    llm_model: str | None = None
    generated_at: datetime
    updated_at: datetime


class CareerRoadmapUpsert(DBModel):
    """What the repository sends on upsert — no `id`, DB fills that in on
    first insert and keeps it on subsequent updates (the upsert matches on
    `user_id`, not `id`)."""

    user_id: str
    target_role: str
    timeline_months: int
    weekly_commitment: int
    primary_goal: str
    roadmap_json: dict
    llm_model: str


class RoadmapActivityInsert(DBModel):
    """One row per generate/regenerate action — a lightweight audit trail,
    not something the current UI reads back (see README for why the table
    exists but isn't surfaced yet)."""

    roadmap_id: str
    user_id: str
    activity_type: str
    description: str | None = None
