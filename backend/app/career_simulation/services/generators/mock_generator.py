"""Deterministic, zero-dependency generator.

Runs with no API key and no network call — every field is computed from
rule-based heuristics against the actual profile/experience data in
`SimulationContext`, plus the hypothetical scenario the user described. This
is the fallback path only: when `OPENAI_API_KEY` is configured, `factory.py`
switches to `LangGraphSimulationGenerator`, whose system prompt is where
this feature's real depth guarantee lives (nuanced, role-aware, scenario-
scoped reasoning about incremental value for arbitrary hypothetical
actions). This generator's job is narrower but non-negotiable: never invent
a probability/percentage/guarantee, and get the feature's single most
important behavior right even without a model — that the SAME hypothetical
action must produce a DIFFERENT verdict for two candidates whose profiles
already do or don't demonstrate the relevant skill (the redundancy-
detection test the module README describes).

Every heuristic here is intentionally simple and inspectable: a skill/topic
extracted from the scenario is classified as "demonstrated" (appears in
experience skills or experience text), "listed" (only in profile.
current_skills), or "absent" (neither) against the candidate's own profile,
and that classification — not the activity type in isolation — is what
drives the verdict, gap impact, and redundancy fields.
"""

from app.career_simulation.schemas.simulation import (
    ActionInfo,
    ComparisonResult,
    ComparisonVerdict,
    EvidenceCreated,
    GapImpact,
    RedundancyAnalysis,
    RemainingGap,
    SignalChange,
    SimulationResult,
    StrengthenedSignal,
    SupportedClaim,
    UnsupportedClaim,
    Verdict,
)
from app.career_simulation.services.generators.base import BaseSimulationGenerator
from app.career_simulation.utils.context import SIMULATION_TYPE_LABELS, SimulationContext

# ---- a compact role -> core skill vocabulary, only used for the
# change_target_role simulation type and for a light role-relevance check.
# Deliberately smaller than career_roadmap's own library (duplicating that
# module's full depth isn't warranted here — this mock path exists to be
# honest and directionally correct, not to be an exhaustive per-role
# curriculum; see career_roadmap/services/generators/mock_generator.py for
# why the two modules keep independent copies rather than importing across
# the module boundary). ---------------------------------------------------
_ROLE_SKILL_LIBRARY: dict[str, list[str]] = {
    "llm engineer": ["python", "pytorch", "transformers", "prompt engineering", "vector databases", "rag", "langchain"],
    "ai engineer": ["python", "machine learning", "pytorch", "vector databases", "prompt engineering"],
    "machine learning engineer": ["python", "statistics", "pytorch", "scikit-learn", "mlops"],
    "ml engineer": ["python", "statistics", "pytorch", "scikit-learn", "mlops"],
    "data scientist": ["python", "statistics", "sql", "pandas", "machine learning"],
    "data analyst": ["sql", "statistics", "data visualization", "python"],
    "data engineer": ["python", "sql", "data pipelines", "etl", "cloud"],
    "backend engineer": ["python", "sql", "databases", "api design", "system design"],
    "backend developer": ["python", "sql", "databases", "api design", "system design"],
    "frontend engineer": ["html", "css", "javascript", "react", "typescript"],
    "frontend developer": ["html", "css", "javascript", "react", "typescript"],
    "full stack developer": ["javascript", "react", "node.js", "sql", "api design"],
    "full stack engineer": ["javascript", "react", "node.js", "sql", "api design"],
    "devops engineer": ["linux", "docker", "kubernetes", "ci/cd", "cloud"],
    "cloud engineer": ["networking", "cloud", "infrastructure as code", "docker"],
    "product manager": ["user research", "product strategy", "roadmapping", "analytics"],
    "mobile developer": ["git", "rest apis", "mobile ui", "swift", "kotlin"],
    "cybersecurity engineer": ["networking", "linux", "security fundamentals", "scripting"],
    "software engineer": ["data structures", "algorithms", "git", "system design", "testing"],
}
_GENERIC_ROLE_SKILLS = ["git", "system design", "testing", "technical communication"]

# Simulation types whose evidence is applied/demonstrated work — these can
# reach HIGH_VALUE when they fill a genuine, currently-absent gap. Types
# NOT in this set (learn_skill, certification) are capped at USEFUL even
# for a genuine gap, per the module README's "listed vs demonstrated"
# discipline — learning about something or being certified in it is weaker
# evidence than having built or done it.
_APPLIED_EVIDENCE_TYPES = {"build_project", "gain_experience", "open_source"}

_VERDICT_ORDER = ["LOW_VALUE", "LIMITED_VALUE", "USEFUL", "HIGH_VALUE"]


def _matching_role_skills(target_role: str) -> list[str]:
    role_lower = target_role.lower().strip()
    for key in sorted(_ROLE_SKILL_LIBRARY, key=len, reverse=True):
        if key in role_lower:
            return _ROLE_SKILL_LIBRARY[key]
    return _GENERIC_ROLE_SKILLS


def _primary_topic(simulation_type: str, scenario_input: dict, scenario_title: str) -> str:
    """The single most representative skill/technology name for this
    scenario — used to classify demonstrated/listed/absent against the
    profile. Falls back to the scenario title itself (or the simulation
    type's label) when the form didn't collect a clean topic field, so this
    never raises on a sparse `scenario_input`."""
    candidates_by_type = {
        "build_project": scenario_input.get("technologies") or [scenario_input.get("project_topic")],
        "gain_experience": scenario_input.get("skills_involved") or [scenario_input.get("role_domain")],
        "learn_skill": [scenario_input.get("skill")],
        "certification": [scenario_input.get("certification_name") or scenario_input.get("domain")],
        "open_source": [scenario_input.get("technology_domain")],
        "change_target_role": [scenario_input.get("new_target_role")],
    }
    candidates = candidates_by_type.get(simulation_type) or []
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return scenario_title or SIMULATION_TYPE_LABELS.get(simulation_type, simulation_type)


def _topic_tokens(topic: str) -> list[str]:
    if not topic:
        return []
    for sep in (",", "/", " and ", " & "):
        topic = topic.replace(sep, ",")
    return [t.strip() for t in topic.split(",") if t.strip()]


def _skill_state(context: SimulationContext, token: str) -> str:
    """'demonstrated' | 'listed' | 'absent' — the classification everything
    else in this generator is built from."""
    token_l = token.lower().strip()
    if not token_l:
        return "absent"
    demonstrated = any(token_l in s.lower() for s in context.experience_skills) or any(
        token_l in f"{e.get('title', '')} {e.get('description', '')}".lower() for e in context.experiences
    )
    if demonstrated:
        return "demonstrated"
    if any(token_l in s.lower() for s in context.current_skills):
        return "listed"
    return "absent"


def _overall_state(states: list[str]) -> str:
    """Collapse several tokens' states into one: 'demonstrated' if most
    tokens already are, 'absent' if most aren't represented at all,
    otherwise 'listed'."""
    if not states:
        return "absent"
    if states.count("demonstrated") >= len(states) / 2:
        return "demonstrated"
    if states.count("absent") >= len(states) / 2:
        return "absent"
    return "listed"


def _role_relevant(tokens: list[str], target_role: str) -> bool:
    role_skills = [s.lower() for s in _matching_role_skills(target_role)]
    if not tokens:
        return True
    for token in tokens:
        token_l = token.lower()
        if any(token_l in skill or skill in token_l for skill in role_skills):
            return True
    return False


def _mentions_scale(scenario_input: dict) -> bool:
    """Whether the scenario itself claimed production/scale/deployment —
    the scope-discipline check: without this, a mock 'build a RAG project'
    result must not claim 'production experience' just because the type is
    build_project (see the module README's second quality test)."""
    keywords = ("production", "deploy", "scale", "users", "traffic", "live")
    text = " ".join(str(v) for v in scenario_input.values() if v).lower()
    return any(keyword in text for keyword in keywords)


def _verdict_for(simulation_type: str, state: str, relevant: bool) -> str:
    if state == "demonstrated":
        level = "LOW_VALUE" if not relevant else "LIMITED_VALUE"
    elif state == "listed":
        level = "USEFUL" if simulation_type in _APPLIED_EVIDENCE_TYPES else "LIMITED_VALUE"
    else:  # absent — a genuine gap
        level = "HIGH_VALUE" if simulation_type in _APPLIED_EVIDENCE_TYPES else "USEFUL"
    if not relevant:
        # Cap: an action irrelevant to the target role can never be the
        # candidate's top-value move, regardless of how novel it is to them.
        capped_index = min(_VERDICT_ORDER.index(level), _VERDICT_ORDER.index("LIMITED_VALUE"))
        level = _VERDICT_ORDER[capped_index]
    return level


class MockSimulationGenerator(BaseSimulationGenerator):
    name = "mock-v1"

    async def generate(self, context: SimulationContext) -> SimulationResult:
        topic = _primary_topic(context.simulation_type, context.scenario_input, context.scenario_title)
        tokens = _topic_tokens(topic)
        states = [_skill_state(context, token) for token in tokens] or ["absent"]
        state = _overall_state(states)
        relevant = _role_relevant(tokens, context.target_role)
        level = _verdict_for(context.simulation_type, state, relevant)
        is_redundant = state == "demonstrated"
        scale_claimed = _mentions_scale(context.scenario_input)

        type_label = SIMULATION_TYPE_LABELS.get(context.simulation_type, context.simulation_type)
        topic_text = topic or "this area"

        verdict = Verdict(level=level, reasoning=self._verdict_reasoning(context, topic_text, state, relevant, level))

        new_signals = []
        strengthened_signals = []
        if state == "absent":
            new_signals.append(
                SignalChange(
                    signal=f"Demonstrated exposure to {topic_text}",
                    before="Not present on the profile in any form.",
                    after=f"Would exist as a direct result of: {type_label.lower()}.",
                    why_it_matters=f"{topic_text} is not currently supported by anything on the profile.",
                    relevance_to_target=f"Directly relevant to {context.target_role}." if relevant else (
                        f"Not strongly tied to {context.target_role} specifically, though still a new signal."
                    ),
                )
            )
        elif state == "listed":
            strengthened_signals.append(
                StrengthenedSignal(
                    signal=f"{topic_text} proficiency",
                    before="Listed on the profile, without a project or experience demonstrating it.",
                    after="Would move from listed-only to demonstrated, applied use.",
                    reason=f"{type_label} converts a claimed skill into evidenced capability.",
                )
            )
        else:
            strengthened_signals.append(
                StrengthenedSignal(
                    signal=f"{topic_text} proficiency",
                    before="Already demonstrated through existing experience/projects.",
                    after="Would add one more instance of largely the same evidence.",
                    reason="The profile already shows this capability more strongly than this action would add.",
                )
            )

        gap_impact = self._gap_impact(context, topic_text, state, context.simulation_type)
        evidence_created = self._evidence_created(context.simulation_type, topic_text)
        new_claims, unsupported_claims = self._claims(context, topic_text, state, scale_claimed)
        remaining_gaps = self._remaining_gaps(context, topic_text, state)

        redundancy = RedundancyAnalysis(
            is_redundant=is_redundant,
            explanation=(
                f"{topic_text} is already demonstrated by existing experience on the profile, so this "
                "action would mostly restate evidence that already exists rather than add new signal."
                if is_redundant
                else f"{topic_text} is not currently demonstrated on the profile, so this action would "
                "add genuinely new signal rather than repeat something already shown."
            ),
        )

        limitations = []
        if not context.latest_analysis:
            limitations.append(
                "No Profile Analysis has been run yet, so gap impact is estimated from the raw profile "
                "rather than from a previously-identified, named gap."
            )
        if not tokens:
            limitations.append("The scenario did not specify a clear skill or topic, so this evaluation is approximate.")

        return SimulationResult(
            simulation_summary=(
                f"Simulated '{context.scenario_title or type_label}' for target role {context.target_role}: "
                f"{topic_text} is currently {state} on the profile."
            ),
            target_role=context.target_role,
            action=ActionInfo(type=context.simulation_type, description=context.scenario_title or type_label),
            verdict=verdict,
            new_signals=new_signals,
            strengthened_signals=strengthened_signals,
            gap_impact=gap_impact,
            evidence_created=evidence_created,
            new_claims_supported=new_claims,
            claims_still_unsupported=unsupported_claims,
            remaining_gaps=remaining_gaps,
            redundancy_analysis=redundancy,
            limitations=limitations,
        )

    async def compare(self, context_a: SimulationContext, context_b: SimulationContext) -> ComparisonResult:
        result_a = await self.generate(context_a)
        result_b = await self.generate(context_b)

        rank = {level: i for i, level in enumerate(_VERDICT_ORDER)}
        a_score = rank[result_a.verdict.level]
        b_score = rank[result_b.verdict.level]
        # Tie-break on redundancy (non-redundant wins) then on remaining-gaps
        # count (fewer remaining gaps addressed = less differentiation, so
        # more remaining gaps closed is treated as slightly favorable to
        # keep the comparison decisive rather than arbitrary).
        if a_score == b_score:
            a_score -= 1 if result_a.redundancy_analysis.is_redundant else 0
            b_score -= 1 if result_b.redundancy_analysis.is_redundant else 0

        better = "option_a" if a_score >= b_score else "option_b"
        winner, loser = (result_a, result_b) if better == "option_a" else (result_b, result_a)
        explanation = (
            f"'{winner.action.description}' rates {winner.verdict.level} versus "
            f"'{loser.action.description}' at {loser.verdict.level} for this candidate's current profile "
            f"and target role of {context_a.target_role} — {winner.redundancy_analysis.explanation}"
        )

        return ComparisonResult(
            target_role=context_a.target_role,
            option_a=result_a,
            option_b=result_b,
            comparison=ComparisonVerdict(better_fit=better, explanation=explanation),
        )

    # ---- helpers ------------------------------------------------------------

    def _verdict_reasoning(self, context: SimulationContext, topic: str, state: str, relevant: bool, level: str) -> str:
        relevance_text = f"for the target role of {context.target_role}" if relevant else (
            f"though it is not strongly tied to {context.target_role} specifically"
        )
        if state == "demonstrated":
            return (
                f"{topic} is already demonstrated through existing experience on the profile, so this action "
                f"mostly restates existing evidence rather than adding new value {relevance_text}."
            )
        if state == "listed":
            return (
                f"{topic} is listed on the profile but not yet demonstrated through a project or experience, "
                f"so this action would convert a claimed skill into evidenced capability {relevance_text}."
            )
        return (
            f"{topic} is not currently supported by anything on the profile, so this action would close a "
            f"genuine, currently-absent gap {relevance_text}, rated {level.replace('_', ' ').title()}."
        )

    def _gap_impact(self, context: SimulationContext, topic: str, state: str, simulation_type: str) -> list[GapImpact]:
        named_gaps = context.latest_missing_signals[:3]
        if not named_gaps:
            named_gaps = [f"Demonstrated, applied experience in {topic}"]
        impacts = []
        for gap in named_gaps:
            overlaps = topic.lower() in gap.lower() or gap.lower() in topic.lower()
            if overlaps and state != "demonstrated":
                status = "RESOLVED" if simulation_type in _APPLIED_EVIDENCE_TYPES and state == "absent" else "PARTIALLY_ADDRESSED"
                explanation = f"This action directly targets '{gap}', moving it from unaddressed toward closed."
            elif overlaps:
                status = "UNCHANGED"
                explanation = f"'{gap}' is already addressed elsewhere on the profile; this action adds little further movement."
            else:
                status = "UNCHANGED"
                explanation = f"This action does not directly target '{gap}'."
            impacts.append(GapImpact(gap=gap, status=status, explanation=explanation))
        return impacts

    def _evidence_created(self, simulation_type: str, topic: str) -> list[EvidenceCreated]:
        by_type = {
            "build_project": [
                EvidenceCreated(evidence=f"A shipped project demonstrating {topic}", significance="Tangible, checkable proof of applied capability."),
                EvidenceCreated(evidence="A public source repository", significance="Something a recruiter or automated match can directly inspect."),
            ],
            "gain_experience": [
                EvidenceCreated(evidence=f"Logged professional/applied experience involving {topic}", significance="Real-world context, not just coursework or self-study."),
            ],
            "learn_skill": [
                EvidenceCreated(evidence=f"Structured familiarity with {topic}", significance="A foundation to build a demonstrated project on next, but not itself applied evidence."),
            ],
            "certification": [
                EvidenceCreated(evidence=f"A credential in {topic}", significance="Structured learning evidence; does not by itself prove production expertise."),
            ],
            "open_source": [
                EvidenceCreated(evidence=f"A public, reviewable contribution involving {topic}", significance="Evidence of collaborating on code beyond the candidate's own projects."),
            ],
            "change_target_role": [
                EvidenceCreated(evidence="A re-evaluated profile fit against a new target role", significance="Clarifies which existing evidence transfers and which does not."),
            ],
        }
        return by_type.get(simulation_type, [])

    def _claims(self, context: SimulationContext, topic: str, state: str, scale_claimed: bool):
        supported = []
        unsupported = []
        if state != "demonstrated":
            supported.append(
                SupportedClaim(
                    claim=f"Has applied, hands-on exposure to {topic}",
                    basis=f"Directly follows from completing: {context.scenario_title or topic}.",
                )
            )
        if context.simulation_type in _APPLIED_EVIDENCE_TYPES and not scale_claimed:
            unsupported.append(
                UnsupportedClaim(
                    claim="Production-scale or large-scale professional experience",
                    reason="The scenario did not specify deployment, real users, production traffic, or scale, "
                    "so this action alone does not support that stronger claim.",
                )
            )
        if context.simulation_type == "certification":
            unsupported.append(
                UnsupportedClaim(
                    claim="Production expertise",
                    reason="A certification demonstrates structured learning, not applied professional expertise.",
                )
            )
        if context.simulation_type == "learn_skill":
            unsupported.append(
                UnsupportedClaim(
                    claim=f"Demonstrated, applied {topic} experience",
                    reason="Learning alone, without a project or applied use, does not yet constitute demonstrated capability.",
                )
            )
        return supported, unsupported

    def _remaining_gaps(self, context: SimulationContext, topic: str, state: str) -> list[RemainingGap]:
        gaps = [
            RemainingGap(
                gap="Repeated, sustained practice beyond this single action",
                why_it_remains="A single action establishes a starting point, not mastery — depth comes from repetition over time.",
            )
        ]
        if context.simulation_type in ("learn_skill", "certification"):
            gaps.append(
                RemainingGap(
                    gap=f"Applied, shipped evidence of {topic}",
                    why_it_remains="Learning or certifying in a topic is not the same as having built something with it.",
                )
            )
        if context.simulation_type in _APPLIED_EVIDENCE_TYPES and not _mentions_scale(context.scenario_input):
            gaps.append(
                RemainingGap(
                    gap="Production-scale or large-team experience",
                    why_it_remains="The scenario as described did not include deployment, scale, or team collaboration at that level.",
                )
            )
        remaining_named = [g for g in context.latest_missing_signals if topic.lower() not in g.lower()][:2]
        for gap in remaining_named:
            gaps.append(RemainingGap(gap=gap, why_it_remains="Not targeted by this specific hypothetical action."))
        return gaps
