-- ---------------------------------------------------------------------------
-- Opportunities -- brings the live table's real column name into source
-- control.
--
-- `005_opportunities_v2.sql` added a column it named `external_id`. At some
-- point after that file was written, the column was renamed directly on the
-- live table to `source_id` -- the same "changed on the live table, never
-- captured as a migration" situation `010_opportunities_v3.sql` documents
-- for `eligible_years`/`duration`, and `002_opportunities.sql`'s own
-- "UPDATE" note calls out. Nothing in `backend/app/ingestion` ever ran
-- against a database missing this rename (no source agent existed until
-- the Devpost one this migration ships alongside), so it went unnoticed
-- until then.
--
-- Written to be safe to run against either shape:
--   - a live/production database that already has `source_id` (rename is a
--     no-op there -- the `if exists`/`if not exists` guards make every
--     statement below idempotent)
--   - a fresh environment bootstrapped from `001..024` in order, which
--     still creates `external_id` per `005_opportunities_v2.sql` as written
-- ---------------------------------------------------------------------------

do $$
begin
  if exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'opportunities' and column_name = 'external_id'
  ) and not exists (
    select 1 from information_schema.columns
    where table_schema = 'public' and table_name = 'opportunities' and column_name = 'source_id'
  ) then
    alter table public.opportunities rename column external_id to source_id;
  end if;
end $$;

-- Belt-and-suspenders: if a fresh bootstrap somehow ends up with neither
-- column (e.g. this file is ever run against a table created without
-- 005 at all), add it directly rather than silently no-op-ing.
alter table public.opportunities
  add column if not exists source_id text;

comment on column public.opportunities.source_id is
  'Stable ID from the source system (e.g. a Devpost hackathon numeric id). '
  'Paired with source, this is the real de-dupe key for automated ingestion '
  '-- matching on (title, organization) breaks on near-duplicate titles. '
  'Named source_id on the live table; named external_id only in this '
  'repo''s pre-2026-09 history (005_opportunities_v2.sql) before this '
  'migration reconciled the two.';

-- Rename the supporting unique index to match, rather than leaving an index
-- named after a column that no longer exists by that name.
drop index if exists public.opportunities_source_external_idx;

create unique index if not exists opportunities_source_source_id_unique
  on public.opportunities (source, source_id)
  where source is not null and source_id is not null;
