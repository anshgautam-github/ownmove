# Supabase

Version-controlled definition of everything Supabase owns: **Postgres schema,
Row Level Security policies, and seed data.**

Previously this lived only in the Supabase dashboard — meaning the schema was
undocumented, unreviewable, and impossible to recreate. These files fix that.

## Apply order

Run in the Supabase SQL Editor (or via the CLI) in this order:

| Order | File | Purpose |
| --- | --- | --- |
| 1 | `schema/001_profiles.sql` | `profiles`, `experiences` |
| 2 | `schema/002_opportunities.sql` | `opportunities` + category constraint |
| 3 | `schema/003_saved_opportunities.sql` | `saved_opportunities` bookmarks |
| 4 | `policies/001_rls.sql` | **Row Level Security — required** |
| 5 | `seeds/001_opportunities.sql` | Sample listings (safe to re-run) |
| 6 | `schema/004_profiles_v2.sql` | Onboarding/resume/analytics columns on `profiles` |
| 7 | `schema/005_opportunities_v2.sql` | Ingestion identity (`source`/`source_id` — column later renamed from `external_id` on the live table, see 32), keyword search |
| 8 | `schema/006_ai_embeddings.sql` | `profile_embeddings`, `opportunity_embeddings` (pgvector) |
| 9 | `schema/007_ai_profile_insights.sql` | `profile_insights` — AI profile analysis output |
| 10 | `schema/008_recommendations_events.sql` | `recommendations`, `interaction_events` |
| 11 | `policies/002_rls_ai.sql` | RLS for the tables added in 6–10 — **required** |
| 12 | `policies/003_storage_resumes.sql` | `resumes` storage bucket + per-user RLS — **required for resume upload** |
| 13 | `schema/009_profiles_v3.sql` | Drops `projects_worked`; renames `profile_summary` → `ai_profile_summary` |
| 14 | `schema/010_opportunities_v3.sql` | Adds `eligible_years`, `duration` to `opportunities` |
| 15 | `schema/011_experiences_v2.sql` | Renames `employment_type` → `experience_type`; adds `skills_used` |
| 16 | `schema/012_profile_analysis.sql` | `profile_analysis` — AI career-intelligence dashboard output |
| 17 | `policies/004_rls_profile_analysis.sql` | RLS for `profile_analysis` — **required** |
| 18 | `schema/013_profile_analysis_blind_spots.sql` | Adds `career_blind_spots` to `profile_analysis` (superseded by 19) |
| 19 | `schema/014_profile_analysis_intelligence_report.sql` | Adds `profile_diagnosis`, `career_signals`, `profile_contradictions`, `score_breakdown`, `evidence_credibility` — the "Career Intelligence Report" redesign |
| 20 | `schema/015_profile_analysis_recruiter_signals.sql` | Adds `recruiter_signals`, replacing `evidence_credibility` (superseded) with a non-verification-implying signal check |
| 21 | `schema/016_career_roadmap.sql` | `career_roadmaps`, `roadmap_activity` — AI-generated personalized roadmap |
| 22 | `policies/005_rls_career_roadmap.sql` | RLS for `career_roadmaps`/`roadmap_activity` — **required** |
| 23 | `schema/017_career_simulation.sql` | `career_simulations` — "what if I did X" decision-support simulations |
| 24 | `policies/006_rls_career_simulation.sql` | RLS for `career_simulations` — **required** |
| 25 | `schema/018_ai_coach.sql` | `coach_conversations`, `coach_messages` — AI Coach conversational decision assistant |
| 26 | `policies/007_rls_ai_coach.sql` | RLS for `coach_conversations`/`coach_messages` — **required** |
| 27 | `seeds/002_opportunities_programs_v2.sql` | Fixes 4 placeholder `apply_url`s on existing "programs" rows (AWS, Summer of Bitcoin, NASA, GDG) and adds 10 more real, verified student programs (safe to re-run) |
| 28 | `seeds/003_opportunities_logo_fix.sql` | Swaps 3 logos (Smart India Hackathon, Outreachy, Kode With Klossy) from Google's favicon endpoint to DuckDuckGo's, which 404'd for those domains (safe to re-run) |
| 29 | `schema/019_opportunities_ingestion.sql` | Adds `fingerprint` (content-based cross-source dedupe key) and `enrichment_status`/`enrichment_queued_at` to `opportunities`, backing `backend/app/ingestion/services/opportunity_service.py` — **required** before that service is used |
| 30 | `schema/020_opportunity_applications.sql` | `opportunity_applications` — lets a user mark an opportunity as applied, hiding it from their Discover lists |
| 31 | `policies/008_rls_opportunity_applications.sql` | RLS for `opportunity_applications` — **required** |
| 32 | `schema/025_opportunities_ingestion_source_id_rename.sql` | Renames `opportunities.external_id` → `source_id` to match what's actually on the live table (idempotent; also backfills the `(source, source_id)` unique index if missing); backs the Devpost hackathon ingestion agent (`backend/app/ingestion/agents/sources/devpost.py`) |

See [`../docs/schema-v2-design.md`](../docs/schema-v2-design.md) for the full
rationale behind 6–15, the ER diagram, and tables intentionally deferred.
`profile_analysis` (16–20) backs the Profile Analysis dashboard feature —
see `backend/app/profile_analysis/README.md`. `career_roadmaps`/
`roadmap_activity` (21–22) back the Career Roadmap feature — see
`backend/app/career_roadmap/README.md`. Unlike `profile_analysis`,
`career_roadmaps` holds at most one row per user (`unique(user_id)`) rather
than append-only history. `career_simulations` (23–24) backs the Career
Simulation feature — see `backend/app/career_simulation/README.md`. Like
`profile_analysis` (and unlike `career_roadmaps`), it is append-only: every
simulation or comparison inserts a new row rather than overwriting one.
`coach_conversations`/`coach_messages` (25–26) back the AI Coach feature —
see `backend/app/ai_coach/README.md`. Unlike any of the above, this is a
normal one-conversation-to-many-messages parent/child pair rather than a
single flat table.

> **Note:** `schema/007_ai_profile_insights.sql` (`profile_insights`) and
> `schema/012_profile_analysis.sql` (`profile_analysis`) now overlap in
> purpose — both were designed to hold "AI profile analysis output," from two
> separate rounds of planning. `profile_analysis` is the one the Profile
> Analysis feature actually reads and writes; `profile_insights` was never
> implemented against and is a candidate for removal once you confirm nothing
> depends on it.

Every file is idempotent (`if not exists`, `drop policy if exists`, `NOT EXISTS`
guards), so re-running is safe.

## Why RLS is not optional

The browser holds only the **anon key** and queries PostgREST directly. Postgres
RLS is the sole thing preventing one user from reading another's data. A table
with RLS disabled is public to anyone with the anon key — which ships in the
JavaScript bundle.

Rules:
- Every user-owned table gets RLS enabled and an explicit policy per operation.
- Ownership is always `= auth.uid()`.
- `opportunities` is curated content: readable by any signed-in user, writable
  by nobody through the API.
- The **service-role key bypasses RLS entirely.** Server-side only, never in the
  browser, never driven by user input.

## Schema notes

`profiles.id` **is** `auth.users.id` (one profile per user). That is what makes
every policy a simple `id = auth.uid()` check with no join.

`saved_opportunities` is a pure join table with `unique (user_id,
opportunity_id)`. That constraint makes "save" idempotent: a duplicate insert
returns `23505`, which the client treats as already-saved rather than an error.

`schema/001_profiles.sql` was originally a reconstruction, since the DDL was
never committed. It has since been corrected against the real live table
twice: once to add columns that existed in Supabase but were never in source
control (`full_name`, `email`, `profile_photo`, `headline`, `bio`, `city`,
`country`, `profile_score`, `onboarding_completed`, `last_profile_analysis`,
`target_role`, `target_company`, `graduation_status`, `resume_url`, plus
renaming `github_username` to the real column name `github_url`), and again
when `projects_worked` was dropped and `profile_summary` was renamed to
`ai_profile_summary` — see `schema/009_profiles_v3.sql`.

`schema/002_opportunities.sql` got the same treatment: `eligible_years`
(`integer[]`) and `duration` (`text`) were added directly on the live table
and are now in the baseline — see `schema/010_opportunities_v3.sql`. This
also retired the `eligibility_tags` column `005_opportunities_v2.sql` had
planned but never applied; `eligible_years` is the real version of that idea.

`experiences.employment_type` was renamed to `experience_type`, and
`skills_used` (`text[]`) was added — a per-role signal, finer-grained than
`profiles.current_skills` — see `schema/011_experiences_v2.sql`.

`profile_embeddings` and `opportunity_embeddings` (006) are deliberately
**not** vector columns on `profiles`/`opportunities` — see
`docs/schema-v2-design.md` for why. They require the `vector` extension,
enabled inline by that file (Supabase has it available by default).

## Migrations

`migrations/` is reserved for the Supabase CLI (`supabase migration new …`)
once you adopt it. Until then, `schema/` + `policies/` are the source of truth;
add new numbered files rather than editing applied ones.
