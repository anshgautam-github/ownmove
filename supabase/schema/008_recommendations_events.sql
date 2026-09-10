-- ---------------------------------------------------------------------------
-- Recommendations (cached AI output) and interaction_events (raw signal).
-- Two different shapes, deliberately:
--
--  - recommendations is a materialized "current best guess" — one row per
--    (user, opportunity), overwritten in place via upsert. It's what the
--    "For You" feed reads, so it stays cheap to query and never grows
--    unbounded.
--  - interaction_events is an append-only log of what actually happened. It
--    is the feedback/training signal the recommendation model is scored
--    against, so it is never overwritten or summarized away.
-- ---------------------------------------------------------------------------

create table if not exists public.recommendations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  opportunity_id uuid not null references public.opportunities (id) on delete cascade,
  score numeric(5, 4) not null check (score between 0 and 1),
  reasons jsonb not null default '[]',
  model_version text not null,
  generated_at timestamptz not null default now(),
  unique (user_id, opportunity_id)
);

-- "Top-N for this user, highest score first" is the only query shape that
-- matters for the feed.
create index if not exists recommendations_user_score_idx
  on public.recommendations (user_id, score desc);

create table if not exists public.interaction_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  -- Nullable, ON DELETE SET NULL (not CASCADE): an event log is an audit
  -- trail. If the underlying opportunity is later removed by a curator, the
  -- fact that a user viewed or applied to *something* that day should not
  -- disappear along with it — recommendations, by contrast, are meaningless
  -- without their opportunity and correctly cascade-delete above.
  opportunity_id uuid references public.opportunities (id) on delete set null,
  event_type text not null check (
    event_type in ('view', 'click', 'save', 'unsave', 'apply', 'dismiss')
  ),
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists interaction_events_user_idx
  on public.interaction_events (user_id, created_at desc);

create index if not exists interaction_events_opportunity_idx
  on public.interaction_events (opportunity_id, event_type);
