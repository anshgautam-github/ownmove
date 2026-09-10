"""Deterministic post-processing shared by every generator.

This is the piece that keeps the feature from being "just a ChatGPT wrapper":
no generator's raw output is ever returned to the client as-is. Three things
in particular are fully *computed* here, not trusted from whatever a
generator (mock or LLM) produced:

1. `overall_score` and `score_breakdown` — the score is the output of
   `_build_score_breakdown()`, an itemized, auditable formula over the
   content's own recruiter_signals/career_signals/missing_signals/
   profile_contradictions. A generator's own sense of the score is never
   read; `score_breakdown.final_score` IS `overall_score`, by construction,
   every time.
2. `growth_simulation` — rebuilt from `missing_signals` (specifically each
   gap's own `expected_score_impact` and `recommended_action`), so the
   simulator's predicted points always match the same math the score
   breakdown used, instead of a generator inventing a second, inconsistent
   estimate.
3. `highest_roi_recommendation.estimated_score_gain` — pinned to the single
   biggest missing-signal gap when one exists, for the same reason.

Both the mock generator and the LangGraph pipeline call `reconcile()` as
their last step, so the guarantee is identical regardless of which one ran.
"""

from app.profile_analysis.schemas.analysis import (
    AnalysisContent,
    GrowthAction,
    GrowthSimulation,
    ScoreBreakdown,
    ScoreFactor,
)

_IMPORTANCE_PENALTY = {"high": 10, "medium": 5, "low": 2}
_CONTRADICTION_PENALTY = 8
_BASE_SCORE = 50
_MAX_GROWTH_ACTIONS = 3
_RECRUITER_SIGNAL_POINTS = {"Strong": 3, "Moderate": 1, "Limited": -2, "Missing": -4, "Unknown": 0}
_RECRUITER_SIGNAL_FACTOR_RANGE = 20


def clamp(value: int, low: int = 0, high: int = 100) -> int:
    return max(low, min(high, round(value)))


def _average(values: list[int]) -> float:
    return sum(values) / len(values) if values else 0.0


def _build_score_breakdown(content: AnalysisContent) -> ScoreBreakdown:
    """Every point in `overall_score` traces to one line item here — this is
    the actual formula, not a post-hoc explanation of a different number."""
    positive: list[ScoreFactor] = []
    negative: list[ScoreFactor] = []

    if content.recruiter_signals:
        raw_points = sum(_RECRUITER_SIGNAL_POINTS.get(s.status, 0) for s in content.recruiter_signals)
        points = clamp(raw_points, low=-_RECRUITER_SIGNAL_FACTOR_RANGE, high=_RECRUITER_SIGNAL_FACTOR_RANGE)
        counts: dict[str, int] = {}
        for s in content.recruiter_signals:
            counts[s.status] = counts.get(s.status, 0) + 1
        # Fixed, readable order regardless of dict insertion order.
        breakdown_text = ", ".join(
            f"{counts[status]} {status.lower()}"
            for status in ("Strong", "Moderate", "Limited", "Missing", "Unknown")
            if status in counts
        )
        factor = ScoreFactor(
            label="Recruiter-visible signals",
            points=points,
            reason=f"Across {len(content.recruiter_signals)} recruiter-visible signal(s): {breakdown_text}.",
        )
        (positive if points >= 0 else negative).append(factor)

    if content.career_signals:
        confidences = [clamp(s.confidence) for s in content.career_signals]
        avg = _average(confidences)
        points = round((avg - 50) * 0.3)
        n = len(content.career_signals)
        factor = ScoreFactor(
            label="Career signal strength",
            points=points,
            reason=f"Average confidence across {n} detected career signal(s) is {round(avg)}%.",
        )
        (positive if points >= 0 else negative).append(factor)

    for signal in content.missing_signals:
        penalty = _IMPORTANCE_PENALTY.get(signal.importance, 2)
        negative.append(
            ScoreFactor(label=f"Missing: {signal.title}", points=-penalty, reason=signal.why_it_matters)
        )

    for contradiction in content.profile_contradictions:
        negative.append(
            ScoreFactor(
                label=contradiction.contradiction,
                points=-_CONTRADICTION_PENALTY,
                reason=contradiction.why_it_matters,
            )
        )

    final_score = clamp(_BASE_SCORE + sum(f.points for f in positive) + sum(f.points for f in negative))

    return ScoreBreakdown(
        base_score=_BASE_SCORE,
        positive_factors=positive,
        negative_factors=negative,
        final_score=final_score,
    )


def _build_growth_simulation(content: AnalysisContent, current_score: int) -> GrowthSimulation:
    """Rebuilt from the same `missing_signals` the score breakdown already
    penalized — the simulator's "if you fix this, you gain N" claim is
    therefore always the mirror image of the penalty being removed, not an
    independent guess."""
    ranked = sorted(content.missing_signals, key=lambda s: s.expected_score_impact, reverse=True)
    top = ranked[:_MAX_GROWTH_ACTIONS]

    actions = [
        GrowthAction(
            action=signal.recommended_action,
            estimated_points=clamp(signal.expected_score_impact, low=0, high=30),
            reason=signal.why_it_matters,
        )
        for signal in top
    ]

    total_gain = sum(a.estimated_points for a in actions)
    future_score = clamp(current_score + total_gain, low=current_score, high=100)

    if actions:
        basis = (
            f"Sum of the score impact of closing your top {len(actions)} missing signal(s) below "
            f"({', '.join(f'+{a.estimated_points}' for a in actions)}), capped at 100."
        )
    else:
        basis = (
            "No missing signals detected right now, so there is no specific gap to simulate closing — "
            "the score is currently limited by evidence depth rather than any one absence. Keep adding "
            "projects and experiences to raise it further."
        )

    return GrowthSimulation(
        current_score=current_score,
        future_score=future_score,
        actions=actions,
        calculation_basis=basis,
    )


def reconcile(content: AnalysisContent) -> AnalysisContent:
    """Clamp every score in-place, then recompute overall_score,
    score_breakdown, growth_simulation, and the highest-ROI gain so all four
    are internally consistent, and return the same instance (mutation is
    fine here — this is the last stop before the caller persists the
    result)."""
    for signal in content.career_signals:
        signal.confidence = clamp(signal.confidence)

    for missing in content.missing_signals:
        missing.expected_score_impact = clamp(missing.expected_score_impact, low=0, high=30)

    content.score_breakdown = _build_score_breakdown(content)
    content.overall_score = content.score_breakdown.final_score

    content.growth_simulation = _build_growth_simulation(content, content.overall_score)

    ranked_gaps = sorted(content.missing_signals, key=lambda s: s.expected_score_impact, reverse=True)
    if ranked_gaps:
        content.highest_roi_recommendation.estimated_score_gain = clamp(
            ranked_gaps[0].expected_score_impact, low=0, high=100 - content.overall_score
        )
    else:
        content.highest_roi_recommendation.estimated_score_gain = clamp(
            content.highest_roi_recommendation.estimated_score_gain, low=0, high=100 - content.overall_score
        )

    return content
