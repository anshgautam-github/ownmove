-- profiles.profile_score / ai_profile_summary / last_profile_analysis are
-- documented (see 001_profiles.sql) as backend-written columns, but the
-- existing RLS UPDATE policy (policies/001_rls.sql) is row-level only and
-- doesn't stop the owning user from setting these directly via
-- `PATCH /rest/v1/profiles`. As of this migration, no backend code path
-- actually writes these three columns yet (grepped the whole app/ tree —
-- they're read in prompt-context builders and declared on the Profile
-- model/schema, but nothing calls .update()/.upsert() with them), so this
-- trigger is safe to add now: it can only reject writes, never break an
-- existing one. If a future feature needs the backend itself to set these
-- columns, that write MUST go through get_admin_supabase() (the
-- service-role client) — see app/db/supabase.py — not the user-scoped
-- client every other write in this app correctly uses, or this trigger
-- will silently revert it back to the old value.
create or replace function public.enforce_profile_backend_only_columns()
returns trigger as $$
begin
  if auth.role() <> 'service_role' then
    new.profile_score := old.profile_score;
    new.ai_profile_summary := old.ai_profile_summary;
    new.last_profile_analysis := old.last_profile_analysis;
  end if;
  return new;
end;
$$ language plpgsql security definer;

drop trigger if exists profiles_protect_backend_columns on public.profiles;
create trigger profiles_protect_backend_columns
  before update on public.profiles
  for each row execute function public.enforce_profile_backend_only_columns();
