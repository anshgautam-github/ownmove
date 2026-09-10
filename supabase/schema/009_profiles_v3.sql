-- ---------------------------------------------------------------------------
-- Profiles v3 — two changes made directly on the live table, brought into
-- source control:
--
--  1. `projects_worked` removed. Project count turned out not to be a useful
--     enough signal on its own to keep collecting.
--  2. `profile_summary` renamed to `ai_profile_summary`, so its name makes
--     the same claim as `profile_score` and `last_profile_analysis` do:
--     this column is written by the backend's AI analysis job, never by the
--     client. (Plain `profile_summary` reads like something a user fills in.)
--
-- Both statements are safe to run whether or not this environment ever had
-- the old shape — `drop column if exists` no-ops if already gone, and the
-- guarded rename below no-ops if `profile_summary` doesn't exist (either
-- because it was already renamed, or because this is a fresh database built
-- from the now-corrected 001_profiles.sql, which never had the old name).
-- ---------------------------------------------------------------------------

alter table public.profiles
  drop column if exists projects_worked;

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public'
      and table_name = 'profiles'
      and column_name = 'profile_summary'
  ) then
    alter table public.profiles rename column profile_summary to ai_profile_summary;
  end if;
end $$;

comment on column public.profiles.ai_profile_summary is
  'Written by the backend AI profile-analysis job. Never set by the client — '
  'see profile_score and last_profile_analysis, which follow the same rule.';
