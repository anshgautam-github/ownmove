-- ---------------------------------------------------------------------------
-- Opportunities v2 — ingestion-safe identity and server-side keyword search.
-- Semantic (vector) search is handled by the dedicated opportunity_embeddings
-- table in 006, not by a column here.
--
-- This file originally also added an `eligibility_tags text[]` column for
-- structured eligibility signal. That was never applied to the live table —
-- a real `eligible_years integer[]` column was added there directly instead
-- (see schema/010_opportunities_v3.sql), which is a better fit for the
-- actual signal (specific graduation years) than free-text tags would have
-- been. Removed here rather than left as dead, never-run SQL.
-- ---------------------------------------------------------------------------

alter table public.opportunities
  add column if not exists source text not null default 'manual',
  add column if not exists external_id text;

comment on column public.opportunities.source is
  'Where the row came from: manual, or a scraper/partner-feed identifier. '
  'Lets an ingestion job know how to re-sync a given row.';
comment on column public.opportunities.external_id is
  'Stable ID from the source system. Paired with source, this is the real '
  'de-dupe key for automated ingestion — matching on (title, organization), '
  'as the seed file currently does, breaks on near-duplicate titles.';

-- Only enforced for rows that actually came from an automated source —
-- manual rows (source = 'manual', external_id null) never collide.
create unique index if not exists opportunities_source_external_idx
  on public.opportunities (source, external_id)
  where external_id is not null;

-- Tag filtering — the Discover category+tag matching and the client-side
-- "for you" fallback both filter on this array.
create index if not exists opportunities_tags_gin_idx
  on public.opportunities using gin (tags);

-- Server-side keyword search, backing the search box already in Discover
-- (currently client-side only, so it can only search what's already loaded).
-- Generated + stored so it's always in sync and indexable.
alter table public.opportunities
  add column if not exists search_vector tsvector
  generated always as (
    setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('english', coalesce(organization, '')), 'B') ||
    setweight(to_tsvector('english', coalesce(description, '')), 'C')
  ) stored;

create index if not exists opportunities_search_vector_idx
  on public.opportunities using gin (search_vector);
