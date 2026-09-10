# `career_roadmap`

Backs the dashboard's **Career Roadmap** page: `POST /career-ai/career-roadmap`
generates (or regenerates) a personalized roadmap toward a target role,
`GET /career-ai/career-roadmap` returns the user's current one. This is the
only place in the backend that talks to an LLM for this feature.

## Why this module doesn't follow the rest of the app's layering

Same reasoning as `app.profile_analysis` (see that module's README for the
full rationale) — this is a **vertical slice** (`routers/`, `services/`,
`schemas/`, `models/`, `utils/` nested under `app/career_roadmap/`) rather
than spread across the top-level `schemas/`, `models/`, `services/`,
`api/v1/routes/` folders. There is an older, unimplemented scaffold at
`app/api/v1/routes/roadmap.py` / `app/services/roadmap_service.py` /
`app/schemas/roadmap.py` / `app/ai/prompts/roadmap.py` /
`app/ai/chains/roadmap.py` predating this module — each of those files now
has a docstring note pointing here. They're left in place (unimplemented,
`NotImplementedYetError`) rather than deleted, and nothing in the frontend
calls their routes (`/api/v1/roadmap/...`, distinct from this module's
`/api/v1/career-ai/career-roadmap`).

## How this differs from `profile_analysis`

The most important structural difference: `career_roadmaps` has a
`unique(user_id)` constraint — **at most one roadmap per user**, overwritten
on every regenerate — not append-only history like `profile_analysis`. That
one fact shapes several things below: `repository.save_roadmap()` upserts
rather than inserts, there is no history/timeline endpoint, and the RLS
policy needs an UPDATE grant that `profile_analysis` doesn't.

The second difference: there is no numeric score here, so there is no
`utils/scoring.py` equivalent — no `reconcile()` step reconciling a
generator's output against deterministic math. Each generator is
responsible for its own internally consistent output (phase durations that
sum to the requested timeline, tasks scaled to the requested weekly
commitment).

## Files, and why each exists

```
career_roadmap/
├── schemas/roadmap.py           Wire contract — the ONE shape mock and LLM must both produce
├── models/roadmap.py            DB row shapes for career_roadmaps / roadmap_activity
├── utils/context.py             RoadmapContext — profile + experiences + latest analysis + setup answers
├── services/generators/base.py             Abstract generator interface
├── services/generators/mock_generator.py   Rule-based generator, zero network calls
├── services/generators/langgraph_generator.py  LangChain + OpenAI structured-output generator
├── services/generators/factory.py          Picks mock vs. real based on OPENAI_API_KEY
├── services/repository.py       All Supabase reads/writes for this feature
├── services/roadmap_service.py  Orchestration: fetch → generate → upsert → log activity → return
└── routers/roadmap_router.py    Thin HTTP layer: POST + GET /career-ai/career-roadmap
```

**`schemas/roadmap.py`** — `RoadmapContent` (title, target_role,
overall_goal, estimated_duration, overview, `industry_landscape`,
`starting_point`, `phases`, expected_skills, `portfolio_outcomes`,
final_outcome) is the structured-output schema for the LLM AND the mock
generator's return type, same role `AnalysisContent` plays in
`profile_analysis`.

This shape was deepened significantly from an earlier, shallower version
(flat per-phase `tasks` + `milestones` list) to make the roadmap read as an
actual curriculum rather than a generic task list:

- `IndustryLandscape` (`current_frameworks_and_tools` / `emerging_trends` /
  `why_this_matters`) is new: general field context — what practitioners in
  this exact target role use today — independent of the candidate's own
  profile, unlike everything else in this schema. Added because a roadmap
  driven purely by the candidate's personal gaps can still leave them
  unaware of the field's current tooling landscape, even where a given
  tool isn't taught as its own phase. See "Industry Landscape vs. Starting
  Point" below for how this differs from `StartingPoint`.
- `StartingPoint` (`existing_strengths` / `priority_gaps` /
  `roadmap_strategy`) makes the gap analysis the whole roadmap is derived
  from visible to the user, instead of leaving it as invisible internal
  reasoning.
- `RoadmapPhase` gained `phase_number`, `duration_weeks` (an int, not a
  string range — the frontend computes the cumulative "Weeks X-Y" display,
  see `RoadmapView.jsx`'s `withWeekRanges`), `personalization_reason`
  (why this phase sits exactly here, for this profile), `builds_on` /
  `unlocks` (what makes the phase list read as a dependency graph instead of
  an arbitrary sequence), and a single `milestone` (was a list; a phase has
  exactly one checkpoint).
- `RoadmapTask` was replaced by `RoadmapObjective` — several per phase
  (roughly 2-5, scaled to weekly commitment), each with `topics` (concrete
  sub-topics), `estimated_hours` (an int), `resources` (see
  `RoadmapResource` below), a concrete `deliverable`, and observable
  `completion_criteria` (a list, not a single sentence).
- `RoadmapResource` is new: `title` / `provider` / `type` (course, book,
  documentation, paper, tutorial, video, repository, or practice) / `reason`
  / `free`. **Deliberately has no `url` field at all** — see "Resources have
  no URLs, by design" below.
- `portfolio_outcomes` is new: the concrete, shippable artifacts the user
  should finish with, distinct from `expected_skills` (a skills list) and
  `final_outcome` (a capability/readiness summary).

`RoadmapContent` deliberately does NOT declare `primary_goal`,
`timeline_months`, `weekly_commitment`, `id`, `user_id`, `llm_model`,
`generated_at`, or `updated_at` — those come from the DB row, not from
generated content (see `roadmap_service._to_response`).

`RoadmapGenerateRequest` (the setup-screen/Regenerate input) and
`CareerRoadmapResponse` (persistence metadata layered on `RoadmapContent`)
are unchanged in shape.

**`models/roadmap.py`** — unchanged: `CareerRoadmapRow` (loose, for reads),
`CareerRoadmapUpsert` (strict, for the upsert write), `RoadmapActivityInsert`
(one row per generate/regenerate — a lightweight audit trail, not read back
by the current UI). `roadmap_json` is still just `dict` at this layer — the
deepened internal shape above is a `schemas/roadmap.py`-only change, not a
DB migration (see "Data model" below).

**`utils/context.py`** — `RoadmapContext` wraps the raw `profiles` +
`experiences` rows, an optional latest `profile_analysis` row, and the
setup answers into `to_prompt_text()`. Deliberately does NOT import
`app.profile_analysis.utils.context.ProfileContext` — that module's own
README restricts imports to its router, so this reads the same kind of
signal (leadership, research, portfolio, ...) with its own small,
independent implementation instead. Also surfaces the latest Profile
Analysis's `career_signals` and `recruiter_signals` (not just its summary
fields) — this is what lets the roadmap tell "already strong enough"
(`existing_strengths`) apart from "missing" (`priority_gaps`) at the level
of a named signal, not just a single overall score.

**`services/generators/mock_generator.py`** — deterministic, zero network
calls; the fallback path only (used when `OPENAI_API_KEY` is not set). It
holds itself to the same resource-fabrication standard as the LLM generator
(a small, hand-curated `_RESOURCE_LIBRARY` of real, stable, official-docs
and well-known URLs — anything not confidently correct gets no resource
entry at all rather than a guessed one) but cannot reasonably build an
exhaustive, dependency-aware curriculum for arbitrary target roles the way
a live model can — see `langgraph_generator.py` below for where the
platform's real depth guarantee lives. It matches the target role against
`_ROLE_SKILL_LIBRARY` (falls back to a generic technical baseline for an
unrecognized role), diffs against the profile's actual skills to find
genuine gaps, never recommends a skill/portfolio link/leadership role the
profile already has, and builds 3 phases (3-month plan) or 4 phases
(6-month plan): close skill gaps (or deepen existing ones, if none are
missing) → build and ship one project → (6-month only) close a secondary
differentiation gap (leadership/hackathons/open source) → a final
goal-specific phase templated per `primary_goal`. `builds_on`/`unlocks` are
filled in as a second pass once every phase's title is known, chaining each
phase to its neighbor.

**`services/generators/langgraph_generator.py`** — a single
`ChatOpenAI(...).with_structured_output(RoadmapContent, method="json_schema",
strict=True)` call (OpenAI's Structured Outputs mode — every required field
guaranteed present). No LangGraph pipeline (unlike profile_analysis, and
deliberately not added here either — see the module docstring) since
there's no deterministic post-processing node to run afterward. **This file
is where the platform's actual roadmap-quality guarantee lives** — see
"The system prompt" below.

**`services/generators/factory.py`** — `get_roadmap_generator()` returns the
LangChain/OpenAI generator if `OPENAI_API_KEY` is set, otherwise the mock,
identical pattern to `profile_analysis/services/generators/factory.py`.

**`services/repository.py`** — reads `profiles`, `experiences`, and the
latest `profile_analysis` row directly (rather than importing
`profile_analysis`'s service layer — see "How this differs" above); reads/
upserts `career_roadmaps`; best-effort inserts into `roadmap_activity`
(swallows its own errors — a logging failure should never fail the roadmap
generation the user is waiting on).

**`services/roadmap_service.py`** — `generate_roadmap()` builds a
`RoadmapContext`, calls the generator, upserts the result, logs an activity
row, and returns the combined response; `get_current_roadmap()` reads the
user's single row without generating anything, 404ing (→ the frontend's
setup screen, not an error) if none exists yet.

**`routers/roadmap_router.py`** — thin HTTP layer. The same `POST` endpoint
backs both "Generate Roadmap" (first time) and "Regenerate Roadmap" (the
frontend resends the roadmap's own stored setup answers); `GET` returns the
current one without generating anything.

## Data model

`career_roadmaps` / `roadmap_activity` (see
`supabase/schema/016_career_roadmap.sql`) — `career_roadmaps` has
`unique(user_id)`, so "current roadmap" is just `eq(user_id, ...)`, no
`order by`/`limit` needed the way `profile_analysis`'s "latest" is. RLS (see
`supabase/policies/005_rls_career_roadmap.sql`) grants each user SELECT +
INSERT + UPDATE on their own `career_roadmaps` row (the UPDATE grant is
what `profile_analysis` doesn't need, since regenerate overwrites in place)
and SELECT + INSERT (no UPDATE/DELETE) on their own `roadmap_activity` rows.

## Swapping in real OpenAI

1. Set `OPENAI_API_KEY` in `backend/.env` (shared with `profile_analysis`).
2. Optionally set `CAREER_ROADMAP_MODEL` (defaults to `DEFAULT_CHAT_MODEL`).
3. No other code changes — `factory.py` switches generators automatically.

## The system prompt (`langgraph_generator.py::_SYSTEM_PROMPT`)

Casts the model as a **Technical Career Curriculum Architect**, not a
chatbot or career-advice assistant. Its job: turn (profile + target role +
goal + available time) into a structured, dependency-aware technical
development plan.

It's structured in three parts:

1. **A silent internal gap analysis (Step 1)** the model is instructed to
   reason through before producing anything — current capabilities, which
   of those are actually *supported* by evidence (a project/experience, not
   just a listed skill), missing foundations, missing role-specific
   skills, missing practical (applied, not just theoretical) experience,
   and missing career signals (portfolio/OSS/writing, informed by the
   latest Profile Analysis if one exists). The prompt is explicit that this
   reasoning must never be output as chain-of-thought — only its
   conclusions, in `starting_point`'s fields.
2. **An industry-landscape instruction (Step 1B)**, explicitly separated
   from Step 1 because it draws on a different kind of knowledge: general,
   current knowledge of the field itself (frameworks/tools/trends
   practitioners in this exact target role use today), not evidence from
   the candidate's own profile. The prompt instructs the model to be
   specific (name the actual tool, not a category) and conservative (state
   only what it's genuinely confident is current — never overclaim
   something as "the latest" or "cutting-edge"). See "Industry Landscape
   vs. Starting Point" below for why these two are kept distinct.
3. **25 hard rules**, covering: never inventing experience/skills the
   profile doesn't show; never re-teaching what's already present; never
   crediting course completion as mastery; a phase must have a real
   `builds_on`/`unlocks`, not be arbitrarily reorderable; role/profile/
   timeline/commitment/goal must actually change the roadmap's shape (two
   different target roles must produce structurally different roadmaps,
   never the same shape with different labels); 2-5 objectives per phase,
   scaled to weekly commitment; concrete topics/deliverables/completion
   criteria (never "understand X"); 2-4 resources per objective serving
   distinct purposes (learn / reference / deep dive / build); phase
   `duration_weeks` must sum to `timeline_months * 4`; foundational gaps
   before project work before the goal-facing final phase; specific
   `expected_skills` (never "basic understanding of X", never inflated
   labels like "expert" unless earned by scope); concrete
   `portfolio_outcomes`; a `final_outcome` naming capabilities + artifacts +
   readiness, explicitly never a guarantee of employment/expertise; the
   no-URLs rule below; and never fabricating a framework/tool/trend name in
   `industry_landscape`.

## Industry Landscape vs. Starting Point

These two sections sit next to each other in the roadmap (Industry
Landscape first, Starting Point second) and are easy to conflate, but they
answer different questions and are grounded in different kinds of
knowledge:

- **Industry Landscape** answers "what does this field look like right
  now?" — general, role-level knowledge (frameworks, tools, platforms,
  well-established current trends) that's true of the target role
  regardless of who's asking. It is NOT a claim about this candidate's
  profile.
- **Starting Point** answers "where does THIS candidate stand against THIS
  target role?" — profile-grounded, evidence-based (existing_strengths /
  priority_gaps / roadmap_strategy), and must trace to something specific
  in the given profile, experiences, or latest Profile Analysis.

This is why the system prompt keeps them as separate steps (Step 1 vs. Step
1B) with different evidentiary standards: Step 1 forbids the model from
claiming anything about the candidate that isn't profile-supported; Step 1B
explicitly permits (and requires) drawing on general industry knowledge,
while still holding it to a conservative, non-hyped standard (rule 24 —
never fabricate a framework/tool/trend, and never overclaim something as
"the latest" without genuine confidence). A tool can legitimately appear in
both sections for different reasons — e.g. PyTorch might appear in
`industry_landscape.current_frameworks_and_tools` (it's what the field
uses) and again inside a phase's `objectives.topics` (it's what this
specific roadmap teaches this specific candidate) — that overlap is
expected, not a bug.

## Resources have no URLs, by design

`RoadmapResource` has no `url` field at all — not a nullable one, an absent
one. Earlier this had a nullable `url` ("include one only if confident it's
real"), but even resources fetched and confirmed live during development
(official docs, arXiv papers, well-known courses) get restructured, moved to
a new domain, or renamed often enough that a link stated with full
confidence today is not a durable guarantee — this system has no mechanism
to keep a generated link accurate after the fact, and a stale or dead link
is worse than no link. So a resource is now identified by `title` +
`provider` + `type` + `reason` only — described precisely enough (e.g. "the
official PyTorch tutorials", provider "PyTorch") that the user can find the
current version with their own search, which stays accurate regardless of
how the source restructures its site. Rule 13 of the system prompt makes
this explicit: never include a URL or link anywhere in the output, including
inside free-text fields. `ResourceItem.jsx` renders title/provider/type/
reason only — there is no link-rendering code path to accidentally trigger.

## Frontend rendering

`frontend/src/components/career-ai/roadmap/`:

- `RoadmapView.jsx` — added an "Industry Landscape" ReportSection (current
  frameworks/tools, emerging trends, why it matters), a "Starting Point"
  section (existing strengths / priority gaps / strategy), and a
  "Portfolio Outcomes" section; computes each phase's cumulative
  "Weeks X-Y" display from `duration_weeks` (`withWeekRanges`).
- `PhaseCard.jsx` — renders `purpose`, `personalization_reason`, `builds_on`/
  `unlocks` (as two small callout boxes), `objectives`, and the single
  `milestone`.
- `ObjectiveItem.jsx` (new) — one objective per `<details>` element for
  progressive disclosure (title/priority/hours always visible; why it
  matters, topics, resources, deliverable, and completion criteria only
  render once expanded), so a 4-5-objective phase doesn't dump everything
  onscreen at once.
- `ResourceItem.jsx` (new) — a type badge (Course/Book/Docs/Paper/Tutorial/
  Video/Repo/Practice) plus a Paid marker when `free: false`; renders
  title/provider/reason as plain text only — there is no link-rendering
  code path, since `RoadmapResource` has no `url` field to render.
- `MilestoneItem.jsx` — updated for `title` (was `name`) and a
  `completion_criteria` list (was a single string).
- `TaskItem.jsx` — superseded by `ObjectiveItem.jsx`; left as a documented
  stub rather than deleted (this workspace's file-retention convention).

## Backward compatibility with rows generated before this change

`roadmap_json` is still just a `jsonb` blob — no migration is required (see
`models/roadmap.py`'s docstring). A row generated under the old, shallower
shape won't validate against the current `RoadmapContent` on read, though:
`roadmap_service.get_current_roadmap()` catches that `pydantic.ValidationError`
and raises `NotFoundError` the same as "no roadmap yet" — the frontend falls
back to the setup screen, and a fresh Generate Roadmap produces a row in the
current shape. `generate_roadmap()` itself never hits this path, since its
input is always the current call's freshly-validated generator output.
