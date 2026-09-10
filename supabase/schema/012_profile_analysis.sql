-- ---------------------------------------------------------------------------
-- Profile analysis — AI-generated career intelligence output.
--
-- Append-only history, same shape as profile_insights (007): every run of
-- the Profile Analysis feature inserts a new row rather than overwriting the
-- last one, so a student's progress over time is a real, queryable signal,
-- not something overwritten the next time they click "Re-analyze". The
-- backend always reads "latest" as `order by created_at desc limit 1`.
--
-- Each major section is its own jsonb column (career_dna, recruiter_view,
-- missing_signals, opportunity_readiness, growth_simulation, evidence_scores,
-- highest_roi_recommendation) rather than one big blob, so a future
-- migration can query or index into a single section without touching the
-- others, and the frontend cards map 1:1 onto columns.
-- ---------------------------------------------------------------------------

create table if not exists public.profile_analysis (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles (id) on delete cascade,
  overall_score integer,
  career_dna jsonb,
  recruiter_view jsonb,
  missing_signals jsonb,
  opportunity_readiness jsonb,
  growth_simulation jsonb,
  evidence_scores jsonb,
  highest_roi_recommendation jsonb,
  -- Which model produced this row, and which prompt/schema version — so a
  -- future model swap doesn't corrupt the ability to compare old vs. new
  -- analyses, and a bad prompt version can be identified and excluded.
  ai_model text,
  analysis_version integer default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

-- "This profile's latest analysis" is the only read pattern that matters on
-- a hot path (dashboard load); history browsing is a secondary, cold path.
create index if not exists profile_analysis_profile_created_idx
  on public.profile_analysis (profile_id, created_at desc);
