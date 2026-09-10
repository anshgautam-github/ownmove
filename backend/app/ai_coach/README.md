# AI Coach

A **context-aware career decision assistant**. Its job: "help the user
reason through a career decision, constraint, uncertainty, or immediate
problem using their actual career context." It is NOT a generic chatbot.

## Feature boundary

| Feature | Question it answers |
| --- | --- |
| Profile Analysis | Where do I currently stand? |
| Career Roadmap | How do I systematically reach my target role? |
| Career Simulator | What would happen if I hypothetically did X? |
| Opportunity Matcher | Which real opportunities fit me? |
| **AI Coach** | **Given my situation right now, how should I think about this decision/problem?** |

The Coach recognizes when a request would fully duplicate one of the other
four features (e.g. "generate my complete 12-month roadmap", "analyze my
whole profile", "what if I learn PyTorch", "find internships for me") and
responds briefly with a routing suggestion + CTA to that feature's existing
tab, rather than recreating it. A request that mixes a specialized topic
with real trade-offs/constraints (e.g. "should I do AWS certification or
finish my backend project before placements?") stays with the Coach —
routing only checks the FIRST message of a conversation, specifically so a
mid-conversation follow-up like "what if I have six months instead?" is
never mistaken for a fresh routing decision.

## Architecture

Same self-contained vertical-slice shape as every other Career AI module:

```
ai_coach/
  schemas/coach.py         # structured response + request/response wire schemas
  models/coach.py          # DB row shapes (coach_conversations, coach_messages)
  utils/context.py         # CoachContext: USER_CONTEXT/CURRENT_CONVERSATION/USER_QUESTION
  services/
    generators/
      base.py, mock_generator.py, langgraph_generator.py, factory.py
    repository.py          # Supabase I/O (user-scoped client only)
    coach_service.py        # orchestration: create/continue conversation -> generate -> persist
  routers/coach_router.py
```

No LangGraph, no agents, no vector memory/embeddings, no RAG — same
constraint every sibling module follows. A single structured-output call
per turn, with a bounded recent-message window, is the entire memory
model for V1.

## Structured response, not a hard union

`CoachStructuredResponse` (schemas/coach.py) is one Pydantic schema, not a
true discriminated union of five shapes — OpenAI's structured-outputs mode
binds most reliably to a single schema. `intent` decides which ONE of
`decision` / `problem_solving` / `evaluation` is populated (the others stay
null); the frontend renders a genuinely different structured card per
intent by switching on which field is present. `prioritization` and
`preparation` both use the `decision` shape (both are fundamentally "what
should I do, why, what's the trade-off," just over different horizons).
`routing` is populated only when a routing suggestion applies.
`suggested_title` is populated only on a conversation's first turn.

## Conversation architecture

`coach_conversations` (one row per thread) / `coach_messages` (many rows
per conversation) — a normal parent/child pair, unlike `career_roadmaps`
(one row per user) or `career_simulations`/`profile_analysis` (flat
append-only history). `title`/`conversation_type` start `NULL` and are
filled in once the first assistant reply classifies the conversation's
intent (and, if the generator supplied one, a short title like "PyTorch vs
RAG Project"). `updated_at` is bumped on every new message, so the history
list (ordered `updated_at desc`) surfaces the most recently active
conversation first.

`coach_messages.structured_content` stores the full
`CoachStructuredResponse` for assistant turns (`NULL` for user messages).
System prompts are never stored as conversation messages, and no API key
is ever stored or exposed.

## Memory model

Every turn re-fetches `profiles`/`experiences`/`profile_analysis` live
(not cached in the conversation) — a profile edit mid-conversation is
reflected in the very next reply. `CoachContext` caps conversation history
to the most recent 8 messages (`_MAX_HISTORY_MESSAGES` in `utils/
context.py`) — enough to resolve a follow-up like "what if I have six
months instead?" against the prior turn, without unbounded token growth.

## Grounding & anti-hallucination

The system prompt (`langgraph_generator.py`'s `_SYSTEM_PROMPT`) requires
the KNOWN / USER_REPORTED / INFERRED / UNKNOWN distinction, forbids
fabricated hiring/interview/salary probabilities, arbitrary scores, fake
achievements/skills/experience, and unsupported diagnoses (e.g. "your
resume is the problem" from application count alone) — `problem_solving`
content must separate known facts from possible explanations and name
what's still unknown. It also forbids generic coaching platitudes unless
immediately followed by profile-specific reasoning, and requires every
decision/evaluation answer to reason about INCREMENTAL VALUE for this
specific candidate (the same question must resolve differently for two
different profiles).

The mock generator (used when no `OPENAI_API_KEY` is set) enforces the
same discipline mechanically: it classifies a decision option's extracted
subject, or an evaluation message's overlap with the user's own listed/
demonstrated skills, as `demonstrated` / `listed` / `absent` against the
actual profile, and derives its recommendation from that — never from the
activity type alone.

## Quality tests this module targets

1. **Time-boxed decision**: "three weeks before applications, learn PyTorch
   or finish my in-progress RAG project?" → prioritize finishing the
   existing project (demonstrable output before the deadline), while still
   naming what would flip that recommendation.
2. **No unsupported diagnosis**: "40 applications, no interviews" → never
   asserts a specific cause; separates known fact from possible
   explanations and unknowns, and only elevates an explanation using
   information actually present (e.g. no GitHub/resume on file).
3. **No over-routing on a full-roadmap request**: recognizes the request
   belongs to Career Roadmap and gives a brief answer + CTA rather than
   generating the plan itself.
4. **Incremental value differs per candidate**: "should I take an intro
   Python course?" must NOT get the same answer for a candidate with no
   programming background as for one with existing Python projects/
   internship experience.

## Security

LLM calls happen only in this backend process; the API key is never sent
to the frontend. `profile_id` is always `user.id` from the authenticated
JWT — never read from the request body. Every conversation read/write
verifies ownership via `CoachRepository.require_conversation` (404s
rather than 403s on a conversation belonging to someone else, so a caller
can never confirm an id they don't own actually exists) — RLS enforces
the same check again independently at the database layer.

## API

- `POST /api/v1/career-ai/ai-coach/conversations` — start a conversation with its first message
- `GET /api/v1/career-ai/ai-coach/conversations` — list conversations (title/type/last activity)
- `GET /api/v1/career-ai/ai-coach/conversations/{id}` — fetch one conversation with full message history
- `POST /api/v1/career-ai/ai-coach/conversations/{id}/messages` — continue a conversation
- `DELETE /api/v1/career-ai/ai-coach/conversations/{id}` — delete a conversation

## Frontend

`CareerCoachDashboard.jsx` is the state-machine container
(`loading-initial -> landing -> conversation -> error`). `coach/` holds
`starterConfig.js` (the four starter cards), `ConversationView.jsx` +
`AssistantMessage.jsx` (renders `DecisionCard`/`ProblemSolvingCard`/
`EvaluationCard`/`RoutingCTA` depending on which field of
`structured_content` is populated — never 8 identical cards), and
`ConversationHistoryList.jsx`. `onNavigateTab` is threaded from
`AppShell.jsx`'s `SidebarContentBody` (its existing `setActive` state
setter) down to `RoutingCTA`, so a routing suggestion switches the Career
AI sidebar to an existing tab (`profile-analysis`/`career-roadmap`/
`career-simulation`/`opportunity-matcher`) rather than inventing a route.

## Known assumptions / simplifications

- Routing detection only runs on a conversation's first message — a
  deliberate simplification so mid-conversation follow-ups (which often
  echo phrases like "what if") are never mistaken for a fresh routing
  decision (see quality test 3's constraints vs. section 18's memory
  requirement — these two spec requirements are in tension for any
  phrase-based detector, and this module resolves it by scoping routing
  to first-turn-only).
- The mock generator's option-splitting (`_split_options`) only recognizes
  " or " / " vs " / " versus " as decision connectors — good enough for the
  quality tests and common phrasing; the LLM path has no such limitation.
- `coach_messages` has no `profile_id` column of its own; RLS enforces
  ownership transitively through `conversation_id -> coach_conversations.
  profile_id` via an `EXISTS` subquery (see policies/007_rls_ai_coach.sql).
