-- Defense-in-depth only: app/ingestion/utils/validation.py already rejects
-- any apply_url that isn't a valid http(s) URL before insert/update
-- (basic_field_checks -> _looks_like_url, gated by opportunity_service.py's
-- `if not validation.is_valid: return ... rejected`). This constraint just
-- makes that guarantee hold even for a write that bypasses the ingestion
-- pipeline entirely (a dashboard edit, a future admin tool, a manual
-- correction via the SQL editor).
alter table public.opportunities
  add constraint opportunities_apply_url_scheme_check
  check (apply_url is null or apply_url ~* '^https?://');
