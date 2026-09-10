-- ---------------------------------------------------------------------------
-- Opportunities — ingestion persistence support for
-- `backend/app/ingestion/services/opportunity_service.py`.
--
-- Two independent additions, both additive and safe to run against a table
-- that already has them:
--
--   1. `fingerprint` — a content-based dedupe key (title + organization +
--      apply_url, normalized and hashed — see
--      `app/ingestion/utils/fingerprint.py`). `(source, external_id)`
--      (schema/005_opportunities_v2.sql) already catches "the same source
--      re-scraping the same listing"; it says nothing about two DIFFERENT
--      sources listing the SAME real-world opportunity. `fingerprint`
--      catches that case too.
--
--   2. `enrichment_status` / `enrichment_queued_at` — lets
--      `OpportunityService.mark_for_enrichment()` record that a row is
--      waiting on AI enrichment without a separate queue table. The actual
--      enrichment worker (`app/workers/tasks/opportunity_enrichment.py`) is
--      still a stub — this only adds the column ingestion writes to.
-- ---------------------------------------------------------------------------

alter table public.opportunities
  add column if not exists fingerprint text,
  add column if not exists enrichment_status text not null default 'pending',
  add column if not exists enrichment_queued_at timestamptz;

comment on column public.opportunities.fingerprint is
  'SHA-256 of normalized (title, organization, apply_url) — a content-based '
  'dedupe key independent of source, catching the same real-world '
  'opportunity listed by two different sources. Null for rows ingested '
  'before this column existed or inserted manually without going through '
  'OpportunityService.';
comment on column public.opportunities.enrichment_status is
  'pending | in_progress | completed | skipped | failed. Set by '
  'OpportunityService.mark_for_enrichment(); read/advanced by the (not yet '
  'implemented) AI enrichment worker.';
comment on column public.opportunities.enrichment_queued_at is
  'When this row was last queued for enrichment. Null means never queued.';

alter table public.opportunities
  drop constraint if exists opportunities_enrichment_status_check;

alter table public.opportunities
  add constraint opportunities_enrichment_status_check check (
    enrichment_status in ('pending', 'in_progress', 'completed', 'skipped', 'failed')
  );

-- Partial + unique: only rows that went through OpportunityService (and
-- therefore have a fingerprint) are checked for cross-source duplicates.
-- Manual rows (fingerprint null) never collide with each other.
create unique index if not exists opportunities_fingerprint_idx
  on public.opportunities (fingerprint)
  where fingerprint is not null;

-- Powers "how many opportunities are waiting on enrichment" without a
-- sequential scan.
create index if not exists opportunities_enrichment_status_idx
  on public.opportunities (enrichment_status)
  where enrichment_status <> 'completed';
