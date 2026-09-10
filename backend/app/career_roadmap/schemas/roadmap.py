"""Wire + generator contract for Career Roadmap.

`RoadmapContent` is the one schema both generators (mock and LangChain/
OpenAI) and the HTTP response share — same pattern as
`app.profile_analysis.schemas.analysis.AnalysisContent`. LangChain's
`with_structured_output(RoadmapContent, method="json_schema", strict=True)`
binds directly to this class, so the model's raw output either matches this
shape exactly or LangChain raises before the caller ever sees it.

This is a roadmap, not a report: unlike Profile Analysis there is no numeric
score to reconcile here, so there is no `utils/scoring.py` equivalent in
this module — every generator is responsible for its own internally
consistent output (phase durations that sum to the requested timeline, task
counts that make sense for the requested weekly commitment), enforced by
construction in the mock generator and by prompt instruction for the LLM
generator.

This shape is deliberately deeper than a v1 roadmap would be (see the
module's own git history / PR description if curious why): a phase is no
longer "an objective plus a flat task list" — it is a dependency-aware node
in a curriculum graph (`builds_on`/`unlocks`), containing several concrete
learning-and-building `objectives`, each with its own topic list, resources,
and a single demonstrable `deliverable`. The intent is that nothing in this
schema can be filled in with a generic, could-apply-to-any-role sentence —
every field either names something specific or is empty.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Priority = Literal["high", "medium", "low"]

# What a resource actually is, so the frontend can render a distinct badge
# per type (see roadmap/ResourceItem.jsx) instead of a flat, undifferentiated
# link list.
ResourceType = Literal[
    "course", "book", "documentation", "paper", "tutorial", "video", "repository", "practice"
]

TimelineMonths = Literal[3, 6]
WeeklyCommitment = Literal[5, 10, 15, 20]
PrimaryGoal = Literal[
    "Get an Internship",
    "Land a Full-Time Job",
    "Prepare for Placements",
    "Switch Career",
    "Research",
    "Build Strong Portfolio",
]


class StartingPoint(BaseModel):
    """The gap analysis the rest of the roadmap is derived from — made
    visible to the user rather than kept as invisible internal reasoning, so
    the roadmap's shape is legible ("this is why it looks like this"), not
    just internally consistent."""

    existing_strengths: list[str] = Field(
        default_factory=list,
        description="Skills/signals the profile already supports for this target role — what the "
        "roadmap deliberately does NOT re-teach.",
    )
    priority_gaps: list[str] = Field(
        default_factory=list,
        description="The highest-impact things missing between the current profile and this target "
        "role, in priority order — what the roadmap exists to close.",
    )
    roadmap_strategy: str = Field(
        description="1-3 sentences on the overall approach this roadmap takes and why, given the "
        "strengths/gaps above, the timeline, and the weekly commitment."
    )


class IndustryLandscape(BaseModel):
    """The current, real-world technical landscape for this target role —
    general industry context, NOT a personalized claim about the
    candidate's own profile (that's what `StartingPoint` is for). Exists
    because a roadmap driven purely by the candidate's personal gaps can
    still leave them unaware of what practitioners in this exact role are
    actually using right now — a framework/tool worth knowing about even if
    it isn't explicitly taught as its own phase in this specific plan."""

    current_frameworks_and_tools: list[str] = Field(
        default_factory=list,
        description="Frameworks, libraries, platforms, and tools in active, common use for this "
        "target role today, named specifically (e.g. 'LangGraph for agent orchestration', not "
        "'agent frameworks' or 'modern tools').",
    )
    emerging_trends: list[str] = Field(
        default_factory=list,
        description="Well-established, current shifts reshaping this role, stated factually and "
        "conservatively — not speculation or hype about the distant future.",
    )
    why_this_matters: str = Field(
        description="1-2 sentences on why staying current on this landscape specifically matters "
        "for this target role and the candidate's stated primary goal."
    )


class RoadmapResource(BaseModel):
    """One recommended resource for an objective. Deliberately has NO `url`
    field: a specific URL a generator states with confidence today can still
    be wrong, moved, or dead by the time the user actually clicks it (course
    platforms restructure, docs get reorganized, papers get re-hosted) — so
    rather than try to keep a generated link accurate forever, this names
    the resource (what it is, who publishes it, why it's recommended) and
    leaves finding the current URL to the user's own search, which is more
    reliable than any link this system could hard-code or generate."""

    title: str
    provider: str
    type: ResourceType
    reason: str = Field(description="Why this specific resource, for this specific objective.")
    free: bool


class RoadmapObjective(BaseModel):
    """One concrete, scoped unit of learning-and-building inside a phase.
    This is the level real depth lives at — a phase without several of these
    is a phase that hasn't actually been thought through."""

    title: str
    objective: str = Field(description="What this objective is, specifically — not a restated title.")
    why_it_matters: str = Field(
        description="Why THIS objective, for THIS role, at THIS point in the roadmap — not a generic "
        "justification that could apply to any skill."
    )
    topics: list[str] = Field(
        default_factory=list,
        description="The specific sub-topics this objective covers — concrete technical terms, not "
        "vague category names.",
    )
    estimated_hours: int = Field(description="Realistic total hours for this objective given the stated weekly commitment.")
    priority: Priority
    resources: list[RoadmapResource] = Field(default_factory=list)
    deliverable: str = Field(
        description="The concrete thing produced by doing this objective — code, a written artifact, a "
        "working demo — not 'understand X'."
    )
    completion_criteria: list[str] = Field(
        default_factory=list,
        description="Concrete, observable signs this objective is actually done — never a vague "
        "aspiration like 'understand transformers'.",
    )


class RoadmapMilestone(BaseModel):
    """The single checkpoint that closes out a phase. Represents
    demonstrated capability, not course completion — `completion_criteria`
    must be things a user (or someone else) could look at and verify."""

    title: str
    description: str
    completion_criteria: list[str] = Field(default_factory=list)


class RoadmapPhase(BaseModel):
    """One node in the roadmap's dependency graph. `builds_on` and
    `unlocks` are what make the roadmap read as a connected curriculum
    rather than an arbitrary list of chapters — every phase past the first
    should be able to name what it assumes and what it sets up."""

    phase_number: int
    title: str
    duration_weeks: int
    purpose: str = Field(description="What this phase accomplishes, in one or two sentences.")
    personalization_reason: str = Field(
        description="Why THIS phase, in THIS position, for THIS user specifically — should reference "
        "something concrete from their profile (a skill they already have, an experience, a stated "
        "gap), not generic reasoning."
    )
    builds_on: list[str] = Field(
        default_factory=list,
        description="What prior capability (from the profile, or an earlier phase) this phase assumes.",
    )
    unlocks: list[str] = Field(
        default_factory=list,
        description="What this phase makes the user ready to learn or build next.",
    )
    objectives: list[RoadmapObjective] = Field(default_factory=list)
    milestone: RoadmapMilestone


class RoadmapContent(BaseModel):
    """Exactly what a generator (mock or AI) must produce. Mirrors
    `AnalysisContent`'s role in profile_analysis: the structured-output
    schema for the LLM AND the mock generator's return type, so the router/
    service code cannot tell which one produced a given instance.

    Deliberately does NOT declare `primary_goal`, `timeline_months`,
    `weekly_commitment`, `id`, `user_id`, `llm_model`, `generated_at`, or
    `updated_at` as fields — those are supplied authoritatively by
    `roadmap_service._to_response` from the DB row, not echoed back through
    generated content (see that function's docstring for why)."""

    title: str
    target_role: str
    overall_goal: str
    estimated_duration: str
    overview: str
    industry_landscape: IndustryLandscape
    starting_point: StartingPoint
    phases: list[RoadmapPhase] = Field(default_factory=list)
    expected_skills: list[str] = Field(default_factory=list)
    portfolio_outcomes: list[str] = Field(
        default_factory=list,
        description="The concrete, shippable artifacts (projects, write-ups, contributions) the user "
        "should have produced by the end — the tangible evidence of the roadmap, not a skills list "
        "restated.",
    )
    final_outcome: str = Field(
        description="What the user should concretely be able to DEMONSTRATE by the end — capabilities, "
        "artifacts, and target-role readiness. Never a guarantee of employment or expertise."
    )


class RoadmapGenerateRequest(BaseModel):
    """What the setup screen (or the Regenerate action, replaying the same
    values back) submits. `target_role` defaults to the profile's own
    `target_role` in the frontend, but is always sent explicitly — the
    backend never silently substitutes a different role than what was
    shown to the user."""

    target_role: str = Field(..., max_length=200)
    timeline_months: TimelineMonths
    weekly_commitment: WeeklyCommitment
    primary_goal: PrimaryGoal


class CareerRoadmapResponse(RoadmapContent):
    """The full HTTP response — generator output plus persistence metadata
    and the setup answers it was generated from. Unlike
    `profile_analysis` (append-only history), `career_roadmaps` holds at
    most one row per user (`unique(user_id)` in the schema) — regenerating
    overwrites this same row rather than inserting a new one, so there is no
    separate "history" endpoint here."""

    id: str
    user_id: str
    timeline_months: int
    weekly_commitment: int
    primary_goal: str
    llm_model: str | None = None
    generated_at: datetime
    updated_at: datetime
