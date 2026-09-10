-- ---------------------------------------------------------------------------
-- Saved opportunities (bookmarks)
--
-- Pure join table — no duplicated opportunity data, so curated listings can be
-- edited or removed centrally without orphaning or staling a user's saves.
-- The unique constraint is what makes "save" idempotent: a duplicate insert
-- returns 23505, which the client treats as already-saved rather than an error.
-- ---------------------------------------------------------------------------

create table if not exists public.saved_opportunities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  opportunity_id uuid not null references public.opportunities (id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_id, opportunity_id)
);

-- The Saved page lists a single user's rows, newest first.
create index if not exists saved_opportunities_user_idx
  on public.saved_opportunities (user_id, created_at desc);
