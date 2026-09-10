"""Wire + generator contract for Career Simulation.

Career Simulation answers a different question than Profile Analysis
(current-state diagnosis) or Career Roadmap (how to progress): "BEFORE I
spend time doing X, what would X actually add to my profile for THIS target
role?" It is a decision-support tool, not a motivational one — see this
module's README for the full product framing.

`SimulationResult` is the generator contract (mock and LLM both return this)
for a single hypothetical action. `ComparisonResult` wraps two independent
`SimulationResult`s plus a head-to-head verdict, for the "compare two moves"
mode. Both are stored whole in `career_simulations.result` (jsonb) — same
"one blob, read back whole" pattern `career_roadmaps.roadmap_json` uses,
not one column per section.

Enum casing note: the LLM-facing `VerdictLevel` is UPPERCASE
(HIGH_VALUE/USEFUL/LIMITED_VALUE/LOW_VALUE) to match the exact structured-
output shape specified for this feature, but the DB's flat `verdict` text
column has a CHECK constraint requiring lowercase snake_case
(high_value/useful/limited_value/low_value). `simulation_service.py` is
responsible for translating between the two — see its `_VERDICT_DB_MAP`.
The nested `result.verdict.level` stored inside the jsonb blob stays
UPPERCASE (it is the generator's literal output, unmodified); only the
flat top-level DB column is lowercased, since that's the one the SQL CHECK
constraint governs.
"""

from typing import Literal

import json

from pydantic import BaseModel, Field, field_validator

# ---- enums shared with models/simulation.py's DB-facing shapes -----------
#
# Matches career_simulations_type_check exactly, one-to-one with the seven
# simulation types this feature supports (A-G in the product spec).
# "compare_moves" is never sent as an ordinary create request — it's only
# ever set server-side when persisting a comparison (see
# services/simulation_service.py's compare_simulations()).
SimulationType = Literal[
    "build_project",
    "gain_experience",
    "learn_skill",
    "certification",
    "open_source",
    "change_target_role",
    "compare_moves",
]

# The six types a single (non-comparison) simulation request may specify.
SingleSimulationType = Literal[
    "build_project",
    "gain_experience",
    "learn_skill",
    "certification",
    "open_source",
    "change_target_role",
]

SimulationStatus = Literal["pending", "completed", "failed"]

VerdictLevel = Literal["HIGH_VALUE", "USEFUL", "LIMITED_VALUE", "LOW_VALUE"]
GapStatus = Literal["RESOLVED", "PARTIALLY_ADDRESSED", "UNCHANGED"]


class ActionInfo(BaseModel):
    """What was actually simulated, restated so the result is
    self-describing without needing to join back to the request."""

    type: SimulationType
    description: str = Field(description="A concise, specific restatement of the hypothetical action simulated.")


class Verdict(BaseModel):
    """The headline judgment. Represents incremental value for THIS
    candidate toward THIS target role — never the universal value of the
    activity in the abstract."""

    level: VerdictLevel
    reasoning: str = Field(
        description="Grounded in current profile + hypothetical action + target role. Never a generic "
        "statement that could apply to any candidate doing this activity."
    )


class SignalChange(BaseModel):
    """A brand-new observable signal the hypothetical action would create —
    something not present in the profile today."""

    signal: str
    before: str = Field(description="The state of this signal today, in the real profile.")
    after: str = Field(description="The state this signal would reach if the hypothetical action were completed.")
    why_it_matters: str
    relevance_to_target: str = Field(description="Why this signal specifically matters for the stated target role.")


class StrengthenedSignal(BaseModel):
    """An existing signal the action would deepen rather than create from
    nothing — distinct from `SignalChange`, which is net-new."""

    signal: str
    before: str
    after: str
    reason: str


class GapImpact(BaseModel):
    """How the action affects one specific, previously-identified gap
    between the candidate and the target role."""

    gap: str
    status: GapStatus
    explanation: str


class EvidenceCreated(BaseModel):
    """Tangible evidence the action would produce IF completed as
    described — a repository, a write-up, a demonstrated responsibility —
    never a vague claim of improvement."""

    evidence: str
    significance: str


class SupportedClaim(BaseModel):
    """Something the candidate could truthfully claim AFTER completing the
    action that they cannot strongly claim today."""

    claim: str
    basis: str = Field(description="What specifically, about the hypothetical action, supports this claim.")


class UnsupportedClaim(BaseModel):
    """A claim that completing this action would NOT, by itself, support —
    stated explicitly so the result never implies more than the scenario
    actually described (see the module README's scope-discipline test)."""

    claim: str
    reason: str


class RemainingGap(BaseModel):
    """A gap between the candidate and the target role that would still
    exist after the hypothetical action — always populated when true, so
    the result never reads as unconditionally positive."""

    gap: str
    why_it_remains: str


class RedundancyAnalysis(BaseModel):
    """Whether this action adds genuinely new signal, or mostly restates
    something the profile already demonstrates more strongly — the
    feature's core differentiator from a generic "is this activity good"
    answer. See the module README's redundancy-detection test."""

    is_redundant: bool
    explanation: str


class SimulationResult(BaseModel):
    """Exactly what a generator (mock or AI) must produce for ONE
    hypothetical action. Both `MockSimulationGenerator` and
    `LangGraphSimulationGenerator` return this — the service/router layer
    cannot tell which one produced a given instance. Stored whole inside
    `career_simulations.result` for a single (non-comparison) simulation."""

    simulation_summary: str = Field(description="A short, plain-language summary of what was simulated and found.")
    target_role: str
    action: ActionInfo
    verdict: Verdict
    new_signals: list[SignalChange] = Field(default_factory=list)
    strengthened_signals: list[StrengthenedSignal] = Field(default_factory=list)
    gap_impact: list[GapImpact] = Field(default_factory=list)
    evidence_created: list[EvidenceCreated] = Field(default_factory=list)
    new_claims_supported: list[SupportedClaim] = Field(default_factory=list)
    claims_still_unsupported: list[UnsupportedClaim] = Field(default_factory=list)
    remaining_gaps: list[RemainingGap] = Field(default_factory=list)
    redundancy_analysis: RedundancyAnalysis
    limitations: list[str] = Field(
        default_factory=list,
        description="Anything the simulation could not confidently assess — e.g. insufficient profile "
        "information, or a scenario too vague to evaluate precisely. Never left silently empty just to "
        "look complete; state a real limitation when one exists.",
    )


class ComparisonVerdict(BaseModel):
    better_fit: Literal["option_a", "option_b"]
    explanation: str = Field(
        description="Grounded specifically in the candidate's OWN current profile and target role — "
        "never a general statement about which activity is 'better' in the abstract."
    )


class ComparisonResult(BaseModel):
    """The full output of "compare two moves" mode. `option_a` and
    `option_b` are each a complete, independent `SimulationResult` —
    evaluated on their own first, exactly as a single simulation would be —
    and `comparison` is the head-to-head synthesis on top. Stored whole
    inside `career_simulations.result` for a `simulation_type ==
    'compare_moves'` row."""

    target_role: str
    option_a: SimulationResult
    option_b: SimulationResult
    comparison: ComparisonVerdict


# ---- request schemas -------------------------------------------------------

# scenario_input is intentionally a free-form dict (see SimulationCreateRequest's
# own docstring for why), which means nothing about its shape bounds its size.
# Without this, a single request within the AI_EXPENSIVE rate limit's request-
# count budget could still carry an arbitrarily large payload straight into the
# LLM prompt -- inflating per-request token cost well beyond what request-count
# throttling accounts for. 20KB is generous for genuine scenario form data
# (a handful of short fields) while still bounding the worst case.
_MAX_SCENARIO_INPUT_JSON_BYTES = 20_000


def _validate_scenario_input_size(value: dict) -> dict:
    if len(json.dumps(value)) > _MAX_SCENARIO_INPUT_JSON_BYTES:
        raise ValueError(
            f"scenario_input is too large (must serialize to at most "
            f"{_MAX_SCENARIO_INPUT_JSON_BYTES} bytes of JSON)."
        )
    return value


class SimulationCreateRequest(BaseModel):
    """What the setup screen submits for a single (non-comparison)
    simulation. `scenario_input` is intentionally a free-form dict rather
    than a discriminated union of per-type models: each simulation type's
    form collects a different, small set of fields (see the module README
    for the field set each type collects), and this keeps the request body
    forgiving of a type's exact field set changing without a backend
    migration — `utils/context.py` reads whatever keys are present and
    degrades gracefully for missing ones."""

    simulation_type: SingleSimulationType
    target_role: str = Field(
        max_length=200,
        description="The target role this simulation is evaluated against. For 'change_target_role', this "
        "IS the hypothetical new role; for every other type, this is normally the profile's own target role.",
    )
    scenario_title: str = Field(..., max_length=300)
    scenario_input: dict = Field(default_factory=dict)

    _validate_scenario_input = field_validator("scenario_input")(_validate_scenario_input_size)


class SimulationOption(BaseModel):
    """One side of a 'compare two moves' request — same shape as
    `SimulationCreateRequest` minus `target_role`, since both options in a
    comparison are always evaluated against the same target role."""

    simulation_type: SingleSimulationType
    scenario_title: str = Field(..., max_length=300)
    scenario_input: dict = Field(default_factory=dict)

    _validate_scenario_input = field_validator("scenario_input")(_validate_scenario_input_size)


class SimulationCompareRequest(BaseModel):
    target_role: str = Field(..., max_length=200)
    option_a: SimulationOption
    option_b: SimulationOption


# ---- response schemas -------------------------------------------------------


class CareerSimulationResponse(BaseModel):
    """The full HTTP response for one `career_simulations` row. `result` is
    `None` while `status == 'pending'` (never actually observed by the
    frontend today, since generation happens synchronously within the
    request, but modeled honestly for the failure/timeout case) or when
    `status == 'failed'`. Its inner shape is a `SimulationResult` dict for
    every `simulation_type` except `compare_moves`, where it is a
    `ComparisonResult` dict instead — the frontend branches on
    `simulation_type` to know which shape to expect, same way it already
    branches on other Career AI response shapes."""

    id: str
    profile_id: str
    simulation_type: SimulationType
    target_role: str
    scenario_title: str
    scenario_input: dict
    result: dict | None = None
    verdict: str | None = None
    status: SimulationStatus
    model_used: str | None = None
    created_at: str
    completed_at: str | None = None


class SimulationHistoryItem(BaseModel):
    """One row in the "Recent Simulations" list — deliberately minimal
    (scenario, target role, verdict, date), matching the spec's explicit
    instruction not to build complex analytics around simulation history."""

    id: str
    simulation_type: SimulationType
    target_role: str
    scenario_title: str
    verdict: str | None = None
    status: SimulationStatus
    created_at: str
