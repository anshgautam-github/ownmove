-- ---------------------------------------------------------------------------
-- Experiences v2 — two changes made directly on the live table, brought into
-- source control:
--
--  1. `employment_type` renamed to `experience_type` (guarded: no-ops if
--     already renamed, or if this is a fresh database built from the
--     now-corrected 001_profiles.sql, which never had the old name).
--  2. `skills_used text[]` added — skills exercised in that specific role,
--     a finer-grained signal than profiles.current_skills.
-- ---------------------------------------------------------------------------

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'experiences'
      and column_name = 'employment_type'
  ) then
    alter table public.experiences rename column employment_type to experience_type;
  end if;
end $$;

alter table public.experiences
  add column if not exists skills_used text[] not null default '{}';

comment on column public.experiences.skills_used is
  'Skills exercised in this specific role — a finer-grained signal than '
  'profiles.current_skills, which is unscoped across a person''s whole history.';
