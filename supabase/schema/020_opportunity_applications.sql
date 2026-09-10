-- ---------------------------------------------------------------------------
-- Applied opportunities
--
-- Same shape as schema/003_saved_opportunities.sql (a pure join table,
-- unique(user_id, opportunity_id) makes marking-applied idempotent), but a
-- separate table rather than a status column on saved_opportunities: saving
-- (bookmarking) and applying are independent actions — a user can apply
-- without ever bookmarking, or bookmark without applying — so they get
-- independent tables rather than one conflating both meanings.
--
-- Marking an opportunity applied is how a user hides it from their Discover
-- lists (see frontend/src/services/supabase/opportunityApplications.js) —
-- this table is the durable record of that, not just client-side state.
-- ---------------------------------------------------------------------------

create table if not exists public.opportunity_applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  opportunity_id uuid not null references public.opportunities (id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, opportunity_id)
);

-- Backs "which opportunity ids has this user applied to" — the query
-- Discover runs on every load to filter its lists.
create index if not exists opportunity_applications_user_idx
  on public.opportunity_applications (user_id, created_at desc);
