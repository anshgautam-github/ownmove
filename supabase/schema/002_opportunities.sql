-- ---------------------------------------------------------------------------
-- Opportunities
--
-- Backs every Discover category. "For You" and "All" are computed views over
-- this same table, not separate categories.
--
-- UPDATE: `eligible_years` and `duration` were added directly on the live
-- table (never in source control) and are folded into this baseline —
-- see schema/010_opportunities_v3.sql, which carries them forward for any
-- environment still on the older shape.
-- ---------------------------------------------------------------------------

create table if not exists public.opportunities (
  id uuid primary key default gen_random_uuid(),
  category text not null,
  title text not null,
  organization text,
  logo_url text,
  description text,
  location text,
  is_remote boolean not null default false,
  apply_url text,
  tags text[] not null default '{}',
  application_deadline date,
  posted_at timestamptz not null default now(),
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  -- Graduation years this listing is open to (e.g. {2026,2027}) — matched
  -- against profiles.graduation_year for eligibility filtering/recommendation.
  -- Empty array means "no year restriction stated", not "nobody's eligible".
  eligible_years integer[] default '{}',
  -- Free text on purpose ("6 weeks", "Summer 2026", "48 hours") — durations
  -- across categories (internship vs. hackathon vs. program) don't share a
  -- unit, so a single numeric column would force a bad common denominator.
  duration text
);

-- Kept as a named constraint (rather than inline) so new categories can be
-- added by dropping + recreating just this one object.
alter table public.opportunities
  drop constraint if exists opportunities_category_check;

alter table public.opportunities
  add constraint opportunities_category_check check (
    category in (
      'internships',
      'programs',
      'hackathons',
      'open-source',
      'certifications',
      'challenges',
      'communities',
      'events'
    )
  );

-- Safe to re-run against a table created before this column existed.
alter table public.opportunities add column if not exists logo_url text;

-- Matches the Discover query exactly: filter by category + active, newest first.
create index if not exists opportunities_category_active_idx
  on public.opportunities (category, is_active, posted_at desc);
