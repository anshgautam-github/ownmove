-- ---------------------------------------------------------------------------
-- RLS for career_roadmaps and roadmap_activity.
--
-- Same ownership pattern as profile_analysis (policies/004): written by the
-- backend ON BEHALF OF the requesting user, using that user's own JWT (see
-- career_roadmap/services/repository.py) — never the service-role key.
--
-- career_roadmaps additionally needs an UPDATE policy that profile_analysis
-- doesn't: regenerating a roadmap upserts the user's single existing row
-- (`unique(user_id)`) rather than inserting new history, so both the
-- insert and update paths of that upsert must be allowed.
-- ---------------------------------------------------------------------------

alter table public.career_roadmaps enable row level security;

drop policy if exists "Users can read their own roadmap" on public.career_roadmaps;
create policy "Users can read their own roadmap"
  on public.career_roadmaps for select to authenticated
  using (user_id = auth.uid());

drop policy if exists "Users can create their own roadmap" on public.career_roadmaps;
create policy "Users can create their own roadmap"
  on public.career_roadmaps for insert to authenticated
  with check (user_id = auth.uid());

drop policy if exists "Users can update their own roadmap" on public.career_roadmaps;
create policy "Users can update their own roadmap"
  on public.career_roadmaps for update to authenticated
  using (user_id = auth.uid())
  with check (user_id = auth.uid());

-- No delete policy: a roadmap is replaced via regenerate (update), never
-- deleted, from the current feature surface.

alter table public.roadmap_activity enable row level security;

drop policy if exists "Users can read their own roadmap activity" on public.roadmap_activity;
create policy "Users can read their own roadmap activity"
  on public.roadmap_activity for select to authenticated
  using (user_id = auth.uid());

drop policy if exists "Users can create their own roadmap activity" on public.roadmap_activity;
create policy "Users can create their own roadmap activity"
  on public.roadmap_activity for insert to authenticated
  with check (user_id = auth.uid());

-- No update/delete policy: activity entries are immutable log lines once written.
