# Career Simulation

Decision-support feature that answers one question: **"BEFORE I spend time
doing X, what would X actually add to my profile for THIS target role?"**

It is deliberately NOT:
- Profile Analysis (diagnoses the CURRENT profile)
- Career Roadmap (explains HOW to progress toward a target role)
- Opportunity Matcher (recommends real, existing opportunities)
- A motivational coach, generic career advisor, recruiter, fortune teller,
  roadmap generator, or profile summarizer

The model evaluates **incremental value**: not "is this activity useful"
in the abstract, but "what NEW value does this specific activity add to
THIS candidate's EXISTING profile, for THIS target role." The same
hypothetical action can — and should — receive a different verdict for two
different candidates' profiles; if it doesn't, personalization has failed
(see "Quality tests" below).

## Architecture

Self-contained vertical slice, same shape as `app/profile_analysis/` and
`app/career_roadmap/`:

```
career_simulation/
  schemas/simulation.py    # wire + generator contract
  models/simulation.py     # DB row shapes (career_simulations)
  utils/context.py         # SimulationContext + KNOWN/HYPOTHETICAL prompt text
  services/
    generators/
      base.py              # BaseSimulationGenerator interface
      mock_generator.py    # deterministic fallback, no API key needed
      langgraph_generator.py  # OpenAI via LangChain structured output
      factory.py           # picks a generator based on OPENAI_API_KEY
    repository.py          # Supabase I/O (user-scoped client only)
    simulation_service.py  # orchestration: create pending -> generate -> complete/fail
  routers/simulation_router.py
```

No LangGraph, no agents, no multi-agent architecture, no vector database,
no embeddings, no RAG, no tool-calling loop, no background workflow — same
constraint `career_roadmap` and `profile_analysis` already follow. This is
structured reasoning over already-known profile data, not retrieval or
autonomous multi-step tool use. `langgraph_generator.py` is named to match
its two sibling modules for consistency, even though (like both of them) it
doesn't actually use LangGraph — a single `with_structured_output(...,
method="json_schema", strict=True)` call is the entire generator.

## Database

`career_simulations` (see `supabase/schema/017_career_simulation.sql`) is
**append-only** — every simulation or comparison inserts a new row — unlike
`career_roadmaps`, which holds at most one row per user. Written in two
phases: an initial `status='pending'` row before the LLM call, then updated
to `status='completed'` (with `result`/`verdict`/`model_used`/
`completed_at`) or `status='failed'`. A failed attempt stays a permanent,
visible row rather than being silently dropped.

`simulation_type` covers seven values (A-G in the product spec):
`build_project`, `gain_experience`, `learn_skill`, `certification`,
`open_source`, `change_target_role`, `compare_moves` (the last is only ever
set server-side when persisting a comparison).

`verdict` is a flat, lowercase snake_case column
(`high_value`/`useful`/`limited_value`/`low_value`) or `NULL` — `NULL` for
`compare_moves` rows, since a single headline verdict doesn't describe
"which of two options is the better fit" (that lives inside
`result.comparison` instead). The richer, UPPERCASE `result.verdict.level`
inside the jsonb blob is the generator's literal structured output and is
never itself constrained by this column's CHECK; `simulation_service.py`'s
`_VERDICT_DB_MAP` is the one place the translation happens.

RLS: `supabase/policies/006_rls_career_simulation.sql`, scoped to
`profile_id = auth.uid()`.

## Fact/hypothesis discipline

`utils/context.py`'s `SimulationContext.to_prompt_text()` renders the real
profile under an explicit `=== CURRENT PROFILE (KNOWN) ===` heading and the
simulated action under an explicit
`=== HYPOTHETICAL CHANGE (NOT REAL) ===` heading, so the fact/hypothesis
boundary is structurally obvious to the model, not left to prose. The
system prompt additionally distinguishes four classes on every reasoning
step: KNOWN, HYPOTHETICAL, INFERRED, UNKNOWN — UNKNOWN is never silently
converted to KNOWN.

Nothing in this feature ever writes a hypothetical result back into
`profiles`, `experiences`, or any other real-data table — `career_simulations`
rows are the only place simulation output is ever persisted. Simulation
data remains isolated from the real profile by construction.

## Anti-hallucination protections

The system prompt (`langgraph_generator.py`'s `_SYSTEM_PROMPT`) explicitly
forbids: hiring/interview/job-offer probabilities, salary-improvement
figures, recruiter-acceptance probabilities, arbitrary profile-improvement
percentages, fake industry statistics, fake achievements/skills/
proficiency/experience/recruiter opinions, and any guarantee. It also
enforces:

- **Listed vs. demonstrated**: a skill in `profiles.current_skills` means
  the candidate *reports* familiarity, not proven proficiency. A
  certification demonstrates structured learning, not production expertise.
  A project doesn't prove professional experience. An internship doesn't
  prove mastery. Open-source participation doesn't prove deep expertise.
- **Scope discipline**: if a scenario doesn't specify deployment, real
  users, production traffic, evaluation, or scale, the model must not
  claim "production" or "large-scale" experience just because the action
  type sounds impressive.
- **Redundancy detection**: before crediting an action with value, the
  model must check whether the profile already demonstrates that
  capability more strongly — a critical, explicitly-required check, not an
  optional nicety.
- **Remaining gaps are mandatory**: a result with no remaining gaps reads
  as motivational AI, not honest analysis, and is treated as a prompt
  violation.

The mock generator (used when no `OPENAI_API_KEY` is configured) enforces
the same discipline mechanically: it classifies the scenario's topic as
`demonstrated` / `listed` / `absent` against the actual profile and derives
the verdict, redundancy flag, and claims from that classification — never
from the activity type alone.

## Quality tests this feature must pass

1. **User A vs. User B**: the same hypothetical action (e.g. "complete an
   introductory ML certification") must produce a *different* verdict for
   a candidate with no ML projects than for a candidate with several — if
   both get the same analysis, personalization has failed.
2. **RAG-project scope test**: simulating "build a RAG project" for an LLM
   Engineer target, with no mention of deployment/users/traffic/
   evaluation/scale, must never claim "production LLM engineering
   experience" or "large-scale AI systems experience" — only what the
   scenario as described actually supports.

## Security

LLM calls happen only in this backend process; the API key is never sent
to or usable by the frontend. `profile_id` is always `user.id` from the
authenticated JWT (`CurrentUser`/`AccessToken` in the router) — never a
value read from the request body. A user can only access their own
simulations, enforced both by application code (`repository.py` always
filters on the authenticated `profile_id`) and by RLS at the database
layer.

## API

- `POST /api/v1/career-ai/career-simulation` — run one hypothetical action
- `POST /api/v1/career-ai/career-simulation/compare` — compare two moves
- `GET /api/v1/career-ai/career-simulation/history` — recent simulations (minimal: scenario/target role/verdict/date)
- `GET /api/v1/career-ai/career-simulation/{id}` — fetch one past simulation or comparison

## Frontend

`frontend/src/components/career-ai/CareerSimulationDashboard.jsx` is the
state-machine container (`loading-initial -> setup -> submitting ->
result-single | result-compare -> error`), mirroring
`CareerRoadmapDashboard.jsx`'s shape. `simulation/` holds:
`SimulationSetupForm.jsx` (type selector + per-type fields + a
"Compare two moves" toggle + profile-derived quick scenarios),
`SimulationResultView.jsx` / `ComparisonResultView.jsx` (structured report
layout, never a single AI paragraph), and shared row components
(`VerdictCard`, `SignalItem`, `GapImpactRow`, `EvidenceItem`, `ClaimItem`,
`RedundancyNotice`), plus `RecentSimulations.jsx` for history.

## Known assumptions / simplifications

- Quick scenario suggestions are derived from the profile's own
  `target_role`/`current_skills` at request time in the frontend — they
  are not a separate backend endpoint, since the spec explicitly says they
  are optional UI sugar, not a core requirement.
- The mock generator's role-skill vocabulary (`_ROLE_SKILL_LIBRARY` in
  `mock_generator.py`) is a smaller, independent copy of the same idea in
  `career_roadmap`'s mock generator — the two modules deliberately don't
  import from each other (see each module's own repository/README
  convention), and this feature's mock path only needs to be directionally
  honest, not an exhaustive per-role curriculum (that depth lives in the
  LLM path's system prompt).
- Comparison mode issues a single structured-output call requesting
  `option_a`, `option_b`, and `comparison` together (rather than three
  separate calls) — this still satisfies "evaluate independently first,
  then compare," since the schema forces each option to be a complete,
  standalone `SimulationResult` before `comparison` is produced, while
  avoiding tripling latency/cost for no added independence.
