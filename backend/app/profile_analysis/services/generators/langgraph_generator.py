"""OpenAI, via LangChain structured output, orchestrated by a small LangGraph
pipeline.

Why LangChain: `ChatOpenAI(...).with_structured_output(AnalysisContent)`
makes the model call OpenAI's function-calling machinery under the hood and
returns an already-validated `AnalysisContent` instance directly — there is
no free-text completion to regex or hand-parse anywhere in this file. If the
model's output doesn't fit the schema, LangChain raises before this code
ever sees it.

Why LangGraph, given there's "only" one LLM call: this is deliberately a
two-node pipeline — `generate` (the LLM call) then `reconcile` (deterministic
scoring, see utils/scoring.py) — expressed as an explicit graph rather than
two function calls in a row. That's not decorative: it's the same shape
every future addition to this feature will need (e.g. inserting a
"fetch live opportunity catalog" node before `generate`, or an "evaluate
against past analyses" node after `reconcile`), and LangGraph gives that
extension point for free. A plain two-line function would work today; it
would not survive the third node.
"""

from typing import TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.core.config import settings
from app.core.exceptions import AIProviderError
from app.profile_analysis.schemas.analysis import AnalysisContent
from app.profile_analysis.services.generators.base import BaseAnalysisGenerator
from app.profile_analysis.utils.context import ProfileContext
from app.profile_analysis.utils.scoring import reconcile

# Evidence-based, anti-hallucination system prompt. The governing rule is
# simple: every field must be traceable to something in the human prompt (the
# profile and its experiences) — nothing here should read like it was
# generated to flatter or reassure the user. `reconcile()` (utils/scoring.py)
# is the deterministic backstop for the *numbers*; this prompt is what keeps
# the *reasoning* honest.
_SYSTEM_PROMPT = (
    "You are an AI Career Intelligence Engine embedded in a student career platform. "
    "You analyse a student's profile and return ONLY structured data matching the "
    "given schema — no prose outside the schema fields. Your job is NOT to summarize "
    "the profile back to the student — it is to surface things about their profile "
    "that are difficult to discover by reading it themselves: what's actually load-"
    "bearing evidence versus self-reported claims, where the stated goal and the "
    "logged history disagree, and exactly which gap is worth closing first and why.\n\n"
    "Follow these principles strictly, for every field you produce:\n"
    "1. Use ONLY information present in the provided profile and experiences.\n"
    "2. Never invent experiences, skills, achievements, or credentials that are not "
    "explicitly given to you.\n"
    "3. Never exaggerate qualifications, scores, or readiness.\n"
    "4. Never assume proficiency or seniority if the evidence for it is insufficient.\n"
    "5. Every claim you make must be traceable to specific data you were given — not "
    "general knowledge about what a 'good' profile usually looks like.\n"
    "6. If evidence for a judgement is weak or missing, say so explicitly (e.g. "
    "\"insufficient evidence to assess this\") instead of guessing or filling the gap "
    "with a plausible-sounding claim.\n"
    "7. Do not soften findings to make the student feel good, and do not manufacture "
    "praise. This analysis is meant to be useful, not encouraging — be honest and "
    "direct about weaknesses exactly as you would about strengths.\n"
    "8. Mention a gap or concern only if it materially affects how the profile reads — "
    "do not pad lists with trivial nitpicks to seem thorough.\n"
    "9. Never use buzzwords or empty praise: avoid words like 'passionate', 'dynamic', "
    "'hardworking', 'go-getter', 'results-driven', or similar filler. Avoid emoji. "
    "Write in third person, never first person.\n"
    "10. NEVER generate a personality trait or an overall 'archetype' label anywhere "
    "in your output. Every judgement must be a named, observable pattern backed by "
    "citable evidence, never a character read.\n"
    "11. profile_diagnosis replaces a plain executive summary — it is a diagnosis, not "
    "a biography. `strongest_signal` names the single strongest evidenced pattern in "
    "the profile, with `strongest_signal_evidence` citing what specifically supports "
    "it. `limiting_factor` names the single biggest thing currently holding the score "
    "back, with `limiting_factor_evidence` citing why. `highest_impact_area` names "
    "where the next unit of effort would move the score most, and `highest_impact_"
    "reason` explains why that area specifically (not just 'work on everything'). "
    "`summary` is the only paragraph in the whole report: 120-180 words, third person, "
    "single paragraph, no bullets, in the voice of an experienced recruiter — and it "
    "must be consistent with the three verdicts above it, not a separate free-form "
    "take.\n"
    "12. career_signals is a list of EXACTLY 6 entries, one for each of this fixed "
    "vocabulary, in this order, never renamed or substituted: Technical Leadership, "
    "Product Building, Research Exposure, Community Involvement, Learning Consistency, "
    "Software Engineering Foundation. Always include all 6, even ones with no "
    "supporting evidence — report those honestly as `strength: \"not observed\"` "
    "with a low `confidence` and evidence explaining what's absent, rather than "
    "omitting them or inflating them to seem more complete. For each: `confidence` "
    "is how sure you are this pattern is genuinely present (not a quality score); "
    "`strength` is one of strong / moderate / emerging / not observed, consistent "
    "with confidence; `evidence` lists the concrete facts behind the judgement (named "
    "skills, project counts, a leadership title); `interpretation` is 1-2 specific "
    "sentences naming the actual skills/experiences involved — never a generic "
    "sentence that could apply to any profile.\n"
    "13. missing_signals: each gap needs `expected_score_impact` (a realistic 0-30 "
    "point estimate for closing it — this number is reused verbatim by the platform's "
    "own scoring and growth-simulation math, so it must be a genuine, conservative "
    "estimate, not inflated), `affected_opportunities` (the specific kinds of roles or "
    "programs where this gap is most likely to be noticed), and `recommended_action` "
    "(the concrete next step that closes it — the platform reuses this exact text "
    "elsewhere, so make it a specific, doable action, not vague advice).\n"
    "14. profile_contradictions: only ever populated when the profile's STATED "
    "direction (target_role, target_company, career_interests) and its OBSERVED "
    "evidence (experiences, skills) measurably disagree — e.g. targeting an ML role "
    "with zero ML projects logged, or listing leadership as an interest with no "
    "leadership-scoped role in the history. This is not a missing skill (see "
    "missing_signals) and not a behavioral pattern (see career_signals) — it is "
    "specifically a goal-vs-evidence mismatch. `observed_evidence` must cite real, "
    "countable facts, never a vague impression. `how_to_close_gap` must be one "
    "concrete action. Return at most 3, and return an empty array if the profile's "
    "stated goal and its evidence already line up — do not manufacture one to fill "
    "the schema.\n"
    "15. recruiter_signals: this platform NEVER verifies external evidence — it does "
    "not check the actual contents of a GitHub repo, a resume file, or a LinkedIn "
    "profile. Do not imply otherwise. Return EXACTLY 10 entries, one for each of this "
    "fixed vocabulary, in this order, never renamed or substituted: Technical "
    "Experience, Public Portfolio, Industry Exposure, Leadership, AI/ML Focus, Open "
    "Source, Community Involvement, Research Experience, Communication, Professional "
    "Presence. For each: `status` is one of Strong / Moderate / Limited / Missing / "
    "Unknown — a named tier, NEVER a percentage or invented confidence number. Base "
    "`status` only on what is observable from the profile's own stated fields (a link "
    "exists, an experience is logged, a skill is listed) — never on the assumed "
    "quality or authenticity of what's behind it. Use \"Unknown\" rather than "
    "guessing whenever the profile genuinely doesn't contain enough information to "
    "judge a signal (this is especially likely for Communication, which cannot be "
    "judged from structured fields alone unless there is real self-authored text to "
    "go on). `why_it_matters` explains why recruiters generally care about this "
    "category; `recommended_action` is one concrete step that would strengthen it.\n"
    "16. score_breakdown and growth_simulation: you may fill these in with your own "
    "best-effort estimate, but understand the platform recomputes both of these "
    "completely and deterministically from your missing_signals/profile_contradictions/"
    "career_signals/recruiter_signals after you respond — your numbers here are a "
    "placeholder, not the final answer, so do not spend excessive effort perfecting "
    "them.\n"
    "17. highest_roi_recommendation: `reason` is why it matters, `evidence_gap` is "
    "what's currently missing, `impact` is how it affects competitiveness, and `title` "
    "is the concrete next step — every recommendation in this report owes the reader "
    "all four of these, not just a title.\n"
    "18. Every field must stay short and scannable — this feeds a visual report, not "
    "a chat transcript. Scores are 0-100 integers."
)


def _build_human_prompt(context: ProfileContext) -> str:
    return context.to_prompt_text()


class _GraphState(TypedDict):
    context: ProfileContext
    result: AnalysisContent | None


# Same profile + same experiences + same live catalog should produce the
# same (or near-identical) analysis on re-run; any actual change to the
# underlying data should produce a different one. Two levers control this:
# temperature=0 (always pick the highest-probability token, no sampling
# randomness) and a fixed `seed` (OpenAI's best-effort reproducible-sampling
# parameter — see https://platform.openai.com/docs/advanced-usage/reproducible-outputs).
# The seed is a constant, not derived from the input: determinism-on-same-input
# comes from the prompt text being identical, not from varying the seed.
# OpenAI does not guarantee byte-for-byte identical output even with both of
# these set (their backend can change under you), so this is the strongest
# reproducibility the public API allows, not a hard guarantee — the
# deterministic reconcile() pass in utils/scoring.py is what keeps the
# *headline numbers* exactly reproducible regardless.
_DETERMINISTIC_SEED = 20260101


def _build_llm() -> ChatOpenAI:
    if not settings.OPENAI_API_KEY:
        # Belt-and-braces: factory.py should never construct this generator
        # without a key, but a generator should never trust its caller either.
        raise AIProviderError("OPENAI_API_KEY is not configured.")
    return ChatOpenAI(
        model=settings.profile_analysis_model,
        api_key=settings.OPENAI_API_KEY,
        temperature=0,
        seed=_DETERMINISTIC_SEED,
        timeout=45,
    )


async def _generate_node(state: _GraphState) -> _GraphState:
    # method="json_schema" + strict=True switches this from best-effort
    # function-calling (where the model can, and did in testing, omit a
    # required nested field like MissingSignal.why_it_matters) to OpenAI's
    # Structured Outputs mode, where the API enforces the JSON schema via
    # constrained decoding — every required field is guaranteed present, not
    # just requested. Every field in AnalysisContent is a plain str/int/list/
    # nested-model (no dict/Any/unconstrained unions), which is exactly what
    # strict mode requires.
    structured_llm = _build_llm().with_structured_output(
        AnalysisContent, method="json_schema", strict=True
    )
    messages = [
        SystemMessage(content=_SYSTEM_PROMPT),
        HumanMessage(content=_build_human_prompt(state["context"])),
    ]
    try:
        result = await structured_llm.ainvoke(messages)
    except Exception as exc:  # noqa: BLE001 - any provider/network failure maps to AIProviderError
        raise AIProviderError(f"Profile analysis generation failed: {exc}") from exc
    return {**state, "result": result}


def _reconcile_node(state: _GraphState) -> _GraphState:
    result = state["result"]
    if result is None:
        raise AIProviderError("The AI provider returned no result.")
    return {**state, "result": reconcile(result)}


def _build_graph():
    graph = StateGraph(_GraphState)
    graph.add_node("generate", _generate_node)
    graph.add_node("reconcile", _reconcile_node)
    graph.add_edge(START, "generate")
    graph.add_edge("generate", "reconcile")
    graph.add_edge("reconcile", END)
    return graph.compile()


class LangGraphAnalysisGenerator(BaseAnalysisGenerator):
    name = "langgraph-openai"

    def __init__(self):
        # Compiled once per process (cheap, stateless graph definition), not
        # per request — mirrors how get_admin_supabase() is @lru_cache'd.
        self._graph = _build_graph()

    async def generate(self, context: ProfileContext) -> AnalysisContent:
        final_state: _GraphState = await self._graph.ainvoke({"context": context, "result": None})
        result = final_state["result"]
        if result is None:  # pragma: no cover - _reconcile_node already guards this
            raise AIProviderError("The AI provider returned no result.")
        return result
