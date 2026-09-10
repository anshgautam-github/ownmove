-- ---------------------------------------------------------------------------
-- Career Roadmap — AI-generated, personalized roadmap toward a target role.
--
-- Unlike profile_analysis (append-only history), career_roadmaps holds AT
-- MOST ONE row per user (`unique(user_id)`): the first "Generate Roadmap"
-- inserts it, every subsequent "Regenerate Roadmap" overwrites that same
-- row in place (see backend/app/career_roadmap/services/repository.py's
-- save_roadmap(), which upserts on user_id). There is deliberately no
-- separate history/timeline endpoint for this feature.
--
-- The entire generated plan (title, overview, phases, tasks, milestones,
-- expected_skills, final_outcome) lives in one `roadmap_json` blob rather
-- than one column per section — none of that structure needs to be
-- queried or indexed independently; it's read back whole and rendered
-- whole. The setup answers that produced it (target_role, timeline_months,
-- weekly_commitment, primary_goal) are kept as real columns since a future
-- feature (e.g. "roadmaps like mine") might filter on them directly.
--
-- roadmap_activity is a lightweight, append-only audit trail of
-- generate/regenerate events — not surfaced in the UI yet, but present so
-- a future "roadmap history" or admin view doesn't need a schema change.
--
-- These tables were created directly against the live database before this
-- migration file was written; the statements below are `if not exists` so
-- running this file anywhere (including against that same database) is a
-- safe no-op.
-- ---------------------------------------------------------------------------

create table if not exists public.career_roadmaps (
  id uuid not null default gen_random_uuid (),
  user_id uuid not null,
  target_role text not null,
  timeline_months integer not null,
  weekly_commitment integer not null,
  primary_goal text not null,
  roadmap_json jsonb not null,
  llm_model text null,
  generated_at timestamp with time zone not null default now(),
  updated_at timestamp with time zone not null default now(),
  constraint career_roadmaps_pkey primary key (id),
  constraint career_roadmaps_user_unique unique (user_id),
  constraint career_roadmaps_user_id_fkey foreign key (user_id) references auth.users (id) on delete cascade
);

create index if not exists career_roadmaps_user_idx on public.career_roadmaps using btree (user_id);

create table if not exists public.roadmap_activity (
  id uuid not null default gen_random_uuid (),
  roadmap_id uuid not null,
  user_id uuid not null,
  activity_type text not null,
  description text null,
  created_at timestamp with time zone not null default now(),
  constraint roadmap_activity_pkey primary key (id),
  constraint roadmap_activity_roadmap_id_fkey foreign key (roadmap_id) references career_roadmaps (id) on delete cascade,
  constraint roadmap_activity_user_id_fkey foreign key (user_id) references auth.users (id) on delete cascade
);

create index if not exists roadmap_activity_user_idx on public.roadmap_activity using btree (user_id);
create index if not exists roadmap_activity_roadmap_idx on public.roadmap_activity using btree (roadmap_id);
