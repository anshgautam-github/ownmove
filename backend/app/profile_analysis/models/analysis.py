"""Row shape for public.profile_analysis.

Kept separate from schemas/analysis.py on purpose (same rule the rest of the
backend follows, see app/models/base.py's docstring): this describes what
Postgres actually stores — every jsonb column is a loose `dict | list | None`
because a row written by an older analysis_version may not match the current
AnalysisContent schema exactly. ProfileAnalysisResponse (the wire contract)
is what guarantees a fixed shape to the frontend; the row model does not.

Column set below reflects the "Career Intelligence Report" redesign
(profile_diagnosis / career_signals / profile_contradictions /
score_breakdown / recruiter_signals — see
supabase/schema/014_profile_analysis_intelligence_report.sql and
supabase/schema/015_profile_analysis_recruiter_signals.sql). Earlier column
sets (career_dna, career_blind_spots, recruiter_view, evidence_scores,
evidence_credibility) still exist in the live table for any rows written
before these migrations, but nothing in the current codebase reads or writes
those columns anymore — see analysis_service.py's ValidationError handling
for how an old-shape row is treated as "no analysis yet" rather than
crashing.
"""

from app.models.base import DBModel, TimestampedModel


class ProfileAnalysisRow(TimestampedModel):
    id: str
    profile_id: str
    overall_score: int | None = None
    profile_diagnosis: dict | None = None
    career_signals: list | None = None
    missing_signals: list | None = None
    profile_contradictions: list | None = None
    score_breakdown: dict | None = None
    growth_simulation: dict | None = None
    recruiter_signals: list | None = None
    highest_roi_recommendation: dict | None = None
    ai_model: str | None = None
    analysis_version: int = 1


class ProfileAnalysisInsert(DBModel):
    """What the repository sends on insert — no id/timestamps, DB fills those in."""

    profile_id: str
    overall_score: int
    profile_diagnosis: dict
    career_signals: list
    missing_signals: list
    profile_contradictions: list
    score_breakdown: dict
    growth_simulation: dict
    recruiter_signals: list
    highest_roi_recommendation: dict
    ai_model: str
    analysis_version: int
