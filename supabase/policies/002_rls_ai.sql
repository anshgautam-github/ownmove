-- ---------------------------------------------------------------------------
-- RLS for the AI-data tables added in schema/004-008.
-- ---------------------------------------------------------------------------

-- profile_embeddings / opportunity_embeddings: never read by the client —
-- only the backend (service-role key, which bypasses RLS) generates and
-- consumes these for ANN search. RLS is enabled with *no* policy for
-- `authenticated`, which makes them correctly unreachable from the browser
-- by default-deny, without needing an explicit "deny" rule.
alter table public.profile_embeddings enable row level security;
alter table public.opportunity_embeddings enable row level security;

-- profile_insights: the student should see their own analysis history;
-- only the backend (service-role) ever writes it.
alter table public.profile_insights enable row level security;

drop policy if exists "Users can read their own profile insights" on public.profile_insights;
create policy "Users can read their own profile insights"
  on public.profile_insights for select to authenticated
  using (profile_id = auth.uid());

-- recommendations: same shape — the user reads their own feed, the backend
-- (service-role) writes it.
alter table public.recommendations enable row level security;

drop policy if exists "Users can read their own recommendations" on public.recommendations;
create policy "Users can read their own recommendations"
  on public.recommendations for select to authenticated
  using (user_id = auth.uid());

-- interaction_events: the client may log its own lightweight events (e.g. a
-- card view) directly, but may never read the log back or edit/delete it —
-- an event log the actor can rewrite is not evidence of anything. Deletion
-- still happens naturally via the user_id cascade if the account is removed.
alter table public.interaction_events enable row level security;

drop policy if exists "Users can log their own events" on public.interaction_events;
create policy "Users can log their own events"
  on public.interaction_events for insert to authenticated
  with check (user_id = auth.uid());
