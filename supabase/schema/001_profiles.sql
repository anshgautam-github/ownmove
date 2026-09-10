-- ---------------------------------------------------------------------------
-- Profiles & experiences
--
-- One profile per Supabase auth user (profiles.id IS auth.users.id), which is
-- what makes the RLS policies below a simple `id = auth.uid()` check.
--
-- UPDATE: this file originally shipped as a reconstruction (see git history)
-- because the real DDL was never committed. It has since been corrected
-- against the live table's actual definition twice:
--
--  1. Columns added directly in the Supabase dashboard and never in source
--     control (full_name, email, profile_photo, headline, bio, city,
--     country, profile_score, onboarding_completed, last_profile_analysis,
--     target_role, target_company, graduation_status, resume_url), plus one
--     naming fix (github_username -> github_url, matching the real column).
--  2. `projects_worked` was removed and `profile_summary` was renamed to
--     `ai_profile_summary` — see schema/009_profiles_v3.sql, which carries
--     both changes forward for any environment still on the older shape.
--
-- `experiences.employment_type` was similarly renamed to `experience_type`,
-- and `skills_used` was added — see schema/011_experiences_v2.sql.
-- ---------------------------------------------------------------------------

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,

  -- identity
  full_name text,
  email text,
  profile_photo text,
  headline text,
  bio text,
  city text,
  country text,

  -- education
  college_name text,
  education_level text,
  degree text,
  branch text,
  major text,
  graduation_year integer,
  graduation_status text,

  -- career signal (feeds recommendations)
  career_interests text[] not null default '{}',
  current_skills text[] not null default '{}',
  target_role text,
  target_company text,
  github_url text,
  linkedin_url text,
  resume_url text,

  -- AI-derived (written by the backend, never by the client — see
  -- policies/001_rls.sql, which does not grant authenticated users update
  -- access to these columns' intent even though Postgres has no per-column
  -- RLS; the backend is expected to be the only writer)
  profile_score integer default 0,
  ai_profile_summary text,
  last_profile_analysis timestamptz,

  -- bookkeeping
  auth_provider text,
  onboarding_completed boolean not null default false,
  submitted_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.experiences (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references public.profiles (id) on delete cascade,
  title text,
  company text,
  experience_type text,
  location text,
  start_date date,
  end_date date,
  currently_working boolean not null default false,
  description text,
  created_at timestamptz not null default now(),
  -- Skills exercised in this specific role — a finer-grained signal than
  -- profiles.current_skills, which is unscoped across a person's whole
  -- history. Feeds richer embeddings/recommendations once the AI layer
  -- reads experiences, not just the top-level profile.
  skills_used text[] not null default '{}'
);

-- Experiences are always fetched by owner.
create index if not exists experiences_profile_idx
  on public.experiences (profile_id);
