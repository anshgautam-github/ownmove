"""Wire + generator contract for Profile Analysis.

`AnalysisContent` is deliberately the *one* schema shared by every generator
(mock and LangGraph/OpenAI) and the HTTP response. It is what
`ChatOpenAI.with_structured_output()` is bound to, so the model's raw output
either matches this shape exactly or LangChain raises — there is no
hand-rolled JSON parsing anywhere in this feature.

Score fields are plain `int`, not `Field(ge=0, le=100)`. An LLM occasionally
drifts outside a stated range; a hard pydantic constraint would turn that
into a validation exception instead of a value worth clamping. Clamping is a
deterministic, recoverable step — see utils/scoring.py — so it happens
explicitly after parsing, not as a validation side effect.

This is the "Career Intelligence Report" shape: every section here exists to
answer one specific question a person could not easily answer by reading
their own profile, and every conclusion is required (by the system prompt,
for the LLM generator; by construction, for the mock generator) to cite
specific evidence rather than a general impression. There is deliberately no
personality-trait or archetype field anywhere in this file — see
CareerSignal's docstring for why.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Importance = Literal["high", "medium", "low"]
SignalStrength = Literal["strong", "moderate", "emerging", "not observed"]
RecruiterSignalStatus = Literal["Strong", "Moderate", "Limited", "Missing", "Unknown"]


class ProfileDiagnosis(BaseModel):
    """Replaces "Executive Summary". A diagnosis, not a biography: it names
    the single strongest evidenced signal, the single biggest factor
    currently holding the score back, and the one area where the next unit
    of effort would move the score the most — each grounded in specifics
    from this profile. `summary` is the only prose paragraph in the whole
    report (120-180 words, third person, no bullets) and it must be
    consistent with the three verdicts above it, not a separate free-form
    take."""

    strongest_signal: str
    strongest_signal_evidence: list[str] = Field(default_factory=list)
    limiting_factor: str
    limiting_factor_evidence: list[str] = Field(default_factory=list)
    highest_impact_area: str
    highest_impact_reason: str
    summary: str


class CareerSignal(BaseModel):
    """One observable, named pattern in the profile — deliberately NOT a
    personality trait or archetype. The fixed vocabulary is: Technical
    Leadership, Product Building, Research Exposure, Community Involvement,
    Learning Consistency, Software Engineering Foundation. A signal is only
    ever reported at "strong" or "moderate" strength when there is real,
    countable evidence for it; a signal with weak or no evidence is reported
    honestly as "emerging" or "not observed" rather than omitted or
    inflated — omitting it would hide a real (negative) finding, and
    inflating it would fabricate a positive one. `confidence` is how sure
    the analysis is that this pattern is genuinely present, not a quality
    score, and it is shown as a number/badge, never a progress bar."""

    signal: str
    strength: SignalStrength
    confidence: int
    evidence: list[str] = Field(default_factory=list)
    interpretation: str


class MissingSignal(BaseModel):
    """A gap a recruiter or matching system would notice. Beyond naming the
    gap, this now has to justify itself in the same way every other
    recommendation in this report does: what it costs (`expected_score_impact`,
    the actual points closing this gap would add — the same number
    `score_breakdown` and `growth_simulation` are computed from, not a
    separate made-up figure), who specifically cares
    (`affected_opportunities` — the kinds of roles/programs where this gap
    is most likely to be noticed), and `recommended_action` — the concrete
    step that closes it, which `growth_simulation` reuses directly rather
    than re-deriving its own wording for the same fix."""

    title: str
    importance: Importance
    why_it_matters: str
    expected_score_impact: int
    affected_opportunities: list[str] = Field(default_factory=list)
    recommended_action: str


class ProfileContradiction(BaseModel):
    """Where the profile's *stated* direction (target_role, target_company,
    career_interests) and its *observed* evidence (experiences, skills) pull
    in different directions — e.g. targeting an ML role with zero ML
    projects logged, or listing "leadership" as an interest with no
    leadership-scoped role anywhere in the history. This is a structural
    mismatch, not a missing skill (see MissingSignal) and not a personality
    read (see CareerSignal) — it exists only when there's a real, citable gap
    between the two, and both generators return an empty list rather than
    inventing one when the profile's stated goal and its evidence already
    line up."""

    contradiction: str
    stated_goal: str
    observed_evidence: list[str] = Field(default_factory=list)
    why_it_matters: str
    how_to_close_gap: str


class ScoreFactor(BaseModel):
    """One line item in the score's math — `points` is signed (positive
    factors raise the score, negative factors lower it) so the breakdown
    reads as an itemized bill, not a vague list of pros and cons."""

    label: str
    points: int
    reason: str


class ScoreBreakdown(BaseModel):
    """Exactly why `overall_score` is what it is. This section is computed
    entirely by `utils/scoring.py::reconcile()` from the rest of the
    content — never trusted verbatim from a generator — so it is
    guaranteed to add up: `base_score + sum(positive_factors.points) -
    sum(abs(p) for p in negative_factors.points) == final_score` is an
    invariant `reconcile()` enforces, not a convention a generator is asked
    to follow."""

    base_score: int
    positive_factors: list[ScoreFactor] = Field(default_factory=list)
    negative_factors: list[ScoreFactor] = Field(default_factory=list)
    final_score: int


class GrowthAction(BaseModel):
    """One recommended action inside the Growth Simulator, with its own
    point estimate and the reasoning behind that specific number — replacing
    a flat list of strings with something a reader can actually audit."""

    action: str
    estimated_points: int
    reason: str


class GrowthSimulation(BaseModel):
    """"If you do X, Y, Z, your score could go from A to B" — but now with
    `calculation_basis` stating, in one sentence, the method behind that
    prediction (which this report's own math computes, from real missing
    signals and contradictions, not a generic "keep improving" estimate)."""

    current_score: int
    future_score: int
    actions: list[GrowthAction] = Field(default_factory=list)
    calculation_basis: str


class RecruiterSignal(BaseModel):
    """Replaces "Evidence Credibility". That section's "verified /
    partially_verified" language implied this platform had checked the
    actual contents of a GitHub repo, a resume file, or a LinkedIn profile —
    it never did. This section makes no verification claim at all: it names
    a signal a recruiter is likely to notice scanning the profile during an
    initial review, and `status` describes only what is observable from the
    profile's own stated fields (a link exists, an experience is logged, a
    skill is listed), never the quality or authenticity of what's behind
    it. `status` is a named tier (Strong / Moderate / Limited / Missing /
    Unknown), never a percentage — there is no invented confidence number
    anywhere in this model. "Unknown" is a valid, honest answer when the
    profile genuinely doesn't contain enough information to judge a signal
    either way (e.g. communication ability, from structured fields alone) —
    it must be used instead of guessing at a tier the evidence doesn't
    support. The vocabulary is fixed: Technical Experience, Public
    Portfolio, Industry Exposure, Leadership, AI/ML Focus, Open Source,
    Community Involvement, Research Experience, Communication, Professional
    Presence."""

    signal: str
    status: RecruiterSignalStatus
    why_it_matters: str
    recommended_action: str


class HighestRoiRecommendation(BaseModel):
    """The single highest-leverage next move. Every field maps to one part
    of the four-part explanation every recommendation in this report owes
    the reader: `reason` (why it matters), `evidence_gap` (what evidence is
    currently missing), `impact` (how it affects competitiveness), and
    `title` (what to do next)."""

    title: str
    evidence_gap: str
    impact: str
    reason: str
    estimated_score_gain: int


class AnalysisContent(BaseModel):
    """Exactly what a generator (mock or AI) must produce.

    This is the structured-output schema for the LLM AND the mock
    generator's return type — the router/service code cannot tell which one
    produced a given instance, which is the whole point: swapping generators
    never touches anything downstream.
    """

    overall_score: int
    profile_diagnosis: ProfileDiagnosis
    career_signals: list[CareerSignal] = Field(default_factory=list)
    missing_signals: list[MissingSignal] = Field(default_factory=list)
    profile_contradictions: list[ProfileContradiction] = Field(default_factory=list)
    score_breakdown: ScoreBreakdown
    growth_simulation: GrowthSimulation
    recruiter_signals: list[RecruiterSignal] = Field(default_factory=list)
    highest_roi_recommendation: HighestRoiRecommendation


class ProfileAnalysisResponse(AnalysisContent):
    """The full HTTP response — generator output plus persistence metadata."""

    id: str
    profile_id: str
    ai_model: str
    analysis_version: int
    created_at: datetime


class ScoreHistoryPoint(BaseModel):
    """One past analysis's headline number — powers the Profile Timeline
    section. Deliberately just these two fields, not the full
    ProfileAnalysisResponse: the timeline only ever plots overall_score
    against time, and profile_analysis is append-only history (see
    supabase/schema/012_profile_analysis.sql), so this is a cheap, narrow
    read across every past row rather than the latest one."""

    overall_score: int
    created_at: datetime
