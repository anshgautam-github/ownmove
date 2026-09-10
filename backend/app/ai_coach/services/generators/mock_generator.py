"""Deterministic, zero-dependency generator.

Runs with no API key and no network call. This is the fallback path only:
when `OPENAI_API_KEY` is configured, `factory.py` switches to
`LangGraphCoachGenerator`, whose system prompt is where this feature's real
reasoning depth lives (open-ended, nuanced coaching over arbitrary
situations). This generator's job is narrower but non-negotiable: never
fabricate a probability/score/guarantee, never over-route, and get this
feature's defining behavior right even without a model — that the SAME
question ("should I take an intro Python course?") must produce a
DIFFERENT recommendation for a candidate who already has Python projects
than for one who has never programmed (see the module README's quality
tests).

Every heuristic here is intentionally simple, keyword-based, and
inspectable — real open-ended reasoning is the LLM path's job.
"""

import re

from app.ai_coach.schemas.coach import (
    CoachStructuredResponse,
    DecisionAnswer,
    DecisionContent,
    EvaluationContent,
    ProblemSolvingContent,
    ReasoningFactor,
    RoutingSuggestion,
    Tradeoff,
)
from app.ai_coach.services.generators.base import BaseCoachGenerator
from app.ai_coach.utils.context import CoachContext

_URGENCY_HINTS = (
    "week", "weeks", "deadline", "before applications", "applications open",
    "next month", "this month", "days", "soon", "interview next",
)
_EXISTING_ASSET_HINTS = ("finish", "existing", "current", "in progress", "already", "improve my", "my existing")
_NEW_LEARNING_HINTS = ("learn", "start", "begin", "new course", "take a course")

_STOPWORDS = {
    "should", "i", "or", "vs", "versus", "the", "a", "an", "to", "my", "for", "of", "and", "is", "this",
    "what", "do", "does", "it", "on", "in", "before", "after", "with", "instead", "than", "will", "would",
}


# ---- routing (first-turn only; see README's "why routing only checks the
# first message" note — a mid-conversation "what if..." is a follow-up, not
# a fresh routing decision) --------------------------------------------------
_ROUTING_RULES: list[tuple[str, list[str], list[str]]] = [
    (
        "career-roadmap",
        ["roadmap", "complete plan", "learning plan", "curriculum", "step by step plan", "month plan", "months plan"],
        ["generate", "create", "build me", "give me a", "make me a"],
    ),
    (
        "profile-analysis",
        ["analyze my profile", "analyse my profile", "weaknesses in my profile", "profile analysis", "where do i stand", "strengths and weaknesses"],
        [],
    ),
    (
        "career-simulation",
        ["what if i", "what would happen if i", "simulate"],
        [],
    ),
    (
        "opportunity-matcher",
        ["find internships", "find opportunities", "show me internships", "match me with", "recommend internships", "find me a"],
        [],
    ),
]
# Comparative/decision markers that must NEVER be routed away, even if a
# routing phrase also appears — e.g. "Should I do AWS certification or
# finish my backend project before placements?" must stay with the Coach.
_DECISION_OVERRIDE_HINTS = (" or ", " vs ", " versus ", "should i", "instead of")


def _detect_routing(message: str) -> RoutingSuggestion | None:
    lowered = message.lower()
    if any(hint in lowered for hint in _DECISION_OVERRIDE_HINTS):
        return None
    for feature, must_hints, any_of_hints in _ROUTING_RULES:
        if not any(hint in lowered for hint in must_hints):
            continue
        if any_of_hints and not any(hint in lowered for hint in any_of_hints):
            continue
        labels = {
            "career-roadmap": ("Career Roadmap", "That's exactly what Career Roadmap builds — a full, phased plan toward a target role."),
            "profile-analysis": ("Profile Analysis", "A full breakdown of your profile's strengths and gaps is Profile Analysis's job."),
            "career-simulation": ("Career Simulator", "Evaluating one hypothetical action's impact on your profile is exactly what Career Simulator does."),
            "opportunity-matcher": ("Opportunity Matcher", "Finding real, current opportunities that fit you is Opportunity Matcher's job, not the Coach's."),
        }
        label, reason = labels[feature]
        return RoutingSuggestion(feature=feature, reason=reason, cta_label=f"Open {label}")
    return None


def _classify_intent(message: str) -> str:
    lowered = message.lower()
    if any(k in lowered for k in ("no interview", "not getting interview", "haven't received interview", "not finishing", "confused between", "no clear specialization", "what's wrong", "what is wrong")):
        return "problem_solving"
    if any(k in lowered for k in ("worth it", "worth doing", "worth my time", "worth taking", "is this worth", "should i do this")):
        return "evaluation"
    if any(k in lowered for k in ("interview next week", "interview this week", "hackathon this weekend", "applications open", "prepare for")):
        return "preparation"
    if any(k in lowered for k in ("prioritize", "focus on", "what should i focus", "hours per week", "hours a week")):
        return "prioritization"
    if any(k in lowered for k in (" or ", " vs ", " versus ", "should i")):
        return "decision"
    return "general"


_TOPIC_STOPWORDS = {
    "start", "starting", "learning", "learn", "finish", "finishing", "improve", "improving", "my", "existing",
    "current", "begin", "beginning", "the", "a", "an", "take", "taking", "do", "doing", "this", "for", "of", "to",
}


def _extract_keyword(phrase: str) -> str:
    """Strips generic verbs/articles so a short option phrase like 'start
    learning PyTorch' reduces to its actual subject ('PyTorch') before
    being checked against the profile — matching against the whole phrase
    directly would never match a short skill name (see `_skill_state`)."""
    words = [w for w in re.findall(r"[A-Za-z0-9+.#]+", phrase) if w.lower() not in _TOPIC_STOPWORDS]
    return " ".join(words) or phrase


def _skill_state(context: CoachContext, phrase: str) -> str:
    """'demonstrated' | 'listed' | 'absent' — same three-way classification
    career_simulation's mock generator uses, applied here to a decision
    option's extracted subject. Checks BOTH substring directions against
    skill names (both sides are short strings — e.g. keyword 'ML' should
    match a listed skill 'ML' either way) and keyword-within-description
    for experiences (the keyword is short, the description is long, so
    only keyword-in-description makes sense there)."""
    keyword = _extract_keyword(phrase).lower().strip()
    if not keyword:
        return "absent"
    demonstrated = any(keyword in s.lower() or s.lower() in keyword for s in context.experience_skills) or any(
        keyword in f"{e.get('title', '')} {e.get('description', '')}".lower() for e in context.experiences
    )
    if demonstrated:
        return "demonstrated"
    if any(keyword in s.lower() or s.lower() in keyword for s in context.current_skills):
        return "listed"
    return "absent"


def _message_topic_state(context: CoachContext, message: str) -> str:
    """'demonstrated' | 'listed' | 'absent' — for evaluation questions,
    where the message is a full sentence rather than a short option
    phrase (e.g. 'Should I take an introductory Python course?'). Checking
    the whole message against short skill names the way `_skill_state`
    does won't match, so this instead scans whether any of the profile's
    OWN skills/keywords appear within the message — the direction that
    actually works for free-form text. This is what makes the same
    question resolve differently for a candidate who already has the
    relevant skill/experience versus one who doesn't (see the module
    README's quality test)."""
    lowered = message.lower()
    for skill in context.experience_skills:
        if skill and skill.lower() in lowered:
            return "demonstrated"
    for experience in context.experiences:
        title = (experience.get("title") or "").lower()
        if title and any(word in lowered for word in title.split() if len(word) > 3):
            return "demonstrated"
    for skill in context.current_skills:
        if skill and skill.lower() in lowered:
            return "listed"
    return "absent"


def _split_options(message: str) -> list[str] | None:
    lowered = message.lower()
    for connector in (" or ", " vs ", " versus "):
        if connector in lowered:
            # Split on the ORIGINAL (not lowered) string so casing is preserved
            # in the option text shown back to the user.
            idx = lowered.index(connector)
            left = message[:idx]
            right = message[idx + len(connector):]
            # Trim a leading "Should I " and a trailing "?" for cleaner phrases.
            left = re.sub(r"(?i)^\s*should i\s+", "", left).strip(" ?.")
            right = right.strip(" ?.")
            # Cut the right side off at the first clause boundary so trailing
            # constraint text ("before applications") doesn't get treated as
            # part of the option itself.
            right = re.split(r"\bbefore\b|\bafter\b|,", right, maxsplit=1)[0].strip()
            if left and right:
                return [left, right]
    return None


def _suggest_title(message: str) -> str:
    options = _split_options(message)
    if options:
        return f"{options[0][:24].strip()} vs {options[1][:24].strip()}".title()
    words = [w for w in re.findall(r"[A-Za-z0-9']+", message) if w.lower() not in _STOPWORDS]
    title = " ".join(words[:6]).title() or "Career Question"
    return title[:60]


class MockCoachGenerator(BaseCoachGenerator):
    name = "mock-v1"

    async def generate(self, context: CoachContext) -> CoachStructuredResponse:
        message = context.user_question.strip()
        is_first_turn = len(context.windowed_messages) == 0

        routing = _detect_routing(message) if is_first_turn else None
        suggested_title = _suggest_title(message) if context.is_new_conversation else None

        if routing:
            return CoachStructuredResponse(
                intent="general",
                message=(
                    f"{routing.reason} I can still give you a quick take here, but for the full picture you're "
                    f"better served opening {routing.cta_label.replace('Open ', '')}."
                ),
                routing=routing,
                suggested_title=suggested_title,
            )

        intent = _classify_intent(message)

        if intent == "decision":
            return self._decision_response(context, message, "decision", suggested_title)
        if intent == "prioritization":
            return self._prioritization_response(context, message, suggested_title)
        if intent == "preparation":
            return self._preparation_response(context, message, suggested_title)
        if intent == "evaluation":
            return self._evaluation_response(context, message, suggested_title)
        if intent == "problem_solving":
            return self._problem_solving_response(context, message, suggested_title)
        return self._general_response(context, message, suggested_title)

    # ---- intent handlers ----------------------------------------------------

    def _decision_response(self, context: CoachContext, message: str, intent: str, title: str | None) -> CoachStructuredResponse:
        options = _split_options(message) or [message, "the alternative"]
        option_a, option_b = options[0], options[1]
        lowered = message.lower()
        urgent = any(hint in lowered for hint in _URGENCY_HINTS)

        a_is_existing = any(hint in option_a.lower() for hint in _EXISTING_ASSET_HINTS)
        b_is_existing = any(hint in option_b.lower() for hint in _EXISTING_ASSET_HINTS)
        a_state = _skill_state(context, option_a)
        b_state = _skill_state(context, option_b)

        # Core rule (quality test 1): under a near-term deadline, finishing
        # an existing/in-progress asset outranks starting new learning,
        # because it produces demonstrable output before the deadline.
        if urgent and (a_is_existing or b_is_existing) and a_is_existing != b_is_existing:
            winner, loser = (option_a, option_b) if a_is_existing else (option_b, option_a)
            reasoning_factors = [
                ReasoningFactor(
                    factor="Time horizon",
                    explanation=f"The situation described is time-boxed, and finishing '{winner}' produces demonstrable, "
                    "shippable output before that deadline — starting something new typically doesn't.",
                ),
                ReasoningFactor(
                    factor="Target role fit",
                    explanation=f"Given a target of {context.target_role}, applied, finished work is generally stronger "
                    "evidence than a partially-learned new skill at this stage.",
                ),
            ]
            tradeoff = Tradeoff(
                gain=f"Finishing '{winner}' gives you a complete, demonstrable artifact in time.",
                cost=f"Choosing this delays progress on '{loser}'.",
            )
            recommendation = f"Prioritize finishing '{winner}' over starting '{loser}' given the timeline described."
            change_conditions = [
                f"If {loser.lower()} were itself a core, explicitly-required skill for {context.target_role} that "
                "the deadline depends on, this recommendation would flip.",
                "If the timeline were significantly longer, both could reasonably be pursued in sequence.",
            ]
        else:
            # Fallback (quality test 4's logic): prefer whichever option is
            # NOT already demonstrated/listed on the profile — it closes a
            # genuine gap rather than restating existing evidence.
            if a_state == b_state:
                winner, loser = option_a, option_b
                reasoning_factors = [
                    ReasoningFactor(
                        factor="Current profile signal",
                        explanation=f"Neither option is clearly ahead based on what's on file for {context.target_role} — "
                        "this needs more specific information about your actual constraint to differentiate them confidently.",
                    )
                ]
            else:
                order = {"absent": 0, "listed": 1, "demonstrated": 2}
                winner, loser = (option_a, option_b) if order[a_state] < order[b_state] else (option_b, option_a)
                winner_state = a_state if winner == option_a else b_state
                loser_state = b_state if winner == option_a else a_state
                reasoning_factors = [
                    ReasoningFactor(
                        factor="Existing evidence",
                        explanation=f"'{loser}' is already {loser_state} on your profile, while '{winner}' is currently "
                        f"{winner_state} — so '{winner}' would close a gap '{loser}' wouldn't.",
                    )
                ]
            tradeoff = Tradeoff(
                gain=f"'{winner}' adds a signal your profile doesn't already show for {context.target_role}.",
                cost=f"Time spent on '{winner}' is time not spent deepening '{loser}'.",
            )
            recommendation = f"Lean toward '{winner}' — it's the less-represented option on your current profile."
            change_conditions = [
                f"If '{loser}' were actually a stated, hard requirement for {context.target_role} that you haven't "
                "mentioned, that would outweigh this.",
                "If there's a near-term deadline this description didn't mention, that could change which option is more urgent.",
            ]

        return CoachStructuredResponse(
            intent=intent,
            message=recommendation,
            decision=DecisionContent(
                answer=DecisionAnswer(headline=recommendation, summary=f"Comparing '{option_a}' against '{option_b}' for {context.target_role}."),
                reasoning_factors=reasoning_factors,
                tradeoff=tradeoff,
                recommendation=recommendation,
                next_action=[f"Start with: {winner}"],
                what_would_change_my_recommendation=change_conditions,
                uncertainties=[] if urgent else ["The specific time constraint, if any, wasn't stated."],
            ),
            suggested_title=title,
        )

    def _prioritization_response(self, context: CoachContext, message: str, title: str | None) -> CoachStructuredResponse:
        gaps = []
        if context.latest_analysis:
            gaps = [s.get("title") for s in (context.latest_analysis.get("missing_signals") or []) if s.get("title")]
        focus = gaps[0] if gaps else f"the most applied, demonstrable work you can produce for {context.target_role}"
        recommendation = f"Prioritize {focus} over adding another new topic this cycle."
        return CoachStructuredResponse(
            intent="prioritization",
            message=recommendation,
            decision=DecisionContent(
                answer=DecisionAnswer(headline=recommendation, summary=f"Given your current profile and target of {context.target_role}."),
                reasoning_factors=[
                    ReasoningFactor(
                        factor="Named gap" if gaps else "Demonstrated output",
                        explanation=(
                            f"Profile Analysis previously named '{focus}' as a gap against {context.target_role}."
                            if gaps
                            else "Applied, finished work is the strongest lever available without more specific constraints stated."
                        ),
                    )
                ],
                tradeoff=Tradeoff(gain="Closes a known gap with visible evidence.", cost="Less time for breadth across other topics."),
                recommendation=recommendation,
                next_action=[f"Block time this week specifically for: {focus}"],
                what_would_change_my_recommendation=[
                    "If you have an imminent deadline (interview, application window) not mentioned here, that should take priority instead.",
                ],
                uncertainties=["The exact hours available per week weren't stated." if "hour" not in message.lower() else ""],
            ),
            suggested_title=title,
        )

    def _preparation_response(self, context: CoachContext, message: str, title: str | None) -> CoachStructuredResponse:
        recommendation = "Spend your remaining time on the highest-leverage, most reviewable preparation, not broad new learning."
        return CoachStructuredResponse(
            intent="preparation",
            message=recommendation,
            decision=DecisionContent(
                answer=DecisionAnswer(headline=recommendation, summary=f"Short-horizon preparation for {context.target_role}."),
                reasoning_factors=[
                    ReasoningFactor(
                        factor="Time horizon",
                        explanation="With limited time before the event described, depth on what you can already speak to "
                        "beats breadth on something new.",
                    )
                ],
                tradeoff=Tradeoff(gain="Walk in able to discuss your actual work fluently.", cost="Less time for new material."),
                recommendation=recommendation,
                next_action=[
                    "Re-read your own project(s)/experience and rehearse explaining one concrete technical decision from each.",
                    "Identify the one or two most likely questions given your target role and prepare specific answers.",
                ],
                what_would_change_my_recommendation=["If the event specifically tests unfamiliar material, some targeted new review is warranted instead."],
                uncertainties=[],
            ),
            suggested_title=title,
        )

    def _evaluation_response(self, context: CoachContext, message: str, title: str | None) -> CoachStructuredResponse:
        state = _message_topic_state(context, message)
        if state == "demonstrated":
            verdict = "Likely low added value — this looks redundant with what you already show."
            adds = ["Marginal reinforcement of something already demonstrated."]
            not_adds = ["New signal — your profile already shows this more strongly through existing experience."]
            recommendation = "Not a priority right now; time is better spent elsewhere."
        elif state == "listed":
            verdict = "Reasonable but not urgent — it would convert a listed skill into demonstrated proficiency."
            adds = ["Moves a self-reported skill toward demonstrated evidence."]
            not_adds = ["It alone won't be strong evidence without an applied project or outcome attached."]
            recommendation = "Worth doing if it's low-cost, but pair it with applying the skill somewhere, not as a substitute for that."
        else:
            verdict = "Likely worth it — it targets something not currently on your profile at all."
            adds = ["A genuinely new signal your profile doesn't currently show."]
            not_adds = ["On its own it won't fully substitute for applied, demonstrated experience."]
            recommendation = f"Worth prioritizing, especially given your target of {context.target_role}."
        return CoachStructuredResponse(
            intent="evaluation",
            message=verdict,
            evaluation=EvaluationContent(
                verdict=verdict,
                what_it_adds=adds,
                what_it_does_not_add=not_adds,
                fit_with_goal=f"Evaluated against your stated target of {context.target_role}.",
                tradeoff="Time spent here is time not spent on whatever else you'd otherwise prioritize.",
                recommendation=recommendation,
            ),
            suggested_title=title,
        )

    def _problem_solving_response(self, context: CoachContext, message: str, title: str | None) -> CoachStructuredResponse:
        known = [message.strip()]
        possible = [
            "Role/eligibility fit between your applications and the roles targeted",
            "How applications are being targeted (volume vs. fit)",
            "Resume positioning relative to the target role",
            "Visible, reviewable evidence (portfolio/GitHub) reachable from your application",
        ]
        recommended_checks = []
        if not context.has_github and not context.has_resume:
            recommended_checks.append("Neither a GitHub link nor a resume is on file — reviewable evidence may not even be reaching recruiters.")
        elif not context.has_github:
            recommended_checks.append("No GitHub link is on file — if your work is your strongest evidence, it may not be visible.")
        recommended_checks.append("Compare the roles you applied to against your actual target role and current skills for fit.")
        unknowns = [
            "Which specific roles/companies were targeted",
            "What the resume itself emphasizes",
            "Whether applications were tailored per role or sent identically",
        ]
        return CoachStructuredResponse(
            intent="problem_solving",
            message="The lack of interviews suggests the issue is occurring before the interview stage, but the application "
            "count alone can't identify the specific cause.",
            problem_solving=ProblemSolvingContent(
                known=known,
                possible_explanations=possible,
                unknowns=unknowns,
                recommended_checks=recommended_checks,
                next_action=["Pick the two most likely areas above and check them directly before changing anything else."],
            ),
            suggested_title=title,
        )

    def _general_response(self, context: CoachContext, message: str, title: str | None) -> CoachStructuredResponse:
        return CoachStructuredResponse(
            intent="general",
            message=(
                f"Given your target of {context.target_role}, tell me a bit more about the constraint or trade-off "
                "you're weighing and I can reason through it with you specifically."
            ),
            clarifying_question="What's the actual decision, deadline, or constraint you're working with right now?",
            suggested_title=title,
        )
