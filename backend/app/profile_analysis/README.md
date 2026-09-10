# `profile_analysis`

Backs the dashboard's **Profile Analysis** page: `POST /career-ai/profile-analysis`
generates a fresh AI read of the caller's profile, `GET /career-ai/profile-analysis`
returns the latest saved one. This is the only place in the backend that talks
to an LLM for this feature.

## Why this module doesn't follow the rest of the app's layering

Everywhere else, `schemas/`, `models/`, `services/` and `api/v1/routes/` are
top-level folders shared by every feature. This feature is deliberately a
**vertical slice** instead — its own `routers/`, `services/`, `schemas/`,
`models/`, `utils/` nested under `app/profile_analysis/`. Two reasons:

1. It has a genuinely different shape from a normal CRUD route: a swappable AI
   backend, a deterministic post-processing pass, and a benchmark-programs
   table that only this feature cares about. Spreading that across the shared
   folders would mean five almost-empty files scattered through unrelated
   directories, all only ever imported by each other.
2. It's meant to be legible as one unit — read this directory top to bottom
   and you have the whole feature, instead of chasing `analysis_service.py`
   through `services/`, `schemas/analysis.py` through `schemas/`, etc.

Nothing outside this package should import anything from it except
`routers.analysis_router.router`, which `api/v1/router.py` mounts like any
other router.

## Files, and why each exists

```
profile_analysis/
├── schemas/analysis.py         Wire contract — the ONE shape mock and LLM must both produce
├── models/analysis.py          DB row shapes (loose, for reads) vs. insert shape (strict, for writes)
├── utils/context.py            ProfileContext — turns raw profile+experience rows into signals
├── utils/programs.py           Deprecated stub (see file docstring)
├── utils/scoring.py            reconcile() — the "not a ChatGPT wrapper" guardrail
├── services/generators/base.py             Abstract generator interface
├── services/generators/mock_generator.py   Rule-based generator, zero network calls
├── services/generators/langgraph_generator.py  LangGraph + OpenAI generator
├── services/generators/factory.py          Picks mock vs. real based on OPENAI_API_KEY
├── services/repository.py      All Supabase reads/writes for this feature
├── services/analysis_service.py Orchestration: fetch → generate → reconcile → save → return
└── routers/analysis_router.py  Thin HTTP layer: POST + GET /career-ai/profile-analysis
```

**`schemas/analysis.py`** — Pydantic models for every section the frontend
renders (`ProfileDiagnosis`, `CareerSignal`, `MissingSignal`,
`ProfileContradiction`, `ScoreBreakdown`, `GrowthSimulation`,
`RecruiterSignal`, `HighestRoiRecommendation`), composed into
`AnalysisContent`. This is the "Career Intelligence Report" redesign: every
section exists to answer one specific question a person couldn't easily
answer by reading their own profile, and every conclusion cites real
evidence rather than a general impression — see each model's own docstring
for the reasoning behind its shape. This is the contract both
`MockAnalysisGenerator` and `LangGraphAnalysisGenerator` must satisfy —
LangChain's `with_structured_output(AnalysisContent)` uses this same class
to force the LLM's output into valid JSON, so the frontend never has to
handle a shape the mock generator wouldn't also produce. Score fields are
plain `int`, not range-constrained (`Field(ge=0, le=100)`) — an LLM drifting
to 104 should get clamped by `reconcile()`, not throw a validation error and
500 the request.

There is deliberately no personality-trait or "archetype" field anywhere in
this schema (an earlier version of this feature had one, called "Career
DNA" — see CareerSignal's docstring for why it was removed). `CareerSignal`
reports 6 fixed, observable patterns (Technical Leadership, Product
Building, Research Exposure, Community Involvement, Learning Consistency,
Software Engineering Foundation) honestly, including as "not observed" when
there's no evidence for one — never filtered down to a flattering subset.

`ProfileContradiction` is deliberately distinct from `MissingSignal`: a
missing signal is an *absence* ("no GitHub"); a contradiction is where the
profile's *stated* direction (`target_role`, `target_company`,
`career_interests`) and its *observed* evidence (experiences, skills)
measurably disagree (e.g. targeting an ML role with zero ML projects
logged, or listing "leadership" as an interest with no leadership-scoped
role in the history). Its `observed_evidence` field must be real, countable
facts, never a vague impression, and both generators return an empty list
rather than inventing one when a profile's stated goal and its evidence
already line up.

`ScoreBreakdown` is the itemized, auditable math behind `overall_score` —
see `utils/scoring.py` below. It is computed entirely by `reconcile()`, not
trusted from a generator, so `base_score + sum(factor.points for factor in
positive_factors + negative_factors) == final_score` always holds.

`RecruiterSignal` replaces an earlier "Evidence Credibility" section whose
verified/partially_verified language implied this platform checks the
actual contents of a GitHub repo, a resume file, or a LinkedIn profile — it
never did. This platform performs no external verification of any kind.
`RecruiterSignal` makes no such claim: it reports a fixed, 10-item
vocabulary (Technical Experience, Public Portfolio, Industry Exposure,
Leadership, AI/ML Focus, Open Source, Community Involvement, Research
Experience, Communication, Professional Presence), each with a named
`status` tier (Strong/Moderate/Limited/Missing/Unknown) derived only from
what's observable in the profile's own stated fields — never a percentage,
and never a claim about the quality of what's behind a link. "Unknown" is a
first-class, honest status for signals (like Communication) that structured
profile fields genuinely can't support a confident read on.

**`models/analysis.py`** — `ProfileAnalysisRow` (loose types, for rows read
back from `profile_analysis`) and `ProfileAnalysisInsert` (strict, for what we
write). Kept separate from `schemas/` because a DB row and an API response
happen to look similar today but shouldn't be forced to stay identical.

**`utils/context.py`** — `ProfileContext` wraps the raw `profiles` +
`experiences` rows and exposes derived signals (`has_github`, `has_resume`,
`has_leadership_signal`, `has_hackathon_signal`, `has_research_signal`,
`has_open_source_signal`, `has_portfolio_signal`, `all_skills`, ...) as
properties, plus `to_prompt_text()`, which renders the same data as a
structured block for the LLM prompt. Both generators read from the exact same
object, so "does this profile have a leadership signal" is answered
identically whether or not OpenAI is involved.

**`utils/programs.py`** — deprecated, kept in place (empty of logic) rather
than deleted since files already written to this workspace can't be removed
outright. See the file's docstring for its history — it's not part of the
running feature.

**`utils/scoring.py`** — `reconcile(content)` is the mechanism that makes this
"not a ChatGPT wrapper": it computes `score_breakdown` (and therefore
`overall_score`, which is just `score_breakdown.final_score`) as an itemized
sum over the content's own `recruiter_signals`, `career_signals`,
`missing_signals`, and `profile_contradictions` — a generator's own opinion
of "what the score should be" is never read at all. It then rebuilds
`growth_simulation` from the same `missing_signals` (each gap's own
`expected_score_impact`/`recommended_action`), and pins the ROI
recommendation's `estimated_score_gain` to the single biggest gap when one
exists, so all three numbers stay the mirror image of the same underlying
math instead of three independent guesses. Every generator's raw output —
mock or LLM — is required to pass through this before it's returned.

**`services/generators/base.py`** — `BaseAnalysisGenerator.generate(context)`
is the one method both implementations must provide. Swapping mock for real
AI is a one-line change in `factory.py`; nothing else in the codebase
(including the frontend) needs to know which one is running.

**`services/generators/mock_generator.py`** — deterministic, rule-based,
zero network calls. Runs today with no configuration at all, so the feature
is testable immediately, and gives every reviewer a stable fixture to compare
LLM output against.

**`services/generators/langgraph_generator.py`** — a 2-node LangGraph pipeline
(`generate` → `reconcile`) wrapping a single `ChatOpenAI(...).with_structured_output(AnalysisContent)`
call. It's a graph rather than a bare LLM call for one concrete reason: it
guarantees no raw model output ever reaches the caller without first passing
through the deterministic `reconcile` node — that boundary is structural, not
a convention someone has to remember to call. It also gives this feature room
to grow (e.g. a future "fetch similar profiles" node) without restructuring.

**`services/generators/factory.py`** — `get_analysis_generator()` returns the
LangGraph/OpenAI generator if `OPENAI_API_KEY` is set, otherwise the mock. The
OpenAI-specific generator is imported lazily inside the branch so that running
with no key never even imports `langchain`/`langgraph`.

**`services/repository.py`** — every Supabase call this feature makes:
fetching the profile and experiences, reading the latest saved analysis,
computing the next `analysis_version`, and inserting a new row. Isolated here
so `analysis_service.py` reads as pure orchestration with no query strings in
it.

**`services/analysis_service.py`** — the actual flow: build a user-scoped
Supabase client from the caller's own JWT (so RLS applies), load profile +
experiences, build a `ProfileContext`, call the generator, save the result,
return it. No FastAPI imports — this could be called from a script or a
background job just as easily as from the router.

**`routers/analysis_router.py`** — thin HTTP layer. `POST` runs a fresh
analysis (costs an LLM call when OpenAI is configured); `GET` returns the
latest saved one without generating anything, so the frontend can show a
cached result on page load without paying for a new run every time.

## Data model

`profile_analysis` (see `supabase/schema/012_profile_analysis.sql`, plus the
additive `career_blind_spots` column in
`supabase/schema/013_profile_analysis_blind_spots.sql` — superseded, see
below — and the current section columns in
`supabase/schema/014_profile_analysis_intelligence_report.sql`) is
**append-only** —
every run inserts a new row rather than updating in place, mirroring the
`profile_insights` design from an earlier migration. "Latest" is just `order
by created_at desc limit 1`. RLS (see
`supabase/policies/004_rls_profile_analysis.sql`) grants each user SELECT +
INSERT on their own rows only, no UPDATE/DELETE — this feature runs as the
user (via their JWT), not as a trusted service-role job, which is why it
differs from the service-role-only policies on the other AI tables.

The table still carries its original columns (`career_dna`, `recruiter_view`,
`career_blind_spots`, `evidence_scores`) from earlier iterations of this
feature — additive-only migrations mean nothing gets dropped. Nothing in the
current codebase reads or writes them; a row saved before migration 014
simply won't parse into the current `ProfileAnalysisResponse`, and
`analysis_service.py` treats that the same as "no analysis yet" (see its
`ValidationError` handling) rather than crashing.

## Swapping in real OpenAI

1. Set `OPENAI_API_KEY` in `backend/.env` (see `.env.example`).
2. Optionally set `PROFILE_ANALYSIS_MODEL` (defaults to `DEFAULT_CHAT_MODEL`).
3. `pip install -r requirements.txt` — `openai`, `langchain`,
   `langchain-openai`, `langgraph` are already listed; they weren't resolved
   against PyPI in the sandbox this feature was built in, so re-run
   `pip install -U langchain langchain-openai langgraph openai` and re-freeze
   if the pins don't resolve cleanly for you.

No other code changes, and no frontend changes, are needed — `factory.py`
switches generators automatically once the key is present.
