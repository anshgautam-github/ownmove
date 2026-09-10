"""Wire + generator contract for AI Coach.

AI Coach answers a different question than every other Career AI feature:
"Given my situation right now, how should I think about this decision/
problem?" — not "where do I stand" (Profile Analysis), "how do I
systematically reach my target role" (Career Roadmap), "what would happen
if I hypothetically did X" (Career Simulator), or "which real opportunities
fit me" (Opportunity Matcher). See this module's README for the full
product framing and the exact boundary examples.

`CoachStructuredResponse` is the one schema both generators (mock and
LangChain/OpenAI) return, and what `structured_content` stores in
`coach_messages`. It is deliberately NOT a hard discriminated union of five
unrelated shapes — OpenAI's structured-outputs mode binds most reliably to
a single schema, and a genuinely different visual per intent is achieved by
which ONE of `decision` / `problem_solving` / `evaluation` is populated
(the others stay null), which the frontend switches on via `intent`. This
mirrors how `RoadmapContent`/`SimulationResult` are each one shape, not a
union, elsewhere in this codebase.

`intent` maps onto `coach_conversations.conversation_type`'s CHECK
constraint (decision/prioritization/evaluation/problem_solving/preparation/
general) — `prioritization` and `preparation` both render using the
`decision` content shape (a prioritization or preparation question is
still fundamentally "what should I do, why, and what's the trade-off"),
per this module's system prompt.
"""

from typing import Literal

from pydantic import BaseModel, Field

CoachIntent = Literal["decision", "prioritization", "evaluation", "problem_solving", "preparation", "general"]

# Matches careerAiOptions' nav keys in frontend/src/pages/AppShell.jsx
# exactly — these are real, existing tabs within the Career AI section,
# not invented routes. "Do not invent routes" per the feature spec.
RoutingTarget = Literal["profile-analysis", "career-roadmap", "career-simulation", "opportunity-matcher"]


class ReasoningFactor(BaseModel):
    factor: str
    explanation: str = Field(description="WHY this factor matters for THIS user specifically — never generic.")


class Tradeoff(BaseModel):
    gain: str
    cost: str


class DecisionAnswer(BaseModel):
    headline: str = Field(description="A short, direct statement of the recommended path — not a restated question.")
    summary: str


class DecisionContent(BaseModel):
    """Used for `decision`, `prioritization`, and `preparation` intents —
    all three are fundamentally 'what should I do, why, and what am I
    trading off,' just over different horizons (a single choice, a time
    allocation, or preparation for a near-term event)."""

    answer: DecisionAnswer
    reasoning_factors: list[ReasoningFactor] = Field(default_factory=list)
    tradeoff: Tradeoff | None = None
    recommendation: str = Field(
        description="The concrete recommendation. Never presented as universal truth — see "
        "`what_would_change_my_recommendation`."
    )
    next_action: list[str] = Field(default_factory=list, description="Short, concrete, immediate steps. Not a roadmap.")
    what_would_change_my_recommendation: list[str] = Field(
        default_factory=list,
        description="Concrete unknowns or circumstances under which a DIFFERENT option would become preferable.",
    )
    uncertainties: list[str] = Field(default_factory=list)


class ProblemSolvingContent(BaseModel):
    """Used for `problem_solving` intent — separates what's actually known
    from speculation, per the module's core anti-diagnosis rule."""

    known: list[str] = Field(default_factory=list, description="Only what is directly observed/stated — never inferred.")
    possible_explanations: list[str] = Field(
        default_factory=list, description="Candidate explanations — never asserted as the confirmed cause."
    )
    unknowns: list[str] = Field(default_factory=list, description="What would need to be known to narrow this down.")
    recommended_checks: list[str] = Field(default_factory=list)
    next_action: list[str] = Field(default_factory=list)


class EvaluationContent(BaseModel):
    """Used for `evaluation` intent — judging something the user pasted or
    described (a course, internship, certification, hackathon, project
    idea, ...) against THEIR profile and target role, never a summary of
    what they pasted."""

    verdict: str = Field(description="A short, direct verdict — e.g. 'Worth doing, but not urgent right now.'")
    what_it_adds: list[str] = Field(default_factory=list)
    what_it_does_not_add: list[str] = Field(default_factory=list)
    fit_with_goal: str
    tradeoff: str
    recommendation: str


class RoutingSuggestion(BaseModel):
    """Populated only when the user's request primarily belongs to another
    specialized Career AI feature and would duplicate it if the Coach tried
    to fully answer it in place (see this module's README's routing
    examples). The Coach still gives a brief, useful response — this is a
    suggestion, not a refusal."""

    feature: RoutingTarget
    reason: str = Field(description="Why this specific request fits that feature better than a coaching answer.")
    cta_label: str = Field(description="Short button label, e.g. 'Open Career Roadmap'.")


class CoachStructuredResponse(BaseModel):
    """Exactly what a generator (mock or AI) must produce for one coaching
    turn. `message` is always present — the plain-language reply shown as
    the lead text regardless of intent. Exactly one of `decision` /
    `problem_solving` / `evaluation` is populated for a substantive
    coaching answer; all three may be null for a `general` intent that's
    just a short, direct answer with no need for structure (e.g. "yes,
    that's a reasonable interview prep timeline")."""

    intent: CoachIntent
    message: str = Field(description="The core, plain-language reply. Always present regardless of intent.")
    decision: DecisionContent | None = None
    problem_solving: ProblemSolvingContent | None = None
    evaluation: EvaluationContent | None = None
    routing: RoutingSuggestion | None = None
    suggested_title: str | None = Field(
        default=None,
        description="A short (3-6 word) descriptive conversation title, e.g. 'PyTorch vs RAG Project'. Populate "
        "ONLY when this is the first message of a new conversation; leave null on every later turn.",
    )
    clarifying_question: str | None = Field(
        default=None,
        description="Populate ONLY when the available context is genuinely insufficient to answer usefully — ask "
        "ONE specific, useful question rather than guessing. Never populate this just to be cautious when enough "
        "context already exists.",
    )


# ---- request / response wire schemas ---------------------------------------


class StartConversationRequest(BaseModel):
    """What the landing screen (a starter card or the 'Ask AI Coach...'
    box) submits to begin a new conversation."""

    message: str = Field(min_length=1, max_length=4000)


class SendMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)


class CoachMessageResponse(BaseModel):
    id: str
    role: Literal["user", "assistant"]
    content: str
    structured_content: dict | None = None
    created_at: str


class CoachConversationResponse(BaseModel):
    id: str
    profile_id: str
    title: str | None = None
    conversation_type: str | None = None
    created_at: str
    updated_at: str


class CoachConversationDetail(CoachConversationResponse):
    messages: list[CoachMessageResponse] = Field(default_factory=list)


class CoachConversationSummary(BaseModel):
    """One row in the lightweight conversation history list."""

    id: str
    title: str | None = None
    conversation_type: str | None = None
    updated_at: str


class CoachTurnResponse(BaseModel):
    """What both 'start a conversation' and 'send a message' return — the
    conversation's current metadata plus the one new user/assistant message
    pair produced by this turn. The frontend appends these two messages to
    whatever it already has rather than re-fetching the whole thread."""

    conversation: CoachConversationResponse
    user_message: CoachMessageResponse
    assistant_message: CoachMessageResponse
