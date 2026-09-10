-- ---------------------------------------------------------------------------
-- AI profile analysis output — kept out of `profiles` on purpose. profiles is
-- transactional and user-edited; re-running analysis should never compete for
-- that row's lock. It's also a history table, not a single overwritten row:
-- a student's "strengths/gaps" from three months ago is a legitimate
-- progress signal, not junk to discard on the next analysis run.
-- ---------------------------------------------------------------------------

create table if not exists public.profile_insights (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles (id) on delete cascade,
  completion_score smallint not null check (completion_score between 0 and 100),
  strengths jsonb not null default '[]',
  gaps jsonb not null default '[]',
  recommended_focus_areas text[] not null default '{}',
  summary text,
  model_version text not null,
  generated_at timestamptz not null default now()
);

-- The only read pattern is "this profile's latest analysis"; history is kept
-- for trend views but is never scanned in full on a hot path.
create index if not exists profile_insights_latest_idx
  on public.profile_insights (profile_id, generated_at desc);
