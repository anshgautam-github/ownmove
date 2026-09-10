-- ---------------------------------------------------------------------------
-- Opportunities v3 — two columns added directly on the live table, brought
-- into source control. Both are additive and safe to run against a table
-- that already has them (`add column if not exists`).
-- ---------------------------------------------------------------------------

alter table public.opportunities
  add column if not exists eligible_years integer[] default '{}',
  add column if not exists duration text;

comment on column public.opportunities.eligible_years is
  'Graduation years this listing is open to (e.g. {2026,2027}) — matched '
  'against profiles.graduation_year for eligibility filtering/recommendation. '
  'Empty array means "no year restriction stated", not "nobody is eligible".';
comment on column public.opportunities.duration is
  'Free text ("6 weeks", "Summer 2026", "48 hours") — durations across '
  'categories (internship vs. hackathon vs. program) don''t share a unit, so '
  'a single numeric column would force a bad common denominator.';

-- Eligibility filtering by graduation year.
create index if not exists opportunities_eligible_years_gin_idx
  on public.opportunities using gin (eligible_years);
